"""Tests for Phase 2 scoring function."""
import pytest
from app.backend.services.optimiser import OptimiserService


def test_score_v2_calculation():
    """Test Phase 2 scoring function with known inputs."""
    optimiser = OptimiserService()
    
    score = optimiser._calculate_score_v2(
        flight_cost=10000.0,
        hotel_cost=5000.0,
        transfer_cost=1000.0,
        arrival_spread_minutes=120.0,
        avg_travel_time_minutes=600.0,
        connections_rate=0.3,
        late_arrival_risk=0.2,
        operational_complexity_score=50.0
    )
    
    # Expected: 10000*1.0 + 5000*0.8 + 1000*0.5 + 120*5 + 600*2 + 0.3*500 + 0.2*200 + 50*300
    # = 10000 + 4000 + 500 + 600 + 1200 + 150 + 40 + 15000 = 31490
    expected_score = 10000.0 + 4000.0 + 500.0 + 600.0 + 1200.0 + 150.0 + 40.0 + 15000.0
    assert abs(score - expected_score) < 0.01


def test_score_v2_hotel_weight():
    """Test that hotel cost has appropriate weight."""
    optimiser = OptimiserService()
    
    # Same flight cost, different hotel costs
    score1 = optimiser._calculate_score_v2(
        flight_cost=10000.0,
        hotel_cost=3000.0,
        transfer_cost=1000.0,
        arrival_spread_minutes=120.0,
        avg_travel_time_minutes=600.0,
        connections_rate=0.3,
        late_arrival_risk=0.2,
        operational_complexity_score=50.0
    )
    
    score2 = optimiser._calculate_score_v2(
        flight_cost=10000.0,
        hotel_cost=5000.0,  # Higher hotel cost
        transfer_cost=1000.0,
        arrival_spread_minutes=120.0,
        avg_travel_time_minutes=600.0,
        connections_rate=0.3,
        late_arrival_risk=0.2,
        operational_complexity_score=50.0
    )
    
    # Score2 should be higher (worse)
    assert score2 > score1
    # Difference should be 2000 * 0.8 = 1600
    assert abs((score2 - score1) - 1600.0) < 0.01


def test_score_v2_late_arrival_penalty():
    """Test that late arrival risk adds significant penalty."""
    optimiser = OptimiserService()
    
    score_low_risk = optimiser._calculate_score_v2(
        flight_cost=10000.0,
        hotel_cost=5000.0,
        transfer_cost=1000.0,
        arrival_spread_minutes=120.0,
        avg_travel_time_minutes=600.0,
        connections_rate=0.3,
        late_arrival_risk=0.1,  # Low risk
        operational_complexity_score=50.0
    )
    
    score_high_risk = optimiser._calculate_score_v2(
        flight_cost=10000.0,
        hotel_cost=5000.0,
        transfer_cost=1000.0,
        arrival_spread_minutes=120.0,
        avg_travel_time_minutes=600.0,
        connections_rate=0.3,
        late_arrival_risk=0.8,  # High risk
        operational_complexity_score=50.0
    )
    
    # High risk should have much higher score
    assert score_high_risk > score_low_risk
    # Difference should be 0.7 * 200 = 140
    assert abs((score_high_risk - score_low_risk) - 140.0) < 0.01
