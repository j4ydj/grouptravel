"""AI endpoints for LLM features."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.backend.db.session import get_db
from app.backend.db.models import Event as EventModel, SimulationResult as SimulationResultModel
from app.backend.schemas.ai import (
    ParseEventTextRequest,
    AISummaryResponse,
    AskRequest,
    AIAnswerResponse
)
from app.backend.schemas.event import EventDraft
from app.backend.services.llm import (
    get_llm_client,
    PARSE_EVENT_TEXT_SYSTEM_PROMPT,
    EXEC_SUMMARY_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT
)
import json

router = APIRouter()


@router.post("/ai/parse_event_text", response_model=EventDraft)
async def parse_event_text(request: ParseEventTextRequest):
    """Parse natural language event description into structured EventDraft."""
    llm_client = get_llm_client()
    
    try:
        event_draft = await llm_client.complete_json(
            schema=EventDraft,
            system_prompt=PARSE_EVENT_TEXT_SYSTEM_PROMPT,
            user_prompt=request.text,
            temperature=0
        )
        return event_draft
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse event text: {str(e)}"
        )


@router.post("/events/{event_id}/ai/summary", response_model=AISummaryResponse)
async def generate_summary(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Generate executive summary of simulation results."""
    # Get latest simulation results
    result = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    # Build facts JSON (only numeric metrics, no PII)
    facts = {
        "event_id": event_id,
        "total_options": len(result.results),
        "options": []
    }
    
    for opt in result.results:
        facts["options"].append({
            "location": opt.get("location"),
            "total_cost": opt.get("total_cost"),
            "avg_travel_time_minutes": opt.get("avg_travel_time_minutes"),
            "arrival_spread_minutes": opt.get("arrival_spread_minutes"),
            "connections_rate": opt.get("connections_rate"),
            "score": opt.get("score")
        })
    
    # Get LLM client
    llm_client = get_llm_client()
    
    try:
        summary_response = await llm_client.complete_json(
            schema=AISummaryResponse,
            system_prompt=EXEC_SUMMARY_SYSTEM_PROMPT,
            user_prompt=f"Generate an executive summary based on these simulation facts:\n\n{json.dumps(facts, indent=2)}",
            temperature=0
        )
        return summary_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.post("/events/{event_id}/ask", response_model=AIAnswerResponse)
async def ask_question(
    event_id: str,
    request: AskRequest,
    db: Session = Depends(get_db)
):
    """Answer questions about simulation results using LLM."""
    # Get latest simulation results
    result = db.query(SimulationResultModel).filter_by(event_id=event_id).order_by(
        SimulationResultModel.version.desc()
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run simulation first."
        )
    
    # Build facts JSON (only numeric metrics, no PII)
    facts = {
        "event_id": event_id,
        "total_options": len(result.results),
        "options": []
    }
    
    for opt in result.results:
        facts["options"].append({
            "location": opt.get("location"),
            "total_cost": opt.get("total_cost"),
            "avg_travel_time_minutes": opt.get("avg_travel_time_minutes"),
            "arrival_spread_minutes": opt.get("arrival_spread_minutes"),
            "connections_rate": opt.get("connections_rate"),
            "score": opt.get("score")
        })
    
    # Get LLM client
    llm_client = get_llm_client()
    
    try:
        answer_response = await llm_client.complete_json(
            schema=AIAnswerResponse,
            system_prompt=QA_SYSTEM_PROMPT,
            user_prompt=f"FACTS JSON:\n{json.dumps(facts, indent=2)}\n\nQuestion: {request.question}",
            temperature=0
        )
        return answer_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )
