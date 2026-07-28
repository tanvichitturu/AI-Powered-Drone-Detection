# Detection Agent (A1)

Wraps the REAL `DetectionAgent` class (teammate's `detector.py`) with the
MQTT + camera-loop glue it doesn't have on its own.

```
Camera/video/RTSP (or demo_mode) ──▶ service.py ──▶ drone/raw_detections ──▶ tracking_agent
```

## Run

```bash
pip install -r requirements.txt
python service.py
```

With `detection.model_path: null` in `config.yaml` (the default),
`DetectionAgent` runs in its own real `demo_mode` — no camera, no model,
just a fixed single demo detection published every tick. This is the real
class's own sanctioned test behavior, not something invented here. Set a
real trained model path to switch to actual inference; no other code
changes needed.

## Contract

**Publishes:** `drone/raw_detections`
```json
{"detections": [{"frame_id": 1, "camera_id": "...", "class": "drone", "confidence": 0.91, "bbox": [x1,y1,x2,y2], "center": [cx,cy]}, ...]}
```
This is `DetectionAgent.detect()`'s real return list, published unmodified
inside one envelope key — not translated or reshaped.
`tracking_agent/service.py` has been updated to consume this exact shape.

## What's verified

No `ultralytics`/ `paho-mqtt` in the build sandbox, so full camera-loop
execution wasn't run end-to-end. What IS verified, against the real,
unmodified `detector.py`:
- `DetectionAgent(model_path=None)` correctly enters `demo_mode`.
- `.detect()` returns the exact real output shape this service publishes.

Run for real and report the first error verbatim if anything breaks —
almost certainly a missing `ultralytics`/`opencv` install if using a real
model, or a camera permissions issue if using a live source.
