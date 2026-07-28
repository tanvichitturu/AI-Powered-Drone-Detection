from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import time
from datetime import datetime

from coordinator import coordinator
from state import CoordinatorState

app = FastAPI(title="Coordinator API")

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state store
current_state: CoordinatorState = {
    "alerts": [],
    "operator_query": None,
    "conversation_history": [],
    "analysis": None,
    "response": None,
    "action": None,
    "threat_level": "low",
    "requires_approval": False,
    "active_drones": [],
    "last_updated": None
}

class Alert(BaseModel):
    drone_id: int
    threat_level: str
    risk_score: float
    reason: str
    current_position: List[float]
    speed: float
    predicted_trajectory: List[List[float]]
    confidence: float

class Query(BaseModel):
    question: str


_last_receive_time = time.time()
_STALE_TIMEOUT_SECONDS = 2.0  # Clear alerts if no update within 2 seconds

import asyncio

@app.post("/alerts")
async def receive_alerts(alerts: List[Alert]):
    global current_state, _last_receive_time
    _last_receive_time = time.time()
    
    alerts_dict = [alert.model_dump() for alert in alerts]
    active_drones = [a["drone_id"] for a in alerts_dict]
    
    threat_priority = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    highest_threat = max(
        alerts_dict,
        key=lambda x: threat_priority.get(x.get("threat_level", "low"), 0),
        default={"threat_level": "low"}
    )
    threat_level = highest_threat.get("threat_level", "low")
    requires_approval = threat_level in ["high", "critical"]
    
    current_state["alerts"] = alerts_dict
    current_state["active_drones"] = active_drones
    current_state["threat_level"] = threat_level
    current_state["requires_approval"] = requires_approval
    current_state["last_updated"] = datetime.now().isoformat()
    
    # Trigger escalation via coordinator graph if critical threat detected
    if threat_level == "critical" and not current_state.get("action"):
        try:
            result = await asyncio.to_thread(coordinator.invoke, current_state)
            current_state = result
        except Exception as e:
            print(f"[Coordinator] Error in critical escalation: {e}")

    return {
        "status": "alerts processed",
        "threat_level": current_state["threat_level"],
        "active_drones": current_state["active_drones"],
        "requires_approval": current_state["requires_approval"]
    }

@app.get("/alerts")
async def get_alerts():
    global current_state, _last_receive_time
    
    # If tracking hasn't sent an update recently, automatically clear stale alerts
    if time.time() - _last_receive_time > _STALE_TIMEOUT_SECONDS:
        current_state["alerts"] = []
        current_state["active_drones"] = []
        current_state["threat_level"] = "low"
        current_state["requires_approval"] = False

    return {
        "alerts": current_state["alerts"],
        "threat_level": current_state["threat_level"],
        "active_drones": current_state["active_drones"],
        "last_updated": current_state["last_updated"]
    }


@app.post("/query")
async def operator_query(query: Query):
    """Operator asks a question, Coordinator responds"""
    global current_state
    
    current_state["operator_query"] = query.question
    try:
        result = await asyncio.to_thread(coordinator.invoke, current_state)
        current_state = result
        response_text = result.get("response", "No response generated.")
    except Exception as e:
        print(f"[Coordinator] Error in operator_query: {e}")
        response_text = f"Coordinator API Error: {str(e)}"
    
    return {
        "question": query.question,
        "response": response_text,
        "threat_level": current_state["threat_level"],
        "requires_approval": current_state.get("requires_approval", False)
    }

@app.get("/status")
async def get_status():
    """Current system state"""
    return {
        "status": "operational",
        "threat_level": current_state["threat_level"],
        "active_drones": current_state["active_drones"],
        "requires_approval": current_state["requires_approval"],
        "last_updated": current_state["last_updated"],
        "total_alerts": len(current_state["alerts"])
    }

@app.get("/")
async def root():
    return {"message": "Coordinator API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)