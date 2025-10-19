"""Application configuration using Pydantic settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

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
        default_factory=lambda: [
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "claude-3-sonnet-20240229",
            "grok-1",
            "gemini-pro",
            "deepseek-chat",
            "manus",
        ],
        alias="DEFAULT_MODELS",
    )
    openai_timeout_seconds: float = Field(default=45.0, alias="OPENAI_TIMEOUT_SECONDS")

    # Additional API keys for other providers. If unset, those providers are disabled.
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    grok_api_key: str | None = Field(default=None, alias="GROK_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    manus_api_key: str | None = Field(default=None, alias="MANUS_API_KEY")

    # Timeout settings for the additional providers
    anthropic_timeout_seconds: float = Field(default=45.0, alias="ANTHROPIC_TIMEOUT_SECONDS")
    grok_timeout_seconds: float = Field(default=45.0, alias="GROK_TIMEOUT_SECONDS")
    gemini_timeout_seconds: float = Field(default=45.0, alias="GEMINI_TIMEOUT_SECONDS")
    deepseek_timeout_seconds: float = Field(default=45.0, alias="DEEPSEEK_TIMEOUT_SECONDS")
    manus_timeout_seconds: float = Field(default=45.0, alias="MANUS_TIMEOUT_SECONDS")

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
