"""Export API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
import json
import csv
import io
from app.backend.db.session import get_db
from app.backend.db.models import Event as EventModel, SimulationResult as SimulationResultModel, Attendee, EventAttendee
from app.backend.schemas.export import ConcurPayload, FinanceExport, OrganiserBrief
from app.backend.services.export import ExportService
from app.backend.services.audit import AuditService
from app.backend.services.llm import get_llm_client
from app.backend.core.security import get_current_user

router = APIRouter()
export_service = ExportService()
audit_service = AuditService()


@router.get("/events/{event_id}/export/concur", response_model=List[ConcurPayload])
async def export_concur_payloads(
    event_id: str,
    option_index: int = Query(0, ge=0, description="Index of option in results"),
    db: Session = Depends(get_db)
):
    """Generate Concur deep-link payloads for all attendees."""
    # Get event
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Get latest simulation result
    result = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    if option_index >= len(result.results):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option index {option_index} out of range"
        )
    
    option_data = result.results[option_index]
    
    # Get attendees
    event_attendee_rels = db.query(EventAttendee).filter_by(event_id=event_id).all()
    attendee_ids = [ea.attendee_id for ea in event_attendee_rels]
    attendees = db.query(Attendee).filter(Attendee.id.in_(attendee_ids)).all()
    
    # Build attendee map
    attendee_map = {a.id: a for a in attendees}
    
    # Generate payloads
    payloads = []
    hotel_assignment = option_data.get("hotel_assignment")
    
    for ai_data in option_data.get("attendee_itineraries", []):
        attendee = attendee_map.get(ai_data["attendee_id"])
        if not attendee:
            continue
        
        from app.backend.schemas.itinerary import AttendeeItinerary
        itinerary = AttendeeItinerary(**ai_data)
        
        payload = export_service.generate_concur_payload(
            attendee=attendee,
            itinerary=itinerary,
            hotel_assignment=hotel_assignment,
            event=event
        )
        payloads.append(payload)
    
    # Audit log
    audit_service.log_action(
        action="export_concur",
        event_id=event_id,
        user=get_current_user(),
        metadata={"option_index": option_index, "payload_count": len(payloads)},
        db=db
    )
    
    return payloads


@router.get("/events/{event_id}/export/finance")
async def export_finance(
    event_id: str,
    option_index: Optional[int] = Query(None, description="Index of option (defaults to best)"),
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """Generate finance export (JSON or CSV)."""
    # Get event
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Get latest simulation result
    result_model = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    # Reconstruct SimulationResultV2
    from app.backend.schemas.itinerary import SimulationResultV2, OptionResultV2
    
    # Simplified: use first option if V2 not available
    if option_index is None:
        option_index = 0
    
    option_data = result_model.results[option_index]
    
    # Generate export
    finance_export = export_service.generate_finance_export(
        event=event,
        result=None,  # Simplified for MVP
        selected_option_index=option_index
    )
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Employee ID", "Flight Cost", "Hotel Cost", "Transfer Cost", "Total Cost"])
        
        # Rows
        for person in finance_export.per_person_breakdown:
            writer.writerow([
                person["employee_id"],
                person["flight_cost"],
                person["hotel_cost"],
                person["transfer_cost"],
                    person["total_cost"]
            ])
        
        # Audit log
        audit_service.log_action(
            action="export_finance",
            event_id=event_id,
            user=get_current_user(),
            metadata={"format": format, "option_index": option_index},
            db=db
        )
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=finance_export_{event_id}.csv"}
        )
    else:
        return finance_export


@router.get("/events/{event_id}/export/brief", response_model=OrganiserBrief)
async def export_organiser_brief(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Generate AI organiser brief."""
    # Get event
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Get latest simulation result
    result_model = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    # Generate brief
    llm_client = get_llm_client()
    brief = await export_service.generate_organiser_brief(
        event=event,
        result=None,  # Simplified - would need full V2 reconstruction
        llm_client=llm_client
    )
    
    # Audit log
    audit_service.log_action(
        action="export_brief",
        event_id=event_id,
        user=get_current_user(),
        metadata={"format": brief.format},
        db=db
    )
    
    return brief
