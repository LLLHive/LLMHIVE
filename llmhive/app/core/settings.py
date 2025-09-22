"""Application settings module using Pydantic BaseSettings."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env files.

    TODO: migrate to ``pydantic-settings`` once the project upgrades to
    Pydantic v2.x for improved performance and richer features.
    """

    env: str = Field("development", description="Current runtime environment")

    db_url: str = Field(
        "sqlite+aiosqlite:///./llmhive.db",
        description="SQLAlchemy database URL. Uses SQLite by default for dev.",
        env="DB_URL",
    )

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")

    enable_debate: bool = Field(True, env="ENABLE_DEBATE")
    enable_factcheck: bool = Field(True, env="ENABLE_FACTCHECK")

    default_accuracy: float = Field(0.8)
    default_speed: float = Field(0.4)
    default_creativity: float = Field(0.3)
    default_cost: float = Field(0.5)

    outbound_http_allowlist: list[str] = Field(
        default_factory=lambda: ["https://api.bing.microsoft.com", "https://www.googleapis.com"]
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
