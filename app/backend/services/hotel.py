"""Hotel optimization service."""
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from collections import defaultdict
from app.backend.db.models import Hotel
from app.backend.schemas.hotel import RoomNightAnalysis, HotelAssignment


class HotelOptimisationService:
    """Service for optimizing hotel selection and room night calculations."""
    
    def compute_room_nights(
        self,
        arrival_times: List[datetime],
        departure_times: List[datetime],
        duration_days: int
    ) -> RoomNightAnalysis:
        """
        Compute room night requirements from arrival/departure times.
        
        Args:
            arrival_times: List of arrival datetimes
            departure_times: List of departure datetimes
            duration_days: Event duration in days
        
        Returns:
            RoomNightAnalysis with room requirements
        """
        if not arrival_times or not departure_times:
            return RoomNightAnalysis(
                required_rooms_per_night=[],
                peak_occupancy=0,
                shoulder_nights=0,
                total_room_nights=0,
                nights_with_peak=0
            )
        
        # Normalize to dates (midnight)
        arrival_dates = [dt.date() for dt in arrival_times]
        departure_dates = [dt.date() for dt in departure_times]
        
        # Find date range
        earliest_arrival = min(arrival_dates)
        latest_departure = max(departure_dates)
        
        # Calculate event dates (assuming event starts on earliest arrival)
        event_start = earliest_arrival
        event_end = event_start + timedelta(days=duration_days)
        
        # Count rooms needed per night
        rooms_per_night = defaultdict(int)
        
        for arrival_date, departure_date in zip(arrival_dates, departure_dates):
            # Person needs room from arrival until departure
            # But event runs from event_start to event_end
            # So they need room from max(arrival, event_start) to min(departure, event_end)
            check_in = max(arrival_date, event_start)
            check_out = min(departure_date, event_end)
            
            # Count each night they need a room
            current_date = check_in
            while current_date < check_out:
                rooms_per_night[current_date] += 1
                current_date += timedelta(days=1)
        
        # Build list of required rooms per night (for event duration)
        required_rooms = []
        current_date = event_start
        while current_date < event_end:
            required_rooms.append(rooms_per_night[current_date])
            current_date += timedelta(days=1)
        
        peak_occupancy = max(required_rooms) if required_rooms else 0
        
        # Calculate shoulder nights (extra nights before/after event)
        shoulder_nights = 0
        
        # Nights before event start
        for arrival_date in arrival_dates:
            if arrival_date < event_start:
                shoulder_nights += (event_start - arrival_date).days
        
        # Nights after event end
        for departure_date in departure_dates:
            if departure_date > event_end:
                shoulder_nights += (departure_date - event_end).days
        
        # Total room nights
        total_room_nights = sum(required_rooms) + shoulder_nights
        
        # Nights at peak
        nights_with_peak = sum(1 for r in required_rooms if r == peak_occupancy)
        
        return RoomNightAnalysis(
            required_rooms_per_night=required_rooms,
            peak_occupancy=peak_occupancy,
            shoulder_nights=shoulder_nights,
            total_room_nights=total_room_nights,
            nights_with_peak=nights_with_peak
        )
    
    def select_optimal_hotel(
        self,
        airport_code: str,
        num_attendees: int,
        room_nights: RoomNightAnalysis,
        approved_only: bool = True,
        db: Session
    ) -> Optional[HotelAssignment]:
        """
        Select optimal hotel based on capacity, rate, and distance.
        
        Args:
            airport_code: Destination airport code
            num_attendees: Number of attendees
            room_nights: Room night analysis
            approved_only: Only consider approved hotels
            db: Database session
        
        Returns:
            HotelAssignment or None if no suitable hotel found
        """
        # Query hotels
        query = db.query(Hotel).filter_by(airport_code=airport_code)
        
        if approved_only:
            query = query.filter_by(approved=True)
        
        hotels = query.all()
        
        if not hotels:
            return None
        
        # Score hotels
        best_hotel = None
        best_score = float('inf')
        
        for hotel in hotels:
            # Check capacity
            if hotel.capacity and hotel.capacity < room_nights.peak_occupancy:
                continue
            
            # Score: lower is better
            # Factors: rate, distance, capacity match
            score = 0.0
            
            if hotel.corporate_rate:
                score += hotel.corporate_rate * 100  # Rate weight
            else:
                score += 10000  # Penalty for missing rate
            
            if hotel.distance_to_venue_km:
                score += hotel.distance_to_venue_km * 10  # Distance weight
            
            # Prefer hotels with capacity close to peak (not too large)
            if hotel.capacity:
                capacity_diff = abs(hotel.capacity - room_nights.peak_occupancy)
                score += capacity_diff * 5
            
            if score < best_score:
                best_score = score
                best_hotel = hotel
        
        if not best_hotel:
            return None
        
        # Calculate total cost
        total_cost = self.calculate_hotel_cost(
            best_hotel,
            room_nights.total_room_nights,
            room_nights.shoulder_nights
        )
        
        return HotelAssignment(
            hotel_id=best_hotel.id,
            hotel_name=best_hotel.name,
            total_cost=total_cost,
            room_nights=room_nights.total_room_nights,
            extra_nights=room_nights.shoulder_nights,
            room_night_analysis=room_nights
        )
    
    def calculate_hotel_cost(
        self,
        hotel: Hotel,
        room_nights: int,
        extra_nights: int
    ) -> float:
        """
        Calculate total hotel cost.
        
        Args:
            hotel: Hotel model
            room_nights: Total room nights needed
            extra_nights: Extra nights (shoulder nights)
        
        Returns:
            Total cost in USD
        """
        if not hotel.corporate_rate:
            # Default rate if not specified
            return room_nights * 150.0  # $150/night default
        
        # Base cost for event nights
        base_cost = room_nights * hotel.corporate_rate
        
        # Extra nights might have different rate (assume same for now)
        extra_cost = extra_nights * hotel.corporate_rate
        
        return base_cost + extra_cost
