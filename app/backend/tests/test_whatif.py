"""Tests for what-if exploration service."""
import pytest
from datetime import date
from app.backend.services.whatif import WhatIfExplorationService, WhatIfProposal
from app.backend.db.models import Event
from app.backend.schemas.itinerary import SimulationResult, OptionResult


def test_generate_variations():
    """Test variation generation."""
    service = WhatIfExplorationService()
    
    event = Event(
        id="test",
        name="Test Event",
        candidate_locations=["LIS", "MUC"],
        candidate_date_windows=[{
            "start_date": "2024-06-01",
            "end_date": "2024-06-08"
        }],
        duration_days=3,
        created_by="test"
    )
    
    baseline_result = SimulationResult(
        event_id="test",
        results=[],
        ranked_options=[],
        created_at=date.today(),
        version=1
    )
    
    proposals = service.generate_variations(event, baseline_result)
    
    assert len(proposals) <= 5
    assert len(proposals) > 0
    
    # Should have date shift proposals
    date_shifts = [p for p in proposals if p.proposal_type == "date_shift"]
    assert len(date_shifts) >= 1


def test_nearby_airports_mapping():
    """Test nearby airports mapping."""
    service = WhatIfExplorationService()
    
    # Test known mappings
    assert "LIS" in service.NEARBY_AIRPORTS
    assert "MUC" in service.NEARBY_AIRPORTS
    assert len(service.NEARBY_AIRPORTS["LIS"]) > 0
