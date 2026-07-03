## Agents

### Prediction Agent
The Prediction Agent takes tracks from the Tracking Agent and predicts where 
the drone is going to be in the next N seconds. Built in four levels of 
increasing sophistication:

- **Kalman Filter** — classical mathematical baseline assuming constant velocity
- **LSTM** — deep learning sequence model learning temporal patterns
- **Transformer** — self-attention based architecture for better long-range dependencies
- **Social Force Transformer** — physics-informed transformer using velocity, 
acceleration, heading and destination force features (14 features per timestep)

We evaluate models using two metrics:
- **ADE (Average Displacement Error)** — average distance between predicted and 
actual position across all timestamps
- **FDE (Final Displacement Error)** — distance between predicted and actual 
position at the final timestamp only

#### Model Results (3D Simulated Data)

| Model | ADE | FDE |
|-------|-----|-----|
| Kalman Filter | 2.4213 | 3.9685 |
| LSTM | 2.7209 | 4.1753 |
| Transformer | 2.6791 | 4.0752 |
| Social Force Transformer | 1.9569 | 3.2349 |

Social Force Transformer achieves **19% improvement** over the Kalman baseline.

#### Input Format
```json
{
  "drone_id": 1,
  "positions": [[x1,y1,z1], [x2,y2,z2]]
}
```

#### Output Format
```json
{
  "drone_id": 1,
  "current_position": [x, y, z],
  "speed": 12.5,
  "predicted_trajectory": [[x1,y1,z1], [x2,y2,z2]],
  "confidence": 0.87
}
```

#### Files
| File | Description |
|------|-------------|
| `kalman_filter.py` | Kalman Filter implementation |
| `lstm.py` | LSTM model architecture |
| `transformer.py` | Transformer model with positional encoding |
| `dataset.py` | Dataset generation with Social Force features |
| `train_lstm.py` | LSTM training pipeline |
| `train_transformer.py` | Transformer training pipeline |
| `train_social_transformer.py` | Social Force Transformer training pipeline |
| `evaluate_all.py` | Full model comparison with ADE/FDE metrics |
| `predictor.py` | Production predictor with multi-drone JSON output |

#### Running
```bash
# Train Social Force Transformer
python prediction_agent/train_social_transformer.py

# Evaluate all models
python prediction_agent/evaluate_all.py

# Test predictor
python prediction_agent/test_predictor.py
```

---

### Coordinator Agent
The Coordinator Agent is the brain of the system. It receives threat alerts 
from the Threat Agent, reasons over them using an LLM (Llama 3.1 via Groq), 
and communicates with the human operator in natural language using LangGraph.

#### Features
- Real-time threat analysis using LLM reasoning
- Natural language operator interface
- Automatic escalation for critical threats
- Human-in-the-loop approval for critical decisions
- MQTT subscriber for real-time alert streaming
- FastAPI endpoints for operator UI integration

#### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/alerts` | ThreatAgent pushes alerts here |
| GET | `/alerts` | Fetch latest alerts |
| POST | `/query` | Operator asks a natural language question |
| GET | `/status` | Current system state |

#### Setup
```bash
# Copy env file and add your Groq API key
cp coordinator_agent/.env.example coordinator_agent/.env

# Install dependencies
pip install langgraph langchain langchain-groq fastapi uvicorn paho-mqtt python-dotenv
```

#### Running
```bash
# Start MQTT subscriber (in separate terminal)
python coordinator_agent/mqtt_subscriber.py

# Start FastAPI server (in separate terminal)
python coordinator_agent/api.py

# Test coordinator
python coordinator_agent/test_coordinator.py
```

#### Files
| File | Description |
|------|-------------|
| `state.py` | LangGraph state schema |
| `prompts.py` | LLM prompts for threat analysis and responses |
| `coordinator.py` | LangGraph graph with nodes and routing |
| `api.py` | FastAPI endpoints |
| `mqtt_subscriber.py` | MQTT subscriber bridging alerts to coordinator |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Detection | YOLO |
| Tracking | DeepSORT / ByteTrack |
| Prediction | PyTorch, LSTM, Transformer |
| Coordination | LangGraph, Groq (Llama 3.1) |
| API | FastAPI, Uvicorn |
| Messaging | MQTT (Mosquitto), paho-mqtt |
| Edge Deployment | NVIDIA Jetson Orin |
| Database | PostgreSQL |
| Containerization | Docker |

## Setup

```bash
# Clone repo
git clone https://github.com/tanvichitturu/AI-Powered-Drone-Detection.git

# Create virtual environment
python -m venv drone_env
drone_env\Scripts\activate  # Windows

# Install dependencies
pip install torch torchvision ultralytics deep-sort-realtime
pip install langgraph langchain langchain-groq
pip install fastapi uvicorn paho-mqtt python-dotenv
pip install opencv-python numpy matplotlib

# Set up environment variables
cp coordinator_agent/.env.example coordinator_agent/.env
# Add your GROQ_API_KEY to .env
```
