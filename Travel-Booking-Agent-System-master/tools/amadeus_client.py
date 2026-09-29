"""Fallback tool stub (Amadeus disabled)."""

from langchain_core.tools import tool


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search flight options using mock data."""
    return (
        f"Mock Flight Search ({origin} -> {destination} on {date}):\n"
        f"- Flight FL-101 | Dep: 08:00 | $250\n"
        f"- Flight FL-202 | Dep: 15:30 | $310"
    )