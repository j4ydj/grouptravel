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
    page_icon="",
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

st.title("Group Travel Optimiser")
st.markdown('<div class="app-subtitle">Internal decision-support tool for comparing locations and dates for group travel.</div>', unsafe_allow_html=True)
st.markdown('<div class="app-divider"></div>', unsafe_allow_html=True)

# Visual polish (more noticeable)
st.markdown(
    """
    <style>
    :root { --gt-border: #e5e7eb; --gt-text: #111827; --gt-muted: #6b7280; --gt-bg: #f7f8fa; }
    html, body, .main { background-color: var(--gt-bg); }
    .main .block-container { padding-top: 1.75rem; padding-bottom: 2.5rem; }
    .main h1 { font-size: 2.1rem; font-weight: 600; color: var(--gt-text); }
    .main h2, .main h3 { font-weight: 600; color: var(--gt-text); }
    .app-subtitle { color: var(--gt-muted); margin-top: -0.75rem; margin-bottom: 0.75rem; }
    .app-divider { height: 1px; background: var(--gt-border); margin: 0.75rem 0 1.25rem 0; }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid var(--gt-border); }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 { color: var(--gt-text); }
    div[data-testid="stMetric"] { background: #ffffff; padding: 12px; border-radius: 10px; border: 1px solid var(--gt-border); }
    .stDataFrame { background: #ffffff; border-radius: 10px; border: 1px solid var(--gt-border); }
    details { background: #ffffff; border-radius: 10px; border: 1px solid var(--gt-border); padding: 0.25rem 0.75rem; }
    div[data-testid="stForm"] { background: #ffffff; border-radius: 12px; border: 1px solid var(--gt-border); padding: 1rem; }
    div[data-testid="stTabs"] { background: #ffffff; border-radius: 12px; border: 1px solid var(--gt-border); padding: 0.25rem; }
    button[kind="primary"] { background: #111827; border: none; border-radius: 8px; }
    button[kind="secondary"] { border: 1px solid var(--gt-border); border-radius: 8px; }
    label { color: var(--gt-text) !important; }
    .stCaption { color: var(--gt-muted); }
    .topbar { display: flex; align-items: center; justify-content: space-between; background: #ffffff; border: 1px solid var(--gt-border); border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 1rem; }
    .topbar-title { font-weight: 600; color: var(--gt-text); }
    .topbar-meta { color: var(--gt-muted); font-size: 0.9rem; }
    .footer { color: var(--gt-muted); font-size: 0.85rem; margin-top: 1.5rem; text-align: center; }
    .step-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0 1rem 0; }
    .step-chip { background: #ffffff; border: 1px solid var(--gt-border); border-radius: 999px; padding: 0.25rem 0.75rem; font-size: 0.85rem; color: var(--gt-text); }
    </style>
    """,
    unsafe_allow_html=True
)

# Branded top bar
st.markdown(
    '<div class="topbar"><div class="topbar-title">Group Travel Optimiser</div><div class="topbar-meta">Internal • MVP</div></div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="step-chips">'
    '<div class="step-chip">1. Event</div>'
    '<div class="step-chip">2. Attendees</div>'
    '<div class="step-chip">3. Hotels</div>'
    '<div class="step-chip">4. Simulate</div>'
    '<div class="step-chip">5. Results</div>'
    '<div class="step-chip">6. Itineraries</div>'
    '<div class="step-chip">7. Summary</div>'
    '</div>',
    unsafe_allow_html=True
)
st.sidebar.title("Navigation")

# Page selection
page = st.sidebar.selectbox(
    "Choose a page",
    [
        "Trip Flow",
        "Manage Attendees"
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
        elif method == "PUT":
            response = requests.put(url, json=data)
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
    
    tab1, tab2, tab3 = st.tabs(["CSV Upload", "Manual Entry", "Edit Attendee"])
    
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
            employee_id = st.text_input("Employee ID *", help="Unique ID (no names or emails).")
            home_airport = st.text_input(
                "Home Airport (IATA code) *",
                max_chars=3,
                help="3-letter airport code, e.g. LHR, JFK."
            ).upper()
            travel_class = st.selectbox(
                "Travel Class",
                ["economy", "premium_economy", "business", "first"]
            )
            preferred_airports = st.text_input("Preferred Airports (comma-separated IATA codes)", help="Optional, e.g. LHR, LGW")
            preferred_airlines = st.text_input("Preferred Airlines (comma-separated codes)", help="Optional, e.g. BA, LH")
            
            submitted = st.form_submit_button("Add Attendee")
            
            if submitted:
                is_iata = len(home_airport) == 3 and home_airport.isalpha()
                if employee_id and is_iata:
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
                    st.error("Please fill in required fields. Home Airport must be a 3-letter IATA code.")
    
    with tab3:
        st.subheader("Edit Attendee")
        
        # Fetch all attendees for dropdown
        attendees_data = api_request("GET", "/attendees")
        if attendees_data:
            attendees = attendees_data.get("attendees", [])
            if attendees:
                # Create dropdown options
                attendee_options = {f"{a['employee_id']} ({a['home_airport']})": a for a in attendees}
                selected_display = st.selectbox("Select Attendee to Edit", list(attendee_options.keys()))
                
                if selected_display:
                    selected_attendee = attendee_options[selected_display]
                    
                    with st.form("edit_attendee_form"):
                        st.text_input("Employee ID", value=selected_attendee["employee_id"], disabled=True, help="Employee ID cannot be changed")
                        
                        home_airport = st.text_input("Home Airport (IATA code) *", value=selected_attendee["home_airport"], max_chars=3).upper()
                        
                        travel_class = st.selectbox(
                            "Travel Class",
                            ["economy", "premium_economy", "business", "first"],
                            index=["economy", "premium_economy", "business", "first"].index(selected_attendee.get("travel_class", "economy"))
                        )
                        
                        preferred_airports_str = ", ".join(selected_attendee.get("preferred_airports", []))
                        preferred_airports = st.text_input("Preferred Airports (comma-separated IATA codes)", value=preferred_airports_str)
                        
                        preferred_airlines_str = ", ".join(selected_attendee.get("preferred_airlines", []))
                        preferred_airlines = st.text_input("Preferred Airlines (comma-separated codes)", value=preferred_airlines_str)
                        
                        timezone = st.text_input("Timezone", value=selected_attendee.get("timezone") or "")
                        
                        submitted = st.form_submit_button("Update Attendee")
                        
                        if submitted:
                            if len(home_airport) == 3:
                                update_data = {
                                    "home_airport": home_airport,
                                    "travel_class": travel_class,
                                    "preferred_airports": [p.strip() for p in preferred_airports.split(",") if p.strip()],
                                    "preferred_airlines": [a.strip() for a in preferred_airlines.split(",") if a.strip()]
                                }
                                
                                if timezone:
                                    update_data["timezone"] = timezone
                                elif selected_attendee.get("timezone"):
                                    # Allow clearing timezone by submitting empty
                                    update_data["timezone"] = None
                                
                                result = api_request("PUT", f"/attendees/{selected_attendee['id']}", update_data)
                                if result:
                                    st.success(f"Updated attendee: {selected_attendee['employee_id']}")
                                    st.rerun()  # Refresh to show updated data
                                else:
                                    st.error("Failed to update attendee")
                            else:
                                st.error("Home Airport must be 3 characters")
            else:
                st.info("No attendees available. Add attendees first.")
        else:
            st.warning("Could not fetch attendees list")
    
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


# Page: Trip Flow
elif page == "Trip Flow":
    st.header("Trip Flow")
    st.caption("Create event → attach attendees → simulate → review results → generate summary")
    
    # Step 1: Select or create event
    st.subheader("Step 1 — Create or Select Event")
    events_data = api_request("GET", "/events")
    if events_data and isinstance(events_data, list) and events_data:
        event_options = {f"{e['name']} ({e['id']})": e['id'] for e in events_data}
        selected_event_name = st.selectbox("Select Existing Event", list(event_options.keys()))
        event_id_input = event_options[selected_event_name]
    else:
        st.info("No events found. Create a new event below.")
        event_id_input = None
    
    with st.expander("Create New Event"):
        with st.form("trip_flow_create_event"):
            event_name = st.text_input("Event Name *")
            locations_input = st.text_input("Destination Airports (IATA codes) *", placeholder="LIS, MUC")
            num_windows = st.number_input("Number of Date Options", min_value=1, max_value=3, value=2)
            
            date_windows = []
            for i in range(int(num_windows)):
                col1, col2 = st.columns(2)
                with col1:
                    start = st.date_input(f"Option {i+1} Depart Date", value=date.today() + timedelta(days=30), key=f"tf_start_{i}")
                with col2:
                    end = st.date_input(f"Option {i+1} Return Date", value=date.today() + timedelta(days=37), key=f"tf_end_{i}")
                if start and end:
                    if end < start:
                        st.error(f"Option {i+1}: Return date must be after depart date.")
                        continue
                    date_windows.append({"start_date": start.isoformat(), "end_date": end.isoformat()})
            
            duration_days = st.number_input("Duration (days)", min_value=1, max_value=30, value=3)
            created_by = st.text_input("Created By", value="admin")
            
            submitted = st.form_submit_button("Create Event")
            if submitted:
                locations = [loc.strip().upper() for loc in locations_input.split(",") if loc.strip()]
                invalid_locations = [loc for loc in locations if len(loc) != 3 or not loc.isalpha()]
                if invalid_locations:
                    st.error(f"Invalid IATA codes: {', '.join(invalid_locations)}")
                    st.stop()
                if len(locations) < 1 or len(locations) > 3:
                    st.error("Please provide 1–3 destination airports.")
                    st.stop()
                if not date_windows:
                    st.error("Please provide at least one valid date option.")
                    st.stop()
                
                event_data = {
                    "name": event_name,
                    "candidate_locations": locations,
                    "candidate_date_windows": date_windows,
                    "duration_days": duration_days,
                    "created_by": created_by
                }
                create_result = api_request("POST", "/events", event_data)
                if create_result:
                    st.success(f"Event created: {create_result['id']}")
                    st.rerun()
    
    # Step 2: Attach attendees
    st.subheader("Step 2 — Attach Attendees")
    if event_id_input:
        attendees_data = api_request("GET", "/attendees")
        if attendees_data:
            attendees = attendees_data.get("attendees", [])
            if attendees:
                attendee_options = {f"{a['employee_id']} ({a['home_airport']})": a['id'] for a in attendees}
                selected_attendee_ids = st.multiselect(
                    "Select Attendees",
                    options=list(attendee_options.keys()),
                    default=list(attendee_options.keys())
                )
                if st.button("Attach Attendees"):
                    attendee_ids = [attendee_options[name] for name in selected_attendee_ids]
                    if not attendee_ids:
                        st.error("Select at least one attendee before attaching.")
                        st.stop()
                    attach_result = api_request("POST", f"/events/{event_id_input}/attendees", {"attendee_ids": attendee_ids})
                    if attach_result:
                        st.success(f"Attached {len(attendee_ids)} attendees.")
                    else:
                        st.error("Failed to attach attendees.")
            else:
                st.info("No attendees available. Add attendees first.")
        else:
            st.warning("Could not fetch attendees list.")
    else:
        st.info("Select or create an event to attach attendees.")
    
    # Step 3: Hotels (optional)
    st.subheader("Step 3 — Hotels (Optional)")
    if event_id_input:
        event_data = api_request("GET", f"/events/{event_id_input}")
        candidate_locations = []
        if event_data:
            candidate_locations = event_data.get("candidate_locations", [])

        hotels_data = api_request("GET", "/hotels")
        if hotels_data and isinstance(hotels_data, list):
            hotels_for_event = [
                h for h in hotels_data
                if not candidate_locations or h.get("airport_code") in candidate_locations
            ]
            if hotels_for_event:
                hotel_options = {
                    f"{h['name']} ({h['airport_code']})": h["id"]
                    for h in hotels_for_event
                }
                selected_hotels = st.multiselect(
                    "Select Hotels to Include",
                    options=list(hotel_options.keys()),
                    default=list(hotel_options.keys())
                )
                st.info("Hotels are included automatically for matching destinations.")
            else:
                st.info("No hotels found for the selected destinations.")
        else:
            st.info("No hotels available. Ask me to add hotels if needed.")
    else:
        st.info("Select or create an event to see hotels.")

    # Step 4: Run simulation
    st.subheader("Step 4 — Run Simulation")
    if event_id_input:
        if st.button("Run Simulation", type="primary"):
            with st.spinner("Running simulation..."):
                result = api_request("POST", f"/events/{event_id_input}/simulate")
                if result:
                    st.success("Simulation completed!")
                else:
                    st.error("Simulation failed.")
    
    # Step 5: Results overview
    st.subheader("Step 5 — Results Overview")
    if event_id_input:
        results_data = api_request("GET", f"/events/{event_id_input}/results/latest")
        if results_data:
            results = results_data.get("results", [])
            ranked = results_data.get("ranked_options", [])
            if results:
                table_data = []
                for rank_idx, opt_idx in enumerate(ranked):
                    opt = results[opt_idx]
                    table_data.append({
                        "Rank": rank_idx + 1,
                        "Location": opt["location"],
                        "Dates": f"{opt['date_window_start']} → {opt['date_window_end']}",
                        "Total Cost": f"${opt['total_cost']:,.2f}",
                        "Avg Travel Time": f"{opt['avg_travel_time_minutes']:.0f} min",
                        "Arrival Spread": f"{opt['arrival_spread_minutes']:.0f} min",
                        "Connections Rate": f"{opt['connections_rate']:.2%}",
                        "Score": f"{opt['score']:.2f}"
                    })
                st.dataframe(pd.DataFrame(table_data), use_container_width=True)
            else:
                st.info("No results available yet.")
        else:
            st.info("Run a simulation to see results.")

    # Step 6: Itinerary Details
    st.subheader("Step 6 — Itinerary Details")
    if event_id_input:
        results_data = api_request("GET", f"/events/{event_id_input}/results/latest")
        if results_data:
            results = results_data.get("results", [])
            ranked = results_data.get("ranked_options", [])
            if results and ranked:
                for rank_idx, opt_idx in enumerate(ranked):
                    opt = results[opt_idx]
                    with st.expander(f"Option {rank_idx + 1}: {opt['location']} ({opt['date_window_start']} → {opt['date_window_end']})"):
                        st.write(f"**Total Cost:** ${opt['total_cost']:,.2f}")
                        st.write(f"**Avg Travel Time:** {opt['avg_travel_time_minutes']:.0f} minutes")
                        st.write(f"**Arrival Spread:** {opt['arrival_spread_minutes']:.0f} minutes")
                        st.write(f"**Connections Rate:** {opt['connections_rate']:.2%}")
                        st.write("**Per-Attendee Itineraries:**")
                        for ai in opt.get("attendee_itineraries", []):
                            itinerary = ai.get("itinerary", {})
                            if itinerary.get("airline") == "LOCAL" or itinerary.get("travel_minutes") == 0:
                                st.write(f"- **{ai['employee_id']}**: Local attendee (no flight needed)")
                            else:
                                flight_number = itinerary.get("flight_number")
                                times = f"{itinerary.get('depart_time')} → {itinerary.get('arrive_time')}"
                                flight_label = f"{itinerary['airline']}" + (f" {flight_number}" if flight_number else "")
                                st.write(
                                    f"- **{ai['employee_id']}**: {flight_label} "
                                    f"({itinerary['origin']} → {itinerary['destination']}), "
                                    f"{times}, {itinerary['stops']} stops, "
                                    f"${itinerary['price']:.2f}"
                                )
                                segments = itinerary.get("segments", [])
                                if segments:
                                    for seg in segments:
                                        seg_label = f"  • {seg.get('leg','outbound').title()} {seg.get('segment_index', 0)+1}: "
                                        seg_label += f"{seg.get('origin')} → {seg.get('destination')} "
                                        seg_label += f"{seg.get('depart_time')} → {seg.get('arrive_time')} "
                                        seg_label += f"({seg.get('airline')} {seg.get('flight_number','')})"
                                        st.write(seg_label)
            else:
                st.info("No results available yet.")
        else:
            st.info("Run a simulation to see itinerary details.")
    
    # Step 7: AI Summary
    st.subheader("Step 7 — Executive Summary")
    if event_id_input:
        if st.button("Generate Executive Summary"):
            with st.spinner("Generating summary..."):
                summary = api_request("POST", f"/events/{event_id_input}/ai/summary")
                if summary and summary.get("summary"):
                    st.markdown(summary["summary"])
                else:
                    st.error("Summary failed. Ensure a simulation exists and LLM is configured.")
    st.markdown('<div class="footer">Version 0.4 • Updated today</div>', unsafe_allow_html=True)
    


# Page: Create Event (Form)
elif page == "Create Event (Form)":
    st.header("Create Event (Form)")
    
    with st.form("create_event_form"):
        event_name = st.text_input("Event Name *")
        
        st.subheader("Candidate Locations")
        locations_input = st.text_input(
            "IATA Airport Codes (comma-separated) *",
            placeholder="LIS, MUC, LHR",
            help="Use 1–3 destination airports."
        )
        
        st.subheader("Date Options (Depart/Return)")
        num_windows = st.number_input("Number of Date Options", min_value=1, max_value=5, value=2)
        
        date_windows = []
        for i in range(int(num_windows)):
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input(f"Option {i+1} Depart Date", value=date.today() + timedelta(days=30), key=f"start_{i}")
            with col2:
                end = st.date_input(f"Option {i+1} Return Date", value=date.today() + timedelta(days=37), key=f"end_{i}")
            if start and end:
                if end < start:
                    st.error(f"Option {i+1}: Return date must be after depart date.")
                    continue
                date_windows.append({"start_date": start.isoformat(), "end_date": end.isoformat()})
        
        duration_days = st.number_input("Duration (days) *", min_value=1, max_value=30, value=3, help="Workshop duration.")
        created_by = st.text_input("Created By", value="admin")
        
        submitted = st.form_submit_button("Create Event")
        
        if submitted:
            if event_name and locations_input:
                locations = [loc.strip().upper() for loc in locations_input.split(",") if loc.strip()]
                invalid_locations = [loc for loc in locations if len(loc) != 3 or not loc.isalpha()]
                if invalid_locations:
                    st.error(f"Invalid IATA codes: {', '.join(invalid_locations)}")
                    st.stop()
                if len(locations) < 1 or len(locations) > 3:
                    st.error("Please provide 1–3 destination airports.")
                    st.stop()
                
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
        # Attendee attachment section
        st.subheader("Attach Attendees")
        
        # Fetch all attendees
        attendees_data = api_request("GET", "/attendees")
        if attendees_data:
            attendees = attendees_data.get("attendees", [])
            if attendees:
                attendee_options = {f"{a['employee_id']} ({a['home_airport']})": a['id'] for a in attendees}
                selected_attendee_ids = st.multiselect(
                    "Select Attendees",
                    options=list(attendee_options.keys()),
                    default=list(attendee_options.keys())  # Select all by default
                )
                
                if st.button("Attach Selected Attendees"):
                    # Convert display names back to IDs
                    attendee_ids = [attendee_options[name] for name in selected_attendee_ids]
                    if not attendee_ids:
                        st.error("Select at least one attendee before attaching.")
                        st.stop()
                    
                    attach_result = api_request(
                        "POST",
                        f"/events/{event_id_input}/attendees",
                        {"attendee_ids": attendee_ids}
                    )
                    
                    if attach_result:
                        st.success(f"Attached {len(attendee_ids)} attendees to event")
                    else:
                        st.error("Failed to attach attendees")
            else:
                st.info("No attendees available. Add attendees first.")
        else:
            st.warning("Could not fetch attendees list")
        
        st.divider()
        
        # Simulation section
        st.subheader("Run Simulation")
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
                    flight_cost = opt.get("flight_cost", opt["total_cost"])
                    hotel_cost = opt.get("hotel_cost", 0.0)
                    transfer_cost = opt.get("transfer_cost", 0.0)
                    table_data.append({
                        "Rank": rank_idx + 1,
                        "Location": opt["location"],
                        "Date Window": f"{opt['date_window_start']} to {opt['date_window_end']}",
                        "Total Cost": f"${opt['total_cost']:,.2f}",
                        "Flight Cost": f"${flight_cost:,.2f}",
                        "Hotel Cost": f"${hotel_cost:,.2f}",
                        "Transfer Cost": f"${transfer_cost:,.2f}",
                        "Avg Travel Time": f"{opt['avg_travel_time_minutes']:.0f} min",
                        "Arrival Spread": f"{opt['arrival_spread_minutes']:.0f} min",
                        "Connections Rate": f"{opt['connections_rate']:.2%}",
                        "Score": f"{opt['score']:.2f}"
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # Comparison grid (top 3)
                st.subheader("Top Options Comparison")
                top_indices = ranked[:3]
                comparison_rows = []
                for rank_idx, opt_idx in enumerate(top_indices):
                    opt = results[opt_idx]
                    itineraries = opt.get("attendee_itineraries", [])
                    attendee_count = max(len(itineraries), 1)
                    cost_per_attendee = opt["total_cost"] / attendee_count
                    flight_cost = opt.get("flight_cost", opt["total_cost"])
                    hotel_cost = opt.get("hotel_cost", 0.0)
                    comparison_rows.append({
                        "Rank": rank_idx + 1,
                        "Location": opt["location"],
                        "Dates": f"{opt['date_window_start']} → {opt['date_window_end']}",
                        "Total Cost": f"${opt['total_cost']:,.2f}",
                        "Flight Cost": f"${flight_cost:,.2f}",
                        "Hotel Cost": f"${hotel_cost:,.2f}",
                        "Cost per Attendee": f"${cost_per_attendee:,.2f}",
                        "Avg Travel Time": f"{opt['avg_travel_time_minutes']:.0f} min",
                        "Arrival Spread": f"{opt['arrival_spread_minutes']:.0f} min",
                        "Connections": f"{opt['connections_rate']:.2%}"
                    })
                st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True)

                # Recommended option summary
                if ranked:
                    best_option = results[ranked[0]]
                    st.subheader("Recommended Option")
                    
                    itineraries = best_option.get("attendee_itineraries", [])
                    attendee_count = max(len(itineraries), 1)
                    cost_per_attendee = best_option["total_cost"] / attendee_count
                    travel_times = [ai.get("itinerary", {}).get("travel_minutes", 0) for ai in itineraries]
                    travel_times = [t for t in travel_times if isinstance(t, (int, float))]
                    median_travel_time = int(pd.Series(travel_times).median()) if travel_times else 0
                    local_count = sum(
                        1 for ai in itineraries
                        if ai.get("itinerary", {}).get("airline") == "LOCAL"
                        or ai.get("itinerary", {}).get("travel_minutes") == 0
                    )
                    arrival_times = []
                    for ai in itineraries:
                        arrive_time = ai.get("itinerary", {}).get("arrive_time")
                        if arrive_time:
                            arrival_times.append(arrive_time)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Cost", f"${best_option['total_cost']:,.2f}")
                    with col2:
                        st.metric("Avg Travel Time", f"{best_option['avg_travel_time_minutes']:.0f} min")
                    with col3:
                        st.metric("Arrival Spread", f"{best_option['arrival_spread_minutes']:.0f} min")
                    with col4:
                        st.metric("Connections Rate", f"{best_option['connections_rate']:.2%}")
                    
                    col5, col6, col7 = st.columns(3)
                    with col5:
                        st.metric("Cost per Attendee", f"${cost_per_attendee:,.2f}")
                    with col6:
                        st.metric("Median Travel Time", f"{median_travel_time} min")
                    with col7:
                        st.metric("Local Attendees", f"{local_count}")

                    # Earliest / latest arrival times
                    if arrival_times:
                        try:
                            earliest = min(arrival_times)
                            latest = max(arrival_times)
                            st.caption(f"Earliest arrival: {earliest} • Latest arrival: {latest}")
                        except Exception:
                            pass
                    
                    if len(ranked) > 1:
                        second_option = results[ranked[1]]
                        cost_delta = second_option["total_cost"] - best_option["total_cost"]
                        score_delta = second_option["score"] - best_option["score"]
                        st.caption(
                            f"Saves ${cost_delta:,.2f} vs option #2. "
                            f"Score advantage: {score_delta:.2f}."
                        )

                        # Why recommended (simple reasoning)
                        reasons = []
                        if cost_delta > 0:
                            reasons.append(f"Lower total cost by ${cost_delta:,.2f}")
                        if best_option["arrival_spread_minutes"] < second_option["arrival_spread_minutes"]:
                            spread_delta = second_option["arrival_spread_minutes"] - best_option["arrival_spread_minutes"]
                            reasons.append(f"Tighter arrival spread by {spread_delta:.0f} minutes")
                        if best_option["avg_travel_time_minutes"] < second_option["avg_travel_time_minutes"]:
                            time_delta = second_option["avg_travel_time_minutes"] - best_option["avg_travel_time_minutes"]
                            reasons.append(f"Shorter average travel time by {time_delta:.0f} minutes")
                        if best_option["connections_rate"] < second_option["connections_rate"]:
                            conn_delta = (second_option["connections_rate"] - best_option["connections_rate"]) * 100
                            reasons.append(f"Fewer connections by {conn_delta:.0f}%")
                        if reasons:
                            st.markdown("**Why this option wins**")
                            for reason in reasons[:3]:
                                st.write(f"- {reason}")
                
                # Arrival histogram for top-ranked option
                if ranked:
                    st.subheader("Arrival Time Distribution (Top Option)")
                    
                    # Compute histogram from itineraries
                    arrivals_by_hour = [0] * 24
                    for ai in best_option.get("attendee_itineraries", []):
                        arrive_time_str = ai.get("itinerary", {}).get("arrive_time")
                        if arrive_time_str:
                            # Handle both string and time object formats
                            if isinstance(arrive_time_str, str):
                                try:
                                    hour = int(arrive_time_str.split(":")[0])
                                    arrivals_by_hour[hour] += 1
                                except (ValueError, IndexError):
                                    pass
                            elif hasattr(arrive_time_str, 'hour'):
                                # It's a time object
                                arrivals_by_hour[arrive_time_str.hour] += 1
                    
                    # Create DataFrame for chart
                    hist_df = pd.DataFrame({
                        "Hour": list(range(24)),
                        "Arrivals": arrivals_by_hour
                    })
                    st.bar_chart(hist_df.set_index("Hour"))
                
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
                            itinerary = ai.get("itinerary", {})
                            if itinerary.get("airline") == "LOCAL" or itinerary.get("travel_minutes") == 0:
                                st.write(f"- **{ai['employee_id']}**: Local attendee (no flight needed)")
                            else:
                                st.write(
                                    f"- **{ai['employee_id']}**: {itinerary['airline']} "
                                    f"({itinerary['origin']} → {itinerary['destination']}), "
                                    f"{itinerary['stops']} stops, "
                                    f"${itinerary['price']:.2f}"
                                )
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
        # Ensure results exist
        results_data = api_request("GET", f"/events/{event_id_input}/results/latest")
        if not results_data:
            st.warning("No simulation results found. Run a simulation first.")
            if st.button("Run Simulation Now"):
                with st.spinner("Running simulation..."):
                    sim_result = api_request("POST", f"/events/{event_id_input}/simulate")
                    if sim_result:
                        st.success("Simulation completed. Generate summary below.")
        else:
            if st.button("Generate Summary", type="primary"):
                with st.spinner("Generating executive summary..."):
                    result = api_request("POST", f"/events/{event_id_input}/ai/summary")
                    
                    if result and result.get("summary"):
                        st.success("Summary generated!")
                        st.markdown(f"### Executive Summary\n\n{result['summary']}")
                    else:
                        st.error("Summary failed. Check LLM settings and try again.")


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
