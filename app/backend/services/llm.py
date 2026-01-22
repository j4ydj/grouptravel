"""LLM client abstraction layer."""
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import json
from app.backend.core.config import settings

T = TypeVar("T", bound=BaseModel)


# System prompts (verbatim as specified)
PARSE_EVENT_TEXT_SYSTEM_PROMPT = """You are an internal assistant that converts event descriptions into a strict JSON spec. You must not include personal data. Use IATA airport codes when possible. If cities are provided, map to major airport codes (Lisbon->LIS, Munich->MUC, Frankfurt->FRA, London->LHR, Paris->CDG, New York->JFK, Singapore->SIN, Sydney->SYD). If unknown, leave as null. Output only JSON."""

EXEC_SUMMARY_SYSTEM_PROMPT = """You are an executive summariser. Use only the provided FACTS JSON. Do not invent numbers. If something is missing, say so."""

QA_SYSTEM_PROMPT = """You answer questions about a simulation using ONLY the FACTS JSON. If the answer is not in FACTS, say 'I don't know based on the current simulation.' Keep answers concise."""


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def complete_json(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0
    ) -> T:
        """
        Complete a JSON response using the LLM.
        
        Args:
            schema: Pydantic model class for response validation
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature for generation (default 0 for deterministic)
        
        Returns:
            Validated Pydantic model instance
        
        Raises:
            ValueError: If response cannot be validated against schema
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI LLM client implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o)
        """
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
    
    async def complete_json(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0
    ) -> T:
        """Complete JSON using OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temperature
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        try:
            data = json.loads(content)
            return schema(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse OpenAI response: {e}")


class VertexClient(LLMClient):
    """Vertex AI LLM client implementation."""
    
    def __init__(
        self,
        project: str,
        location: str,
        model: str = "gemini-1.5-pro",
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Vertex AI client.
        
        Args:
            project: GCP project ID
            location: GCP location (e.g., us-central1)
            model: Model name (default: gemini-1.5-pro)
            credentials_path: Path to service account credentials JSON
        """
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            if credentials_path:
                import os
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            
            vertexai.init(project=project, location=location)
            self.model_name = model
            self.model = GenerativeModel(model)
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform package not installed. "
                "Install with: pip install google-cloud-aiplatform"
            )
    
    async def complete_json(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0
    ) -> T:
        """Complete JSON using Vertex AI."""
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nRespond with valid JSON only."
        
        response = await self.model.generate_content_async(
            full_prompt,
            generation_config={
                "temperature": temperature,
                "response_mime_type": "application/json"
            }
        )
        
        content = response.text
        if not content:
            raise ValueError("Empty response from Vertex AI")
        
        try:
            data = json.loads(content)
            return schema(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse Vertex AI response: {e}")


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and offline use."""
    
    async def complete_json(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0
    ) -> T:
        """Return mock response based on schema."""
        # Simple mock: return default instance or hardcoded response
        # For parse_event_text, return a default EventDraft
        if schema.__name__ == "EventDraft":
            from app.backend.schemas.event import EventDraft, DateWindow
            from datetime import date, timedelta
            
            # Try to extract basic info from prompt
            locations = []
            if "lisbon" in user_prompt.lower() or "lis" in user_prompt.lower():
                locations.append("LIS")
            if "munich" in user_prompt.lower() or "muc" in user_prompt.lower():
                locations.append("MUC")
            if "london" in user_prompt.lower() or "lhr" in user_prompt.lower():
                locations.append("LHR")
            if "paris" in user_prompt.lower() or "cdg" in user_prompt.lower():
                locations.append("CDG")
            
            if not locations:
                locations = ["LIS", "MUC"]  # Default
            
            # Default date window (next month)
            today = date.today()
            next_month = today + timedelta(days=30)
            date_windows = [
                DateWindow(start_date=next_month, end_date=next_month + timedelta(days=7))
            ]
            
            return EventDraft(
                name="Workshop Event",
                candidate_locations=locations,
                candidate_date_windows=date_windows,
                duration_days=3,
                created_by="system"
            )
        
        if schema.__name__ == "AISummaryResponse":
            from app.backend.schemas.ai import AISummaryResponse
            summary = (
                "- Recommended option is the lowest total cost and score.\n"
                "- Review arrival spread and connections rate for operational fit.\n"
                "- Cost and timing tradeoffs are reflected in the ranking.\n"
                "- Validate date options align with workshop duration.\n"
                "- Results are based on current simulation facts."
            )
            return AISummaryResponse(summary=summary)
        
        if schema.__name__ == "AIAnswerResponse":
            from app.backend.schemas.ai import AIAnswerResponse
            return AIAnswerResponse(answer="I don't know based on the current simulation.", confidence=0.0)
        
        # For summary/QA, return simple text response
        if "Summary" in schema.__name__ or "summary" in user_prompt.lower():
            return schema(**{"summary": "Mock executive summary: The simulation analyzed multiple options. Top recommendation based on cost and convenience."})
        
        if "Answer" in schema.__name__ or "answer" in user_prompt.lower():
            return schema(**{"answer": "Mock answer: Based on the simulation facts provided, this is a mock response.", "confidence": "medium"})
        
        # Default: try to create instance with empty dict
        try:
            return schema()
        except Exception:
            # If that fails, try with minimal fields
            return schema(**{})


def get_llm_client() -> LLMClient:
    """
    Factory function to get LLM client based on configuration.
    
    Returns:
        LLMClient instance
    """
    provider = settings.llm_provider.lower()
    
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
        return OpenAIClient(api_key=settings.openai_api_key, model=settings.llm_model)
    
    elif provider == "vertex":
        if not settings.vertex_project:
            raise ValueError("VERTEX_PROJECT not set")
        return VertexClient(
            project=settings.vertex_project,
            location=settings.vertex_location,
            model=settings.llm_model,
            credentials_path=settings.google_application_credentials
        )
    
    elif provider == "mock":
        return MockLLMClient()
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
