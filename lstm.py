import torch
import torch.nn as nn

class PredictionLSTM(nn.Module):
    def __init__(self, input_size=3, hidden_size=128, 
                 num_layers=2, output_steps=10, dropout=0.2):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.output_steps = output_steps
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )
        
        # Fully connected output layer
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, output_steps * 3)  # 3 for x, y, z coordinates
        )
    
    def forward(self, x):
        # x shape: (batch, input_steps, 3)
        
        # Initialize hidden state
        batch_size = x.shape[0]
        h0 = torch.zeros(self.num_layers, batch_size, 
                         self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, batch_size, 
                         self.hidden_size).to(x.device)
        
        # LSTM forward pass
        out, _ = self.lstm(x, (h0, c0))
        
        # Take last timestep output
        out = self.fc(out[:, -1, :])
        
        # Reshape to (batch, output_steps, 3)
        return out.view(-1, self.output_steps, 3)