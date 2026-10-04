import os
import sys
from dotenv import load_dotenv

# Ensure local imports resolve properly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

import streamlit as st
from tools.flight_search import search_realtime_flights

st.title("✈️ Real-Time Flight Search")

origin = st.text_input("Origin Airport Code (e.g., JFK, KHI)", "JFK")
destination = st.text_input("Destination Airport Code (e.g., LAX, DXB)", "LAX")
depart_date = st.date_input("Departure Date")

if st.button("Search Flights"):
    if not origin or not destination:
        st.error("Please enter both origin and destination airport codes.")
    else:
        st.info(f"Searching live flights from {origin.upper()} to {destination.upper()}...")
        results = search_realtime_flights(origin.upper(), destination.upper(), depart_date)
        st.write(results)