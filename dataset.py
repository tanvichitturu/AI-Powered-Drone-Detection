import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

def simulate_drone(n_points=200, noise=0.5):
    t = np.linspace(0, 4*np.pi, n_points)
    x = t * 2 + np.random.normal(0, noise, n_points)
    y = np.sin(t) * 5 + np.random.normal(0, noise, n_points)
    z = np.cos(t) * 2 + np.random.normal(0, noise, n_points)  # altitude
    return np.column_stack([x, y, z])

def create_sliding_windows(trajectory, input_steps=20, output_steps=10):
    x, y = [], []
    for i in range(len(trajectory) - input_steps - output_steps):
        x.append(trajectory[i:i+input_steps])
        y.append(trajectory[i+input_steps:i+input_steps+output_steps])
    return np.array(x), np.array(y)

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