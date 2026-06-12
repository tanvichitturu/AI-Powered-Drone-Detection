import matplotlib.pyplot as plt
import numpy as np
from kalman_filter import KalmanFilter
# Simulate a drone flying in a curved path
def simulate_drone(n_points=100, noise=0.5):
    t = np.linspace(0, 4*np.pi, n_points)
    x = t * 2 + np.random.normal(0, noise, n_points)
    y = np.sin(t) * 5 + np.random.normal(0, noise, n_points)
    z = np.cos(t) * 2 + np.random.normal(0, noise, n_points)
    return np.column_stack([x, y, z])

# Generate trajectory
trajectory = simulate_drone(n_points=100)

# Run Kalman Filter
kf = KalmanFilter(dt=1.0)
kf.initialize(trajectory[0])

# Use first 70 points as observed, predict next 10
observed = trajectory[:70]
actual_future = trajectory[70:80]

# Feed observations to filter
for pos in observed:
    kf.predict()
    kf.update(pos)

# Predict 10 future steps
predicted_future = kf.predict_future(n_steps=10)

# Compute ADE and FDE
def compute_ADE(predicted, actual):
    distances = np.sqrt(np.sum((predicted - actual)**2, axis=1))
    return np.mean(distances)

def compute_FDE(predicted, actual):
    diff = predicted[-1] - actual[-1]
    return np.sqrt(np.sum(diff**2))

ade = compute_ADE(predicted_future, actual_future)
fde = compute_FDE(predicted_future, actual_future)
print(f"Kalman Filter — ADE: {ade:.4f}, FDE: {fde:.4f}")

# Plot
plt.figure(figsize=(10, 6))
plt.plot(observed[:, 0], observed[:, 1], 'b-', label='Observed', linewidth=2)
plt.plot(actual_future[:, 0], actual_future[:, 1], 'g-', label='Actual Future', linewidth=2)
plt.plot(predicted_future[:, 0], predicted_future[:, 1], 'r--', label='Kalman Prediction', linewidth=2)
plt.scatter(observed[-1, 0], observed[-1, 1], c='blue', s=100, zorder=5, label='Last observed')
plt.legend()
plt.title('Kalman Filter Trajectory Prediction')
plt.xlabel('X position')
plt.ylabel('Y position')
plt.grid(True)
plt.savefig('kalman_prediction.png', dpi=150, bbox_inches='tight')
plt.show()