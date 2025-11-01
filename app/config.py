import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and .env file.
    Secrets are loaded separately at application startup from Google Cloud Secret Manager.
    """
    # Google Cloud Project ID for Secret Manager
    PROJECT_ID: str = os.environ.get("GCP_PROJECT", "llmhive-orchestrator")
    
    # API Keys (loaded from environment variables or Secret Manager at startup)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Model configuration
    MODEL_CONFIG_PATH: str = "models.yaml"
    PLANNING_MODEL: str = "gpt-4-turbo"
    CRITIQUE_MODEL: str = "gpt-4"
    SYNTHESIS_MODEL: str = "gpt-4-turbo"
    
    # Cross-origin resource sharing (CORS)
    # Comma-separated list of allowed origins for the FastAPI service.
    # Defaults to "*" for local development convenience. In production,
    # set this to your deployed front-end domain(s).
    CORS_ALLOW_ORIGINS: str = "*"

    # Application metadata
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "LLMHive"
    APP_VERSION: str = "1.3.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
