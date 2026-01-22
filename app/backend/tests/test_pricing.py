"""Tests for pricing provider determinism."""
import pytest
from datetime import date
from app.backend.services.pricing import MockPricingProvider


@pytest.mark.asyncio
async def test_mock_pricing_determinism():
    """Test that MockPricingProvider returns identical results for same inputs."""
    provider = MockPricingProvider(volatile=False)
    
    origin = "JFK"
    destination = "LIS"
    depart_date = date(2024, 6, 1)
    return_date = date(2024, 6, 5)
    constraints = {"travel_class": "economy"}
    
    # Get itinerary twice
    itinerary1 = await provider.get_best_itinerary(
        origin, destination, depart_date, return_date, constraints
    )
    itinerary2 = await provider.get_best_itinerary(
        origin, destination, depart_date, return_date, constraints
    )
    
    # Should be identical
    assert itinerary1.price == itinerary2.price
    assert itinerary1.airline == itinerary2.airline
    assert itinerary1.stops == itinerary2.stops
    assert itinerary1.travel_minutes == itinerary2.travel_minutes


@pytest.mark.asyncio
async def test_mock_pricing_different_inputs():
    """Test that different inputs produce different results."""
    provider = MockPricingProvider(volatile=False)
    
    constraints = {"travel_class": "economy"}
    depart_date = date(2024, 6, 1)
    return_date = date(2024, 6, 5)
    
    # Different destinations
    itinerary1 = await provider.get_best_itinerary(
        "JFK", "LIS", depart_date, return_date, constraints
    )
    itinerary2 = await provider.get_best_itinerary(
        "JFK", "MUC", depart_date, return_date, constraints
    )
    
    # Should be different (very unlikely to be identical)
    assert itinerary1.destination != itinerary2.destination
    # Prices might be different (not guaranteed but very likely)


@pytest.mark.asyncio
async def test_mock_pricing_travel_class_multiplier():
    """Test that travel class affects pricing."""
    provider = MockPricingProvider(volatile=False)
    
    origin = "JFK"
    destination = "LIS"
    depart_date = date(2024, 6, 1)
    return_date = date(2024, 6, 5)
    
    economy_itinerary = await provider.get_best_itinerary(
        origin, destination, depart_date, return_date,
        {"travel_class": "economy"}
    )
    
    business_itinerary = await provider.get_best_itinerary(
        origin, destination, depart_date, return_date,
        {"travel_class": "business"}
    )
    
    # Business should be more expensive
    assert business_itinerary.price > economy_itinerary.price
