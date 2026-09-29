"""Deterministic fake flight/hotel offers for MOCK_MODE.

Numbers are seeded off the destination string so the same request always
produces the same offers (useful for tests), and are intentionally priced
so a default $1500 budget trip *will* go over budget on the first pass --
that's what exercises the negotiation loop in the demo instead of it only
ever taking the happy path.
"""

from __future__ import annotations

import hashlib


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


def search_flights(origin: str, destination: str, cabin: str = "ECONOMY") -> dict | None:
    """Return a fake flight offer, or None to simulate 'no results'."""
    seed = _seed(origin + destination)
    if seed % 11 == 0:  # occasionally simulate a dead search to exercise retry
        return None
    base = 250 + (seed % 400)
    multiplier = {"ECONOMY": 1.0, "PREMIUM_ECONOMY": 1.4, "BUSINESS": 2.6}[cabin]
    price = round(base * multiplier, 2)
    return {
        "carrier": ["IndiGo", "Air India", "Emirates", "Lufthansa"][seed % 4],
        "cabin": cabin,
        "price": price,
        "stops": 0 if seed % 3 else 1,
    }


def search_hotels(destination: str, stars_min: int = 3, nights: int = 4) -> dict | None:
    seed = _seed(destination + str(stars_min))
    if seed % 13 == 0:
        return None
    per_night = 40 + stars_min * 25 + (seed % 60)
    return {
        "name": f"{destination.title()} {'Grand ' if stars_min >= 4 else ''}Hotel",
        "stars": stars_min,
        "per_night": per_night,
        "nights": nights,
        "price": round(per_night * nights, 2),
    }
