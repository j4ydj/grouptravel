"""Hotel CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.backend.db.session import get_db
from app.backend.db.models import Hotel as HotelModel
from app.backend.schemas.hotel import HotelCreate, Hotel as HotelSchema

router = APIRouter()


@router.post("/hotels", response_model=HotelSchema, status_code=status.HTTP_201_CREATED)
async def create_hotel(
    hotel: HotelCreate,
    db: Session = Depends(get_db)
):
    """Create a new hotel."""
    db_hotel = HotelModel(**hotel.model_dump())
    db.add(db_hotel)
    db.commit()
    db.refresh(db_hotel)
    
    return db_hotel


@router.get("/hotels", response_model=List[HotelSchema])
async def list_hotels(
    airport_code: Optional[str] = Query(None, description="Filter by airport code"),
    approved: Optional[bool] = Query(None, description="Filter by approved status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List hotels with optional filters."""
    query = db.query(HotelModel)
    
    if airport_code:
        query = query.filter_by(airport_code=airport_code.upper())
    
    if approved is not None:
        query = query.filter_by(approved=approved)
    
    hotels = query.offset(skip).limit(limit).all()
    return hotels


@router.get("/hotels/{hotel_id}", response_model=HotelSchema)
async def get_hotel(
    hotel_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific hotel by ID."""
    hotel = db.query(HotelModel).filter_by(id=hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel {hotel_id} not found"
        )
    return hotel


@router.put("/hotels/{hotel_id}", response_model=HotelSchema)
async def update_hotel(
    hotel_id: str,
    hotel_update: HotelCreate,
    db: Session = Depends(get_db)
):
    """Update a hotel."""
    hotel = db.query(HotelModel).filter_by(id=hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel {hotel_id} not found"
        )
    
    # Update fields
    for key, value in hotel_update.model_dump().items():
        setattr(hotel, key, value)
    
    db.commit()
    db.refresh(hotel)
    
    return hotel
