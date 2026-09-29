"""Booking agent: only reached after human approval. Writes a booking
record to SQLite and updates long-term memory with the traveler's chosen
cabin/hotel tier so next time's defaults are already personalized.

In MOCK_MODE and against Amadeus's test environment alike, this creates
a *sandbox* confirmation -- no real payment, no real ticket. That's the
right thing for a demo; just don't present it as booking real travel.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

import config
from memory import store as long_term_memory
from state import TripState


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            destination TEXT,
            total_cost REAL,
            flight_summary TEXT,
            hotel_summary TEXT,
            itinerary_summary TEXT,
            created_at TEXT
        )
        """
    )


def booking_node(state: TripState) -> dict:
    req = state["request"]
    flight = state.get("flight_result") or {}
    hotel = state.get("hotel_result") or {}
    itinerary = state.get("itinerary_result") or {}

    booking_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    try:
        _init_db(conn)
        conn.execute(
            "INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                booking_id,
                state.get("user_id", "anonymous"),
                req["destination"],
                state.get("total_cost", 0.0),
                flight.get("summary", ""),
                hotel.get("summary", ""),
                itinerary.get("summary", ""),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    long_term_memory.save_preferences(
        state.get("user_id", "anonymous"),
        req,
        flight.get("payload", {}),
        hotel.get("payload", {}),
    )

    confirmation = {
        "booking_id": booking_id,
        "destination": req["destination"],
        "total_cost": state.get("total_cost", 0.0),
        "sandbox": True,
    }
    return {
        "booking_confirmation": confirmation,
        "trace": [f"booking_agent: confirmed sandbox booking {booking_id}"],
    }
