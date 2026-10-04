import os
from langchain_community.utilities import SerpAPIWrapper

def search_realtime_flights(origin: str, destination: str, depart_date: str):
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Error: SERPAPI_API_KEY is not configured in .env"

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": str(depart_date),
        "currency": "USD",
        "hl": "en",
    }
    
    search = SerpAPIWrapper(params=params, serpapi_api_key=api_key)
    try:
        return search.run(f"Flights from {origin} to {destination} on {depart_date}")
    except Exception as e:
        return f"Flight search failed: {str(e)}"