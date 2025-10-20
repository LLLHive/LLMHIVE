"""Application configuration using Pydantic settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file early so environment variables are available for settings
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env", override=False)


class Settings(BaseSettings):
    """Central application settings."""

    app_name: str = "LLMHive"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: str = Field(default="sqlite:///./llmhive.db", alias="DATABASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    default_models: List[str] = Field(
        default_factory=lambda: ["gpt-4o-mini", "gpt-3.5-turbo"], alias="DEFAULT_MODELS"
    )
    openai_timeout_seconds: float = Field(default=45.0, alias="OPENAI_TIMEOUT_SECONDS")
    grok_api_key: str | None = Field(default=None, alias="GROK_API_KEY")
    grok_base_url: str = Field(default="https://api.x.ai/v1", alias="GROK_BASE_URL")
    grok_timeout_seconds: float = Field(default=45.0, alias="GROK_TIMEOUT_SECONDS")
    model_aliases: Dict[str, str] = Field(
        default_factory=lambda: {
            "gpt-4": "gpt-4o-mini",
            "gpt4": "gpt-4o-mini",
            "gpt-4o": "gpt-4o",
            "gpt-3": "gpt-3.5-turbo",
            "gpt3": "gpt-3.5-turbo",
            "grok": "grok-beta",
            "grok-1": "grok-1",
            "grok-beta": "grok-beta",
        },
        alias="MODEL_ALIASES",
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


settings = get_settings()
