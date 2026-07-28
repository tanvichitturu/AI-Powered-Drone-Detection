# Threat Assessment Agent

Wraps the REAL `ThreatAssessmentAgent` (from teammate's `threat_assessment.py`)
and REAL `PredictionAgent` (from `prediction_agent/predictor.py`) with the
MQTT glue neither file has on its own.

```
drone/raw_telemetry ──▶ service.py ──▶ drone/threat_alerts ──▶ coordinator_agent
  (tracking_agent)       buffers 20/drone,                      (mqtt_subscriber.py)
                          predictor.predict(),
                          threat_agent.assess_all()
```

## Run

```bash
pip install -r requirements.txt   # includes torch — predictor.py needs it
python service.py
```

## Why `assess_all()`, not `assess()` per message

The real `ThreatAssessmentAgent.assess()` takes a `nearby_drone_count`
parameter for swarm detection, defaulting to `1`. Calling it once per
incoming message would always pass `1`, silently disabling swarm detection
regardless of how many drones are actually active. This service instead
maintains `latest_predictions: {drone_id: prediction}` and calls
`assess_all()` on the whole batch every time any drone's prediction
updates — so `nearby_drone_count` reflects reality and output stays
risk-sorted, as the real class intends.

## Staleness pruning

A drone with no new telemetry for `stale_timeout_seconds` (default 5s,
`config.yaml`) is dropped from the batch. Without this, a drone that went
silent (lost tracking, landed, whatever) would stay in every future
`assess_all()` call forever — inflating `nearby_drone_count` and never
leaving the dashboard.

## Publishes a batch, not one alert per message

`{JSON array of Alert dicts}` to `drone/threat_alerts`.
`coordinator_agent/mqtt_subscriber.py` already handles this — confirmed by
reading its actual code: `alerts = payload if isinstance(payload, list) else [payload]`.

## What's verified

No `torch` in the build sandbox, so tested against a fake `predictor.py`
matching the real interface exactly (same input/output shape), combined
with the REAL, unmodified `threat_assessment.py`. Confirmed:
- Path resolution to `prediction_agent/` (2 `.parent` calls from
  `threat_agent/service.py` — one fewer than the tracking-side dev tool,
  which sits one folder deeper).
- Real zone-based scoring fires correctly (`"inside restricted zone,
  predicted trajectory enters restricted zone"`).
- Batch growth to 2 drones produces a correctly risk-sorted 2-item array.
- Staleness pruning actually removes a silent drone from the active batch.

Not yet run against the REAL `predictor.py` (needs `torch` + the actual
`.pth`/`.npy` files) or a real broker. Run for real and report the first
error verbatim if anything breaks.
