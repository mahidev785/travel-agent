import os
from serpapi import GoogleSearch

def search_realtime_flights(origin: str, destination: str, depart_date: str):
    """Fetches live flight options directly using SerpAPI Google Flights engine."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Error: SERPAPI_API_KEY is missing from environment variables."

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": str(depart_date),
        "type": "2",  # 2 = One-way flight
        "currency": "USD",
        "hl": "en",
        "api_key": api_key,
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # Check if best_flights exist in the response
        if "best_flights" in results and results["best_flights"]:
            flights_summary = []
            for flight in results["best_flights"]:
                flight_info = flight["flights"][0]
                airline = flight_info.get("airline", "Unknown Airline")
                flight_num = flight_info.get("flight_number", "")
                price = flight.get("price", "N/A")
                duration = flight.get("total_duration", "N/A")
                
                flights_summary.append(
                    f"✈️ **{airline}** ({flight_num}) — **${price}** | Duration: {duration} mins"
                )
            return "\n\n".join(flights_summary)
        
        elif "other_flights" in results and results["other_flights"]:
            flights_summary = []
            for flight in results["other_flights"]:
                flight_info = flight["flights"][0]
                airline = flight_info.get("airline", "Unknown Airline")
                price = flight.get("price", "N/A")
                flights_summary.append(f"✈️ **{airline}** — **${price}**")
            return "\n\n".join(flights_summary)
            
        else:
            return f"No flights found from {origin} to {destination} on {depart_date}. Try a future date."

    except Exception as e:
        return f"Flight search failed: {str(e)}"