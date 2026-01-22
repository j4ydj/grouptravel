"""Optimiser service for simulating and scoring travel options."""
from datetime import date, datetime, time, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.backend.db.models import Event, Attendee, EventAttendee
from app.backend.services.pricing import MockPricingProvider, PricingProvider, DuffelProvider
from app.backend.services.hotel import HotelOptimisationService
from app.backend.services.transfer import TransferBatchingService
from app.backend.services.preference import PreferenceLearningService
from app.backend.schemas.itinerary import OptionResult, OptionResultV2, AttendeeItinerary, Itinerary
from app.backend.schemas.event import DateWindow
from app.backend.core.config import settings


class OptimiserService:
    """Service for optimizing group travel options."""
    
    def __init__(self, pricing_provider: Optional[PricingProvider] = None):
        """
        Initialize optimiser service.
        
        Args:
            pricing_provider: Pricing provider instance (defaults to MockPricingProvider or DuffelProvider if configured)
        """
        if pricing_provider:
            self.pricing_provider = pricing_provider
        elif settings.duffel_api_key:
            # Use Duffel if API key is configured
            self.pricing_provider = DuffelProvider(api_key=settings.duffel_api_key)
        else:
            # Default to mock
            self.pricing_provider = MockPricingProvider(
                volatile=settings.price_volatility
            )
        self.hotel_service = HotelOptimisationService()
        self.transfer_service = TransferBatchingService()
        self.preference_service = PreferenceLearningService()
    
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
        return_date = date_window.start_date + timedelta(days=duration_days)
        
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
    
    def _calculate_score_v2(
        self,
        flight_cost: float,
        hotel_cost: float,
        transfer_cost: float,
        arrival_spread_minutes: float,
        avg_travel_time_minutes: float,
        connections_rate: float,
        late_arrival_risk: float,
        operational_complexity_score: float
    ) -> float:
        """
        Calculate Phase 2 optimization score.
        
        Lower score is better.
        
        Formula:
        score = flight_cost * 1.0
              + hotel_cost * 0.8
              + transfer_cost * 0.5
              + arrival_spread_minutes * 5
              + avg_travel_time_minutes * 2
              + connections_rate * 500
              + late_arrival_risk * 200
              + operational_complexity_score * 300
        
        Args:
            flight_cost: Total flight cost in USD
            hotel_cost: Total hotel cost in USD
            transfer_cost: Total transfer cost in USD
            arrival_spread_minutes: Time spread in minutes
            avg_travel_time_minutes: Average travel time in minutes
            connections_rate: Rate of connections (0-1)
            late_arrival_risk: Percentage of arrivals after 18:00 (0-1)
            operational_complexity_score: Complexity score
        
        Returns:
            Score (lower is better)
        """
        return (
            flight_cost * 1.0 +
            hotel_cost * 0.8 +
            transfer_cost * 0.5 +
            arrival_spread_minutes * 5 +
            avg_travel_time_minutes * 2 +
            connections_rate * 500 +
            late_arrival_risk * 200 +
            operational_complexity_score * 300
        )
    
    def _calculate_co2_estimate(
        self,
        attendee_itineraries: List[AttendeeItinerary]
    ) -> float:
        """
        Simple CO2 estimate based on distance and travel class.
        
        Args:
            attendee_itineraries: List of attendee itineraries
        
        Returns:
            CO2 estimate in kg
        """
        # Simple model: ~0.25 kg CO2 per km for economy, ~0.5 for business
        total_co2 = 0.0
        
        for ai in attendee_itineraries:
            # Estimate distance (rough: use average distance per route)
            # For MVP: assume ~1000 km average per flight leg
            distance_km = 1000 * (ai.itinerary.stops + 1)
            
            # Travel class multiplier
            if ai.itinerary.airline:  # Simple heuristic
                co2_per_km = 0.25  # Economy default
            else:
                co2_per_km = 0.25
            
            total_co2 += distance_km * co2_per_km
        
        return round(total_co2, 2)
    
    def _calculate_late_arrival_risk(
        self,
        arrival_times: List[datetime]
    ) -> float:
        """
        Calculate percentage of arrivals after 18:00.
        
        Args:
            arrival_times: List of arrival datetimes
        
        Returns:
            Risk percentage (0-1)
        """
        if not arrival_times:
            return 0.0
        
        late_count = sum(1 for dt in arrival_times if dt.hour >= 18)
        return late_count / len(arrival_times)
    
    def _build_arrival_histogram(
        self,
        arrival_times: List[datetime]
    ) -> List[int]:
        """
        Build 24-hour arrival histogram.
        
        Args:
            arrival_times: List of arrival datetimes
        
        Returns:
            List of 24 integers (hourly buckets)
        """
        histogram = [0] * 24
        
        for dt in arrival_times:
            hour = dt.hour
            histogram[hour] += 1
        
        return histogram
    
    async def simulate_option_v2(
        self,
        location: str,
        date_window: DateWindow,
        attendees: List[Attendee],
        duration_days: int,
        db: Session,
        include_hotels: bool = True,
        include_transfers: bool = True
    ) -> OptionResultV2:
        """
        Simulate a single location/date option with Phase 2 features.
        
        Args:
            location: Destination IATA code
            date_window: Date window for the event
            attendees: List of attendees
            duration_days: Event duration in days
            db: Database session
            include_hotels: Whether to include hotel optimization
            include_transfers: Whether to include transfer optimization
        
        Returns:
            OptionResultV2 with all metrics
        """
        # Phase 1: Get flight itineraries (existing logic)
        attendee_itineraries: List[AttendeeItinerary] = []
        all_arrival_times: List[datetime] = []
        all_departure_times: List[datetime] = []
        total_cost = 0.0
        total_travel_time = 0
        connections_count = 0
        
        depart_date = date_window.start_date
        return_date = date_window.start_date + timedelta(days=duration_days)
        
        for attendee in attendees:
            constraints = {
                "travel_class": attendee.travel_class.value if attendee.travel_class else "economy",
                "preferred_airlines": attendee.preferred_airlines or [],
                "time_constraints": attendee.time_constraints or {}
            }
            
            itinerary = await self.pricing_provider.get_best_itinerary(
                origin=attendee.home_airport,
                destination=location,
                depart_date=depart_date,
                return_date=return_date,
                constraints=constraints
            )
            
            total_cost += itinerary.price
            total_travel_time += itinerary.travel_minutes
            if itinerary.stops > 0:
                connections_count += 1
            
            # Build datetime objects for arrival/departure
            arrival_dt = datetime.combine(depart_date, itinerary.arrive_time)
            departure_dt = datetime.combine(return_date, itinerary.depart_time) if hasattr(itinerary, 'return_depart_time') else datetime.combine(return_date, time(10, 0))
            
            all_arrival_times.append(arrival_dt)
            all_departure_times.append(departure_dt)
            
            attendee_itineraries.append(
                AttendeeItinerary(
                    attendee_id=attendee.id,
                    employee_id=attendee.employee_id,
                    itinerary=itinerary
                )
            )
        
        # Calculate Phase 1 metrics
        num_attendees = len(attendees)
        avg_travel_time_minutes = total_travel_time / num_attendees if num_attendees > 0 else 0
        connections_rate = connections_count / num_attendees if num_attendees > 0 else 0
        
        if all_arrival_times:
            arrival_spread_minutes = (max(all_arrival_times) - min(all_arrival_times)).total_seconds() / 60
        else:
            arrival_spread_minutes = 0
        
        # Phase 2: Hotel optimization
        hotel_cost = 0.0
        extra_nights_count = 0
        hotel_assignment = None
        
        if include_hotels and all_arrival_times:
            room_nights = self.hotel_service.compute_room_nights(
                all_arrival_times,
                all_departure_times,
                duration_days
            )
            
            hotel_assignment = self.hotel_service.select_optimal_hotel(
                airport_code=location,
                num_attendees=num_attendees,
                room_nights=room_nights,
                approved_only=True,
                db=db
            )
            
            if hotel_assignment:
                hotel_cost = hotel_assignment.total_cost
                extra_nights_count = hotel_assignment.extra_nights
        
        # Phase 2: Transfer optimization
        transfer_cost = 0.0
        operational_complexity_score = 0.0
        transfer_plan = None
        
        if include_transfers and all_arrival_times and hotel_assignment:
            attendee_ids = [ai.attendee_id for ai in attendee_itineraries]
            waves = self.transfer_service.compute_arrival_waves(
                all_arrival_times,
                attendee_ids
            )
            
            transfer_plan = self.transfer_service.optimize_transfers(
                waves=waves,
                airport_code=location,
                hotel_id=hotel_assignment.hotel_id,
                db=db
            )
            
            if transfer_plan:
                transfer_cost = transfer_plan.total_cost
                operational_complexity_score = transfer_plan.operational_complexity_score
        
        # Phase 2: Additional metrics
        late_arrival_risk = self._calculate_late_arrival_risk(all_arrival_times)
        co2_estimate = self._calculate_co2_estimate(attendee_itineraries)
        arrival_histogram = self._build_arrival_histogram(all_arrival_times)
        
        # Calculate Phase 2 score
        score = self._calculate_score_v2(
            flight_cost=total_cost,
            hotel_cost=hotel_cost,
            transfer_cost=transfer_cost,
            arrival_spread_minutes=arrival_spread_minutes,
            avg_travel_time_minutes=avg_travel_time_minutes,
            connections_rate=connections_rate,
            late_arrival_risk=late_arrival_risk,
            operational_complexity_score=operational_complexity_score
        )
        
        # Build OptionResultV2
        base_result = OptionResult(
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
        
        return OptionResultV2(
            **base_result.model_dump(),
            hotel_cost=round(hotel_cost, 2),
            extra_nights_count=extra_nights_count,
            transfer_cost=round(transfer_cost, 2),
            operational_complexity_score=round(operational_complexity_score, 2),
            co2_estimate_kg=co2_estimate,
            late_arrival_risk=round(late_arrival_risk, 4),
            hotel_assignment=hotel_assignment,
            transfer_plan=transfer_plan,
            arrival_histogram=arrival_histogram
        )
