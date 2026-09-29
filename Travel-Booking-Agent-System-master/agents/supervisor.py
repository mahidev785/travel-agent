"""Supervisor: the one LLM-routing decision in the main graph. The
Streamlit UI collects origin/destination/dates/budget as structured form
fields (an LLM parsing free text into a date is exactly the kind of thing
that quietly breaks demos), so the only real judgment call left for the
supervisor is: does this trip need the itinerary/RAG agent at all, or is
the traveler just asking for flights + hotel?
"""

from __future__ import annotations

from langgraph.types import Send

from state import TripState
from tools.llm_client import TravelLLM

_llm = TravelLLM()


def supervisor_node(state: TripState) -> dict:
    wants_itinerary = _llm.wants_itinerary(state["request"]["preferences"])
    trace = [
        f"supervisor: routing to flight + hotel"
        + (" + itinerary" if wants_itinerary else "")
        + " agents"
    ]
    return {"trace": trace, "wants_itinerary": wants_itinerary}


def fan_out(state: TripState) -> list[Send]:
    """Conditional edge that returns Send objects -- this is the parallel
    fan-out: all targeted agents run concurrently instead of one after
    another, and each gets its own slice of state.
    """
    targets = [
        Send("flight_agent", {"request": state["request"], "flight_attempts": 0}),
        Send("hotel_agent", {"request": state["request"], "hotel_attempts": 0}),
    ]
    if state.get("wants_itinerary"):
        targets.append(
            Send("itinerary_agent", {"request": state["request"], "itinerary_attempts": 0})
        )
    return targets
