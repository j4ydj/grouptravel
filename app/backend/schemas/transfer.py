"""Transfer Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, time
from app.backend.db.models import TransferMode


class TransferOptionCreate(BaseModel):
    """Schema for creating a transfer option."""
    airport_code: str = Field(..., min_length=3, max_length=3, description="IATA airport code")
    hotel_id: Optional[str] = Field(None, description="Hotel ID (optional)")
    mode: TransferMode = Field(..., description="Transfer mode")
    capacity: int = Field(..., gt=0, description="Vehicle capacity")
    cost_per_trip: float = Field(..., ge=0, description="Cost per trip in USD")
    duration_minutes: int = Field(..., ge=0, description="Duration in minutes")


class TransferOption(BaseModel):
    """Schema for transfer option response."""
    id: str
    airport_code: str
    hotel_id: Optional[str]
    mode: TransferMode
    capacity: int
    cost_per_trip: float
    duration_minutes: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransferWave(BaseModel):
    """Grouped arrivals for transfer batching."""
    wave_start: datetime = Field(..., description="Start of wave window")
    wave_end: datetime = Field(..., description="End of wave window")
    attendee_count: int = Field(..., ge=0, description="Number of attendees in wave")
    attendee_ids: List[str] = Field(..., description="Attendee IDs in this wave")


class TransferLeg(BaseModel):
    """Single transfer leg."""
    wave: TransferWave
    mode: TransferMode
    vehicle_count: int = Field(..., ge=0, description="Number of vehicles needed")
    total_cost: float = Field(..., ge=0, description="Total cost for this leg")
    capacity_utilization: float = Field(..., ge=0, le=1, description="Capacity utilization (0-1)")


class TransferPlan(BaseModel):
    """Complete transfer plan for an option."""
    airport_code: str
    hotel_id: str
    total_cost: float = Field(..., ge=0, description="Total transfer cost")
    total_vehicles: int = Field(..., ge=0, description="Total number of vehicles")
    legs: List[TransferLeg] = Field(..., description="Individual transfer legs")
    operational_complexity_score: float = Field(..., ge=0, description="Complexity score (higher = more complex)")
