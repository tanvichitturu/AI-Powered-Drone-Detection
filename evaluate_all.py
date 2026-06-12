import os
import torch
import numpy as np
import matplotlib.pyplot as plt

from dataset import simulate_drone, compute_social_features
from lstm import PredictionLSTM
from transformer import DroneTransformer
from kalman_filter import KalmanFilter

INPUT_STEPS = 20
OUTPUT_STEPS = 10
NUM_TESTS = 100

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load models
lstm_model = PredictionLSTM(output_steps=OUTPUT_STEPS)
lstm_model.load_state_dict(torch.load(os.path.join(BASE_DIR, "best_lstm.pth"), map_location=device))
lstm_model.to(device)
lstm_model.eval()

transformer_model = DroneTransformer(input_size=3, output_steps=OUTPUT_STEPS)
transformer_model.load_state_dict(torch.load(os.path.join(BASE_DIR, "best_transformer.pth"), map_location=device))
transformer_model.to(device)
transformer_model.eval()

social_model = DroneTransformer(input_size=14,d_model=128,nhead=4,num_layers=3,output_steps=OUTPUT_STEPS)
social_model.load_state_dict(torch.load(os.path.join(BASE_DIR, "best_social_transformer.pth"), map_location=device))
social_model.to(device)
social_model.eval()

# Load stats
lstm_stats = np.load(os.path.join(BASE_DIR, "norm_stats.npy"))
transformer_stats = np.load(os.path.join(BASE_DIR, "norm_stats_transformer.npy"))
social_stats = np.load(os.path.join(BASE_DIR, "norm_stats_social.npy"))

# Helper functions
def predict(model, observed, stats):
    mean, std = stats[0], stats[1]
    observed_norm = (observed - mean) / std
    input_seq = torch.FloatTensor(observed_norm[-INPUT_STEPS:]).unsqueeze(0).to(device)
    with torch.no_grad():
        pred_norm = model(input_seq).squeeze(0).cpu().numpy()
    return pred_norm * std + mean

def predict_social(model, observed, stats):
    mean, std = stats[0], stats[1]
    features = compute_social_features(observed)
    features_norm = (features - mean) / std
    input_seq = torch.FloatTensor(features_norm[-INPUT_STEPS:]).unsqueeze(0).to(device)
    with torch.no_grad():
        pred_norm = model(input_seq).squeeze(0).cpu().numpy()
    return pred_norm * std + mean

def compute_ADE(predicted, actual):
    distances = np.sqrt(np.sum((predicted - actual)**2, axis=1))
    return np.mean(distances)

def compute_FDE(predicted, actual):
    diff = predicted[-1] - actual[-1]
    return np.sqrt(np.sum(diff**2))

# Evaluation loop
kalman_ades, kalman_fdes = [], []
lstm_ades, lstm_fdes = [], []
transformer_ades, transformer_fdes = [], []
social_ades, social_fdes = [], []

example_data = None
print("\nEvaluating models...\n")

for i in range(NUM_TESTS):
    trajectory = simulate_drone(n_points=100, noise=0.5)
    observed = trajectory[:70]
    actual_future = trajectory[70:80]

    # Kalman
    kf = KalmanFilter(dt=1.0)
    kf.initialize(observed[0])
    for pos in observed:
        kf.predict()
        kf.update(pos)
    kalman_future = kf.predict_future(n_steps=OUTPUT_STEPS)

    # LSTM
    lstm_future = predict(lstm_model, observed, lstm_stats)

    # Transformer
    transformer_future = predict(transformer_model, observed, transformer_stats)

    # Social Force Transformer
    social_future = predict_social(social_model, observed, social_stats)

    # Metrics
    kalman_ades.append(compute_ADE(kalman_future, actual_future))
    kalman_fdes.append(compute_FDE(kalman_future, actual_future))
    lstm_ades.append(compute_ADE(lstm_future, actual_future))
    lstm_fdes.append(compute_FDE(lstm_future, actual_future))
    transformer_ades.append(compute_ADE(transformer_future, actual_future))
    transformer_fdes.append(compute_FDE(transformer_future, actual_future))
    social_ades.append(compute_ADE(social_future, actual_future))
    social_fdes.append(compute_FDE(social_future, actual_future))

    if i == 0:
        example_data = (observed, actual_future, kalman_future,
                       lstm_future, transformer_future, social_future)

# Average metrics
kalman_ade, kalman_fde = np.mean(kalman_ades), np.mean(kalman_fdes)
lstm_ade, lstm_fde = np.mean(lstm_ades), np.mean(lstm_fdes)
transformer_ade, transformer_fde = np.mean(transformer_ades), np.mean(transformer_fdes)
social_ade, social_fde = np.mean(social_ades), np.mean(social_fdes)

print("=" * 55)
print(f"{'Model':<25} {'ADE':>12} {'FDE':>12}")
print("-" * 55)
print(f"{'Kalman Filter':<25} {kalman_ade:>12.4f} {kalman_fde:>12.4f}")
print(f"{'LSTM':<25} {lstm_ade:>12.4f} {lstm_fde:>12.4f}")
print(f"{'Transformer':<25} {transformer_ade:>12.4f} {transformer_fde:>12.4f}")
print(f"{'Social Force Transformer':<25} {social_ade:>12.4f} {social_fde:>12.4f}")
print("=" * 55)

# Plot
observed, actual_future, kalman_future, lstm_future, transformer_future, social_future = example_data

fig = plt.figure(figsize=(14, 8))
ax = fig.add_subplot(111, projection='3d')

ax.plot(observed[:, 0], observed[:, 1], observed[:, 2], 'b-', linewidth=2, label='Observed')
ax.plot(actual_future[:, 0], actual_future[:, 1], actual_future[:, 2], 'g-', linewidth=3, label='Actual Future')
ax.plot(kalman_future[:, 0], kalman_future[:, 1], kalman_future[:, 2], 'r--', linewidth=2, label=f'Kalman (ADE={kalman_ade:.2f})')
ax.plot(lstm_future[:, 0], lstm_future[:, 1], lstm_future[:, 2], 'm-', linewidth=2, label=f'LSTM (ADE={lstm_ade:.2f})')
ax.plot(transformer_future[:, 0], transformer_future[:, 1], transformer_future[:, 2], color='orange', linewidth=2, label=f'Transformer (ADE={transformer_ade:.2f})')
ax.plot(social_future[:, 0], social_future[:, 1], social_future[:, 2], color='cyan', linewidth=2, label=f'Social Force (ADE={social_ade:.2f})')

ax.set_xlabel("X Position")
ax.set_ylabel("Y Position")
ax.set_zlabel("Z Altitude")
ax.set_title("All Models Comparison — 3D Trajectory Prediction")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR, "all_models_comparison.png"), dpi=150, bbox_inches="tight")
plt.show()