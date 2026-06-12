from dataset import DroneDataset
from transformer import DroneTransformer
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
import matplotlib.pyplot as plt

INPUT_STEPS = 20
OUTPUT_STEPS = 10
BATCH_SIZE = 32
EPOCHS = 50
LR = 0.0005

dataset = DroneDataset(
    n_trajectories=300,
    input_steps=INPUT_STEPS,
    output_steps=OUTPUT_STEPS
)

train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

model = DroneTransformer(
    input_size=14,     # social force features
    d_model=128,
    nhead=4,
    num_layers=3,
    output_steps=OUTPUT_STEPS
)

print(f"Social Transformer parameters: {sum(p.numel() for p in model.parameters()):,}")

optimizer = optim.Adam(model.parameters(), lr=LR)
criterion = nn.MSELoss()
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

train_losses, val_losses = [], []
best_val_loss = float('inf')

print("Training Social Force Transformer...")

for epoch in range(EPOCHS):
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
    
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_social_transformer.pth')
    
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch+1}/{EPOCHS} | Train: {train_loss:.4f} | Val: {val_loss:.4f}")

print("Done!")
np.save('norm_stats_social.npy', np.array([dataset.mean, dataset.std]))

plt.figure(figsize=(10, 4))
plt.plot(train_losses, label='Train')
plt.plot(val_losses, label='Val')
plt.title('Social Force Transformer Training')
plt.legend()
plt.grid(True)
plt.savefig('social_transformer_training.png', dpi=150)
plt.show()