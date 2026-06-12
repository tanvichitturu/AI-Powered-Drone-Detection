import numpy as np
import torch
import os
from transformer import DroneTransformer
from dataset import compute_social_features

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class PredictionAgent:
    def __init__(self):
        # Load normalization stats
        norm_stats = np.load(os.path.join(BASE_DIR, 'norm_stats_social.npy'))
        self.mean = norm_stats[0]
        self.std = norm_stats[1]
        
        # Load best model — Social Force Transformer
        self.model = DroneTransformer(
            input_size=14,
            d_model=128,
            nhead=4,
            num_layers=3,
            output_steps=10
        )
        self.model.load_state_dict(
            torch.load(os.path.join(BASE_DIR, 'best_social_transformer.pth'),
            map_location='cpu')
        )
        self.model.eval()
    
    def predict(self, drone_id, position_history):
        """
        drone_id: int
        position_history: list of at least 20 [x, y, z] positions
        """
        positions = np.array(position_history)
        
        # Current position
        current_position = positions[-1].tolist()
        
        # Speed from last two positions
        diff = positions[-1] - positions[-2]
        speed = float(np.sqrt(np.sum(diff**2)))
        
        # Compute social features
        features = compute_social_features(positions)
        features_norm = (features - self.mean) / self.std
        input_seq = torch.FloatTensor(features_norm[-20:]).unsqueeze(0)
        
        # Predict
        with torch.no_grad():
            pred_norm = self.model(input_seq).squeeze(0).numpy()
        
        predicted_trajectory = (pred_norm * self.std + self.mean).tolist()
        
        # Confidence — higher speed = less certain
        confidence = round(float(1.0 / (1.0 + speed * 0.1)), 2)
        
        return {
            "drone_id": drone_id,
            "current_position": current_position,
            "speed": round(speed, 2),
            "predicted_trajectory": predicted_trajectory,
            "confidence": confidence
        }
    def predict_all(self, detections):
        results = []
        for drone_id, position_history in detections.items():
            # Need at least 20 positions to predict
            if len(position_history) < 20:
                print(f"Drone {drone_id}: not enough history ({len(position_history)} points), skipping")
                continue
            result = self.predict(drone_id, position_history)
            results.append(result)
        return results