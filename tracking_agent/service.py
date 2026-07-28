import json
import sys
import yaml
import time
import paho.mqtt.client as mqtt
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from track import DroneTracker
from logger import flight_log

CONFIG_PATH = Path(__file__).parent / "config.yaml"
try:
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
except FileNotFoundError:
    flight_log.critical(f"config.yaml not found at {CONFIG_PATH}")
    print(f"[FATAL] config.yaml not found at {CONFIG_PATH}")
    sys.exit(1)

tracker = DroneTracker(
    frame_rate=cfg["tracker"]["expected_fps"],
    max_history=cfg["tracker"]["max_history_frames"],
    match_thresh=cfg["tracker"]["match_threshold"],
    max_lost=cfg["tracker"]["max_lost_grace_period"],
    bytetrack_high_thresh=cfg.get("bytetrack", {}).get("high_conf_threshold", 0.5),
    bytetrack_match_thresh=cfg.get("bytetrack", {}).get("match_iou_threshold", 0.3),
    bytetrack_low_match_thresh=cfg.get("bytetrack", {}).get("low_conf_match_iou_threshold", 0.5),
)

RAW_DETECTIONS_TOPIC = cfg.get("mqtt", {}).get("subscribe_topic", "drone/raw_detections")
RAW_TELEMETRY_TOPIC = cfg.get("mqtt", {}).get("publish_topic", "drone/raw_telemetry")
_schema_warned = False
_messages_received = 0
_alerts_published = 0

# --- NEW: Outbound Rate Limiting ---
PUBLISH_INTERVAL_SECONDS = 1.0  # Only send 1 update per second to the LLM
_last_published_times = {}      # Tracks the last broadcast time per drone_id
# -----------------------------------

# Confirmed from detection_agent/detector.py's real DetectionAgent.detect()
# return shape - not assumed. It only ever returns "drone"/"uav"/"quadcopter"
# as the "class" string (everything else is filtered out before publish), so
# this maps each to a stable numeric code for track.py's [x,y,x,y,conf,cls]
# array contract. track.py doesn't act on the class code today, so any
# unknown label safely falls back to 0.0 rather than dropping the detection.
DETECTION_CLASS_CODES = {"drone": 0.0, "uav": 1.0, "quadcopter": 2.0}


def _translate_detections(detections):
    """
    Converts real DetectionAgent output:
        [{"bbox": [x1,y1,x2,y2], "confidence": c, "class": "drone", ...}, ...]
    into the numeric [x1,y1,x2,y2,conf,cls] arrays track.py's update()
    already accepts on its non-YOLO-object path.
    """
    boxes = []
    for det in detections:
        bbox = det.get("bbox")
        conf = det.get("confidence")
        if bbox is None or conf is None or len(bbox) != 4:
            continue
        cls_code = DETECTION_CLASS_CODES.get(str(det.get("class", "")).lower(), 0.0)
        boxes.append([float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]), float(conf), cls_code])
    return boxes


def fmt_alerts(track_payload):
    """
    Translates DroneTracker's internal payload into the subset of the
    Coordinator schema that TRACKING is actually responsible for.
    Deliberately omits predicted_trajectory/threat_level/risk_score/reason -
    those are A3's job, not A2's.
    """
    alerts = []
    for t in track_payload:
        cx, cy = t["centroid"]
        alerts.append({
            "drone_id": int(t["track_id"]),
            "current_position": [float(cx), float(cy), 0.0],
            "speed": float(t["speed"]),
            "confidence": float(t["confidence"]),
        })
    return alerts


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[TRACKING SERVICE] Connected. Subscribing to '{RAW_DETECTIONS_TOPIC}'.")
        client.subscribe(RAW_DETECTIONS_TOPIC)
    else:
        print(f"[ERROR] MQTT connect failed: {reason_code}")


def on_message(client, userdata, msg):
    global _schema_warned, _messages_received, _alerts_published, _last_published_times
    try:
        payload = json.loads(msg.payload.decode())

        if "detections" not in payload:
            if not _schema_warned:
                flight_log.warning(
                    f"Message on '{RAW_DETECTIONS_TOPIC}' has no 'detections' "
                    f"key (keys present: {list(payload.keys())})."
                )
                _schema_warned = True
                
        boxes = _translate_detections(payload.get("detections", []))

        # Update tracker with current frame detections
        track_data = tracker.update(boxes, frame=None)

        current_time = time.time()

        if track_data:
            for alert in fmt_alerts(track_data):
                drone_id = alert["drone_id"]
                
                last_time = _last_published_times.get(drone_id, 0.0)
                
                if current_time - last_time >= PUBLISH_INTERVAL_SECONDS:
                    client.publish(RAW_TELEMETRY_TOPIC, json.dumps(alert).encode("utf-8"))
                    _last_published_times[drone_id] = current_time
                    _alerts_published += 1

        _messages_received += 1
        if _messages_received % 100 == 0:
            print(
                f"[TRACKING SERVICE] Heartbeat: {_messages_received} messages "
                f"received, {_alerts_published} telemetry alerts published, "
                f"{len(tracker.active_tracks)} active track(s)."
            )
    except Exception as e:
        flight_log.error(f"Tracking ingestion failure: {e}")
        print(f"[ERROR] Tracking ingestion failure: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

broker = cfg.get("mqtt", {}).get("broker", "localhost")
port = cfg.get("mqtt", {}).get("port", 1883)

client.connect(broker, port, 60)
client.loop_forever()