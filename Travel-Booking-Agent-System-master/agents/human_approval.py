"""Human approval: the interrupt() call. Execution pauses here -- the
checkpointer holds the full state -- until the caller resumes with
Command(resume={...}). See app.py for the Streamlit side of this.
"""

from __future__ import annotations

from langgraph.types import interrupt

from state import TripState


def human_approval_node(state: TripState) -> dict:
    decision = interrupt(
        {
            "flight": state.get("flight_result"),
            "hotel": state.get("hotel_result"),
            "itinerary": state.get("itinerary_result"),
            "total_cost": state.get("total_cost"),
            "budget": state["request"]["budget"],
            "over_budget": state.get("over_budget", False),
            "actions": ["approve", "reject"],
        }
    )
    return {
        "approval_decision": decision,
        "trace": [f"human_approval: traveler chose '{decision.get('action')}'"],
    }


def route_after_approval(state: TripState) -> str:
    decision = state.get("approval_decision") or {}
    return "approve" if decision.get("action") == "approve" else "reject"
