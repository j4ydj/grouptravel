"""Itinerary and result schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date, time


class Itinerary(BaseModel):
    """Flight itinerary schema."""
    origin: str = Field(..., description="Origin IATA code")
    destination: str = Field(..., description="Destination IATA code")
    depart_date: date
    return_date: date
    airline: str = Field(..., description="Airline code")
    stops: int = Field(..., ge=0, description="Number of stops")
    depart_time: time = Field(..., description="Departure time")
    arrive_time: time = Field(..., description="Arrival time")
    travel_minutes: int = Field(..., ge=0, description="Total travel time in minutes")
    price: float = Field(..., ge=0, description="Price in USD")
    concur_deep_link: Optional[str] = Field(None, description="Concur deep link placeholder")


class AttendeeItinerary(BaseModel):
    """Itinerary for a specific attendee."""
    attendee_id: str
    employee_id: str
    itinerary: Itinerary


class OptionResult(BaseModel):
    """Result for a single location/date option."""
    location: str = Field(..., description="Destination IATA code")
    date_window_start: date
    date_window_end: date
    total_cost: float = Field(..., ge=0, description="Total cost in USD")
    avg_travel_time_minutes: float = Field(..., ge=0, description="Average travel time")
    arrival_spread_minutes: float = Field(..., ge=0, description="Time spread between earliest and latest arrival")
    connections_rate: float = Field(..., ge=0, le=1, description="Rate of itineraries with connections")
    score: float = Field(..., description="Optimization score (lower is better)")
    attendee_itineraries: List[AttendeeItinerary] = Field(..., description="Per-attendee itineraries")


class SimulationResult(BaseModel):
    """Complete simulation result."""
    event_id: str
    results: List[OptionResult] = Field(..., description="Results for each option")
    ranked_options: List[int] = Field(..., description="Indices of options ranked by score")
    created_at: datetime
    version: int
