import torch
import numpy as np
import matplotlib.pyplot as plt
from dataset import simulate_drone
from lstm import PredictionLSTM
from kalman_filter import KalmanFilter

INPUT_STEPS = 20
OUTPUT_STEPS = 10

# Load trained model
model = PredictionLSTM(output_steps=OUTPUT_STEPS)
model.load_state_dict(torch.load('best_lstm.pth'))
model.eval()

# Load normalization stats from training — MUST be before evaluation
norm_stats = np.load('norm_stats.npy')
mean = norm_stats[0]
std = norm_stats[1]
print(f"Using norm stats — mean: {mean:.4f}, std: {std:.4f}")

# Generate a fresh test trajectory
trajectory = simulate_drone(n_points=100, noise=0.5)
observed = trajectory[:70]
actual_future = trajectory[70:80]

# Normalize using TRAINING stats
observed_norm = (observed - mean) / std
input_seq = torch.FloatTensor(observed_norm[-INPUT_STEPS:]).unsqueeze(0)

with torch.no_grad():
    predicted_norm = model(input_seq).squeeze(0).numpy()

# Denormalize using TRAINING stats
predicted_future = predicted_norm * std + mean

# ADE and FDE functions
def compute_ADE(predicted, actual):
    distances = np.sqrt(np.sum((predicted - actual)**2, axis=1))
    return np.mean(distances)

def compute_FDE(predicted, actual):
    diff = predicted[-1] - actual[-1]
    return np.sqrt(np.sum(diff**2))

# Kalman baseline
kf = KalmanFilter(dt=1.0)
kf.initialize(observed[0])
for pos in observed:
    kf.predict()
    kf.update(pos)
kalman_future = kf.predict_future(n_steps=OUTPUT_STEPS)

lstm_ade = compute_ADE(predicted_future, actual_future)
lstm_fde = compute_FDE(predicted_future, actual_future)
kalman_ade = compute_ADE(kalman_future, actual_future)
kalman_fde = compute_FDE(kalman_future, actual_future)

print("=" * 40)
print(f"Kalman Filter — ADE: {kalman_ade:.4f}, FDE: {kalman_fde:.4f}")
print(f"LSTM          — ADE: {lstm_ade:.4f}, FDE: {lstm_fde:.4f}")
improvement_ade = ((kalman_ade - lstm_ade) / kalman_ade) * 100
improvement_fde = ((kalman_fde - lstm_fde) / kalman_fde) * 100
print(f"Improvement   — ADE: {improvement_ade:.1f}%, FDE: {improvement_fde:.1f}%")
print("=" * 40)

# 3D Plot
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
ax.plot(observed[:, 0], observed[:, 1], observed[:, 2],
        'b-', label='Observed', linewidth=2)
ax.plot(actual_future[:, 0], actual_future[:, 1], actual_future[:, 2],
        'g-', label='Actual Future', linewidth=2)
ax.plot(kalman_future[:, 0], kalman_future[:, 1], kalman_future[:, 2],
        'r--', label=f'Kalman (ADE:{kalman_ade:.2f})', linewidth=2)
ax.plot(predicted_future[:, 0], predicted_future[:, 1], predicted_future[:, 2],
        'm-', label=f'LSTM (ADE:{lstm_ade:.2f})', linewidth=2)
ax.set_xlabel('X position')
ax.set_ylabel('Y position')
ax.set_zlabel('Z (Altitude)')
ax.set_title('Kalman vs LSTM 3D Trajectory Prediction')
ax.legend()
plt.savefig('lstm_vs_kalman_3d.png', dpi=150, bbox_inches='tight')
plt.show()