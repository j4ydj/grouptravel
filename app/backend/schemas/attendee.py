"""Attendee Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.backend.db.models import TravelClass


class AttendeeCreate(BaseModel):
    """Schema for creating an attendee."""
    employee_id: str = Field(..., description="Unique employee identifier")
    home_airport: str = Field(..., min_length=3, max_length=3, description="IATA airport code")
    preferred_airports: List[str] = Field(default_factory=list, description="Preferred airport codes")
    travel_class: TravelClass = Field(default=TravelClass.ECONOMY, description="Preferred travel class")
    preferred_airlines: List[str] = Field(default_factory=list, description="Preferred airline codes")
    time_constraints: Dict[str, Any] = Field(default_factory=dict, description="Time constraints")
    timezone: Optional[str] = Field(None, description="Timezone (defaults to airport timezone if not provided)")


class Attendee(BaseModel):
    """Schema for attendee response."""
    id: str
    employee_id: str
    home_airport: str
    preferred_airports: List[str]
    travel_class: TravelClass
    preferred_airlines: List[str]
    time_constraints: Dict[str, Any]
    timezone: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AttendeeList(BaseModel):
    """Schema for list of attendees."""
    attendees: List[Attendee]
    total: int
