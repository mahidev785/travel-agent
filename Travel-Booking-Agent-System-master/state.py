"""Shared state schema for the travel booking graph.

Every node in the main graph (and the specialist subgraphs, which share
this schema so they can be plugged in directly as nodes) reads and writes
a subset of these keys. Keeping one schema is simpler than mapping state
across subgraph boundaries, and is a perfectly normal LangGraph pattern
for small-to-medium systems.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional, TypedDict


class TripRequest(TypedDict):
    origin: str
    destination: str
    depart_date: str
    return_date: str
    travelers: int
    budget: float
    hotel_stars_min: int
    preferences: str  # free-text preferences (window seat, vegetarian, etc.)


class AgentResult(TypedDict):
    status: Literal["ok", "degraded", "failed"]
    summary: str
    cost: float
    payload: dict
    attempts: int


def _keep_request(existing: TripRequest, new: TripRequest) -> TripRequest:
    """Reducer for the `request` channel.

    Compiled subgraphs added as nodes return their *entire* final state,
    not just the keys they changed -- so when flight_agent, hotel_agent,
    and itinerary_agent all run in parallel via Send, each of them
    "writes" `request` back unchanged. Without a reducer, LangGraph's
    default last-value channel rejects more than one write per step even
    if the values are identical. This reducer just keeps the latest one.
    """
    return new


class TripState(TypedDict):
    # --- input -----------------------------------------------------
    request: Annotated[TripRequest, _keep_request]

    # --- long-term memory (loaded once at the start of the run) ----
    user_id: str
    remembered_preferences: dict

    # --- supervisor routing decision ------------------------------------
    wants_itinerary: bool

    # --- specialist agent outputs -----------------------------------
    flight_result: Optional[AgentResult]
    hotel_result: Optional[AgentResult]
    itinerary_result: Optional[AgentResult]
    flight_attempts: int
    hotel_attempts: int
    itinerary_attempts: int

    # --- aggregation / negotiation -----------------------------------
    total_cost: float
    over_budget: bool
    negotiation_round: int
    negotiation_targets: list[str]  # which agents to re-run, e.g. ["hotel"]
    working_hotel_stars_min: int
    negotiation_decision: str  # "renegotiate" | "proceed"

    # --- human approval -----------------------------------------------
    approval_decision: Optional[dict]  # {"action": "approve"|"edit"|"reject", ...}

    # --- booking --------------------------------------------------------
    booking_confirmation: Optional[dict]

    # --- observability / UI streaming -----------------------------------
    # `operator.add` makes this an append-only log: every node can add a
    # line and LangGraph merges them instead of overwriting.
    trace: Annotated[list[str], operator.add]


# --- Per-agent sub-states -------------------------------------------------
# Each specialist subgraph only needs a slice of TripState. Declaring a
# TypedDict with a *subset* of the same key names lets LangGraph add the
# compiled subgraph directly as a node in the parent graph -- the runtime
# matches on key names, not on identity of the TypedDict class.


class FlightAgentState(TypedDict):
    request: TripRequest
    flight_result: Optional[AgentResult]
    flight_attempts: int
    trace: Annotated[list[str], operator.add]


class HotelAgentState(TypedDict):
    request: TripRequest
    hotel_result: Optional[AgentResult]
    hotel_attempts: int
    trace: Annotated[list[str], operator.add]


class ItineraryAgentState(TypedDict):
    request: TripRequest
    itinerary_result: Optional[AgentResult]
    itinerary_attempts: int
    trace: Annotated[list[str], operator.add]
