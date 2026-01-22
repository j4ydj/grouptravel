"""Tests for hotel optimization service."""
import pytest
from datetime import datetime, date, timedelta
from app.backend.services.hotel import HotelOptimisationService
from app.backend.db.models import Hotel


def test_compute_room_nights():
    """Test room night calculation."""
    service = HotelOptimisationService()
    
    # Simple case: all arrive same day, leave same day
    arrival_times = [
        datetime(2024, 6, 1, 10, 0),
        datetime(2024, 6, 1, 11, 0),
        datetime(2024, 6, 1, 12, 0)
    ]
    departure_times = [
        datetime(2024, 6, 4, 14, 0),
        datetime(2024, 6, 4, 15, 0),
        datetime(2024, 6, 4, 16, 0)
    ]
    
    analysis = service.compute_room_nights(
        arrival_times=arrival_times,
        departure_times=departure_times,
        duration_days=3
    )
    
    assert analysis.peak_occupancy == 3
    assert analysis.total_room_nights > 0


def test_compute_room_nights_with_spread():
    """Test room nights with arrival/departure spread."""
    service = HotelOptimisationService()
    
    # Some arrive early, some late
    arrival_times = [
        datetime(2024, 5, 31, 10, 0),  # 1 day early
        datetime(2024, 6, 1, 10, 0),   # On time
        datetime(2024, 6, 1, 18, 0)    # On time, late
    ]
    departure_times = [
        datetime(2024, 6, 4, 10, 0),
        datetime(2024, 6, 4, 14, 0),
        datetime(2024, 6, 5, 10, 0)    # 1 day late
    ]
    
    analysis = service.compute_room_nights(
        arrival_times=arrival_times,
        departure_times=departure_times,
        duration_days=3
    )
    
    assert analysis.shoulder_nights > 0  # Should have extra nights
    assert analysis.peak_occupancy >= 2


def test_calculate_hotel_cost():
    """Test hotel cost calculation."""
    service = HotelOptimisationService()
    
    hotel = Hotel(
        id="test",
        name="Test Hotel",
        city="Test",
        airport_code="TST",
        corporate_rate=200.0,
        capacity=50
    )
    
    cost = service.calculate_hotel_cost(hotel, room_nights=10, extra_nights=2)
    assert cost == 12 * 200.0  # 12 total nights


def test_calculate_hotel_cost_no_rate():
    """Test hotel cost with no corporate rate."""
    service = HotelOptimisationService()
    
    hotel = Hotel(
        id="test",
        name="Test Hotel",
        city="Test",
        airport_code="TST",
        corporate_rate=None,
        capacity=50
    )
    
    cost = service.calculate_hotel_cost(hotel, room_nights=10, extra_nights=2)
    assert cost == 12 * 150.0  # Default rate
