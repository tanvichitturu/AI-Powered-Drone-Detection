from typing import TypedDict, List, Optional

class CoordinatorState(TypedDict):
    # Incoming alerts from ThreatAgent
    alerts: List[dict]
    
    # Operator conversation
    operator_query: Optional[str]
    conversation_history: List[dict]
    
    # LLM outputs
    analysis: Optional[str]
    response: Optional[str]
    action: Optional[str]
    
    # Control flow
    threat_level: Optional[str]   # "low", "medium", "high", "critical"
    requires_approval: bool
    
    # System info
    active_drones: List[int]
    last_updated: Optional[str]