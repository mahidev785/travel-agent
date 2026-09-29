"""Long-term memory: preferences that persist *across* sessions, keyed by
user_id -- as opposed to the checkpointer (persistence.py), which persists
the state of a single *in-progress* run keyed by thread_id.

Uses LangGraph's Store interface. InMemoryStore is fine for a demo; swap
in a persistent implementation (e.g. a Postgres- or SQLite-backed Store)
for anything that needs to survive a process restart.
"""

from __future__ import annotations

from langgraph.store.memory import InMemoryStore

_NAMESPACE = ("traveler_preferences",)

store = InMemoryStore()


def load_preferences(user_id: str) -> dict:
    item = store.get(_NAMESPACE, user_id)
    return item.value if item else {}


def save_preferences(user_id: str, request: dict, chosen_flight: dict, chosen_hotel: dict) -> None:
    """Called after a booking completes, so next time the same user asks
    for a trip, we already know their preferred cabin, hotel star rating,
    and dietary notes.
    """
    prefs = load_preferences(user_id)
    prefs.update(
        {
            "preferred_cabin": chosen_flight.get("cabin", prefs.get("preferred_cabin")),
            "preferred_hotel_stars": chosen_hotel.get("stars", prefs.get("preferred_hotel_stars")),
            "usual_budget": request.get("budget", prefs.get("usual_budget")),
            "preferences_notes": request.get("preferences", prefs.get("preferences_notes")),
        }
    )
    store.put(_NAMESPACE, user_id, prefs)
