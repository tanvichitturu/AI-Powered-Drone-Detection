from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime

from coordinator import coordinator
from state import CoordinatorState

app = FastAPI(title="Coordinator API")

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

@app.post("/alerts")
async def receive_alerts(alerts: List[Alert]):
    """ThreatAgent pushes alerts here"""
    global current_state
    
    # Convert to dict
    alerts_dict = [alert.dict() for alert in alerts]
    
    # Update state with new alerts
    current_state["alerts"] = alerts_dict
    current_state["operator_query"] = "Analyze current threat situation"
    
    # Run coordinator graph
    result = coordinator.invoke(current_state)
    current_state = result
    
    return {
        "status": "alerts processed",
        "threat_level": result["threat_level"],
        "active_drones": result["active_drones"],
        "requires_approval": result["requires_approval"]
    }

@app.get("/alerts")
async def get_alerts():
    """Fetch latest alerts"""
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
    
    # Update query in state
    current_state["operator_query"] = query.question
    
    # Run coordinator graph
    result = coordinator.invoke(current_state)
    current_state = result
    
    return {
        "question": query.question,
        "response": result["response"],
        "threat_level": result["threat_level"],
        "requires_approval": result["requires_approval"]
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

# ==========================================================
# Run
# ==========================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)