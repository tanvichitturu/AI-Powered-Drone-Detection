import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
def compute_social_features(positions):
    """
    Compute Social Force inspired motion features from raw positions.
    positions: (N, 3) array
    returns: (N, 14) feature array
    """
    N = len(positions)
    
    # Velocity (first derivative of position)
    velocity = np.zeros_like(positions)
    velocity[1:] = positions[1:] - positions[:-1]
    velocity[0] = velocity[1]
    
    # Acceleration (first derivative of velocity)
    acceleration = np.zeros_like(velocity)
    acceleration[1:] = velocity[1:] - velocity[:-1]
    acceleration[0] = acceleration[1]
    
    # Speed (magnitude of velocity)
    speed = np.sqrt(np.sum(velocity**2, axis=1, keepdims=True))
    
    # Heading angle in xy plane
    heading = np.arctan2(
        velocity[:, 1:2],
        velocity[:, 0:1] + 1e-8
    )
    
    # Destination force
    destination_force = np.zeros_like(positions)
    relaxation_time = 0.5
    desired_speed = float(speed.mean())
    
    for i in range(N):
        if i >= 4:
            trend = positions[i] - positions[i-4]
            trend_norm = np.linalg.norm(trend) + 1e-8
            desired_direction = trend / trend_norm
        else:
            desired_direction = np.array([1.0, 0.0, 0.0])
        
        desired_velocity = desired_direction * desired_speed
        destination_force[i] = (desired_velocity - velocity[i]) / relaxation_time
    
    # Concatenate all features
    features = np.concatenate([
        positions,           # (N, 3)
        velocity,            # (N, 3)
        acceleration,        # (N, 3)
        speed,               # (N, 1)
        heading,             # (N, 1)
        destination_force,   # (N, 3)
    ], axis=1)
    
    return features  # (N, 14)

def simulate_drone(n_points=200, noise=0.5):
    t = np.linspace(0, 4*np.pi, n_points)
    x = t * 2 + np.random.normal(0, noise, n_points)
    y = np.sin(t) * 5 + np.random.normal(0, noise, n_points)
    z = np.cos(t) * 2 + np.random.normal(0, noise, n_points)  # altitude
    return np.column_stack([x, y, z])

def create_sliding_windows(trajectory, input_steps=20, output_steps=10):
    # Compute rich features from raw positions
    features = compute_social_features(trajectory)
    
    X, y = [], []
    for i in range(len(trajectory) - input_steps - output_steps):
        X.append(features[i:i+input_steps])        # input: 14 features
        y.append(trajectory[i+input_steps:i+input_steps+output_steps])  # output: raw x,y,z only
    return np.array(X), np.array(y)

class DroneDataset(Dataset):
    def __init__(self, n_trajectories=500, input_steps=20, output_steps=10):
        all_X, all_y = [], []
        
        for _ in range(n_trajectories):
            # Generate varied trajectories
            traj = simulate_drone(
                n_points=np.random.randint(150, 300),
                noise=np.random.uniform(0.1, 1.0)
            )
            X, y = create_sliding_windows(traj, input_steps, output_steps)
            all_X.append(X)
            all_y.append(y)
        
        all_X = np.concatenate(all_X, axis=0)
        all_y = np.concatenate(all_y, axis=0)

        
        # Normalize
        self.mean = all_X.mean()
        self.std = all_X.std()
        all_X = (all_X - self.mean) / self.std
        all_y = (all_y - self.mean) / self.std
        #all_z = (all_z - self.mean) / self.std
        
        self.X = torch.FloatTensor(all_X)
        self.y = torch.FloatTensor(all_y)
        #self.z = torch.FloatTensor(all_z)
        
        print(f"Dataset created: {len(self.X)} samples")
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]