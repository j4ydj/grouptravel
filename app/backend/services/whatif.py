"""What-if exploration service."""
from typing import List, Dict, Optional
from datetime import date, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.backend.db.models import Event
from app.backend.schemas.event import DateWindow, EventCreate
from app.backend.schemas.itinerary import SimulationResult, OptionResult
from app.backend.services.optimiser import OptimiserService


class WhatIfProposal(BaseModel):
    """A what-if proposal."""
    proposal_type: str  # "date_shift", "nearby_airport", "hub_change", "arrival_window"
    description: str
    variation_data: Dict


class WhatIfResult(BaseModel):
    """Result of evaluating a what-if proposal."""
    proposal: WhatIfProposal
    delta_cost: float  # vs baseline
    delta_score: float  # vs baseline
    new_result: OptionResult
    baseline_result: OptionResult


class WhatIfExplorationService:
    """Service for exploring what-if scenarios."""
    
    # Nearby airports mapping (simplified)
    NEARBY_AIRPORTS = {
        "LIS": ["OPO", "FAO"],
        "MUC": ["FRA", "STR"],
        "LHR": ["LGW", "STN"],
        "CDG": ["ORY"],
        "JFK": ["LGA", "EWR"],
        "LAX": ["SNA", "BUR"]
    }
    
    def generate_variations(
        self,
        event: Event,
        baseline_result: SimulationResult
    ) -> List[WhatIfProposal]:
        """
        Generate up to 5 high-leverage variations.
        
        Args:
            event: Event model
            baseline_result: Baseline simulation result
        
        Returns:
            List of WhatIfProposal
        """
        proposals = []
        
        # 1. Date shift ±1 day
        if event.candidate_date_windows:
            first_window = event.candidate_date_windows[0]
            if isinstance(first_window, dict):
                start_date = date.fromisoformat(first_window["start_date"])
                
                # Shift forward 1 day
                proposals.append(WhatIfProposal(
                    proposal_type="date_shift",
                    description="Shift event start date forward by 1 day",
                    variation_data={
                        "shift_days": 1,
                        "original_start": start_date.isoformat()
                    }
                ))
                
                # Shift backward 1 day
                proposals.append(WhatIfProposal(
                    proposal_type="date_shift",
                    description="Shift event start date backward by 1 day",
                    variation_data={
                        "shift_days": -1,
                        "original_start": start_date.isoformat()
                    }
                ))
        
        # 2. Alternative nearby airports
        for location in event.candidate_locations[:2]:  # Limit to first 2 locations
            nearby = self.NEARBY_AIRPORTS.get(location, [])
            if nearby:
                proposals.append(WhatIfProposal(
                    proposal_type="nearby_airport",
                    description=f"Use {nearby[0]} instead of {location}",
                    variation_data={
                        "original": location,
                        "alternative": nearby[0]
                    }
                ))
        
        # 3. Hub change (if connections exist)
        # Simplified: propose using major hubs
        major_hubs = ["FRA", "LHR", "CDG", "JFK", "DXB"]
        if len(proposals) < 5:
            for hub in major_hubs[:1]:
                proposals.append(WhatIfProposal(
                    proposal_type="hub_change",
                    description=f"Route through {hub} hub",
                    variation_data={
                        "hub": hub
                    }
                ))
        
        return proposals[:5]  # Limit to 5
    
    async def evaluate_proposals(
        self,
        proposals: List[WhatIfProposal],
        event: Event,
        baseline_result: SimulationResult,
        db: Session
    ) -> List[WhatIfResult]:
        """
        Run simulation for each proposal, compute delta vs baseline.
        
        Args:
            proposals: List of proposals
            event: Event model
            baseline_result: Baseline result
            db: Database session
        
        Returns:
            List of WhatIfResult
        """
        results = []
        optimiser = OptimiserService()
        
        # Get baseline best option
        baseline_best_idx = baseline_result.ranked_options[0] if baseline_result.ranked_options else 0
        baseline_best = baseline_result.results[baseline_best_idx]
        
        for proposal in proposals:
            # Create modified event
            modified_event = self._apply_proposal(event, proposal)
            
            if not modified_event:
                continue
            
            # Run simulation
            option_results = await optimiser.simulate_event(modified_event, db)
            
            if not option_results:
                continue
            
            # Find best option
            best_option = min(option_results, key=lambda x: x.score)
            
            # Calculate deltas
            delta_cost = best_option.total_cost - baseline_best.total_cost
            delta_score = best_option.score - baseline_best.score
            
            results.append(WhatIfResult(
                proposal=proposal,
                delta_cost=round(delta_cost, 2),
                delta_score=round(delta_score, 2),
                new_result=best_option,
                baseline_result=baseline_best
            ))
        
        return results
    
    def _apply_proposal(
        self,
        event: Event,
        proposal: WhatIfProposal
    ) -> Optional[Event]:
        """Apply proposal to create modified event."""
        if proposal.proposal_type == "date_shift":
            # Shift date windows
            shift_days = proposal.variation_data["shift_days"]
            modified_windows = []
            
            for window in event.candidate_date_windows:
                if isinstance(window, dict):
                    start = date.fromisoformat(window["start_date"])
                    end = date.fromisoformat(window["end_date"])
                    modified_windows.append({
                        "start_date": (start + timedelta(days=shift_days)).isoformat(),
                        "end_date": (end + timedelta(days=shift_days)).isoformat()
                    })
            
            # Create modified event (copy)
            modified = Event(
                name=event.name + f" (shifted {shift_days} days)",
                candidate_locations=event.candidate_locations,
                candidate_date_windows=modified_windows,
                duration_days=event.duration_days,
                created_by=event.created_by
            )
            return modified
        
        elif proposal.proposal_type == "nearby_airport":
            # Replace location
            original = proposal.variation_data["original"]
            alternative = proposal.variation_data["alternative"]
            
            modified_locations = [
                alt if loc == original else loc
                for loc in event.candidate_locations
            ]
            
            modified = Event(
                name=event.name + f" ({alternative} variant)",
                candidate_locations=modified_locations,
                candidate_date_windows=event.candidate_date_windows,
                duration_days=event.duration_days,
                created_by=event.created_by
            )
            return modified
        
        # Other proposal types would be handled here
        return None
