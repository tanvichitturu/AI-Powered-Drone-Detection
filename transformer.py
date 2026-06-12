import torch
from torch import nn
import math
class Position_encoding(nn.Module):
    def __init__(self, d_model, max_len=100,dropout = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:,0::2] = torch.sin(position * div_term)
        pe[:,1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe',pe)
    def forward(self,x):
            x = x+self.pe[:,:x.size(1)]
            return self.dropout(x)
class DroneTransformer(nn.Module):
    def __init__(self,input_size=3,d_model=64,nhead=4,num_layers=2,output_steps=10,dropout=0.1):
        super().__init__()
        self.output_steps = output_steps
        self.d_model = d_model
        self.input_proj = nn.Linear(input_size, d_model)
        self.pos_Encoder = Position_encoding(d_model, dropout=dropout)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model,nhead=nhead,dim_feedforward=128,dropout=dropout,batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Sequential(nn.Linear(d_model, 64),nn.ReLU(),nn.Dropout(dropout),nn.Linear(64, output_steps * 3))
    def forward(self,x):
        x = self.input_proj(x)
        x = self.pos_Encoder(x)
        out = self.transformer_encoder(x)
        context = out[:,-1,:]
        pred = self.fc(context)
        return pred.view(-1,self.output_steps,3)
        

