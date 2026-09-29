"""Thin, task-specific wrapper around the LLM.

Rather than passing a raw chat model around and building prompts inline
inside every node (hard to test, hard to read), each real task the graph
needs from the LLM gets its own method here. In MOCK_MODE these methods
return deterministic, hand-written outputs so the whole graph can run
end-to-end with zero API calls -- useful for tests, demos, and CI.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

import config


class _ItineraryNeed(BaseModel):
    wants_itinerary: bool = Field(
        description="True if the traveler's preferences mention activities, "
        "sightseeing, food, or things to do -- not just getting there and "
        "having a bed."
    )
    reason: str = Field(description="One short sentence explaining the decision.")


class TravelLLM:
    def __init__(self) -> None:
        self._model = None if config.MOCK_MODE else config.get_raw_model()

    # ------------------------------------------------------------------
    # Supervisor: does this request need the itinerary/RAG agent at all?
    # ------------------------------------------------------------------
    def wants_itinerary(self, preferences: str) -> bool:
        if config.MOCK_MODE:
            keywords = ("see", "visit", "activit", "food", "sight", "museum", "tour")
            return any(k in preferences.lower() for k in keywords) or preferences == ""
        structured = self._model.with_structured_output(_ItineraryNeed)
        result: _ItineraryNeed = structured.invoke(
            "Traveler preferences: "
            f"{preferences!r}\n\n"
            "Decide whether an itinerary/things-to-do agent should run for "
            "this trip."
        )
        return result.wants_itinerary

    # ------------------------------------------------------------------
    # Itinerary agent: turn RAG snippets + prefs into a short day plan
    # ------------------------------------------------------------------
    def write_itinerary(
        self, destination: str, days: int, preferences: str, guide_snippets: list[str]
    ) -> str:
        if config.MOCK_MODE:
            picks = guide_snippets[:days] or [f"Explore central {destination}."]
            lines = [f"Day {i + 1}: {snippet}" for i, snippet in enumerate(picks)]
            return "\n".join(lines)

        context = "\n\n".join(guide_snippets) if guide_snippets else "(no guide notes found)"
        prompt = (
            f"You are planning a {days}-day trip to {destination}.\n"
            f"Traveler preferences: {preferences or 'none stated'}\n\n"
            f"Destination guide notes:\n{context}\n\n"
            "Write one short line per day (Day 1: ..., Day 2: ...). "
            "Keep it grounded in the guide notes above, not invented facts."
        )
        response = self._model.invoke(prompt)
        return response.content
