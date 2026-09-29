"""Streamlit UI. Calls the compiled graph directly in-process (no
separate backend needed) -- exactly the "chatbot with UI" pattern from
the LangGraph fundamentals, just pointed at a bigger graph.

Run with: streamlit run app.py
"""

from __future__ import annotations

import uuid

import streamlit as st
from langgraph.types import Command

import config
from graph import build_graph
from memory.store import load_preferences

st.set_page_config(page_title="Multi-Agent Travel Booking", page_icon="🧳")
st.title("🧳 Multi-agent travel booking")
st.caption(
    f"Model: {config.MODEL_NAME} · Data source: "
    + ("mock (no API keys set)" if config.MOCK_MODE else "Amadeus self-service API")
)

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "thread_config" not in st.session_state:
    st.session_state.thread_config = None
if "awaiting_approval" not in st.session_state:
    st.session_state.awaiting_approval = None
if "final_state" not in st.session_state:
    st.session_state.final_state = None

graph = st.session_state.graph

user_id = st.sidebar.text_input("User ID (for personalization / memory)", value="demo-user")
remembered = load_preferences(user_id) if user_id else {}
if remembered:
    st.sidebar.success("Loaded remembered preferences for this user:")
    st.sidebar.json(remembered)

# ---------------------------------------------------------------------
# Trip request form -- structured fields, not free-text LLM parsing, for
# the fields that actually need to be correct (dates, budget).
# ---------------------------------------------------------------------
with st.form("trip_form"):
    col1, col2 = st.columns(2)
    origin = col1.text_input("Origin (IATA code)", value="BOM")
    destination = col2.text_input("Destination city", value="Goa")

    col3, col4 = st.columns(2)
    depart_date = col3.date_input("Depart")
    return_date = col4.date_input("Return")

    col5, col6, col7 = st.columns(3)
    travelers = col5.number_input("Travelers", min_value=1, max_value=8, value=2)
    budget = col6.number_input(
        "Budget (USD)", min_value=100.0, value=float(remembered.get("usual_budget", 900.0))
    )
    hotel_stars_min = col7.slider(
        "Min hotel stars", 1, 5, int(remembered.get("preferred_hotel_stars", 4))
    )

    preferences = st.text_area(
        "Preferences (free text -- activities, food, anything else)",
        value=remembered.get("preferences_notes", ""),
        placeholder="e.g. want to see the beaches and try local food",
    )

    submitted = st.form_submit_button("Plan my trip")

if submitted:
    thread_id = str(uuid.uuid4())
    st.session_state.thread_config = {"configurable": {"thread_id": thread_id}}
    st.session_state.awaiting_approval = None
    st.session_state.final_state = None

    initial_state = {
        "request": {
            "origin": origin,
            "destination": destination,
            "depart_date": str(depart_date),
            "return_date": str(return_date),
            "travelers": int(travelers),
            "budget": float(budget),
            "hotel_stars_min": int(hotel_stars_min),
            "preferences": preferences,
        },
        "user_id": user_id,
        "trace": [],
    }

    status_box = st.empty()
    lines: list[str] = []
    for event in graph.stream(initial_state, st.session_state.thread_config, stream_mode="values"):
        new_trace = event.get("trace", [])
        if len(new_trace) > len(lines):
            lines = new_trace
            status_box.code("\n".join(lines), language=None)

    snapshot = graph.get_state(st.session_state.thread_config)
    if snapshot.next:  # graph paused on interrupt()
        st.session_state.awaiting_approval = snapshot.tasks[0].interrupts[0].value
    else:
        st.session_state.final_state = snapshot.values

# ---------------------------------------------------------------------
# Human approval step
# ---------------------------------------------------------------------
if st.session_state.awaiting_approval:
    payload = st.session_state.awaiting_approval
    st.subheader("Review before booking")

    c1, c2, c3 = st.columns(3)
    c1.metric("Flight", payload["flight"]["summary"] if payload["flight"] else "—")
    c1.caption(f"${payload['flight']['cost']:.2f}" if payload["flight"] else "")
    c2.metric("Hotel", payload["hotel"]["summary"] if payload["hotel"] else "—")
    c2.caption(f"${payload['hotel']['cost']:.2f}" if payload["hotel"] else "")
    c3.metric("Total vs budget", f"${payload['total_cost']:.2f} / ${payload['budget']:.2f}")

    if payload["itinerary"]:
        st.markdown("**Suggested itinerary:**")
        st.text(payload["itinerary"]["summary"])

    if payload["over_budget"]:
        st.warning("This trip is still over budget after renegotiation -- approve only if that's okay.")

    approve_col, reject_col = st.columns(2)
    if approve_col.button("✅ Approve & book", use_container_width=True):
        for event in graph.stream(
            Command(resume={"action": "approve"}), st.session_state.thread_config, stream_mode="values"
        ):
            pass
        st.session_state.final_state = event
        st.session_state.awaiting_approval = None
        st.rerun()
    if reject_col.button("❌ Reject", use_container_width=True):
        for event in graph.stream(
            Command(resume={"action": "reject"}), st.session_state.thread_config, stream_mode="values"
        ):
            pass
        st.session_state.final_state = event
        st.session_state.awaiting_approval = None
        st.rerun()

# ---------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------
if st.session_state.final_state:
    final = st.session_state.final_state
    if final.get("booking_confirmation"):
        st.success(
            f"Booked! Confirmation `{final['booking_confirmation']['booking_id']}` "
            f"for ${final['booking_confirmation']['total_cost']:.2f} (sandbox, no real payment)."
        )
    else:
        st.info("Trip was not booked.")
    with st.expander("Full run trace"):
        st.code("\n".join(final.get("trace", [])), language=None)
