"""Itinerary and result schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date, time
from app.backend.schemas.hotel import HotelAssignment
from app.backend.schemas.transfer import TransferPlan


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


class OptionResultV2(OptionResult):
    """Extended result with Phase 2 metrics."""
    # Phase 1 fields inherited from OptionResult
    
    # Phase 2 additions
    hotel_cost: float = Field(default=0.0, ge=0, description="Total hotel cost in USD")
    extra_nights_count: int = Field(default=0, ge=0, description="Extra nights needed due to arrival/departure spread")
    transfer_cost: float = Field(default=0.0, ge=0, description="Total transfer cost in USD")
    operational_complexity_score: float = Field(default=0.0, ge=0, description="Operational complexity score")
    co2_estimate_kg: float = Field(default=0.0, ge=0, description="CO2 estimate in kg")
    late_arrival_risk: float = Field(default=0.0, ge=0, le=1, description="Percentage of arrivals after 18:00")
    
    # Detailed breakdowns
    hotel_assignment: Optional[HotelAssignment] = Field(None, description="Hotel assignment details")
    transfer_plan: Optional[TransferPlan] = Field(None, description="Transfer plan details")
    arrival_histogram: Optional[List[int]] = Field(None, description="Arrival histogram (24 hourly buckets)")


class SimulationResult(BaseModel):
    """Complete simulation result."""
    event_id: str
    results: List[OptionResult] = Field(..., description="Results for each option")
    ranked_options: List[int] = Field(..., description="Indices of options ranked by score")
    created_at: datetime
    version: int


class SimulationResultV2(BaseModel):
    """Complete simulation result with Phase 2 data."""
    event_id: str
    results: List[OptionResultV2] = Field(..., description="Results for each option (Phase 2)")
    ranked_options: List[int] = Field(..., description="Indices of options ranked by score")
    created_at: datetime
    version: int
    pricing_provider: Optional[str] = Field(None, description="Pricing provider used")
    pricing_cache_version: Optional[str] = Field(None, description="Cache version")
    random_seed: Optional[int] = Field(None, description="Random seed for reproducibility")
