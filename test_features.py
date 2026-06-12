from dataset import simulate_drone, compute_social_features
import numpy as np
from dataset import create_sliding_windows
traj = simulate_drone(n_points=50)
features = compute_social_features(traj)
print(f"Trajectory shape: {traj.shape}")
print(f"Features shape: {features.shape}")
X, y = create_sliding_windows(traj, input_steps=20, output_steps=10)
print(f"X shape: {X.shape}")  
print(f"y shape: {y.shape}")  
