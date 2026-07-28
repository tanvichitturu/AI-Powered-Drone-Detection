## Services

- mosquitto — MQTT broker, all agents talk through this
- detection_agent — publishes drone/raw_detections, serves video stream on :8002
- tracking_agent — subscribes raw_detections, publishes drone/raw_telemetry
- threat_agent — subscribes raw_telemetry, runs prediction_agent in-process, publishes drone/threat_alerts
- coordinator_agent — subscribes threat_alerts, runs FastAPI on :8000 for the frontend
- frontend — React/Vite app served by nginx on :5173

prediction_agent has no standalone service — threat_agent/service.py imports
it directly as a Python module (from prediction_agent.predictor import
PredictionAgent), so it's built into the threat_agent image rather than run
as its own container.

## Setup

1. Copy .env.example to .env and set GROQ_API_KEY
2. docker compose up --build

Frontend: http://localhost:5173
Coordinator API: http://localhost:8000
Detection video feed: http://localhost:8002/video_feed

## Notes

- Each agent's config.yaml/mqtt_subscriber.py hardcodes broker/host as
  "localhost", which only works when everything runs on one machine outside
  Docker. Each Dockerfile patches this at build time to point at the
  mosquitto service name instead, since containers don't share localhost.
- detection_agent falls back to demo_mode automatically since
  weights/yolo_drone_model.pt isn't present in the image. Mount a real model
  file and update config.yaml to enable live inference.
- coordinator_agent runs two processes (api.py + mqtt_subscriber.py) in one
  container via entrypoint.sh, since mqtt_subscriber.py posts to api.py over
  localhost:8000, which only works if they share a network namespace.
