import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
import matplotlib.pyplot as plt
from dataset import DroneDataset
from lstm import PredictionLSTM

# Hyperparameters
INPUT_STEPS = 20
OUTPUT_STEPS = 10
BATCH_SIZE = 32
EPOCHS = 100
LR = 0.0005

# Create dataset
dataset = DroneDataset(
    n_trajectories=1000,
    input_steps=INPUT_STEPS,
    output_steps=OUTPUT_STEPS
)

# Train/val split
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

# Model
model = PredictionLSTM(
    input_size=3,
    hidden_size=128,
    num_layers=2,
    output_steps=OUTPUT_STEPS
)

optimizer = optim.Adam(model.parameters(), lr=LR)
criterion = nn.MSELoss()
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

# Training loop
train_losses = []
val_losses = []
best_val_loss = float('inf')

print("Starting training...")

for epoch in range(EPOCHS):
    # Training
    model.train()
    train_loss = 0
    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        predictions = model(X_batch)
        loss = criterion(predictions, y_batch)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        train_loss += loss.item()
    
    # Validation
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for X_batch, y_batch in val_loader:
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            val_loss += loss.item()
    
    train_loss /= len(train_loader)
    val_loss /= len(val_loader)
    train_losses.append(train_loss)
    val_losses.append(val_loss)
    
    scheduler.step(val_loss)
    
    # Save best model
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_lstm.pth')
    
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

print("Training complete!")

# Plot training curves
plt.figure(figsize=(10, 4))
plt.plot(train_losses, label='Train Loss')
plt.plot(val_losses, label='Val Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('LSTM Training Curves')
plt.legend()
plt.grid(True)
plt.savefig('lstm_training.png', dpi=150, bbox_inches='tight')
plt.show()

# Save normalization stats
np.save('norm_stats.npy', np.array([dataset.mean, dataset.std]))
print(f"Norm stats saved — mean: {dataset.mean:.4f}, std: {dataset.std:.4f}")