"""Tests for preference learning service."""
import pytest
from app.backend.services.preference import PreferenceLearningService
from app.backend.db.models import PreferenceProfile, Attendee
from app.backend.schemas.itinerary import Itinerary
from datetime import date, time


def test_get_or_create_profile(db_session):
    """Test getting or creating preference profile."""
    service = PreferenceLearningService()
    
    # Create test attendee
    attendee = Attendee(
        id="test1",
        employee_id="EMP001",
        home_airport="JFK"
    )
    db_session.add(attendee)
    db_session.commit()
    
    # Get or create profile
    profile = service.get_or_create_profile(attendee.id, db_session)
    
    assert profile is not None
    assert profile.attendee_id == attendee.id
    assert profile.prefers_early_flights == 0.5  # Default
    assert profile.avoids_connections == 0.5  # Default


def test_update_from_booking(db_session):
    """Test updating profile from booking."""
    service = PreferenceLearningService()
    
    # Create test attendee
    attendee = Attendee(
        id="test2",
        employee_id="EMP002",
        home_airport="LAX"
    )
    db_session.add(attendee)
    db_session.commit()
    
    # Get profile
    profile = service.get_or_create_profile(attendee.id, db_session)
    original_early = profile.prefers_early_flights
    
    # Create booking with early flight
    itinerary = Itinerary(
        origin="LAX",
        destination="LIS",
        depart_date=date(2024, 6, 1),
        return_date=date(2024, 6, 5),
        airline="AA",
        stops=0,
        depart_time=time(8, 0),  # Early flight
        arrive_time=time(14, 0),
        travel_minutes=480,
        price=800.0
    )
    
    # Update profile
    service.update_from_booking(attendee.id, itinerary, db_session)
    
    db_session.refresh(profile)
    
    # Should have increased early flight preference
    assert profile.prefers_early_flights > original_early


def test_apply_soft_constraints():
    """Test applying soft constraints."""
    service = PreferenceLearningService()
    
    # Create mock attendee and profile
    attendee = Attendee(
        id="test3",
        employee_id="EMP003",
        home_airport="JFK"
    )
    
    profile = PreferenceProfile(
        id="profile1",
        attendee_id="test3",
        prefers_early_flights=0.8,  # Strong preference
        avoids_connections=0.9,  # Strong preference
        preferred_hubs=["LHR"],
        typical_arrival_window={"start": "10:00", "end": "14:00"},
        reliability_score=1.0
    )
    
    # Create options
    early_direct = Itinerary(
        origin="JFK",
        destination="LHR",
        depart_date=date(2024, 6, 1),
        return_date=date(2024, 6, 5),
        airline="BA",
        stops=0,
        depart_time=time(8, 0),  # Early
        arrive_time=time(12, 0),  # In window
        travel_minutes=420,
        price=1000.0
    )
    
    late_connecting = Itinerary(
        origin="JFK",
        destination="LHR",
        depart_date=date(2024, 6, 1),
        return_date=date(2024, 6, 5),
        airline="AA",
        stops=1,  # Connection
        depart_time=time(14, 0),  # Late
        arrive_time=time(22, 0),  # Late
        travel_minutes=600,
        price=800.0
    )
    
    scored = service.apply_soft_constraints(
        attendee=attendee,
        profile=profile,
        options=[early_direct, late_connecting]
    )
    
    # Early direct should score higher
    assert len(scored) == 2
    early_score = next(s for it, s in scored if it == early_direct)[1]
    late_score = next(s for it, s in scored if it == late_connecting)[1]
    
    assert early_score > late_score
