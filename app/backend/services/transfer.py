"""Transfer batching service."""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from collections import defaultdict
from app.backend.db.models import TransferOption, TransferMode
from app.backend.schemas.transfer import TransferWave, TransferLeg, TransferPlan


class TransferBatchingService:
    """Service for optimizing transfer batching and routing."""
    
    WAVE_WINDOW_MINUTES = 30  # Default wave window
    VAN_THRESHOLD = 3  # Minimum attendees for van vs individual
    
    def compute_arrival_waves(
        self,
        arrival_times: List[datetime],
        attendee_ids: List[str],
        wave_window_minutes: int = WAVE_WINDOW_MINUTES
    ) -> List[TransferWave]:
        """
        Group arrivals into transfer waves.
        
        Args:
            arrival_times: List of arrival datetimes
            attendee_ids: Corresponding attendee IDs
            wave_window_minutes: Window size for grouping arrivals
        
        Returns:
            List of TransferWave objects
        """
        if not arrival_times or not attendee_ids:
            return []
        
        if len(arrival_times) != len(attendee_ids):
            raise ValueError("arrival_times and attendee_ids must have same length")
        
        # Sort by arrival time
        sorted_data = sorted(zip(arrival_times, attendee_ids))
        
        waves = []
        current_wave_start = None
        current_wave_end = None
        current_attendees = []
        current_attendee_ids = []
        
        for arrival_time, attendee_id in sorted_data:
            if current_wave_start is None:
                # Start first wave
                current_wave_start = arrival_time
                current_wave_end = arrival_time + timedelta(minutes=wave_window_minutes)
                current_attendees = [arrival_time]
                current_attendee_ids = [attendee_id]
            elif arrival_time <= current_wave_end:
                # Add to current wave
                current_attendees.append(arrival_time)
                current_attendee_ids.append(attendee_id)
            else:
                # Close current wave and start new one
                waves.append(TransferWave(
                    wave_start=current_wave_start,
                    wave_end=current_wave_end,
                    attendee_count=len(current_attendees),
                    attendee_ids=current_attendee_ids
                ))
                
                current_wave_start = arrival_time
                current_wave_end = arrival_time + timedelta(minutes=wave_window_minutes)
                current_attendees = [arrival_time]
                current_attendee_ids = [attendee_id]
        
        # Add final wave
        if current_wave_start is not None:
            waves.append(TransferWave(
                wave_start=current_wave_start,
                wave_end=current_wave_end,
                attendee_count=len(current_attendees),
                attendee_ids=current_attendee_ids
            ))
        
        return waves
    
    def optimize_transfers(
        self,
        waves: List[TransferWave],
        airport_code: str,
        hotel_id: str,
        db: Session
    ) -> Optional[TransferPlan]:
        """
        Optimize transfer plan using batching.
        
        Args:
            waves: List of arrival waves
            airport_code: Airport code
            hotel_id: Hotel ID
            db: Database session
        
        Returns:
            TransferPlan or None if no transfer options found
        """
        # Get transfer options
        transfer_options = db.query(TransferOption).filter_by(
            airport_code=airport_code,
            hotel_id=hotel_id
        ).all()
        
        if not transfer_options:
            return None
        
        # Find van and individual options
        van_option = next((to for to in transfer_options if to.mode == TransferMode.VAN), None)
        uber_option = next((to for to in transfer_options if to.mode == TransferMode.UBER), None)
        
        # Fallback: use any available option
        if not van_option and transfer_options:
            van_option = transfer_options[0]
        if not uber_option and transfer_options:
            uber_option = transfer_options[0]
        
        if not van_option or not uber_option:
            return None
        
        # Optimize each wave
        legs = []
        total_cost = 0.0
        total_vehicles = 0
        
        for wave in waves:
            if wave.attendee_count >= self.VAN_THRESHOLD:
                # Use van
                vehicles_needed = (wave.attendee_count + van_option.capacity - 1) // van_option.capacity
                leg_cost = vehicles_needed * van_option.cost_per_trip
                capacity_util = wave.attendee_count / (vehicles_needed * van_option.capacity)
                
                legs.append(TransferLeg(
                    wave=wave,
                    mode=TransferMode.VAN,
                    vehicle_count=vehicles_needed,
                    total_cost=leg_cost,
                    capacity_utilization=capacity_util
                ))
                
                total_cost += leg_cost
                total_vehicles += vehicles_needed
            else:
                # Use individual trips (Uber)
                vehicles_needed = wave.attendee_count
                leg_cost = vehicles_needed * uber_option.cost_per_trip
                
                legs.append(TransferLeg(
                    wave=wave,
                    mode=TransferMode.UBER,
                    vehicle_count=vehicles_needed,
                    total_cost=leg_cost,
                    capacity_utilization=1.0
                ))
                
                total_cost += leg_cost
                total_vehicles += vehicles_needed
        
        # Calculate complexity score
        complexity_score = self.calculate_complexity_score(
            TransferPlan(
                airport_code=airport_code,
                hotel_id=hotel_id,
                total_cost=total_cost,
                total_vehicles=total_vehicles,
                legs=legs,
                operational_complexity_score=0.0  # Will be calculated
            )
        )
        
        return TransferPlan(
            airport_code=airport_code,
            hotel_id=hotel_id,
            total_cost=round(total_cost, 2),
            total_vehicles=total_vehicles,
            legs=legs,
            operational_complexity_score=complexity_score
        )
    
    def calculate_complexity_score(
        self,
        transfer_plan: TransferPlan
    ) -> float:
        """
        Calculate operational complexity score.
        
        Higher score = more complex (more vehicles, more waves, etc.)
        
        Args:
            transfer_plan: Transfer plan
        
        Returns:
            Complexity score
        """
        # Base complexity from number of vehicles
        vehicle_complexity = transfer_plan.total_vehicles * 10
        
        # Complexity from number of waves
        wave_complexity = len(transfer_plan.legs) * 5
        
        # Complexity from mixed modes
        modes = set(leg.mode for leg in transfer_plan.legs)
        mode_complexity = len(modes) * 3
        
        # Complexity from low capacity utilization
        avg_utilization = sum(leg.capacity_utilization for leg in transfer_plan.legs) / len(transfer_plan.legs) if transfer_plan.legs else 1.0
        utilization_penalty = (1.0 - avg_utilization) * 20
        
        return vehicle_complexity + wave_complexity + mode_complexity + utilization_penalty
