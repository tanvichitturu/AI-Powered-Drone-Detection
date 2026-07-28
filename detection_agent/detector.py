import os
from typing import Any, List, Optional


class DetectionAgent:
    """
    Detection Agent for the drone-defense pipeline.

    Input:
        frame: image/frame from camera stream

    Output:
        list of drone detections ready for the Tracking Agent
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        demo_mode: bool = False,
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.demo_mode = demo_mode or model_path is None
        self.model = None

        if not self.demo_mode:
            self.model = self._load_model(model_path)

    def detect(self, frame: Any, frame_id: int = 0, camera_id: str = "camera-01") -> List[dict]:
        if self.demo_mode:
            return self._demo_detection(frame_id, camera_id)

        results = self.model(frame, verbose=False)
        detections = []

        for result in results:
            names = getattr(result, "names", {})
            for box in getattr(result, "boxes", []):
                confidence = float(box.conf[0])
                if confidence < self.confidence_threshold:
                    continue

                class_id = int(box.cls[0])
                label = str(names.get(class_id, class_id)).lower()

                if label not in {"drone", "uav", "quadcopter"}:
                    continue

                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                detections.append(
                    {
                        "frame_id": frame_id,
                        "camera_id": camera_id,
                        "class": label,
                        "confidence": round(confidence, 3),
                        "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                        "center": [round((x1 + x2) / 2, 2), round((y1 + y2) / 2, 2)],
                    }
                )

        return detections

    def _load_model(self, model_path: Optional[str]):
        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"YOLO model not found: {model_path}")

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install ultralytics to run YOLO detection.") from exc

        return YOLO(model_path)

    def _demo_detection(self, frame_id: int, camera_id: str) -> List[dict]:
        import math
        t = frame_id * 0.03
        
        # 4 Independent Drones with distinct trajectories, speeds, altitudes & confidences
        drone_configs = [
            # Drone 1: Fast Recon (High Speed Inbound Arc)
            {
                "id": 1,
                "cx": 640 + math.sin(t * 1.2) * 380 + math.cos(t * 0.4) * 60,
                "cy": 220 + math.cos(t * 0.9) * 100,
                "w": 110 + math.sin(t * 0.4) * 15,
                "h": 65 + math.sin(t * 0.4) * 10,
                "conf": 0.96,
            },
            # Drone 2: Heavy Payload (Slow Low Altitude Approach)
            {
                "id": 2,
                "cx": 420 + math.cos(t * 0.7) * 300,
                "cy": 350 + math.sin(t * 0.5) * 80,
                "w": 125 + math.cos(t * 0.3) * 12,
                "h": 75 + math.cos(t * 0.3) * 8,
                "conf": 0.91,
            },
            # Drone 3: High-Altitude Flanker (Diagonal Fast Sweep)
            {
                "id": 3,
                "cx": 850 + math.sin(t * 0.9 + 2.0) * 280,
                "cy": 160 + math.cos(t * 1.1 + 1.0) * 60,
                "w": 85 + math.sin(t * 0.6) * 10,
                "h": 50 + math.sin(t * 0.6) * 6,
                "conf": 0.88,
            },
            # Drone 4: Perimeter Scout (Loitering Figure-8 Pattern)
            {
                "id": 4,
                "cx": 320 + math.sin(t * 0.6 + 4.0) * 220,
                "cy": 270 + math.cos(t * 0.6 + 1.5) * 90,
                "w": 95 + math.cos(t * 0.5) * 10,
                "h": 55 + math.cos(t * 0.5) * 6,
                "conf": 0.83,
            },
        ]
        
        detections = []
        for cfg in drone_configs:
            cx, cy = cfg["cx"], cfg["cy"]
            w, h = cfg["w"], cfg["h"]
            x1, y1 = cx - w / 2, cy - h / 2
            x2, y2 = cx + w / 2, cy + h / 2
            
            detections.append({
                "frame_id": frame_id,
                "camera_id": camera_id,
                "class": "drone",
                "confidence": cfg["conf"],
                "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                "center": [round(cx, 2), round(cy, 2)],
                "drone_id": cfg["id"],
            })
            
        return detections
