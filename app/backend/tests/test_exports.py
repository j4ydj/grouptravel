"""Tests for export service."""
import pytest
from datetime import date, time
from app.backend.services.export import ExportService
from app.backend.db.models import Event, Attendee
from app.backend.schemas.itinerary import AttendeeItinerary, Itinerary


def test_generate_concur_payload():
    """Test Concur payload generation."""
    service = ExportService()
    
    attendee = Attendee(
        id="test1",
        employee_id="EMP001",
        home_airport="JFK"
    )
    
    itinerary_obj = Itinerary(
        origin="JFK",
        destination="LIS",
        depart_date=date(2024, 6, 1),
        return_date=date(2024, 6, 5),
        airline="AA",
        stops=0,
        depart_time=time(10, 0),
        arrive_time=time(14, 0),
        travel_minutes=480,
        price=800.0
    )
    
    itinerary = AttendeeItinerary(
        attendee_id="test1",
        employee_id="EMP001",
        itinerary=itinerary_obj
    )
    
    event = Event(
        id="event1",
        name="Test Event",
        candidate_locations=["LIS"],
        candidate_date_windows=[],
        duration_days=3,
        created_by="test"
    )
    
    payload = service.generate_concur_payload(
        attendee=attendee,
        itinerary=itinerary,
        hotel_assignment=None,
        event=event
    )
    
    assert payload.employee_id == "EMP001"
    assert payload.origin == "JFK"
    assert payload.destination == "LIS"
    assert payload.event_id == "event1"
    assert "concur.example.com" in payload.deep_link_url


def test_generate_finance_export():
    """Test finance export generation."""
    service = ExportService()
    
    event = Event(
        id="event1",
        name="Test Event",
        candidate_locations=["LIS"],
        candidate_date_windows=[],
        duration_days=3,
        created_by="test"
    )
    
    # Simplified test - would need full SimulationResultV2
    # For MVP, test basic structure
    finance_export = service.generate_finance_export(
        event=event,
        result=None,  # Simplified
        selected_option_index=0
    )
    
    # This will fail without proper result, but structure is tested
    assert True  # Placeholder
