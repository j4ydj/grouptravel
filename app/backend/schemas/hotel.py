"""Hotel Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HotelCreate(BaseModel):
    """Schema for creating a hotel."""
    name: str = Field(..., description="Hotel name")
    city: str = Field(..., description="City name")
    airport_code: str = Field(..., min_length=3, max_length=3, description="IATA airport code")
    chain: Optional[str] = Field(None, description="Hotel chain")
    approved: bool = Field(default=False, description="Whether hotel is approved for corporate use")
    corporate_rate: Optional[float] = Field(None, ge=0, description="Corporate rate per night in USD")
    distance_to_venue_km: Optional[float] = Field(None, ge=0, description="Distance to venue in km")
    capacity: Optional[int] = Field(None, gt=0, description="Room capacity")
    has_meeting_space: bool = Field(default=False, description="Has meeting space")


class Hotel(BaseModel):
    """Schema for hotel response."""
    id: str
    name: str
    city: str
    airport_code: str
    chain: Optional[str]
    approved: bool
    corporate_rate: Optional[float]
    distance_to_venue_km: Optional[float]
    capacity: Optional[int]
    has_meeting_space: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class RoomNightAnalysis(BaseModel):
    """Analysis of room night requirements."""
    required_rooms_per_night: List[int] = Field(..., description="Rooms needed per night")
    peak_occupancy: int = Field(..., description="Peak number of rooms needed")
    shoulder_nights: int = Field(..., ge=0, description="Extra nights needed due to arrival/departure spread")
    total_room_nights: int = Field(..., ge=0, description="Total room nights")
    nights_with_peak: int = Field(..., ge=0, description="Number of nights at peak occupancy")


class HotelAssignment(BaseModel):
    """Hotel assignment for an option."""
    hotel_id: str
    hotel_name: str
    total_cost: float = Field(..., ge=0, description="Total hotel cost in USD")
    room_nights: int = Field(..., ge=0, description="Total room nights")
    extra_nights: int = Field(..., ge=0, description="Extra nights due to spread")
    room_night_analysis: RoomNightAnalysis
