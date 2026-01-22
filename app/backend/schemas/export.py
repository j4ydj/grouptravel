"""Export Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date, datetime


class ConcurPayload(BaseModel):
    """Concur deep-link payload for a single attendee."""
    attendee_id: str
    employee_id: str
    origin: str = Field(..., description="Origin IATA code")
    destination: str = Field(..., description="Destination IATA code")
    depart_date: date
    return_date: date
    airline: str
    fare_class: str
    hotel_id: Optional[str]
    hotel_name: Optional[str]
    cost_centre: str = Field(default="TRAVEL", description="Cost centre code")
    event_id: str
    total_cost: float = Field(..., ge=0, description="Total cost in USD")
    deep_link_url: str = Field(..., description="Concur deep link URL")
    payload_json: Dict = Field(..., description="Full payload JSON")


class FinanceExport(BaseModel):
    """Finance export for event-level cost forecast."""
    event_id: str
    event_name: str
    generated_at: datetime
    forecast_flights: float = Field(..., ge=0, description="Total flight cost forecast")
    forecast_hotels: float = Field(..., ge=0, description="Total hotel cost forecast")
    forecast_transfers: float = Field(..., ge=0, description="Total transfer cost forecast")
    total_commitment: float = Field(..., ge=0, description="Total commitment")
    per_person_breakdown: List[Dict] = Field(..., description="Per-person cost breakdown")
    cost_by_category: Dict[str, float] = Field(..., description="Cost breakdown by category")
    export_format: str = Field(default="json", description="Export format: json or csv")


class OrganiserBrief(BaseModel):
    """AI-generated organiser brief."""
    event_id: str
    event_name: str
    generated_at: datetime
    executive_summary: str = Field(..., description="Executive summary")
    recommended_option: Dict = Field(..., description="Recommended option details")
    savings_vs_alternatives: Dict = Field(..., description="Savings comparison")
    operational_plan: str = Field(..., description="Operational plan text")
    hotel_plan: str = Field(..., description="Hotel plan details")
    transfer_plan: str = Field(..., description="Transfer plan details")
    booking_instructions: str = Field(..., description="Booking instructions stub")
    format: str = Field(default="markdown", description="Format: markdown or pdf")
