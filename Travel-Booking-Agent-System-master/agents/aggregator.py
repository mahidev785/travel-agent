"""Aggregator: totals the cost across whichever agents ran, and -- this is
the iterative-workflow piece -- loops back to renegotiate with the hotel
agent (the most flexible budget lever) if the trip comes in over budget,
capped at MAX_ROUNDS so it can't loop forever.
"""

from __future__ import annotations

from langgraph.types import Send

from state import TripState

MAX_ROUNDS = 3


def aggregate_node(state: TripState) -> dict:
    flight = state.get("flight_result")
    hotel = state.get("hotel_result")
    itinerary = state.get("itinerary_result")

    total_cost = (flight["cost"] if flight else 0.0) + (hotel["cost"] if hotel else 0.0)
    budget = state["request"]["budget"]
    over_budget = total_cost > budget
    round_ = state.get("negotiation_round", 0)
    working_stars = state.get("working_hotel_stars_min", state["request"]["hotel_stars_min"])

    trace = [
        f"aggregator: total ${total_cost:.2f} vs budget ${budget:.2f}"
        + (" -- OVER BUDGET" if over_budget else " -- within budget")
    ]

    if over_budget and round_ < MAX_ROUNDS and working_stars > 1:
        trace.append(
            f"aggregator: renegotiating hotel at {working_stars - 1}★ minimum "
            f"(round {round_ + 1}/{MAX_ROUNDS})"
        )
        return {
            "total_cost": total_cost,
            "over_budget": over_budget,
            "negotiation_round": round_ + 1,
            "working_hotel_stars_min": working_stars - 1,
            "negotiation_decision": "renegotiate",
            "trace": trace,
        }

    if over_budget:
        trace.append("aggregator: still over budget after max rounds -- flagging for the traveler to decide")

    return {
        "total_cost": total_cost,
        "over_budget": over_budget,
        "negotiation_decision": "proceed",
        "trace": trace,
    }


def route_after_aggregate(state: TripState):
    if state.get("negotiation_decision") == "renegotiate":
        renegotiated_request = {**state["request"], "hotel_stars_min": state["working_hotel_stars_min"]}
        return Send("hotel_agent", {"request": renegotiated_request, "hotel_attempts": 0})
    return "human_approval"
