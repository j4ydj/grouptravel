"""Export service for Concur, finance, and organiser briefs."""
from typing import List, Dict, Optional
from datetime import datetime, date
from urllib.parse import urlencode
import json
from sqlalchemy.orm import Session
from app.backend.db.models import Event, Attendee, Hotel
from app.backend.schemas.itinerary import OptionResultV2, SimulationResultV2, AttendeeItinerary
from app.backend.schemas.export import ConcurPayload, FinanceExport, OrganiserBrief
from app.backend.services.llm import LLMClient, get_llm_client


class ExportService:
    """Service for generating export payloads."""
    
    CONCUR_BASE_URL = "https://concur.example.com/book"
    
    def generate_concur_payload(
        self,
        attendee: Attendee,
        itinerary: AttendeeItinerary,
        hotel_assignment: Optional[Dict],
        event: Event
    ) -> ConcurPayload:
        """
        Generate Concur deep-link payload for a single attendee.
        
        Args:
            attendee: Attendee model
            itinerary: Attendee itinerary
            hotel_assignment: Hotel assignment dict (optional)
            event: Event model
        
        Returns:
            ConcurPayload
        """
        # Build payload JSON
        payload_data = {
            "employee_id": attendee.employee_id,
            "origin": itinerary.itinerary.origin,
            "destination": itinerary.itinerary.destination,
            "depart_date": itinerary.itinerary.depart_date.isoformat(),
            "return_date": itinerary.itinerary.return_date.isoformat(),
            "airline": itinerary.itinerary.airline,
            "fare_class": itinerary.itinerary.stops,  # Simplified
            "cost_centre": "TRAVEL",
            "event_id": event.id,
            "event_name": event.name,
            "total_cost": itinerary.itinerary.price
        }
        
        if hotel_assignment:
            payload_data["hotel_id"] = hotel_assignment.get("hotel_id")
            payload_data["hotel_name"] = hotel_assignment.get("hotel_name")
            payload_data["hotel_cost"] = hotel_assignment.get("total_cost", 0)
        
        # Generate deep link URL
        url_params = {
            "origin": itinerary.itinerary.origin,
            "dest": itinerary.itinerary.destination,
            "depart": itinerary.itinerary.depart_date.isoformat(),
            "return": itinerary.itinerary.return_date.isoformat(),
            "employee": attendee.employee_id,
            "event": event.id
        }
        
        deep_link_url = f"{self.CONCUR_BASE_URL}?{urlencode(url_params)}"
        
        return ConcurPayload(
            attendee_id=attendee.id,
            employee_id=attendee.employee_id,
            origin=itinerary.itinerary.origin,
            destination=itinerary.itinerary.destination,
            depart_date=itinerary.itinerary.depart_date,
            return_date=itinerary.itinerary.return_date,
            airline=itinerary.itinerary.airline,
            fare_class="economy",  # Simplified
            hotel_id=hotel_assignment.get("hotel_id") if hotel_assignment else None,
            hotel_name=hotel_assignment.get("hotel_name") if hotel_assignment else None,
            cost_centre="TRAVEL",
            event_id=event.id,
            total_cost=itinerary.itinerary.price + (hotel_assignment.get("total_cost", 0) if hotel_assignment else 0),
            deep_link_url=deep_link_url,
            payload_json=payload_data
        )
    
    def generate_finance_export(
        self,
        event: Event,
        result: SimulationResultV2,
        selected_option_index: Optional[int] = None
    ) -> FinanceExport:
        """
        Generate finance export for event-level cost forecast.
        
        Args:
            event: Event model
            result: Simulation result (V2)
            selected_option_index: Index of selected option (defaults to best ranked)
        
        Returns:
            FinanceExport
        """
        if selected_option_index is None:
            selected_option_index = result.ranked_options[0] if result.ranked_options else 0
        
        selected_option = result.results[selected_option_index]
        
        # Calculate totals
        forecast_flights = selected_option.total_cost
        forecast_hotels = selected_option.hotel_cost
        forecast_transfers = selected_option.transfer_cost
        total_commitment = forecast_flights + forecast_hotels + forecast_transfers
        
        # Per-person breakdown
        per_person_breakdown = []
        for ai in selected_option.attendee_itineraries:
            person_cost = {
                "employee_id": ai.employee_id,
                "flight_cost": ai.itinerary.price,
                "hotel_cost": forecast_hotels / len(selected_option.attendee_itineraries) if selected_option.attendee_itineraries else 0,
                "transfer_cost": forecast_transfers / len(selected_option.attendee_itineraries) if selected_option.attendee_itineraries else 0,
                "total_cost": ai.itinerary.price + (forecast_hotels + forecast_transfers) / len(selected_option.attendee_itineraries) if selected_option.attendee_itineraries else 0
            }
            per_person_breakdown.append(person_cost)
        
        # Cost by category
        cost_by_category = {
            "flights": forecast_flights,
            "hotels": forecast_hotels,
            "transfers": forecast_transfers,
            "total": total_commitment
        }
        
        return FinanceExport(
            event_id=event.id,
            event_name=event.name,
            generated_at=datetime.utcnow(),
            forecast_flights=round(forecast_flights, 2),
            forecast_hotels=round(forecast_hotels, 2),
            forecast_transfers=round(forecast_transfers, 2),
            total_commitment=round(total_commitment, 2),
            per_person_breakdown=per_person_breakdown,
            cost_by_category=cost_by_category,
            export_format="json"
        )
    
    async def generate_organiser_brief(
        self,
        event: Event,
        result: SimulationResultV2,
        llm_client: Optional[LLMClient] = None
    ) -> OrganiserBrief:
        """
        Generate AI-generated comprehensive organiser brief.
        
        Args:
            event: Event model
            result: Simulation result (V2)
            llm_client: LLM client (optional, uses default if not provided)
        
        Returns:
            OrganiserBrief
        """
        if llm_client is None:
            llm_client = get_llm_client()
        
        # Get best option
        best_option_index = result.ranked_options[0] if result.ranked_options else 0
        best_option = result.results[best_option_index]
        
        # Build facts JSON for LLM
        facts = {
            "event_name": event.name,
            "event_id": event.id,
            "duration_days": event.duration_days,
            "total_options": len(result.results),
            "recommended_option": {
                "location": best_option.location,
                "total_cost": best_option.total_cost,
                "hotel_cost": best_option.hotel_cost,
                "transfer_cost": best_option.transfer_cost,
                "arrival_spread_minutes": best_option.arrival_spread_minutes,
                "score": best_option.score
            },
            "alternatives": [
                {
                    "location": opt.location,
                    "total_cost": opt.total_cost,
                    "score": opt.score
                }
                for idx, opt in enumerate(result.results[:3]) if idx != best_option_index
            ]
        }
        
        # Generate brief using LLM
        system_prompt = """You are an executive assistant generating a comprehensive organiser brief for a corporate group travel event. 
        Use only the provided FACTS JSON. Do not invent numbers. Structure the brief with:
        1. Executive summary
        2. Recommended option with rationale
        3. Savings vs alternatives
        4. Operational plan (arrival coordination, hotel, transfers)
        5. Booking instructions stub
        
        Keep it professional and actionable."""
        
        user_prompt = f"Generate an organiser brief based on these facts:\n\n{json.dumps(facts, indent=2)}"
        
        try:
            brief_text = await llm_client.complete_json(
                schema=OrganiserBrief,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )
            
            # If LLM returns structured brief, use it
            if isinstance(brief_text, OrganiserBrief):
                return brief_text
        except Exception:
            # Fallback to template-based brief
            pass
        
        # Fallback: Template-based brief
        savings_vs_alternatives = {}
        if len(result.results) > 1:
            for idx, opt in enumerate(result.results):
                if idx != best_option_index:
                    savings = opt.total_cost - best_option.total_cost
                    savings_vs_alternatives[opt.location] = round(savings, 2)
        
        return OrganiserBrief(
            event_id=event.id,
            event_name=event.name,
            generated_at=datetime.utcnow(),
            executive_summary=f"Analysis of {len(result.results)} options for {event.name}. Recommended option: {best_option.location} with total cost ${best_option.total_cost:,.2f}.",
            recommended_option={
                "location": best_option.location,
                "total_cost": best_option.total_cost,
                "hotel": best_option.hotel_assignment.hotel_name if best_option.hotel_assignment else "TBD",
                "score": best_option.score
            },
            savings_vs_alternatives=savings_vs_alternatives,
            operational_plan=f"Event duration: {event.duration_days} days. Arrival spread: {best_option.arrival_spread_minutes:.0f} minutes. Hotel: {best_option.hotel_assignment.hotel_name if best_option.hotel_assignment else 'TBD'}. Transfer plan available.",
            hotel_plan=f"Hotel: {best_option.hotel_assignment.hotel_name if best_option.hotel_assignment else 'TBD'}. Cost: ${best_option.hotel_cost:,.2f}. Room nights: {best_option.hotel_assignment.room_nights if best_option.hotel_assignment else 'TBD'}.",
            transfer_plan=f"Transfer cost: ${best_option.transfer_cost:,.2f}. Vehicles: {best_option.transfer_plan.total_vehicles if best_option.transfer_plan else 'TBD'}.",
            booking_instructions="Use Concur deep links provided in export. Coordinate arrivals within wave windows.",
            format="markdown"
        )
