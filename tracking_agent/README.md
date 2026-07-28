# Tracking Agent (A2)

Scope: **tracking only.** This agent does not run detection (A1), does not
predict trajectories (A3), does not score threats, and does not talk to the
Coordinator. It has exactly one job: turn raw detection boxes into tracked,
speed-estimated telemetry, over MQTT.

```
A1 (Detection)          THIS AGENT (A2)             A3 (Prediction)
drone/raw_detections ─▶ service.py ─▶ drone/raw_telemetry ─▶ predictor.py
```

## Run

```bash
pip install -r requirements.txt   # production deps only, no YOLO/matplotlib
python service.py
```

Expected log line on success: `[TRACKING SERVICE] Connected. Subscribing to 'drone/raw_detections'.`

## Contract

**Subscribes:** `drone/raw_detections` (configurable in `config.yaml` under `mqtt.subscribe_topic`)

Expected payload — confirmed against `detection_agent/detector.py`'s real
`DetectionAgent.detect()` return shape, not assumed:
```json
{"detections": [{"frame_id": 1, "camera_id": "ptz-camera-north", "class": "drone", "confidence": 0.91, "bbox": [x1,y1,x2,y2], "center": [cx,cy]}, ...]}
```
`service.py` translates each detection into the `[x1,y1,x2,y2,conf,cls]`
numeric array `track.py` expects internally (`_translate_detections()`) —
`track.py` itself is unchanged and still uses its original, already-tested
numeric-array contract.

**Publishes:** `drone/raw_telemetry` (configurable under `mqtt.publish_topic`)

```json
{"drone_id": 1, "current_position": [x, y, 0.0], "speed": 12.3, "confidence": 0.91}
```

Deliberately does **not** include `predicted_trajectory`, `threat_level`,
`risk_score`, or `reason` — those belong to A3 (Prediction) and whatever
Threat Assessment agent sits after it. Don't add them here even if it seems
convenient; it creates two sources of truth for fields tracking doesn't own.

## Known limitations (accepted tradeoffs, not bugs)

- **Global Motion Compensation is permanently disabled** in production.
  `service.py` calls `tracker.update(boxes, frame=None)` because this agent
  has no camera access post-decoupling — GMC needs real pixel frames to
  compute optical flow. `track.py` logs this once on startup.
- **Track IDs are per-process.** If you ever run `service.py` and
  `dev_tools/video_test.py` against the same broker simultaneously, both
  assign IDs starting from 1 independently — A3 would see colliding
  `drone_id`s from two unrelated sources. Never run both against the same
  broker at once.

## Folder layout

```
tracking_agent/
├── service.py          # PRODUCTION entrypoint — run this
├── track.py            # DroneTracker — pure logic, accepts both YOLO
│                        # Boxes objects AND plain [x,y,x,y,conf,cls] arrays
├── utils.py             # math helpers
├── logger.py             # async logger -> logs/flight_telemetry.log
├── config.yaml
├── requirements.txt      # production deps
├── requirements-dev.txt  # + ultralytics/matplotlib, for dev_tools/ only
└── dev_tools/
    ├── video_test.py               # webcam/video + YOLO, local visual debugging only
    ├── benchmark.py                # latency stress test
    ├── benchmark_visual.py         # latency stress test w/ charts
    ├── mock_detector.py            # fakes A1 — publishes fake raw_detections
    └── verify_prediction_integration.py  # fakes A3's MQTT wrapper (doesn't
                                            # exist yet upstream) by calling
                                            # the real PredictionAgent directly
```

## Testing without A1/A3 built yet

```bash
mosquitto -v
python service.py
python dev_tools/verify_prediction_integration.py   # set PREDICTION_AGENT_DIR first
python dev_tools/mock_detector.py
```

If `verify_prediction_integration.py` prints `PREDICTION OK | speed=... next_point=[...]`,
your tracking output is proven correct against the real trained model —
independent of whether A1 or A3's production wrapper exist yet.

## Open items to confirm with the team (not yet resolved)

- **A1's actual `raw_detections` payload shape** — confirm key name (`boxes`?),
  row format, and pixel vs. normalized coordinates.
- **`predicted_trajectory` length** — original spec said 5 points;
  `predictor.py` (`output_steps=10`) produces 10. Doesn't affect this agent
  directly, but downstream schemas disagree.
- **`threat_level` values** — original spec listed `low|medium|high`;
  `coordinator.py` requires a 4th value, `"critical"`, for its escalation
  path to ever fire. Whoever builds Threat Assessment needs to know this.
