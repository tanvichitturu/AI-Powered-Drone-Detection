import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from coordinator import coordinator

#mock alerts for testing
mock_alerts = [
    {
        "drone_id": 1,
        "threat_level": "critical",
        "risk_score": 98,
        "reason": "approaching restricted zone at high speed",
        "current_position": [10.5, 23.2, 15.0],
        "speed": 12.5,
        "predicted_trajectory": [[11.0, 24.0, 14.0], [11.5, 24.8, 13.0]],
        "confidence": 0.87
    },
    {
        "drone_id": 2,
        "threat_level": "low",
        "risk_score": 6,
        "reason": "drone detected but far from perimeter",
        "current_position": [50.0, 80.0, 30.0],
        "speed": 3.2,
        "predicted_trajectory": [[50.5, 80.2, 30.0], [51.0, 80.4, 30.0]],
        "confidence": 0.92
    }
]

# Initial state
initial_state = {
    "alerts": mock_alerts,
    "operator_query": "What is the current threat situation?",
    "conversation_history": [],
    "analysis": None,
    "response": None,
    "action": None,
    "threat_level": None,
    "requires_approval": False,
    "active_drones": [],
    "last_updated": None
}

print("Starting Coordinator Agent test...\n")

result = coordinator.invoke(initial_state)

print("\n" + "="*50)
print("COORDINATOR RESPONSE:")
print("="*50)
print(result["response"])
print("\nThreat Level:", result["threat_level"])
print("Active Drones:", result["active_drones"])
print("Requires Approval:", result["requires_approval"])