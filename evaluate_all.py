import os
import torch
import numpy as np
import matplotlib.pyplot as plt

from dataset import simulate_drone
from lstm import PredictionLSTM
from transformer import DroneTransformer
from kalman_filter import KalmanFilter

# ==========================================================
# Settings
# ==========================================================
INPUT_STEPS = 20
OUTPUT_STEPS = 10
NUM_TESTS = 100

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================================
# Load models
# ==========================================================
lstm_model = PredictionLSTM(output_steps=OUTPUT_STEPS)
lstm_model.load_state_dict(
    torch.load(
        os.path.join(BASE_DIR, "best_lstm.pth"),
        map_location=device
    )
)
lstm_model.to(device)
lstm_model.eval()

transformer_model = DroneTransformer(output_steps=OUTPUT_STEPS)
transformer_model.load_state_dict(
    torch.load(
        os.path.join(BASE_DIR, "best_transformer.pth"),
        map_location=device
    )
)
transformer_model.to(device)
transformer_model.eval()

# ==========================================================
# Load normalization statistics
# ==========================================================
lstm_stats = np.load(
    os.path.join(BASE_DIR, "norm_stats.npy")
)

transformer_stats = np.load(
    os.path.join(BASE_DIR, "norm_stats_transformer.npy")
)


# ==========================================================
# Helper functions
# ==========================================================
def predict(model, observed, stats):
    mean, std = stats[0], stats[1]

    observed_norm = (observed - mean) / std

    input_seq = torch.FloatTensor(
        observed_norm[-INPUT_STEPS:]
    ).unsqueeze(0).to(device)

    with torch.no_grad():
        pred_norm = model(input_seq).squeeze(0).cpu().numpy()

    prediction = pred_norm * std + mean

    return prediction


def compute_ADE(predicted, actual):
    distances = np.sqrt(
        np.sum((predicted - actual) ** 2, axis=1)
    )
    return np.mean(distances)


def compute_FDE(predicted, actual):
    diff = predicted[-1] - actual[-1]
    return np.sqrt(np.sum(diff ** 2))


# ==========================================================
# Evaluation
# ==========================================================
kalman_ades = []
kalman_fdes = []

lstm_ades = []
lstm_fdes = []

transformer_ades = []
transformer_fdes = []

# Save one example for plotting
example_data = None

print("\nEvaluating models...\n")

for i in range(NUM_TESTS):

    trajectory = simulate_drone(
        n_points=100,
        noise=0.5
    )

    observed = trajectory[:70]
    actual_future = trajectory[70:80]

    # ---------------- Kalman ----------------
    kf = KalmanFilter(dt=1.0)
    kf.initialize(observed[0])

    for pos in observed:
        kf.predict()
        kf.update(pos)

    kalman_future = kf.predict_future(
        n_steps=OUTPUT_STEPS
    )

    # ---------------- LSTM ----------------
    lstm_future = predict(
        lstm_model,
        observed,
        lstm_stats
    )

    # ---------------- Transformer ----------------
    transformer_future = predict(
        transformer_model,
        observed,
        transformer_stats
    )

    # ---------------- Metrics ----------------
    kalman_ades.append(
        compute_ADE(kalman_future, actual_future)
    )
    kalman_fdes.append(
        compute_FDE(kalman_future, actual_future)
    )

    lstm_ades.append(
        compute_ADE(lstm_future, actual_future)
    )
    lstm_fdes.append(
        compute_FDE(lstm_future, actual_future)
    )

    transformer_ades.append(
        compute_ADE(transformer_future, actual_future)
    )
    transformer_fdes.append(
        compute_FDE(transformer_future, actual_future)
    )

    # Save one example trajectory
    if i == 0:
        example_data = (
            observed,
            actual_future,
            kalman_future,
            lstm_future,
            transformer_future
        )

# ==========================================================
# Average metrics
# ==========================================================
kalman_ade = np.mean(kalman_ades)
kalman_fde = np.mean(kalman_fdes)

lstm_ade = np.mean(lstm_ades)
lstm_fde = np.mean(lstm_fdes)

transformer_ade = np.mean(transformer_ades)
transformer_fde = np.mean(transformer_fdes)

print("=" * 55)
print(f"{'Model':<20} {'ADE':>12} {'FDE':>12}")
print("-" * 55)
print(f"{'Kalman Filter':<20} {kalman_ade:>12.4f} {kalman_fde:>12.4f}")
print(f"{'LSTM':<20} {lstm_ade:>12.4f} {lstm_fde:>12.4f}")
print(f"{'Transformer':<20} {transformer_ade:>12.4f} {transformer_fde:>12.4f}")
print("=" * 55)

# ==========================================================
# Plot one example
# ==========================================================
(
    observed,
    actual_future,
    kalman_future,
    lstm_future,
    transformer_future
) = example_data

fig = plt.figure(figsize=(14, 8))
ax = fig.add_subplot(111, projection='3d')

# Observed
ax.plot(
    observed[:, 0],
    observed[:, 1],
    observed[:, 2],
    'b-',
    linewidth=2,
    label='Observed'
)

# Actual
ax.plot(
    actual_future[:, 0],
    actual_future[:, 1],
    actual_future[:, 2],
    'g-',
    linewidth=3,
    label='Actual Future'
)

# Kalman
ax.plot(
    kalman_future[:, 0],
    kalman_future[:, 1],
    kalman_future[:, 2],
    'r--',
    linewidth=2,
    label=f'Kalman (ADE={kalman_ade:.2f})'
)

# LSTM
ax.plot(
    lstm_future[:, 0],
    lstm_future[:, 1],
    lstm_future[:, 2],
    'm-',
    linewidth=2,
    label=f'LSTM (ADE={lstm_ade:.2f})'
)

# Transformer
ax.plot(
    transformer_future[:, 0],
    transformer_future[:, 1],
    transformer_future[:, 2],
    color='orange',
    linewidth=2,
    label=f'Transformer (ADE={transformer_ade:.2f})'
)

ax.set_xlabel("X Position")
ax.set_ylabel("Y Position")
ax.set_zlabel("Z Altitude")
ax.set_title("Kalman vs LSTM vs Transformer")

ax.legend()

plt.tight_layout()

plt.savefig(
    os.path.join(BASE_DIR, "all_models_comparison.png"),
    dpi=150,
    bbox_inches="tight"
)

plt.show()