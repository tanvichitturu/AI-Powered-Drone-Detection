from threat_assessment import ThreatAssessmentAgent


agent = ThreatAssessmentAgent(
    restricted_zone_center=[0.0, 0.0, 0.0],
    restricted_zone_radius=100.0,
    warning_zone_radius=250.0,
    protected_assets=[
        {"asset_id": 1, "name": "Command building", "position": [25.0, 20.0, 0.0], "criticality": 1.0}
    ],
)

prediction = {
    "drone_id": 1,
    "current_position": [140.0, 20.0, 30.0],
    "speed": 14.5,
    "predicted_trajectory": [[100.0, 10.0, 25.0], [50.0, 5.0, 20.0], [10.0, 0.0, 15.0]],
    "confidence": 0.9,
}

alert = agent.assess(prediction)

print("Threat Assessment Agent Test")
print("=" * 50)
print(alert)

assert alert["drone_id"] == 1
assert alert["threat_level"] in ["medium", "high", "critical"]
assert "predicted trajectory enters restricted zone" in alert["reason"]
