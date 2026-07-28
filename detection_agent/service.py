"""
Detection Agent MQTT service — wraps the REAL DetectionAgent class
(detector.py) with a camera loop and MQTT publish.
Also runs a background FastAPI server on port 8002 to stream the 
annotated MJPEG video feed to the React frontend.
"""
import sys
import time
import json
import threading
from pathlib import Path

import yaml
import paho.mqtt.client as mqtt

# FastAPI components for video streaming
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure OpenCV is available
try:
    import cv2
except ImportError as err:
    print(f"[ERROR] OpenCV (cv2) import failed: {err}")
    cv2 = None

sys.path.append(str(Path(__file__).parent))
from detector import DetectionAgent

# ==========================================================
# 1. VIDEO STREAMING SERVER SETUP (Runs in background thread)
# ==========================================================
latest_frame = None

import math
import numpy as np
from datetime import datetime

stream_app = FastAPI(title="Detection Video Stream")

# Allow React to fetch the video stream without CORS errors
stream_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_synthetic_demo_frame(frame_id: int) -> np.ndarray:
    """Generates a rich, realistic tactical video frame with sky, terrain, HUD grid."""
    height, width = 720, 1280
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 1. Gradient Sky (Dusk / Tactical Night Sky)
    for y in range(480):
        ratio = y / 480.0
        r = int(12 + ratio * 20)
        g = int(22 + ratio * 35)
        b = int(45 + ratio * 45)
        frame[y, :] = (b, g, r)  # BGR
        
    # 2. Ground / Terrain (Dark slate/olive ground from y=480 to 720)
    for y in range(480, 720):
        ratio = (y - 480) / 240.0
        r = int(18 + ratio * 15)
        g = int(32 + ratio * 20)
        b = int(28 + ratio * 15)
        frame[y, :] = (b, g, r)
        
    # Horizon line
    cv2.line(frame, (0, 480), (width, 480), (70, 95, 70), 1)
    
    # Perspective Grid lines on ground
    for x_offset in range(-200, width + 400, 120):
        cv2.line(frame, (width // 2, 480), (x_offset, 720), (45, 65, 45), 1)
    for h_y in [520, 565, 620, 685]:
        cv2.line(frame, (0, h_y), (width, h_y), (40, 55, 40), 1)
        
    # Tactical HUD Overlay (compass tape at top)
    cv2.line(frame, (200, 30), (1080, 30), (0, 200, 0), 1)
    for deg in range(0, 360, 15):
        pos_x = int(640 + (deg - (frame_id * 2) % 360) * 5)
        if 200 <= pos_x <= 1080:
            cv2.line(frame, (pos_x, 30), (pos_x, 38), (0, 200, 0), 1)
            if deg % 45 == 0:
                dir_label = {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}.get(deg, str(deg))
                cv2.putText(frame, dir_label, (pos_x - 8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 0), 1)
                
    # HUD Telemetry Text
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, f"CAM-01 | TACTICAL SURVEILLANCE | {now_str}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(frame, f"FRAME: {frame_id:06d} | FPS: 25.0 | DETECTOR: DEMO ACTIVE", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 200), 1)
    
    return frame

def draw_drone_graphic(frame: np.ndarray, bbox: list, frame_id: int):
    """Draws a detailed quadcopter drone graphic inside/around the bbox coordinates."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    w, h = max(20, x2 - x1), max(20, y2 - y1)
    
    arm_len = max(w, h) // 2
    
    # 4 Arm lines extending to motors
    motor_offsets = [(-arm_len, -arm_len // 2), (arm_len, -arm_len // 2), (-arm_len, arm_len // 2), (arm_len, arm_len // 2)]
    for mx, my in motor_offsets:
        cv2.line(frame, (cx, cy), (cx + mx, cy + my), (80, 80, 80), 3)
        # Motor housing
        cv2.circle(frame, (cx + mx, cy + my), 5, (40, 40, 40), -1)
        # Spinning rotor disk animation
        rotor_r = max(8, arm_len // 2 + int(math.sin(frame_id * 0.8) * 2))
        cv2.circle(frame, (cx + mx, cy + my), rotor_r, (180, 180, 180), 1)
        # Rotor blade line rotation
        angle = (frame_id * 35) % 360
        rad = math.radians(angle)
        rx = int(rotor_r * math.cos(rad))
        ry = int(rotor_r * math.sin(rad))
        cv2.line(frame, (cx + mx - rx, cy + my - ry), (cx + mx + rx, cy + my + ry), (220, 220, 220), 1)
        
    # Drone Central Chassis Body (Dark metallic ellipse)
    cv2.ellipse(frame, (cx, cy), (max(6, w // 4), max(4, h // 3)), 0, 0, 360, (50, 50, 50), -1)
    cv2.ellipse(frame, (cx, cy), (max(6, w // 4), max(4, h // 3)), 0, 0, 360, (140, 140, 140), 2)
    
    # Glowing Red Strobe LED at center
    strobe_on = (frame_id % 10) < 5
    led_color = (0, 0, 255) if strobe_on else (0, 0, 100)
    cv2.circle(frame, (cx, cy), 4, led_color, -1)

def generate_frames():
    global latest_frame
    while True:
        if latest_frame is None:
            time.sleep(0.05)
            continue
        
        # Encode the frame as a JPEG
        ret, buffer = cv2.imencode('.jpg', latest_frame)
        if ret:
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Cap stream at ~25 FPS to prevent CPU spin and TCP socket buffer flooding
        time.sleep(0.04)

@stream_app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

def run_stream_server():
    # Run on port 8002 so it doesn't conflict with Coordinator API on 8000
    uvicorn.run(stream_app, host="0.0.0.0", port=8002, log_level="warning")


# ==========================================================
# 2. CONFIG & MQTT SETUP
# ==========================================================
CONFIG_PATH = Path(__file__).parent / "config.yaml"
try:
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
except FileNotFoundError:
    print(f"[FATAL] config.yaml not found at {CONFIG_PATH}")
    sys.exit(1)

BROKER = cfg.get("mqtt", {}).get("broker", "localhost")
PORT = cfg.get("mqtt", {}).get("port", 1883)
PUBLISH_TOPIC = cfg.get("mqtt", {}).get("publish_topic", "drone/raw_detections")

det_cfg = cfg.get("detection", {})
MODEL_PATH = det_cfg.get("model_path")

if MODEL_PATH:
    full_model_path = Path(__file__).parent / MODEL_PATH
    if not full_model_path.exists():
        print(f"\n[WARNING] YOLO AI model not found at: {full_model_path}")
        print("[WARNING] Automatically falling back to simulated Demo Mode for now...\n")
        MODEL_PATH = None

CONF_THRESHOLD = det_cfg.get("confidence_threshold", 0.45)
CAMERA_ID = det_cfg.get("camera_id", "camera-01")
SOURCE = det_cfg.get("source", 0)
TARGET_FPS = det_cfg.get("target_fps", 30)

if isinstance(SOURCE, str) and SOURCE.isdigit():
    SOURCE = int(SOURCE)


# ==========================================================
# 3. MAIN AGENT LOOP
# ==========================================================
def main():
    # Boot up the video streaming server in the background
    threading.Thread(target=run_stream_server, daemon=True).start()

    agent = DetectionAgent(model_path=MODEL_PATH, confidence_threshold=CONF_THRESHOLD)

    if agent.demo_mode:
        print("[DETECTION AGENT] Running in demo_mode (no camera needed).")
        cap = None
    else:
        cap = cv2.VideoCapture(SOURCE)
        if not cap.isOpened():
            print(f"[FATAL] Could not open video source: {SOURCE}")
            sys.exit(1)
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        print(f"[DETECTION AGENT] Loaded model: {MODEL_PATH}. Streaming from source={SOURCE}.")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(c, u, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[DETECTION AGENT] Connected. Will publish to '{PUBLISH_TOPIC}'.")
        else:
            print(f"[ERROR] MQTT connect failed: {reason_code}")

    client.on_connect = on_connect
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    global TARGET_FPS
    if agent.demo_mode:
        TARGET_FPS = 25

    frame_interval = 1.0 / TARGET_FPS if TARGET_FPS > 0 else 0
    frame_id = 0
    total_detections_published = 0

    print("[DETECTION AGENT] Running silently. Video stream available at http://localhost:8002/video_feed")
    
    try:
        while True:
            t0 = time.time()
            frame = None

            if cap is not None:
                ret, frame = cap.read()
                if not ret:
                    print("[DETECTION AGENT] Source ended or read failed.")
                    break
            else:
                frame = generate_synthetic_demo_frame(frame_id)

            # 1. Run YOLO inference
            detections = agent.detect(frame=frame, frame_id=frame_id, camera_id=CAMERA_ID)
            
            # 2. Publish coordinates to MQTT (Coordinator & Tracking)
            client.publish(PUBLISH_TOPIC, json.dumps({"detections": detections}).encode("utf-8"))
            
            total_detections_published += len(detections)
            frame_id += 1

            # 3. Draw drone graphic, bounding boxes and pass frame to Streamer
            global latest_frame
            if frame is not None:
                for idx, det in enumerate(detections):
                    bbox = det.get("bbox", [])
                    conf = det.get("confidence", 0.0)
                    drone_id = det.get("drone_id", idx + 1)
                    
                    if len(bbox) == 4:
                        x1, y1, x2, y2 = [int(v) for v in bbox]
                        
                        # 1. Draw synthetic drone graphic at bbox position in demo mode
                        if agent.demo_mode:
                            draw_drone_graphic(frame, bbox, frame_id + idx * 17)
                            
                        # 2. Draw green bounding box & tactical corner accents
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        corner_len = 10
                        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), (0, 255, 0), 3)
                        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), (0, 255, 0), 3)
                        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), (0, 255, 0), 3)
                        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), (0, 255, 0), 3)
                        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), (0, 255, 0), 3)
                        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), (0, 255, 0), 3)
                        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), (0, 255, 0), 3)
                        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), (0, 255, 0), 3)
                        
                        # 3. Target ID & confidence label
                        label = f"DRONE-0{drone_id}: {conf:.2f}"
                        (w_lbl, h_lbl), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                        cv2.rectangle(frame, (x1, y1 - h_lbl - 8), (x1 + w_lbl + 6, y1), (0, 255, 0), -1)
                        cv2.putText(frame, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

                # Save frame AFTER all drawing is complete so FastAPI thread encodes the drawn frame
                latest_frame = frame.copy()

            # Heartbeat logging
            if frame_id % 100 == 0:
                print(
                    f"[DETECTION AGENT] Heartbeat: {frame_id} ticks, "
                    f"{total_detections_published} detections published total."
                )

            # Enforce target FPS
            if frame_interval:
                elapsed = time.time() - t0
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)

    except KeyboardInterrupt:
        print("\n[DETECTION AGENT] Stopped by user.")
    finally:
        if cap is not None:
            cap.release()
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()