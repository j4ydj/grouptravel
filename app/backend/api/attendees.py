"""Attendee CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.backend.db.session import get_db
from app.backend.db.models import Attendee as AttendeeModel
from app.backend.schemas.attendee import AttendeeCreate, Attendee as AttendeeSchema, AttendeeList, AttendeeUpdate

router = APIRouter()


@router.post("/attendees", response_model=AttendeeSchema, status_code=status.HTTP_201_CREATED)
async def create_attendee(
    attendee: AttendeeCreate,
    db: Session = Depends(get_db)
):
    """Create a new attendee."""
    # Check if employee_id already exists
    existing = db.query(AttendeeModel).filter_by(employee_id=attendee.employee_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Attendee with employee_id {attendee.employee_id} already exists"
        )
    
    # Create attendee
    db_attendee = AttendeeModel(**attendee.model_dump())
    db.add(db_attendee)
    db.commit()
    db.refresh(db_attendee)
    
    return db_attendee


@router.get("/attendees", response_model=AttendeeList)
async def list_attendees(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all attendees."""
    attendees = db.query(AttendeeModel).offset(skip).limit(limit).all()
    total = db.query(AttendeeModel).count()
    
    return AttendeeList(attendees=attendees, total=total)


@router.get("/attendees/{attendee_id}", response_model=AttendeeSchema)
async def get_attendee(
    attendee_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific attendee by ID."""
    attendee = db.query(AttendeeModel).filter_by(id=attendee_id).first()
    if not attendee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendee {attendee_id} not found"
        )
    return attendee


@router.put("/attendees/{attendee_id}", response_model=AttendeeSchema)
async def update_attendee(
    attendee_id: str,
    attendee_update: AttendeeUpdate,
    db: Session = Depends(get_db)
):
    """Update an attendee."""
    # Get existing attendee
    attendee = db.query(AttendeeModel).filter_by(id=attendee_id).first()
    if not attendee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendee {attendee_id} not found"
        )
    
    # Update only provided fields
    update_data = attendee_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attendee, field, value)
    
    db.commit()
    db.refresh(attendee)
    
    return attendee
