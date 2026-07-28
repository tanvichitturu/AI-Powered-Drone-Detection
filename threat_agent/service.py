import sys
import json
import time
import collections
from pathlib import Path

import yaml
import paho.mqtt.client as mqtt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(Path(__file__).parent))

from threat_assessment import ThreatAssessmentAgent
from prediction_agent.predictor import PredictionAgent

CONFIG_PATH = Path(__file__).parent / "config.yaml"
try:
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
except FileNotFoundError:
    print(f"[FATAL] config.yaml not found at {CONFIG_PATH}")
    sys.exit(1)

BROKER = cfg.get("mqtt", {}).get("broker", "localhost")
PORT = cfg.get("mqtt", {}).get("port", 1883)
SUBSCRIBE_TOPIC = cfg.get("mqtt", {}).get("subscribe_topic", "drone/raw_telemetry")
PUBLISH_TOPIC = cfg.get("mqtt", {}).get("publish_topic", "drone/threat_alerts")

HISTORY_LENGTH = cfg.get("prediction", {}).get("history_length", 20)
ta_cfg = cfg.get("threat_assessment", {})
STALE_TIMEOUT_SECONDS = ta_cfg.get("stale_timeout_seconds", 5.0)

print("[THREAT ASSESSMENT] Loading PredictionAgent...")
predictor = PredictionAgent()

threat_agent = ThreatAssessmentAgent(
    restricted_zone_center=ta_cfg.get("restricted_zone_center", [0.0, 0.0, 0.0]),
    restricted_zone_radius=ta_cfg.get("restricted_zone_radius", 120.0),
    warning_zone_radius=ta_cfg.get("warning_zone_radius", 250.0),
    protected_assets=ta_cfg.get("protected_assets", []),
)

drone_histories = collections.defaultdict(list)
latest_predictions = {}
last_seen = {}
_messages_received = 0
_batches_published = 0
_schema_warned = False

PUBLISH_INTERVAL_SECONDS = 0.0
_last_publish_time = 0.0


def _prune_stale_drones():
    now = time.time()
    stale_ids = [did for did, ts in last_seen.items() if now - ts > STALE_TIMEOUT_SECONDS]
    for did in stale_ids:
        latest_predictions.pop(did, None)
        last_seen.pop(did, None)
        drone_histories.pop(did, None)
    return stale_ids


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[THREAT ASSESSMENT] Connected. Subscribing to '{SUBSCRIBE_TOPIC}'.")
        client.subscribe(SUBSCRIBE_TOPIC)
    else:
        print(f"[ERROR] MQTT connect failed: {reason_code}")


def on_message(client, userdata, msg):
    global _messages_received, _batches_published, _schema_warned, _last_publish_time
    _messages_received += 1

    try:
        payload = json.loads(msg.payload.decode())

        # Flexible key extraction for drone_id and position
        drone_id = payload.get("drone_id") or payload.get("id") or payload.get("track_id")
        position = payload.get("current_position") or payload.get("position") or payload.get("coords") or payload.get("pos")

        if drone_id is None or position is None:
            if not _schema_warned:
                print(f"[SCHEMA WARN] Message on '{SUBSCRIBE_TOPIC}' missing drone_id/position. Keys found: {list(payload.keys())}")
                _schema_warned = True
            return

        last_seen[drone_id] = time.time()
        drone_histories[drone_id].append(position)

        if len(drone_histories[drone_id]) > HISTORY_LENGTH:
            drone_histories[drone_id].pop(0)

        # Pad history if fewer than 20 frames exist so prediction can run immediately
        padded_history = drone_histories[drone_id]
        if len(padded_history) < HISTORY_LENGTH:
            padded_history = [drone_histories[drone_id][0]] * (HISTORY_LENGTH - len(drone_histories[drone_id])) + drone_histories[drone_id]

        prediction = predictor.predict(drone_id, padded_history)
        latest_predictions[drone_id] = prediction

        _prune_stale_drones()

        # Publish alerts periodically
        current_time = time.time()
        if latest_predictions and (current_time - _last_publish_time >= PUBLISH_INTERVAL_SECONDS):
            alerts = threat_agent.assess_all(list(latest_predictions.values()))
            
            # Ensure output is JSON serializable
            if hasattr(alerts, "to_dict"):
                alerts = alerts.to_dict()

            client.publish(PUBLISH_TOPIC, json.dumps(alerts, default=str).encode("utf-8"))
            _batches_published += 1
            _last_publish_time = current_time

        if _messages_received % 100 == 0:
            print(
                f"[THREAT ASSESSMENT] Heartbeat: {_messages_received} messages received, "
                f"{_batches_published} alert batches published, "
                f"{len(latest_predictions)} active drone track(s)."
            )
    except Exception as e:
        print(f"[ERROR] Threat assessment failure: {e}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()