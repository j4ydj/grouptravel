"""Event CRUD and simulation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from app.backend.db.session import get_db
from app.backend.db.models import Event as EventModel, EventAttendee, SimulationResult as SimulationResultModel, Attendee
from app.backend.schemas.event import EventCreate, Event as EventSchema, EventAttendeesAttach, DateWindow
from app.backend.schemas.itinerary import SimulationResult as SimulationResultSchema, OptionResult
from app.backend.services.optimiser import OptimiserService
from app.backend.services.audit import AuditService
from app.backend.core.security import get_current_user
from app.backend.core.config import settings

router = APIRouter()
audit_service = AuditService()


@router.post("/events", response_model=EventSchema, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    db: Session = Depends(get_db)
):
    """Create a new event."""
    # Convert date windows to JSON-serializable format
    date_windows_json = [
        {
            "start_date": dw.start_date.isoformat(),
            "end_date": dw.end_date.isoformat()
        }
        for dw in event.candidate_date_windows
    ]
    
    # Get current user (placeholder for MVP)
    created_by = get_current_user() or event.created_by
    
    db_event = EventModel(
        name=event.name,
        candidate_locations=event.candidate_locations,
        candidate_date_windows=date_windows_json,
        duration_days=event.duration_days,
        created_by=created_by
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return db_event


@router.get("/events", response_model=List[EventSchema])
async def list_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all events."""
    events = db.query(EventModel).offset(skip).limit(limit).all()
    return events


@router.get("/events/{event_id}", response_model=EventSchema)
async def get_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific event by ID."""
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    return event


@router.post("/events/{event_id}/attendees", status_code=status.HTTP_200_OK)
async def attach_attendees(
    event_id: str,
    request: EventAttendeesAttach,
    db: Session = Depends(get_db)
):
    """Attach attendees to an event."""
    # Verify event exists
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Remove existing attendees
    db.query(EventAttendee).filter_by(event_id=event_id).delete()
    
    # Add new attendees
    for attendee_id in request.attendee_ids:
        event_attendee = EventAttendee(
            event_id=event_id,
            attendee_id=attendee_id
        )
        db.add(event_attendee)
    
    db.commit()
    
    return {"message": f"Attached {len(request.attendee_ids)} attendees to event"}


@router.post("/events/{event_id}/simulate", response_model=SimulationResultSchema, status_code=status.HTTP_200_OK)
async def simulate_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Run simulation for an event."""
    # Get event
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Check if event has attendees
    attendee_count = db.query(EventAttendee).filter_by(event_id=event_id).count()
    if attendee_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event has no attendees attached"
        )
    
    # Run simulation (use V2 if hotels/transfers configured)
    optimiser = OptimiserService()
    
    # Check if hotels/transfers are configured
    from app.backend.db.models import Hotel, TransferOption
    has_hotels = db.query(Hotel).filter_by(airport_code=event.candidate_locations[0] if event.candidate_locations else "").count() > 0
    has_transfers = db.query(TransferOption).count() > 0
    
    # Use V2 simulation if hotels/transfers available
    if has_hotels or has_transfers:
        # Parse date windows
        from app.backend.schemas.event import DateWindow
        date_windows = []
        for dw in event.candidate_date_windows:
            if isinstance(dw, dict):
                start_date_str = dw.get("start_date")
                end_date_str = dw.get("end_date")
                if isinstance(start_date_str, str):
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                else:
                    start_date = start_date_str if isinstance(start_date_str, date) else date.today()
                if isinstance(end_date_str, str):
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                else:
                    end_date = end_date_str if isinstance(end_date_str, date) else date.today()
                date_windows.append(DateWindow(start_date=start_date, end_date=end_date))
        
        # Get attendees
        event_attendee_rels = db.query(EventAttendee).filter_by(event_id=event.id).all()
        attendee_ids = [ea.attendee_id for ea in event_attendee_rels]
        attendees = db.query(Attendee).filter(Attendee.id.in_(attendee_ids)).all()
        
        # Simulate with V2
        option_results = []
        for location in event.candidate_locations:
            for date_window in date_windows:
                option_result = await optimiser.simulate_option_v2(
                    location=location,
                    date_window=date_window,
                    attendees=attendees,
                    duration_days=event.duration_days,
                    db=db,
                    include_hotels=has_hotels,
                    include_transfers=has_transfers
                )
                # Store V2 result (includes all Phase 2 fields)
                option_results.append(option_result)
    else:
        # Use V1 simulation
        option_results = await optimiser.simulate_event(event, db)
    
    if not option_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No simulation results generated"
        )
    
    # Rank options by score (lower is better)
    ranked_indices = sorted(
        range(len(option_results)),
        key=lambda i: option_results[i].score
    )
    
    # Get next version number
    max_version = db.query(SimulationResultModel).filter_by(event_id=event_id).count()
    version = max_version + 1
    
    # Create reproducibility snapshot
    reproducibility_snapshot = audit_service.get_reproducibility_snapshot(
        pricing_provider=settings.llm_provider or "mock",  # Simplified
        pricing_cache_version=None,
        random_seed=None
    )
    
    # Store results with reproducibility info
    simulation_result = SimulationResultModel(
        event_id=event_id,
        results=[result.model_dump() for result in option_results],
        version=version,
        pricing_provider=reproducibility_snapshot.get("pricing_provider"),
        pricing_cache_version=reproducibility_snapshot.get("pricing_cache_version"),
        random_seed=reproducibility_snapshot.get("random_seed"),
        config_snapshot=reproducibility_snapshot.get("config")
    )
    db.add(simulation_result)
    db.commit()
    db.refresh(simulation_result)
    
    # Audit log
    audit_service.log_action(
        action="simulate",
        event_id=event_id,
        user=get_current_user(),
        after_state={"version": version, "options_count": len(option_results)},
        metadata={"pricing_provider": reproducibility_snapshot.get("pricing_provider")},
        db=db
    )
    
    # Return response
    return SimulationResultSchema(
        event_id=event_id,
        results=option_results,
        ranked_options=ranked_indices,
        created_at=simulation_result.created_at,
        version=version
    )


@router.get("/events/{event_id}/results/latest", response_model=SimulationResultSchema)
async def get_latest_results(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Get latest simulation results for an event."""
    # Verify event exists
    event = db.query(EventModel).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Get latest result
    result = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found for this event"
        )
    
    # Reconstruct OptionResult objects from JSON
    from app.backend.schemas.itinerary import OptionResult, AttendeeItinerary
    
    option_results = []
    for opt_data in result.results:
        # Reconstruct AttendeeItinerary objects
        attendee_itineraries = [
            AttendeeItinerary(**ai_data)
            for ai_data in opt_data.get("attendee_itineraries", [])
        ]
        
        # Reconstruct OptionResult
        opt_data_copy = opt_data.copy()
        opt_data_copy["attendee_itineraries"] = attendee_itineraries
        option_results.append(OptionResult(**opt_data_copy))
    
    # Rank options
    ranked_indices = sorted(
        range(len(option_results)),
        key=lambda i: option_results[i].score
    )
    
    return SimulationResultSchema(
        event_id=event_id,
        results=option_results,
        ranked_options=ranked_indices,
        created_at=result.created_at,
        version=result.version
    )
