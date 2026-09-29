"""Flight agent: its own subgraph with two nodes -- search, and a
retry/fallback decision -- rather than one function that hopes the API
call works. This is the failure-recovery pattern: a bad response degrades
the result instead of crashing the whole run.

Data source: mock data in MOCK_MODE, otherwise the Amadeus MCP server if
AMADEUS_MCP_URL/COMMAND is set, otherwise the plain Amadeus REST tool.
"""
from __future__ import annotations

import asyncio
import config
from langgraph.graph import END, START, StateGraph
from state import FlightAgentState
from tools import amadeus_client, flight_mcp, mock_data

MAX_ATTEMPTS = 3
# Progressively relax the ask if nothing comes back: try business, then
# premium economy, then plain economy, on the theory that a cabin filter
# is often why a search comes back empty in the sandbox data.
_CABIN_FALLBACK_ORDER = ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS"]


def _search_via_mcp(origin: str, destination: str, depart_date: str, return_date: str) -> dict | None:
    """Best-effort call into an Amadeus MCP server's flight-search tool.

    Community MCP servers don't share one fixed tool name/schema, so this
    picks the first tool that looks like a flight search and passes the
    obvious keyword args. If that guess is wrong for the server you're
    running, adjust the argument mapping below to match its actual schema.
    """

    async def _run():
        tools = await flight_mcp.get_flight_mcp_tools()
        candidate = next((t for t in tools if "flight" in t.name.lower()), None)
        if candidate is None:
            return None
        return await candidate.ainvoke(
            {
                "origin": origin,
                "destination": destination,
                "departureDate": depart_date,
                "returnDate": return_date,
            }
        )

    try:
        raw = asyncio.run(_run())
    except Exception:
        return None
    if not raw:
        return None
    # Community servers vary in return shape; this expects a dict-like
    # result with at minimum a price. Adjust to match your server.
    if isinstance(raw, dict) and "price" in raw:
        return raw
    return None


def _search(origin: str, destination: str, depart_date: str, return_date: str, cabin: str) -> dict | None:
    if config.MOCK_MODE:
        return mock_data.search_flights(origin, destination, cabin=cabin)
    if flight_mcp.MCP_CONFIGURED:
        result = _search_via_mcp(origin, destination, depart_date, return_date)
        if result:
            return result
        # fall through to REST if the MCP path came back empty
    return amadeus_client.search_flights(origin, destination, depart_date, return_date, cabin=cabin)


def search_node(state: FlightAgentState) -> dict:
    req = state["request"]
    attempt = state.get("flight_attempts", 0)
    cabin = _CABIN_FALLBACK_ORDER[min(attempt, len(_CABIN_FALLBACK_ORDER) - 1)]

    offer = _search(req["origin"], req["destination"], req["depart_date"], req["return_date"], cabin)
    trace = [f"flight_agent: attempt {attempt + 1} ({cabin}) -> {'found' if offer else 'empty'}"]

    if offer:
        return {
            "flight_result": {
                "status": "ok",
                "summary": f"{offer['carrier']} {offer['cabin']}, {offer['stops']} stop(s)",
                "cost": offer["price"],
                "payload": offer,
                "attempts": attempt + 1,
            },
            "flight_attempts": attempt + 1,
            "trace": trace,
        }
    return {"flight_result": None, "flight_attempts": attempt + 1, "trace": trace}


def fallback_node(state: FlightAgentState) -> dict:
    trace = ["flight_agent: no offer found after retries, returning degraded placeholder"]
    return {
        "flight_result": {
            "status": "degraded",
            "summary": "No live flight offer found -- showing an estimated fare so the trip can still be planned",
            "cost": 350.0,
            "payload": {},
            "attempts": state.get("flight_attempts", MAX_ATTEMPTS),
        },
        "trace": trace,
    }


def _route(state: FlightAgentState) -> str:
    if state.get("flight_result") is not None:
        return "done"
    if state.get("flight_attempts", 0) >= MAX_ATTEMPTS:
        return "fallback"
    return "retry"


def build_flight_subgraph():
    builder = StateGraph(FlightAgentState)
    builder.add_node("search", search_node)
    builder.add_node("fallback", fallback_node)
    builder.set_entry_point("search")
    builder.add_conditional_edges(
        "search", _route, {"done": END, "retry": "search", "fallback": "fallback"}
    )
    builder.add_edge("fallback", END)
    return builder.compile()
