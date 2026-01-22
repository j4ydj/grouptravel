"""AI-related Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional


class ParseEventTextRequest(BaseModel):
    """Request schema for parsing event text."""
    text: str = Field(..., min_length=10, description="Natural language event description")


class AISummaryResponse(BaseModel):
    """Response schema for AI summary."""
    summary: str = Field(..., description="Executive summary of simulation results")


class AskRequest(BaseModel):
    """Request schema for Q&A."""
    question: str = Field(..., min_length=1, description="Question about simulation results")


class AIAnswerResponse(BaseModel):
    """Response schema for Q&A."""
    answer: str = Field(..., description="Answer based on simulation facts")
    confidence: Optional[str] = Field(None, description="Confidence level if available")
