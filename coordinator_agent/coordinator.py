import os
import json
from datetime import datetime
from typing import Literal
from dotenv import load_dotenv
load_dotenv()
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from state import CoordinatorState
from prompt import SYSTEM_PROMPT, ANALYSIS_PROMPT, RESPONSE_PROMPT, ESCALATION_PROMPT

# Initialize LLM
llm = ChatGroq(
    model="llama-3.1-8b-instant",  # updated model name
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.1
)
#nodes

def receive_alerts(state: CoordinatorState) -> CoordinatorState:
    """Process incoming alerts and extract key information"""
    alerts = state.get("alerts", [])
    
    if not alerts:
        return {**state, "threat_level": "low", "active_drones": []}
    
    # Extract active drone IDs
    active_drones = [alert["drone_id"] for alert in alerts]
    
    # Find highest threat level
    threat_priority = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    highest_threat = max(
        alerts,
        key=lambda x: threat_priority.get(x.get("threat_level", "low"), 0)
    )
    threat_level = highest_threat.get("threat_level", "low")
    
    print(f"[Coordinator] Received {len(alerts)} alerts. Highest threat: {threat_level}")
    
    return {
        **state,
        "active_drones": active_drones,
        "threat_level": threat_level,
        "last_updated": datetime.now().isoformat()
    }


def analyze_threat(state: CoordinatorState) -> CoordinatorState:
    """LLM analyzes the threat situation"""
    alerts = state.get("alerts", [])
    
    if not alerts:
        return {**state, "analysis": "No active threats detected. System monitoring normally."}
    
    # Format alerts for LLM
    alerts_text = json.dumps(alerts, indent=2)
    
    prompt = ANALYSIS_PROMPT.format(alerts=alerts_text)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    analysis = response.content
    
    print(f"[Coordinator] Threat analysis complete")
    
    return {**state, "analysis": analysis}


def respond_to_operator(state: CoordinatorState) -> CoordinatorState:
    """LLM responds to operator query"""
    query = state.get("operator_query", "What is the current threat status?")
    analysis = state.get("analysis", "")
    alerts = state.get("alerts", [])
    history = state.get("conversation_history", [])
    
    # Format history
    history_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in history[-5:]  # last 5 messages only
    ])
    
    prompt = RESPONSE_PROMPT.format(
        analysis=analysis,
        alerts=json.dumps(alerts, indent=2),
        history=history_text,
        query=query
    )
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    answer = response.content
    
    # Update conversation history
    updated_history = history + [
        {"role": "operator", "content": query},
        {"role": "coordinator", "content": answer}
    ]
    
    print(f"[Coordinator] Response generated")
    
    return {
        **state,
        "response": answer,
        "conversation_history": updated_history
    }


def escalate(state: CoordinatorState) -> CoordinatorState:
    """Handle critical threats requiring immediate attention"""
    alerts = state.get("alerts", [])
    analysis = state.get("analysis", "")
    
    prompt = ESCALATION_PROMPT.format(
        alerts=json.dumps(alerts, indent=2),
        analysis=analysis
    )
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    escalation_message = response.content
    
    print(f"[Coordinator] ⚠️ ESCALATION TRIGGERED")
    
    return {
        **state,
        "response": escalation_message,
        "requires_approval": True,
        "action": "ESCALATED — awaiting operator authorization"
    }


def route_by_threat(state: CoordinatorState) -> Literal["escalate", "respond_to_operator"]:
    """Route to escalation if critical, otherwise respond normally"""
    threat_level = state.get("threat_level", "low")
    
    if threat_level == "critical":
        return "escalate"
    else:
        return "respond_to_operator"


def build_coordinator():
    graph = StateGraph(CoordinatorState)
    
    # Add nodes
    graph.add_node("receive_alerts", receive_alerts)
    graph.add_node("analyze_threat", analyze_threat)
    graph.add_node("respond_to_operator", respond_to_operator)
    graph.add_node("escalate", escalate)
    
    # Add edges
    graph.set_entry_point("receive_alerts")
    graph.add_edge("receive_alerts", "analyze_threat")
    
    # Conditional routing after analysis
    graph.add_conditional_edges(
        "analyze_threat",
        route_by_threat,
        {
            "escalate": "escalate",
            "respond_to_operator": "respond_to_operator"
        }
    )
    
    # Both paths end after responding
    graph.add_edge("escalate", END)
    graph.add_edge("respond_to_operator", END)
    
    return graph.compile()


# Create coordinator instance
coordinator = build_coordinator()