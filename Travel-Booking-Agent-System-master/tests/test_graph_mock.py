"""End-to-end tests against MOCK_MODE -- no API keys, no network calls.

Run with: pytest tests/
"""

import os
import uuid

os.environ["MOCK_MODE"] = "1"
os.environ["SQLITE_DB_PATH"] = ":memory:"

import pytest
from langgraph.types import Command

from graph import build_graph


def _run_to_interrupt(graph, request: dict, user_id: str = "test-user"):
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
    for _ in graph.stream(
        {"request": request, "user_id": user_id, "trace": []}, cfg, stream_mode="values"
    ):
        pass
    return cfg, graph.get_state(cfg)


BASE_REQUEST = {
    "origin": "BOM",
    "destination": "Goa",
    "depart_date": "2026-12-10",
    "return_date": "2026-12-14",
    "travelers": 2,
    "budget": 900.0,
    "hotel_stars_min": 4,
    "preferences": "want to see the beaches and try local food",
}


@pytest.fixture()
def graph():
    return build_graph()


def test_reaches_human_approval(graph):
    cfg, snapshot = _run_to_interrupt(graph, BASE_REQUEST)
    assert snapshot.next, "graph should pause at the human-approval interrupt"
    payload = snapshot.tasks[0].interrupts[0].value
    assert payload["flight"] is not None
    assert payload["hotel"] is not None


def test_negotiation_loop_brings_cost_under_budget(graph):
    # This budget is intentionally tight enough that the first-pass hotel
    # search (4-star) usually overshoots it, forcing at least one
    # renegotiation round -- see aggregator.py.
    cfg, snapshot = _run_to_interrupt(graph, BASE_REQUEST)
    payload = snapshot.tasks[0].interrupts[0].value
    assert payload["total_cost"] <= payload["budget"] or payload["over_budget"]


def test_approve_leads_to_booking(graph):
    cfg, _ = _run_to_interrupt(graph, BASE_REQUEST)
    for event in graph.stream(Command(resume={"action": "approve"}), cfg, stream_mode="values"):
        pass
    assert event["booking_confirmation"] is not None
    assert event["booking_confirmation"]["sandbox"] is True


def test_reject_does_not_book(graph):
    cfg, _ = _run_to_interrupt(graph, BASE_REQUEST)
    for event in graph.stream(Command(resume={"action": "reject"}), cfg, stream_mode="values"):
        pass
    assert event.get("booking_confirmation") is None


def test_supervisor_skips_itinerary_when_not_wanted(graph):
    request = {**BASE_REQUEST, "preferences": "just need a bed, purely functional trip"}
    cfg, snapshot = _run_to_interrupt(graph, request)
    payload = snapshot.tasks[0].interrupts[0].value
    assert payload["itinerary"] is None
