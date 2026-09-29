"""Itinerary agent: retrieves destination-guide snippets (RAG), then asks
the LLM to turn them into a short day-by-day plan. Falls back to a
generic LLM-only writeup (no retries needed -- there's no external API
call here that can transiently fail, only "the corpus has nothing for
this city").
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from state import ItineraryAgentState
from tools import rag_tool
from tools.llm_client import TravelLLM

_llm = TravelLLM()


def _nights(depart_date: str, return_date: str) -> int:
    from datetime import date

    d1 = date.fromisoformat(depart_date)
    d2 = date.fromisoformat(return_date)
    return max(1, (d2 - d1).days)


def plan_node(state: ItineraryAgentState) -> dict:
    req = state["request"]
    snippets = rag_tool.retrieve(req["destination"], req["preferences"], k=_nights(req["depart_date"], req["return_date"]))
    plan_text = _llm.write_itinerary(
        destination=req["destination"],
        days=_nights(req["depart_date"], req["return_date"]),
        preferences=req["preferences"],
        guide_snippets=snippets,
    )
    status = "ok" if snippets else "degraded"
    trace = [f"itinerary_agent: {'used' if snippets else 'no'} destination-guide matches for {req['destination']}"]
    return {
        "itinerary_result": {
            "status": status,
            "summary": plan_text,
            "cost": 0.0,  # activities aren't priced/booked in this project
            "payload": {"snippets": snippets},
            "attempts": 1,
        },
        "itinerary_attempts": 1,
        "trace": trace,
    }


def build_itinerary_subgraph():
    builder = StateGraph(ItineraryAgentState)
    builder.add_node("plan", plan_node)
    builder.set_entry_point("plan")
    builder.add_edge("plan", END)
    return builder.compile()
