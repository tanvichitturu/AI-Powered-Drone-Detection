from detector import DetectionAgent


agent = DetectionAgent(demo_mode=True)
detections = agent.detect(frame=None, frame_id=1, camera_id="ptz-camera-north")

print("Detection Agent Test")
print("=" * 50)
print(detections)

assert len(detections) == 1
assert detections[0]["class"] == "drone"
assert detections[0]["confidence"] > 0.35
