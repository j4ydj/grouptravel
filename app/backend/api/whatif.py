"""What-if exploration and constraint reasoning API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.backend.db.session import get_db
from app.backend.db.models import Event as EventModel, SimulationResult as SimulationResultModel
from app.backend.schemas.ai import AskRequest, AIAnswerResponse
from app.backend.services.whatif import WhatIfExplorationService, WhatIfProposal, WhatIfResult
from app.backend.services.audit import AuditService
from app.backend.services.llm import get_llm_client, QA_SYSTEM_PROMPT
from app.backend.core.security import get_current_user
import json

router = APIRouter()
whatif_service = WhatIfExplorationService()
audit_service = AuditService()


@router.post("/events/{event_id}/ai/whatif", response_model=List[WhatIfResult])
async def run_whatif_exploration(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Run what-if exploration to generate and evaluate variations."""
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
    
    # Reconstruct SimulationResult (simplified)
    from app.backend.schemas.itinerary import SimulationResult, OptionResult
    
    # Build baseline result
    baseline_result = SimulationResult(
        event_id=event_id,
        results=[],  # Would need full reconstruction
        ranked_options=result_model.results and [0] or [],
        created_at=result_model.created_at,
        version=result_model.version
    )
    
    # Generate proposals
    proposals = whatif_service.generate_variations(event, baseline_result)
    
    # Evaluate proposals
    results = await whatif_service.evaluate_proposals(
        proposals=proposals,
        event=event,
        baseline_result=baseline_result,
        db=db
    )
    
    # Audit log
    audit_service.log_action(
        action="whatif_exploration",
        event_id=event_id,
        user=get_current_user(),
        metadata={"proposals_count": len(proposals), "results_count": len(results)},
        db=db
    )
    
    return results


@router.post("/events/{event_id}/ai/constraint-reason", response_model=AIAnswerResponse)
async def constraint_reasoning(
    event_id: str,
    request: AskRequest,
    db: Session = Depends(get_db)
):
    """Answer constraint reasoning questions using LLM."""
    # Get latest simulation results
    result = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    # Build enhanced facts JSON for constraint reasoning
    facts = {
        "event_id": event_id,
        "total_options": len(result.results),
        "options": []
    }
    
    for opt in result.results:
        facts["options"].append({
            "location": opt.get("location"),
            "total_cost": opt.get("total_cost"),
            "hotel_cost": opt.get("hotel_cost", 0),
            "transfer_cost": opt.get("transfer_cost", 0),
            "arrival_spread_minutes": opt.get("arrival_spread_minutes"),
            "connections_rate": opt.get("connections_rate"),
            "late_arrival_risk": opt.get("late_arrival_risk", 0),
            "score": opt.get("score")
        })
    
    # Add constraint reasoning prompt
    constraint_prompt = f"""FACTS JSON:
{json.dumps(facts, indent=2)}

Question: {request.question}

Answer using ONLY the FACTS. For constraint reasoning questions like:
- "What change reduces cost the most?" - compare costs across options
- "Who is causing arrival spread?" - analyze arrival patterns
- "Why is X better than Y?" - compare scores and metrics

If the answer is not in FACTS, say 'I don't know based on the current simulation.'"""
    
    # Get LLM client
    llm_client = get_llm_client()
    
    try:
        answer_response = await llm_client.complete_json(
            schema=AIAnswerResponse,
            system_prompt=QA_SYSTEM_PROMPT,
            user_prompt=constraint_prompt,
            temperature=0
        )
        return answer_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )
