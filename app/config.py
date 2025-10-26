import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and .env file.
    Secrets are loaded separately at application startup.
    """
    # Google Cloud Project ID for Secret Manager
    PROJECT_ID: str = os.environ.get("GCP_PROJECT", "llmhive-orchestrator")
    
    # API Keys (can be loaded from environment or Secret Manager)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Model configuration
    MODEL_CONFIG_PATH: str = "models.yaml"
    PLANNING_MODEL: str = "gpt-4-turbo"
    CRITIQUE_MODEL: str = "gpt-4"
    SYNTHESIS_MODEL: str = "gpt-4-turbo"
    
    # Application metadata
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "LLMHive"
    APP_VERSION: str = "1.3.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
