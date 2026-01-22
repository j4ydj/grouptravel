"""API integration tests."""
import pytest
from datetime import date
from app.backend.db.models import Attendee, Event, EventAttendee, TravelClass


def test_create_attendee(client, sample_attendee_data):
    """Test creating an attendee."""
    response = client.post("/api/attendees", json=sample_attendee_data)
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == sample_attendee_data["employee_id"]
    assert data["home_airport"] == sample_attendee_data["home_airport"]


def test_list_attendees(client, sample_attendee_data):
    """Test listing attendees."""
    # Create an attendee first
    client.post("/api/attendees", json=sample_attendee_data)
    
    # List attendees
    response = client.get("/api/attendees")
    assert response.status_code == 200
    data = response.json()
    assert "attendees" in data
    assert len(data["attendees"]) > 0


def test_create_event(client, sample_event_data):
    """Test creating an event."""
    response = client.post("/api/events", json=sample_event_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_event_data["name"]
    assert "id" in data


def test_simulate_event(client, db_session, sample_event_data, sample_attendee_data):
    """Test simulating an event."""
    # Create attendee
    attendee_resp = client.post("/api/attendees", json=sample_attendee_data)
    attendee_id = attendee_resp.json()["id"]
    
    # Create event
    event_resp = client.post("/api/events", json=sample_event_data)
    event_id = event_resp.json()["id"]
    
    # Attach attendee
    client.post(f"/api/events/{event_id}/attendees", json={"attendee_ids": [attendee_id]})
    
    # Run simulation
    response = client.post(f"/api/events/{event_id}/simulate")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "ranked_options" in data
    assert len(data["results"]) > 0


def test_parse_event_text(client):
    """Test parsing event text with mock LLM."""
    response = client.post(
        "/api/ai/parse_event_text",
        json={"text": "Workshop in Lisbon or Munich next month for 3 days"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "candidate_locations" in data
