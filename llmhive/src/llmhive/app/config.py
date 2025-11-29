"""Configuration settings for LLMHive."""
from __future__ import annotations

import os
from typing import List


class Settings:
    """Application settings loaded from environment variables."""
    
    # Default models for orchestration
    default_models: List[str] = ["gpt-4o-mini", "claude-3-haiku"]
    
    # API key (optional, for authentication)
    api_key: str | None = os.getenv("API_KEY")
    
    # Provider API keys (loaded from environment)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    grok_api_key: str | None = os.getenv("GROK_API_KEY")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    manus_api_key: str | None = os.getenv("MANUS_API_KEY")
    
    # Provider timeouts (optional)
    openai_timeout_seconds: int | None = None
    anthropic_timeout_seconds: int | None = None
    grok_timeout_seconds: int | None = None
    gemini_timeout_seconds: int | None = None
    deepseek_timeout_seconds: int | None = None
    manus_timeout_seconds: int | None = None


# Global settings instance
settings = Settings()

