"""Event Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime, date


class DateWindow(BaseModel):
    """Date window schema."""
    start_date: date
    end_date: date


class EventCreate(BaseModel):
    """Schema for creating an event."""
    name: str = Field(..., description="Event name")
    candidate_locations: List[str] = Field(..., min_items=1, description="List of IATA airport codes")
    candidate_date_windows: List[DateWindow] = Field(..., min_items=1, description="List of date windows")
    duration_days: int = Field(..., gt=0, description="Event duration in days")
    created_by: str = Field(..., description="Creator identifier")


class EventDraft(BaseModel):
    """Schema for event draft from LLM parsing."""
    name: str
    candidate_locations: List[str] = Field(default_factory=list)
    candidate_date_windows: List[DateWindow] = Field(default_factory=list)
    duration_days: int = Field(default=3)
    created_by: str = "system"


class Event(BaseModel):
    """Schema for event response."""
    id: str
    name: str
    candidate_locations: List[str]
    candidate_date_windows: List[Dict[str, Any]]  # JSON representation
    duration_days: int
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventAttendeesAttach(BaseModel):
    """Schema for attaching attendees to an event."""
    attendee_ids: List[str] = Field(..., min_items=1, description="List of attendee IDs")
