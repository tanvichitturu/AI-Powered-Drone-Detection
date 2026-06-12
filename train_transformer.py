import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import numpy as np
import matplotlib.pyplot as plt

from dataset import DroneDataset
from transformer import DroneTransformer


def main():
    # Hyperparameters
    INPUT_STEPS = 20
    OUTPUT_STEPS = 10
    BATCH_SIZE = 64
    EPOCHS = 20
    LR = 0.0005

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    # Create dataset
    dataset = DroneDataset(
        n_trajectories=100,
        input_steps=INPUT_STEPS,
        output_steps=OUTPUT_STEPS
    )

    print(f"Dataset created: {len(dataset)} samples")

    # Train/validation split
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size

    train_dataset, val_dataset = random_split(
        dataset,
        [train_size, val_size]
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0
    )

    # Model
    model = DroneTransformer(
        input_size=3,
        d_model=64,
        nhead=4,
        num_layers=2,
        output_steps=OUTPUT_STEPS
    ).to(device)

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        patience=5,
        factor=0.5
    )

    train_losses = []
    val_losses = []

    best_val_loss = float("inf")

    print("Starting training...")

    for epoch in range(EPOCHS):

        # Training
        model.train()
        train_loss = 0

        for X_batch, y_batch in train_loader:

            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()

            predictions = model(X_batch)

            loss = criterion(predictions, y_batch)

            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=1.0
            )

            optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)

        # Validation
        model.eval()
        val_loss = 0

        with torch.no_grad():

            for X_batch, y_batch in val_loader:

                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)

                predictions = model(X_batch)

                loss = criterion(predictions, y_batch)

                val_loss += loss.item()

        val_loss /= len(val_loader)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        scheduler.step(val_loss)

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), "best_transformer.pth")

        print(
            f"Epoch {epoch+1:02d}/{EPOCHS} | "
            f"Train Loss: {train_loss:.6f} | "
            f"Val Loss: {val_loss:.6f}"
        )

    print("\nTraining complete!")

    # Save normalization statistics
    np.save(
        "norm_stats_transformer.npy",
        np.array([dataset.mean, dataset.std])
    )

    # Plot losses
    plt.figure(figsize=(10, 4))
    plt.plot(train_losses, label="Train Loss")
    plt.plot(val_losses, label="Validation Loss")

    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Transformer Training Curves")

    plt.legend()
    plt.grid(True)

    plt.savefig(
        "transformer_training.png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.show()


if __name__ == "__main__":
    main()