"""Tests for transfer batching service."""
import pytest
from datetime import datetime, timedelta
from app.backend.services.transfer import TransferBatchingService
from app.backend.db.models import TransferOption, TransferMode


def test_compute_arrival_waves():
    """Test arrival wave computation."""
    service = TransferBatchingService()
    
    # Create arrivals in waves
    base_time = datetime(2024, 6, 1, 10, 0)
    arrival_times = [
        base_time,
        base_time + timedelta(minutes=10),
        base_time + timedelta(minutes=20),
        base_time + timedelta(minutes=45),  # New wave
        base_time + timedelta(minutes=50)
    ]
    attendee_ids = ["A1", "A2", "A3", "A4", "A5"]
    
    waves = service.compute_arrival_waves(
        arrival_times=arrival_times,
        attendee_ids=attendee_ids,
        wave_window_minutes=30
    )
    
    assert len(waves) == 2  # Should have 2 waves
    assert waves[0].attendee_count == 3
    assert waves[1].attendee_count == 2


def test_calculate_complexity_score():
    """Test complexity score calculation."""
    service = TransferBatchingService()
    
    from app.backend.schemas.transfer import TransferPlan, TransferLeg, TransferWave
    
    # Create simple transfer plan
    wave = TransferWave(
        wave_start=datetime(2024, 6, 1, 10, 0),
        wave_end=datetime(2024, 6, 1, 10, 30),
        attendee_count=5,
        attendee_ids=["A1", "A2", "A3", "A4", "A5"]
    )
    
    leg = TransferLeg(
        wave=wave,
        mode=TransferMode.VAN,
        vehicle_count=1,
        total_cost=100.0,
        capacity_utilization=1.0
    )
    
    plan = TransferPlan(
        airport_code="LIS",
        hotel_id="hotel1",
        total_cost=100.0,
        total_vehicles=1,
        legs=[leg],
        operational_complexity_score=0.0  # Will be calculated
    )
    
    complexity = service.calculate_complexity_score(plan)
    assert complexity > 0
