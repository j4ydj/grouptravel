"""Preference profile Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class ArrivalWindow(BaseModel):
    """Typical arrival window."""
    start: str = Field(..., description="Start time HH:MM")
    end: str = Field(..., description="End time HH:MM")


class PreferenceProfileCreate(BaseModel):
    """Schema for creating a preference profile."""
    attendee_id: str = Field(..., description="Attendee ID")
    prefers_early_flights: float = Field(default=0.5, ge=0, le=1, description="Preference for early flights (0-1)")
    avoids_connections: float = Field(default=0.5, ge=0, le=1, description="Preference to avoid connections (0-1)")
    preferred_hubs: List[str] = Field(default_factory=list, description="Preferred hub airports")
    typical_arrival_window: Optional[Dict[str, str]] = Field(None, description="Typical arrival window {start: HH:MM, end: HH:MM}")
    reliability_score: float = Field(default=1.0, ge=0, le=1, description="Reliability score (0-1)")


class PreferenceProfile(BaseModel):
    """Schema for preference profile response."""
    id: str
    attendee_id: str
    prefers_early_flights: float
    avoids_connections: float
    preferred_hubs: List[str]
    typical_arrival_window: Optional[Dict[str, str]]
    reliability_score: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PreferenceUpdate(BaseModel):
    """Schema for EMA-style preference update."""
    attendee_id: str
    booked_itinerary: Dict = Field(..., description="Booked itinerary data")
    # Fields will be updated using EMA from actual booking
