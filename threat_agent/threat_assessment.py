import math
from typing import Dict, List, Optional


class ThreatAssessmentAgent:
    """
    Threat Assessment Agent for the drone-defense pipeline.

    It receives Prediction Agent output and produces Coordinator-compatible
    alerts with drone_id, threat_level, risk_score, reason, position, speed,
    trajectory, and confidence.
    """

    def __init__(
        self,
        restricted_zone_center: Optional[List[float]] = None,
        restricted_zone_radius: float = 120.0,
        warning_zone_radius: float = 250.0,
        protected_assets: Optional[List[Dict]] = None,
    ):
        self.restricted_zone_center = restricted_zone_center or [0.0, 0.0, 0.0]
        self.restricted_zone_radius = restricted_zone_radius
        self.warning_zone_radius = warning_zone_radius
        self.protected_assets = protected_assets or []

    def assess(self, prediction: Dict, nearby_drone_count: int = 1) -> Dict:
        drone_id = prediction["drone_id"]
        current_position = prediction["current_position"]
        speed = float(prediction.get("speed", 0.0))
        predicted_trajectory = prediction.get("predicted_trajectory", [])
        confidence = float(prediction.get("confidence", 1.0))

        score = 0.0
        reasons = []

        zone_distance = self._distance(current_position, self.restricted_zone_center)
        if zone_distance <= self.restricted_zone_radius:
            score += 35
            reasons.append("inside restricted zone")
        elif zone_distance <= self.warning_zone_radius:
            score += 18
            reasons.append("approaching restricted zone")

        if speed >= 12:
            score += 18
            reasons.append("high speed movement")
        elif speed >= 6:
            score += 8
            reasons.append("moderate speed movement")

        if self._trajectory_enters_zone(predicted_trajectory):
            score += 22
            reasons.append("predicted trajectory enters restricted zone")

        asset_reason, asset_score = self._asset_risk(current_position)
        if asset_reason:
            score += asset_score
            reasons.append(asset_reason)

        if nearby_drone_count >= 3:
            score += 15
            reasons.append("possible swarm activity")

        score = min(round(score * max(0.4, min(confidence, 1.0)), 2), 100.0)
        threat_level = self._level(score)

        return {
            "drone_id": drone_id,
            "threat_level": threat_level,
            "risk_score": score,
            "reason": ", ".join(reasons) if reasons else "drone detected but no immediate danger",
            "current_position": current_position,
            "speed": round(speed, 2),
            "predicted_trajectory": predicted_trajectory,
            "confidence": confidence,
        }

    def assess_all(self, predictions: List[Dict]) -> List[Dict]:
        nearby_drone_count = len(predictions)
        alerts = [
            self.assess(prediction, nearby_drone_count=nearby_drone_count)
            for prediction in predictions
        ]
        return sorted(alerts, key=lambda alert: alert["risk_score"], reverse=True)

    def _trajectory_enters_zone(self, trajectory: List[List[float]]) -> bool:
        for point in trajectory:
            if self._distance(point, self.restricted_zone_center) <= self.restricted_zone_radius:
                return True
        return False

    def _asset_risk(self, position: List[float]):
        if not self.protected_assets:
            return None, 0

        nearest_asset = min(
            self.protected_assets,
            key=lambda asset: self._distance(position, asset["position"]),
        )
        distance = self._distance(position, nearest_asset["position"])
        criticality = float(nearest_asset.get("criticality", 1.0))

        if distance <= self.restricted_zone_radius:
            return f"near critical asset: {nearest_asset['name']}", 15 * criticality
        return None, 0

    @staticmethod
    def _distance(a: List[float], b: List[float]) -> float:
        dimensions = min(len(a), len(b))
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(dimensions)))

    @staticmethod
    def _level(score: float) -> str:
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        return "low"
