
import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_community.utilities import SerpAPIWrapper
from state import TripState
"""Wires every agent module into one compiled graph:

START -> supervisor -> [flight | hotel | itinerary] (parallel, Send)
      -> aggregator -> (renegotiate loop back to hotel) | human_approval
      -> human_approval (interrupt) -> booking_agent | END

Run this module directly for a quick MOCK_MODE smoke test; import
build_graph() from app.py for the real Streamlit UI.
"""
def search_travel_info(query: str):
    if not search:
        return "Search functionality is currently disabled because SERPAPI_API_KEY is missing."
    return search.run(query)


# Initialize SerpAPI Wrapper
search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_API_KEY", ""))
search = SerpAPIWrapper(serpapi_api_key="") if "" else None
def search_travel_info(query: str) -> str:
    """
    Searches Google for live travel details like flights, top attractions, 
    restaurants, or current hotel prices.
    """
    try:
        results = search.run(query)
        return results
    except Exception as e:
        return f"Error retrieving web search results: {str(e)}"
from agents.aggregator import aggregate_node, route_after_aggregate
from agents.booking_agent import booking_node
from agents.flight_agent import build_flight_subgraph
from agents.hotel_agent import build_hotel_subgraph
from agents.human_approval import human_approval_node, route_after_approval
from agents.itinerary_agent import build_itinerary_subgraph
from agents.supervisor import fan_out, supervisor_node
from persistence import get_checkpointer
from state import TripState


def build_graph():
    builder = StateGraph(TripState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("flight_agent", build_flight_subgraph())
    builder.add_node("hotel_agent", build_hotel_subgraph())
    builder.add_node("itinerary_agent", build_itinerary_subgraph())
    builder.add_node("aggregator", aggregate_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("booking_agent", booking_node)

    builder.set_entry_point("supervisor")
    builder.add_conditional_edges("supervisor", fan_out)

    builder.add_edge("flight_agent", "aggregator")
    builder.add_edge("hotel_agent", "aggregator")
    builder.add_edge("itinerary_agent", "aggregator")

    builder.add_conditional_edges("aggregator", route_after_aggregate)

    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"approve": "booking_agent", "reject": END},
    )
    builder.add_edge("booking_agent", END)

    return builder.compile(checkpointer=get_checkpointer())


if __name__ == "__main__":
    import uuid

    graph = build_graph()
    config_ = {"configurable": {"thread_id": str(uuid.uuid4())}}
    initial_state = {
        "request": {
            "origin": "BOM",
            "destination": "Goa",
            "depart_date": "2026-12-10",
            "return_date": "2026-12-14",
            "travelers": 2,
            "budget": 900.0,
            "hotel_stars_min": 4,
            "preferences": "want to see the beaches and try local food",
        },
        "user_id": "demo-user",
        "trace": [],
    }

    print("--- running until first interrupt ---")
    for event in graph.stream(initial_state, config_, stream_mode="values"):
        pass
    print("\n".join(event.get("trace", [])))

    snapshot = graph.get_state(config_)
    if snapshot.next:
        print("\n--- INTERRUPTED, awaiting human approval ---")
        print(snapshot.tasks[0].interrupts[0].value)

        from langgraph.types import Command

        print("\n--- resuming with approval ---")
        for event in graph.stream(Command(resume={"action": "approve"}), config_, stream_mode="values"):
            pass
        print("\n".join(event.get("trace", [])))
        print("\nBooking confirmation:", event.get("booking_confirmation"))
    

def suggest_places_node(state: TripState) -> TripState:
    dest = state.get("destination", "Destination")
    pref = state.get("preferences", "top tourist attractions")

    # Perform real-time search via SerpAPI
    query = f"top places to visit and food to eat in {dest} {pref}"
    search_results = search_travel_info(query)

    # Pass search results to Gemini for formatting
    prompt = f"""
    Based on the live web search results below, recommend the top 4 places and activities in {dest}:
    
    Search Results:
    {search_results}
    """
    response = llm.invoke(prompt)

    recs = response.content.split("\n")
    recs = [r.strip("- ") for r in recs if r.strip()]
    return {"recommendations": recs}