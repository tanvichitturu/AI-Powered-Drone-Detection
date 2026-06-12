from predictor import PredictionAgent
from dataset import simulate_drone

agent = PredictionAgent()

# Simulate histories of multiple drones
detections = {
    1: simulate_drone(n_points=50)[:20].tolist(),
    2: simulate_drone(n_points=50)[:20].tolist(),
    3: simulate_drone(n_points=10)[:10].tolist(),  # not enough history
}

results = agent.predict_all(detections)

for result in results:
    print(f"\nDrone {result['drone_id']}:")
    print(f"  Position: {[round(p, 2) for p in result['current_position']]}")
    print(f"  Speed: {result['speed']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Next step: {[round(p, 2) for p in result['predicted_trajectory'][0]]}")