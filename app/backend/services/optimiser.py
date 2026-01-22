"""Optimiser service for simulating and scoring travel options."""
from datetime import date, datetime, time, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.backend.db.models import Event, Attendee, EventAttendee
from app.backend.services.pricing import MockPricingProvider, PricingProvider
from app.backend.schemas.itinerary import OptionResult, AttendeeItinerary, Itinerary
from app.backend.schemas.event import DateWindow
from app.backend.core.config import settings


class OptimiserService:
    """Service for optimizing group travel options."""
    
    def __init__(self, pricing_provider: Optional[PricingProvider] = None):
        """
        Initialize optimiser service.
        
        Args:
            pricing_provider: Pricing provider instance (defaults to MockPricingProvider)
        """
        self.pricing_provider = pricing_provider or MockPricingProvider(
            volatile=settings.price_volatility
        )
    
    def _calculate_score(
        self,
        total_cost: float,
        arrival_spread_minutes: float,
        avg_travel_time_minutes: float,
        connections_rate: float
    ) -> float:
        """
        Calculate optimization score.
        
        Lower score is better.
        
        Formula:
        score = (total_cost * 1.0) + (arrival_spread_minutes * 5) + 
                (avg_travel_time_minutes * 2) + (connections_rate * 500)
        
        Args:
            total_cost: Total cost in USD
            arrival_spread_minutes: Time spread in minutes
            avg_travel_time_minutes: Average travel time in minutes
            connections_rate: Rate of connections (0-1)
        
        Returns:
            Score (lower is better)
        """
        return (
            total_cost * 1.0 +
            arrival_spread_minutes * 5 +
            avg_travel_time_minutes * 2 +
            connections_rate * 500
        )
    
    def _time_to_minutes(self, time_obj: time, base_date: date) -> int:
        """Convert time to minutes since midnight."""
        return time_obj.hour * 60 + time_obj.minute
    
    def _minutes_to_time(self, minutes: int) -> time:
        """Convert minutes since midnight to time object."""
        hours = (minutes // 60) % 24
        mins = minutes % 60
        return time(hours, mins)
    
    async def simulate_option(
        self,
        location: str,
        date_window: DateWindow,
        attendees: List[Attendee],
        duration_days: int
    ) -> OptionResult:
        """
        Simulate a single location/date option.
        
        Args:
            location: Destination IATA code
            date_window: Date window for the event
            attendees: List of attendees
            duration_days: Event duration in days
        
        Returns:
            OptionResult with metrics and attendee itineraries
        """
        attendee_itineraries: List[AttendeeItinerary] = []
        all_arrival_times: List[int] = []
        total_cost = 0.0
        total_travel_time = 0
        connections_count = 0
        
        # Use start of date window for departure
        depart_date = date_window.start_date
        return_date = date_window.start_date + datetime.timedelta(days=duration_days)
        
        for attendee in attendees:
            # Build constraints
            constraints = {
                "travel_class": attendee.travel_class.value if attendee.travel_class else "economy",
                "preferred_airlines": attendee.preferred_airlines or [],
                "time_constraints": attendee.time_constraints or {}
            }
            
            # Get itinerary from pricing provider
            itinerary = await self.pricing_provider.get_best_itinerary(
                origin=attendee.home_airport,
                destination=location,
                depart_date=depart_date,
                return_date=return_date,
                constraints=constraints
            )
            
            # Track metrics
            total_cost += itinerary.price
            total_travel_time += itinerary.travel_minutes
            if itinerary.stops > 0:
                connections_count += 1
            
            # Calculate arrival time in minutes
            arrival_minutes = self._time_to_minutes(itinerary.arrive_time, depart_date)
            all_arrival_times.append(arrival_minutes)
            
            # Create attendee itinerary
            attendee_itineraries.append(
                AttendeeItinerary(
                    attendee_id=attendee.id,
                    employee_id=attendee.employee_id,
                    itinerary=itinerary
                )
            )
        
        # Calculate metrics
        num_attendees = len(attendees)
        avg_travel_time_minutes = total_travel_time / num_attendees if num_attendees > 0 else 0
        connections_rate = connections_count / num_attendees if num_attendees > 0 else 0
        
        # Calculate arrival spread
        if all_arrival_times:
            arrival_spread_minutes = max(all_arrival_times) - min(all_arrival_times)
        else:
            arrival_spread_minutes = 0
        
        # Calculate score
        score = self._calculate_score(
            total_cost=total_cost,
            arrival_spread_minutes=arrival_spread_minutes,
            avg_travel_time_minutes=avg_travel_time_minutes,
            connections_rate=connections_rate
        )
        
        return OptionResult(
            location=location,
            date_window_start=date_window.start_date,
            date_window_end=date_window.end_date,
            total_cost=round(total_cost, 2),
            avg_travel_time_minutes=round(avg_travel_time_minutes, 2),
            arrival_spread_minutes=round(arrival_spread_minutes, 2),
            connections_rate=round(connections_rate, 4),
            score=round(score, 2),
            attendee_itineraries=attendee_itineraries
        )
    
    async def simulate_event(
        self,
        event: Event,
        db: Session
    ) -> List[OptionResult]:
        """
        Simulate all options for an event.
        
        Args:
            event: Event model instance
            db: Database session
        
        Returns:
            List of OptionResult for each location/date combination
        """
        # Get attendees for this event
        event_attendee_rels = db.query(EventAttendee).filter_by(event_id=event.id).all()
        attendee_ids = [ea.attendee_id for ea in event_attendee_rels]
        attendees = db.query(Attendee).filter(Attendee.id.in_(attendee_ids)).all()
        
        if not attendees:
            return []
        
        # Parse date windows
        date_windows = []
        for dw in event.candidate_date_windows:
            if isinstance(dw, dict):
                start_date_str = dw.get("start_date")
                end_date_str = dw.get("end_date")
                if isinstance(start_date_str, str):
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                else:
                    start_date = start_date_str if isinstance(start_date_str, date) else date.today()
                if isinstance(end_date_str, str):
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                else:
                    end_date = end_date_str if isinstance(end_date_str, date) else date.today()
                date_windows.append(DateWindow(start_date=start_date, end_date=end_date))
        
        # Simulate all combinations
        results: List[OptionResult] = []
        
        for location in event.candidate_locations:
            for date_window in date_windows:
                option_result = await self.simulate_option(
                    location=location,
                    date_window=date_window,
                    attendees=attendees,
                    duration_days=event.duration_days
                )
                results.append(option_result)
        
        return results
