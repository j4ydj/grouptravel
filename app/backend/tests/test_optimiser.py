"""Tests for optimiser service."""
import pytest
from datetime import date
from app.backend.services.optimiser import OptimiserService


def test_score_calculation():
    """Test scoring function with known inputs."""
    optimiser = OptimiserService()
    
    # Test case: known values
    total_cost = 10000.0
    arrival_spread_minutes = 120.0
    avg_travel_time_minutes = 600.0
    connections_rate = 0.3
    
    score = optimiser._calculate_score(
        total_cost=total_cost,
        arrival_spread_minutes=arrival_spread_minutes,
        avg_travel_time_minutes=avg_travel_time_minutes,
        connections_rate=connections_rate
    )
    
    # Expected: 10000*1.0 + 120*5 + 600*2 + 0.3*500
    # = 10000 + 600 + 1200 + 150 = 11950
    expected_score = 10000.0 + 600.0 + 1200.0 + 150.0
    assert abs(score - expected_score) < 0.01


def test_score_lower_is_better():
    """Test that lower scores indicate better options."""
    optimiser = OptimiserService()
    
    # Option 1: Lower cost, lower spread
    score1 = optimiser._calculate_score(
        total_cost=5000.0,
        arrival_spread_minutes=60.0,
        avg_travel_time_minutes=400.0,
        connections_rate=0.2
    )
    
    # Option 2: Higher cost, higher spread
    score2 = optimiser._calculate_score(
        total_cost=15000.0,
        arrival_spread_minutes=300.0,
        avg_travel_time_minutes=800.0,
        connections_rate=0.8
    )
    
    assert score1 < score2


@pytest.mark.asyncio
async def test_simulate_option():
    """Test simulating a single option."""
    from app.backend.db.models import Attendee, TravelClass
    from app.backend.schemas.event import DateWindow
    
    optimiser = OptimiserService()
    
    # Create mock attendees
    attendee1 = Attendee(
        id="test1",
        employee_id="EMP001",
        home_airport="JFK",
        travel_class=TravelClass.ECONOMY
    )
    attendee2 = Attendee(
        id="test2",
        employee_id="EMP002",
        home_airport="LAX",
        travel_class=TravelClass.ECONOMY
    )
    
    date_window = DateWindow(
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 8)
    )
    
    result = await optimiser.simulate_option(
        location="LIS",
        date_window=date_window,
        attendees=[attendee1, attendee2],
        duration_days=3
    )
    
    assert result.location == "LIS"
    assert result.total_cost > 0
    assert result.avg_travel_time_minutes > 0
    assert len(result.attendee_itineraries) == 2
    assert result.score > 0
