"""Hotel agent: same retry/fallback subgraph shape as flight_agent.py,
but deliberately uses a plain REST tool (no MCP) so the project shows
both integration styles rather than the same pattern twice.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

import config
from state import HotelAgentState
from tools import amadeus_client, mock_data

MAX_ATTEMPTS = 3
# If nothing comes back, relax the star-rating requirement one notch at
# a time -- a 4-star-minimum search failing is often just a supply gap
# in the sandbox data, not a real "no hotels in this city" situation.
_STAR_FALLBACK_STEP = 1


def _search(destination: str, check_in: str, check_out: str, stars_min: int) -> dict | None:
    if config.MOCK_MODE:
        nights = 4
        return mock_data.search_hotels(destination, stars_min=stars_min, nights=nights)
    return amadeus_client.search_hotels(destination, check_in, check_out, stars_min=stars_min)


def search_node(state: HotelAgentState) -> dict:
    req = state["request"]
    attempt = state.get("hotel_attempts", 0)
    stars_min = max(1, req["hotel_stars_min"] - attempt * _STAR_FALLBACK_STEP)

    offer = _search(req["destination"], req["depart_date"], req["return_date"], stars_min)
    trace = [f"hotel_agent: attempt {attempt + 1} ({stars_min}★ min) -> {'found' if offer else 'empty'}"]

    if offer:
        return {
            "hotel_result": {
                "status": "ok" if stars_min == req["hotel_stars_min"] else "degraded",
                "summary": f"{offer['name']} ({offer['stars']}★, {offer['nights']} nights)",
                "cost": offer["price"],
                "payload": offer,
                "attempts": attempt + 1,
            },
            "hotel_attempts": attempt + 1,
            "trace": trace,
        }
    return {"hotel_result": None, "hotel_attempts": attempt + 1, "trace": trace}


def fallback_node(state: HotelAgentState) -> dict:
    trace = ["hotel_agent: no offer found after retries, returning degraded placeholder"]
    return {
        "hotel_result": {
            "status": "degraded",
            "summary": "No live hotel offer found -- showing an estimated rate so the trip can still be planned",
            "cost": 400.0,
            "payload": {},
            "attempts": state.get("hotel_attempts", MAX_ATTEMPTS),
        },
        "trace": trace,
    }


def _route(state: HotelAgentState) -> str:
    if state.get("hotel_result") is not None:
        return "done"
    if state.get("hotel_attempts", 0) >= MAX_ATTEMPTS:
        return "fallback"
    return "retry"


def build_hotel_subgraph():
    builder = StateGraph(HotelAgentState)
    builder.add_node("search", search_node)
    builder.add_node("fallback", fallback_node)
    builder.set_entry_point("search")
    builder.add_conditional_edges(
        "search", _route, {"done": END, "retry": "search", "fallback": "fallback"}
    )
    builder.add_edge("fallback", END)
    return builder.compile()
