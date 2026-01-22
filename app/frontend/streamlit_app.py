"""Streamlit frontend for Group Travel Optimiser."""
import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import os

st.set_page_config(
    page_title="Group Travel Optimiser",
    page_icon="✈️",
    layout="wide"
)

# API base URL - can be set via environment variable or Streamlit secrets
try:
    API_BASE_URL = os.getenv("API_BASE_URL")
    if not API_BASE_URL:
        try:
            API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000/api")
        except (AttributeError, FileNotFoundError, KeyError):
            API_BASE_URL = "http://localhost:8000/api"
except Exception:
    API_BASE_URL = "http://localhost:8000/api"

st.title("✈️ Group Travel Optimiser")
st.sidebar.title("Navigation")

# Page selection
page = st.sidebar.selectbox(
    "Choose a page",
    [
        "Manage Attendees",
        "Create Event (Form)",
        "Create Event (AI)",
        "Run Simulation",
        "View Results",
        "AI Summary",
        "Ask AI",
        # Phase 2 pages
        "Manage Hotels",
        "Hotels & Nights",
        "Transfers",
        "Operational View",
        "Finance View",
        "What-If Lab",
        "AI Brief"
    ]
)


def api_request(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Make API request."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            st.error(f"Unsupported method: {method}")
            return None
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None


# Page: Manage Attendees
if page == "Manage Attendees":
    st.header("Manage Attendees")
    
    tab1, tab2 = st.tabs(["CSV Upload", "Manual Entry"])
    
    with tab1:
        st.subheader("Upload CSV")
        st.info("CSV should have columns: employee_id, home_airport")
        uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])
        
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            
            if st.button("Import Attendees"):
                success_count = 0
                error_count = 0
                
                for _, row in df.iterrows():
                    attendee_data = {
                        "employee_id": str(row.get("employee_id", "")),
                        "home_airport": str(row.get("home_airport", "")).upper()[:3]
                    }
                    
                    if len(attendee_data["home_airport"]) == 3:
                        result = api_request("POST", "/attendees", attendee_data)
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1
                
                st.success(f"Imported {success_count} attendees. Errors: {error_count}")
    
    with tab2:
        st.subheader("Add Attendee Manually")
        
        with st.form("add_attendee_form"):
            employee_id = st.text_input("Employee ID *")
            home_airport = st.text_input("Home Airport (IATA code) *", max_chars=3).upper()
            travel_class = st.selectbox(
                "Travel Class",
                ["economy", "premium_economy", "business", "first"]
            )
            preferred_airports = st.text_input("Preferred Airports (comma-separated IATA codes)")
            preferred_airlines = st.text_input("Preferred Airlines (comma-separated codes)")
            
            submitted = st.form_submit_button("Add Attendee")
            
            if submitted:
                if employee_id and len(home_airport) == 3:
                    attendee_data = {
                        "employee_id": employee_id,
                        "home_airport": home_airport,
                        "travel_class": travel_class,
                        "preferred_airports": [p.strip() for p in preferred_airports.split(",") if p.strip()],
                        "preferred_airlines": [a.strip() for a in preferred_airlines.split(",") if a.strip()]
                    }
                    
                    result = api_request("POST", "/attendees", attendee_data)
                    if result:
                        st.success(f"Added attendee: {employee_id}")
                    else:
                        st.error("Failed to add attendee")
                else:
                    st.error("Please fill in required fields")
    
    # List attendees
    st.subheader("All Attendees")
    attendees_data = api_request("GET", "/attendees")
    if attendees_data:
        attendees = attendees_data.get("attendees", [])
        if attendees:
            df = pd.DataFrame([
                {
                    "ID": a["id"],
                    "Employee ID": a["employee_id"],
                    "Home Airport": a["home_airport"],
                    "Travel Class": a["travel_class"],
                    "Preferred Airports": ", ".join(a.get("preferred_airports", [])),
                    "Preferred Airlines": ", ".join(a.get("preferred_airlines", []))
                }
                for a in attendees
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No attendees yet")


# Page: Create Event (Form)
elif page == "Create Event (Form)":
    st.header("Create Event (Form)")
    
    with st.form("create_event_form"):
        event_name = st.text_input("Event Name *")
        
        st.subheader("Candidate Locations")
        locations_input = st.text_input("IATA Airport Codes (comma-separated) *", placeholder="LIS, MUC, LHR")
        
        st.subheader("Date Windows")
        num_windows = st.number_input("Number of Date Windows", min_value=1, max_value=5, value=1)
        
        date_windows = []
        for i in range(num_windows):
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input(f"Window {i+1} Start Date", value=date.today() + timedelta(days=30), key=f"start_{i}")
            with col2:
                end = st.date_input(f"Window {i+1} End Date", value=date.today() + timedelta(days=37), key=f"end_{i}")
            if start and end:
                date_windows.append({"start_date": start.isoformat(), "end_date": end.isoformat()})
        
        duration_days = st.number_input("Duration (days) *", min_value=1, max_value=30, value=3)
        created_by = st.text_input("Created By", value="admin")
        
        submitted = st.form_submit_button("Create Event")
        
        if submitted:
            if event_name and locations_input:
                locations = [loc.strip().upper() for loc in locations_input.split(",") if loc.strip()]
                
                if locations and date_windows:
                    event_data = {
                        "name": event_name,
                        "candidate_locations": locations,
                        "candidate_date_windows": date_windows,
                        "duration_days": duration_days,
                        "created_by": created_by
                    }
                    
                    result = api_request("POST", "/events", event_data)
                    if result:
                        st.success(f"Created event: {result['id']}")
                        st.json(result)
                    else:
                        st.error("Failed to create event")
                else:
                    st.error("Please provide at least one location and date window")
            else:
                st.error("Please fill in required fields")


# Page: Create Event (AI)
elif page == "Create Event (AI)":
    st.header("Create Event (AI Text Intake)")
    
    event_text = st.text_area(
        "Describe your event in natural language",
        placeholder="""Example: 
        We're planning a 3-day workshop in either Lisbon or Munich next month. 
        We need to accommodate 15 people traveling from various airports.""",
        height=200
    )
    
    if st.button("Parse Event"):
        if event_text:
            with st.spinner("Parsing event description..."):
                result = api_request("POST", "/ai/parse_event_text", {"text": event_text})
                
                if result:
                    st.success("Event parsed successfully!")
                    st.subheader("Parsed Event Preview")
                    st.json(result)
                    
                    # Confirmation form
                    if st.button("Confirm and Create Event"):
                        event_data = {
                            "name": result["name"],
                            "candidate_locations": result["candidate_locations"],
                            "candidate_date_windows": result["candidate_date_windows"],
                            "duration_days": result["duration_days"],
                            "created_by": result.get("created_by", "system")
                        }
                        
                        create_result = api_request("POST", "/events", event_data)
                        if create_result:
                            st.success(f"Event created: {create_result['id']}")
                            st.balloons()
                else:
                    st.error("Failed to parse event text")
        else:
            st.warning("Please enter event description")


# Page: Run Simulation
elif page == "Run Simulation":
    st.header("Run Simulation")
    
    # Get events
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found. Create an event first.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        if st.button("Run Simulation", type="primary"):
            with st.spinner("Running simulation... This may take a moment."):
                result = api_request("POST", f"/events/{event_id_input}/simulate")
                
                if result:
                    st.success("Simulation completed!")
                    st.json(result)
                else:
                    st.error("Simulation failed")


# Page: View Results
elif page == "View Results":
    st.header("View Simulation Results")
    
    # Get events
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
        
    if event_id_input:
        results_data = api_request("GET", f"/events/{event_id_input}/results/latest")
        
        if results_data:
            st.subheader("Ranked Options")
            
            # Create results table
            results = results_data.get("results", [])
            ranked = results_data.get("ranked_options", [])
            
            if results:
                # Display ranked table
                table_data = []
                for rank_idx, opt_idx in enumerate(ranked):
                    opt = results[opt_idx]
                    table_data.append({
                        "Rank": rank_idx + 1,
                        "Location": opt["location"],
                        "Date Window": f"{opt['date_window_start']} to {opt['date_window_end']}",
                        "Total Cost": f"${opt['total_cost']:,.2f}",
                        "Avg Travel Time": f"{opt['avg_travel_time_minutes']:.0f} min",
                        "Arrival Spread": f"{opt['arrival_spread_minutes']:.0f} min",
                        "Connections Rate": f"{opt['connections_rate']:.2%}",
                        "Score": f"{opt['score']:.2f}"
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # Expandable details
                st.subheader("Detailed Itineraries")
                for rank_idx, opt_idx in enumerate(ranked):
                    opt = results[opt_idx]
                    with st.expander(f"Rank {rank_idx + 1}: {opt['location']} - Score: {opt['score']:.2f}"):
                        st.write(f"**Total Cost:** ${opt['total_cost']:,.2f}")
                        st.write(f"**Average Travel Time:** {opt['avg_travel_time_minutes']:.0f} minutes")
                        st.write(f"**Arrival Spread:** {opt['arrival_spread_minutes']:.0f} minutes")
                        st.write(f"**Connections Rate:** {opt['connections_rate']:.2%}")
                        
                        st.write("**Per-Attendee Itineraries:**")
                        for ai in opt.get("attendee_itineraries", []):
                            st.write(f"- **{ai['employee_id']}**: {ai['itinerary']['airline']} "
                                   f"({ai['itinerary']['origin']} → {ai['itinerary']['destination']}), "
                                   f"{ai['itinerary']['stops']} stops, "
                                   f"${ai['itinerary']['price']:.2f}")
            else:
                st.info("No results available")
        else:
            st.warning("No simulation results found. Run a simulation first.")


# Page: AI Summary
elif page == "AI Summary":
    st.header("AI Executive Summary")
    
    # Get events
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        if st.button("Generate Summary", type="primary"):
            with st.spinner("Generating executive summary..."):
                result = api_request("POST", f"/events/{event_id_input}/ai/summary")
                
                if result:
                    st.success("Summary generated!")
                    st.markdown(f"### Executive Summary\n\n{result['summary']}")
                else:
                    st.error("Failed to generate summary")


# Page: Ask AI
elif page == "Ask AI":
    st.header("Ask AI About Results")
    
    # Get events
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    question = st.text_input("Ask a question about the simulation results")
    
    if event_id_input and question:
        if st.button("Ask", type="primary"):
            with st.spinner("Thinking..."):
                result = api_request("POST", f"/events/{event_id_input}/ask", {"question": question})
                
                if result:
                    st.markdown(f"### Answer\n\n{result['answer']}")
                    if result.get("confidence"):
                        st.caption(f"Confidence: {result['confidence']}")
                else:
                    st.error("Failed to get answer")


# Page: Manage Hotels
elif page == "Manage Hotels":
    st.header("Manage Hotels")
    
    tab1, tab2 = st.tabs(["List Hotels", "Add Hotel"])
    
    with tab1:
        st.subheader("All Hotels")
        airport_filter = st.text_input("Filter by Airport Code (optional)", max_chars=3).upper()
        approved_only = st.checkbox("Show approved only", value=False)
        
        params = {}
        if airport_filter:
            params["airport_code"] = airport_filter
        if approved_only:
            params["approved"] = "true"
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        endpoint = f"/hotels?{query_string}" if query_string else "/hotels"
        
        hotels_data = api_request("GET", endpoint)
        if hotels_data:
            df = pd.DataFrame([
                {
                    "ID": h["id"],
                    "Name": h["name"],
                    "City": h["city"],
                    "Airport": h["airport_code"],
                    "Chain": h.get("chain", ""),
                    "Approved": "Yes" if h["approved"] else "No",
                    "Corporate Rate": f"${h.get('corporate_rate', 0):.2f}" if h.get("corporate_rate") else "N/A",
                    "Capacity": h.get("capacity", "N/A"),
                    "Distance (km)": h.get("distance_to_venue_km", "N/A")
                }
                for h in hotels_data
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hotels found")
    
    with tab2:
        st.subheader("Add New Hotel")
        with st.form("add_hotel_form"):
            name = st.text_input("Hotel Name *")
            city = st.text_input("City *")
            airport_code = st.text_input("Airport Code (IATA) *", max_chars=3).upper()
            chain = st.text_input("Hotel Chain")
            approved = st.checkbox("Approved for corporate use")
            corporate_rate = st.number_input("Corporate Rate (USD/night)", min_value=0.0, value=150.0)
            distance_km = st.number_input("Distance to Venue (km)", min_value=0.0, value=5.0)
            capacity = st.number_input("Room Capacity", min_value=1, value=50)
            has_meeting_space = st.checkbox("Has Meeting Space")
            
            submitted = st.form_submit_button("Add Hotel")
            
            if submitted:
                if name and city and len(airport_code) == 3:
                    hotel_data = {
                        "name": name,
                        "city": city,
                        "airport_code": airport_code,
                        "chain": chain if chain else None,
                        "approved": approved,
                        "corporate_rate": corporate_rate,
                        "distance_to_venue_km": distance_km,
                        "capacity": capacity,
                        "has_meeting_space": has_meeting_space
                    }
                    
                    result = api_request("POST", "/hotels", hotel_data)
                    if result:
                        st.success(f"Added hotel: {name}")
                    else:
                        st.error("Failed to add hotel")
                else:
                    st.error("Please fill in required fields")


# Page: Hotels & Nights
elif page == "Hotels & Nights":
    st.header("Hotels & Room Nights Analysis")
    
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        results_data = api_request("GET", f"/events/{event_id_input}/results/latest")
        
        if results_data:
            results = results_data.get("results", [])
            ranked = results_data.get("ranked_options", [])
            
            if results:
                st.subheader("Hotel Assignments by Option")
                
                for rank_idx, opt_idx in enumerate(ranked[:5]):  # Top 5
                    opt = results[opt_idx]
                    with st.expander(f"Rank {rank_idx + 1}: {opt['location']}"):
                        if opt.get("hotel_assignment"):
                            hotel = opt["hotel_assignment"]
                            st.write(f"**Hotel:** {hotel.get('hotel_name', 'N/A')}")
                            st.write(f"**Total Cost:** ${hotel.get('total_cost', 0):,.2f}")
                            st.write(f"**Room Nights:** {hotel.get('room_nights', 0)}")
                            st.write(f"**Extra Nights:** {hotel.get('extra_nights', 0)}")
                            
                            if hotel.get("room_night_analysis"):
                                analysis = hotel["room_night_analysis"]
                                st.write(f"**Peak Occupancy:** {analysis.get('peak_occupancy', 0)} rooms")
                                
                                # Room night curve
                                if analysis.get("required_rooms_per_night"):
                                    st.line_chart(analysis["required_rooms_per_night"])
                        else:
                            st.info("No hotel assignment available")
            else:
                st.info("No results available")
        else:
            st.warning("No simulation results found. Run a simulation first.")


# Page: Transfers
elif page == "Transfers":
    st.header("Transfer Plans")
    
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        option_index = st.number_input("Option Index", min_value=0, value=0)
        
        transfer_plan_data = api_request("GET", f"/events/{event_id_input}/transfer-plan?option_index={option_index}")
        
        if transfer_plan_data:
            st.subheader("Transfer Plan")
            st.write(f"**Total Cost:** ${transfer_plan_data.get('total_cost', 0):,.2f}")
            st.write(f"**Total Vehicles:** {transfer_plan_data.get('total_vehicles', 0)}")
            st.write(f"**Complexity Score:** {transfer_plan_data.get('operational_complexity_score', 0):.2f}")
            
            st.subheader("Transfer Waves")
            for leg in transfer_plan_data.get("legs", []):
                wave = leg.get("wave", {})
                st.write(f"**Wave:** {wave.get('wave_start', 'N/A')} - {wave.get('wave_end', 'N/A')}")
                st.write(f"  - Mode: {leg.get('mode', 'N/A')}")
                st.write(f"  - Vehicles: {leg.get('vehicle_count', 0)}")
                st.write(f"  - Cost: ${leg.get('total_cost', 0):,.2f}")
                st.write(f"  - Capacity Utilization: {leg.get('capacity_utilization', 0):.1%}")
        else:
            st.warning("No transfer plan available. Run simulation with transfers enabled.")


# Page: Operational View
elif page == "Operational View":
    st.header("Operational View")
    
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        results_data = api_request("GET", f"/events/{event_id_input}/results/latest")
        
        if results_data:
            results = results_data.get("results", [])
            ranked = results_data.get("ranked_options", [])
            
            if results:
                best_option = results[ranked[0]]
                
                st.subheader("Arrival Histogram")
                if best_option.get("arrival_histogram"):
                    histogram = best_option["arrival_histogram"]
                    # Create DataFrame for chart
                    hours = list(range(24))
                    df_hist = pd.DataFrame({
                        "Hour": hours,
                        "Arrivals": histogram
                    })
                    st.bar_chart(df_hist.set_index("Hour"))
                
                st.subheader("Key Metrics")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Arrival Spread", f"{best_option.get('arrival_spread_minutes', 0):.0f} min")
                with col2:
                    st.metric("Late Arrival Risk", f"{best_option.get('late_arrival_risk', 0):.1%}")
                with col3:
                    st.metric("Operational Complexity", f"{best_option.get('operational_complexity_score', 0):.1f}")
                with col4:
                    st.metric("CO2 Estimate", f"{best_option.get('co2_estimate_kg', 0):.1f} kg")
            else:
                st.info("No results available")
        else:
            st.warning("No simulation results found.")


# Page: Finance View
elif page == "Finance View":
    st.header("Finance View")
    
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        format_choice = st.selectbox("Export Format", ["json", "csv"])
        
        if st.button("Generate Finance Export"):
            finance_data = api_request("GET", f"/events/{event_id_input}/export/finance?format={format_choice}")
            
            if finance_data:
                if format_choice == "json":
                    st.json(finance_data)
                else:
                    st.download_button(
                        label="Download CSV",
                        data=finance_data if isinstance(finance_data, str) else str(finance_data),
                        file_name=f"finance_export_{event_id_input}.csv",
                        mime="text/csv"
                    )
                
                # Cost waterfall
                st.subheader("Cost Breakdown")
                if isinstance(finance_data, dict):
                    costs = finance_data.get("cost_by_category", {})
                    if costs:
                        df_costs = pd.DataFrame(list(costs.items()), columns=["Category", "Cost"])
                        st.bar_chart(df_costs.set_index("Category"))
            else:
                st.error("Failed to generate finance export")


# Page: What-If Lab
elif page == "What-If Lab":
    st.header("What-If Exploration Lab")
    
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        if st.button("Run What-If Exploration", type="primary"):
            with st.spinner("Exploring variations..."):
                whatif_results = api_request("POST", f"/events/{event_id_input}/ai/whatif")
                
                if whatif_results:
                    st.success(f"Generated {len(whatif_results)} variations")
                    
                    for idx, result in enumerate(whatif_results):
                        proposal = result.get("proposal", {})
                        st.subheader(f"Variation {idx + 1}: {proposal.get('description', 'N/A')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Delta Cost", f"${result.get('delta_cost', 0):,.2f}")
                        with col2:
                            st.metric("Delta Score", f"{result.get('delta_score', 0):.2f}")
                        
                        new_result = result.get("new_result", {})
                        st.write(f"**New Total Cost:** ${new_result.get('total_cost', 0):,.2f}")
                        st.write(f"**New Score:** {new_result.get('score', 0):.2f}")
                else:
                    st.error("What-if exploration failed")


# Page: AI Brief
elif page == "AI Brief":
    st.header("AI Organiser Brief")
    
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list):
        events = events_data
    else:
        events = []
    
    if not events:
        st.warning("No events found.")
        event_id_input = st.text_input("Or enter Event ID manually")
    else:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events}
        selected_event_name = st.selectbox("Select Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    
    if event_id_input:
        if st.button("Generate Brief", type="primary"):
            with st.spinner("Generating comprehensive brief..."):
                brief_data = api_request("GET", f"/events/{event_id_input}/export/brief")
                
                if brief_data:
                    st.success("Brief generated!")
                    st.markdown(f"### Executive Summary\n\n{brief_data.get('executive_summary', 'N/A')}")
                    st.markdown(f"### Recommended Option\n\n{brief_data.get('recommended_option', {})}")
                    st.markdown(f"### Operational Plan\n\n{brief_data.get('operational_plan', 'N/A')}")
                    st.markdown(f"### Hotel Plan\n\n{brief_data.get('hotel_plan', 'N/A')}")
                    st.markdown(f"### Transfer Plan\n\n{brief_data.get('transfer_plan', 'N/A')}")
                    st.markdown(f"### Booking Instructions\n\n{brief_data.get('booking_instructions', 'N/A')}")
                else:
                    st.error("Failed to generate brief")
