"""Transfer option CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.backend.db.session import get_db
from app.backend.db.models import TransferOption as TransferOptionModel, Event as EventModel
from app.backend.schemas.transfer import TransferOptionCreate, TransferOption as TransferOptionSchema, TransferPlan
from app.backend.services.transfer import TransferBatchingService
from app.backend.services.optimiser import OptimiserService

router = APIRouter()


@router.post("/transfers", response_model=TransferOptionSchema, status_code=status.HTTP_201_CREATED)
async def create_transfer_option(
    transfer: TransferOptionCreate,
    db: Session = Depends(get_db)
):
    """Create a new transfer option."""
    db_transfer = TransferOptionModel(**transfer.model_dump())
    db.add(db_transfer)
    db.commit()
    db.refresh(db_transfer)
    
    return db_transfer


@router.get("/transfers", response_model=List[TransferOptionSchema])
async def list_transfer_options(
    airport_code: Optional[str] = Query(None, description="Filter by airport code"),
    hotel_id: Optional[str] = Query(None, description="Filter by hotel ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List transfer options with optional filters."""
    query = db.query(TransferOptionModel)
    
    if airport_code:
        query = query.filter_by(airport_code=airport_code.upper())
    
    if hotel_id:
        query = query.filter_by(hotel_id=hotel_id)
    
    transfers = query.offset(skip).limit(limit).all()
    return transfers


@router.get("/transfers/{transfer_id}", response_model=TransferOptionSchema)
async def get_transfer_option(
    transfer_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific transfer option by ID."""
    transfer = db.query(TransferOptionModel).filter_by(id=transfer_id).first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer option {transfer_id} not found"
        )
    return transfer


@router.get("/events/{event_id}/transfer-plan", response_model=TransferPlan)
async def get_transfer_plan(
    event_id: str,
    option_index: int = Query(0, ge=0, description="Index of option in results"),
    db: Session = Depends(get_db)
):
    """Get computed transfer plan for a specific event option."""
    # Get latest simulation result
    from app.backend.db.models import SimulationResult as SimulationResultModel
    
    result = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    # Get the specified option
    if option_index >= len(result.results):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Option index {option_index} out of range"
        )
    
    option_data = result.results[option_index]
    
    # Extract transfer plan if available
    if "transfer_plan" in option_data and option_data["transfer_plan"]:
        return TransferPlan(**option_data["transfer_plan"])
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Transfer plan not available for this option"
    )
