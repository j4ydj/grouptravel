"""Preference learning service."""
from typing import List, Tuple, Optional
from datetime import datetime, time
from sqlalchemy.orm import Session
from app.backend.db.models import PreferenceProfile, Attendee
from app.backend.schemas.itinerary import Itinerary


class PreferenceLearningService:
    """Service for learning and applying attendee preferences."""
    
    EMA_ALPHA = 0.1  # Slow learning rate for exponential moving average
    
    def get_or_create_profile(
        self,
        attendee_id: str,
        db: Session
    ) -> PreferenceProfile:
        """
        Get existing preference profile or create default.
        
        Args:
            attendee_id: Attendee ID
            db: Database session
        
        Returns:
            PreferenceProfile
        """
        profile = db.query(PreferenceProfile).filter_by(attendee_id=attendee_id).first()
        
        if not profile:
            profile = PreferenceProfile(
                attendee_id=attendee_id,
                prefers_early_flights=0.5,
                avoids_connections=0.5,
                preferred_hubs=[],
                typical_arrival_window=None,
                reliability_score=1.0
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        return profile
    
    def update_from_booking(
        self,
        attendee_id: str,
        booked_itinerary: Itinerary,
        db: Session
    ) -> None:
        """
        Update preference profile using EMA from actual booking.
        
        Args:
            attendee_id: Attendee ID
            booked_itinerary: Booked itinerary
            db: Database session
        """
        profile = self.get_or_create_profile(attendee_id, db)
        
        # Update prefers_early_flights based on departure time
        # Early flights: departures before 10:00 AM
        depart_hour = booked_itinerary.depart_time.hour
        is_early = 1.0 if depart_hour < 10 else 0.0
        
        profile.prefers_early_flights = (
            (1 - self.EMA_ALPHA) * profile.prefers_early_flights +
            self.EMA_ALPHA * is_early
        )
        
        # Update avoids_connections based on stops
        # Prefer direct flights: stops == 0
        prefers_direct = 1.0 if booked_itinerary.stops == 0 else 0.0
        
        profile.avoids_connections = (
            (1 - self.EMA_ALPHA) * profile.avoids_connections +
            self.EMA_ALPHA * prefers_direct
        )
        
        # Update typical arrival window (simple: track arrival time)
        arrive_hour = booked_itinerary.arrive_time.hour
        arrive_minute = booked_itinerary.arrive_time.minute
        
        # Update window (simple approach: use current booking as center)
        window_start_hour = max(0, arrive_hour - 2)
        window_end_hour = min(23, arrive_hour + 2)
        
        profile.typical_arrival_window = {
            "start": f"{window_start_hour:02d}:00",
            "end": f"{window_end_hour:02d}:59"
        }
        
        # Update preferred hubs (add destination if not already present)
        if booked_itinerary.destination not in profile.preferred_hubs:
            profile.preferred_hubs.append(booked_itinerary.destination)
            # Keep only last 5 hubs
            profile.preferred_hubs = profile.preferred_hubs[-5:]
        
        profile.updated_at = datetime.utcnow()
        db.commit()
    
    def apply_soft_constraints(
        self,
        attendee: Attendee,
        profile: PreferenceProfile,
        options: List[Itinerary]
    ) -> List[Tuple[Itinerary, float]]:
        """
        Score options by preference alignment (soft, not hard).
        
        Returns list of (itinerary, preference_score) tuples.
        Higher score = better match.
        
        Args:
            attendee: Attendee model
            profile: Preference profile
            options: List of itinerary options
        
        Returns:
            List of (itinerary, preference_score) tuples
        """
        scored_options = []
        
        for itinerary in options:
            score = 0.0
            
            # Early flight preference
            depart_hour = itinerary.depart_time.hour
            is_early = 1.0 if depart_hour < 10 else 0.0
            early_score = 1.0 - abs(is_early - profile.prefers_early_flights)
            score += early_score * 0.3
            
            # Connection avoidance
            is_direct = 1.0 if itinerary.stops == 0 else 0.0
            direct_score = 1.0 - abs(is_direct - profile.avoids_connections)
            score += direct_score * 0.3
            
            # Preferred hubs
            if itinerary.destination in profile.preferred_hubs:
                score += 0.2
            
            # Arrival window preference
            if profile.typical_arrival_window:
                arrive_hour = itinerary.arrive_time.hour
                window_start = int(profile.typical_arrival_window["start"].split(":")[0])
                window_end = int(profile.typical_arrival_window["end"].split(":")[0])
                
                if window_start <= arrive_hour <= window_end:
                    score += 0.2
            
            scored_options.append((itinerary, score))
        
        return scored_options
