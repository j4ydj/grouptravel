"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = "sqlite:///./data/grouptravel.db"
    
    # LLM Configuration
    llm_provider: Literal["openai", "vertex", "mock"] = "mock"
    llm_model: str = "gpt-4o"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Vertex AI
    google_application_credentials: Optional[str] = None
    vertex_project: Optional[str] = None
    vertex_location: str = "us-central1"
    
    # Pricing
    price_volatility: bool = False
    
    # Duffel API
    duffel_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
