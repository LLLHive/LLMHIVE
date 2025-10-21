"""Application configuration using Pydantic settings."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file early so environment variables are available for settings
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env", override=False)


def _safe_json_loads(value: object) -> object:
    """Best-effort JSON loader that falls back to the original value."""

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _parse_model_list(value: object) -> list[str] | None:
    """Normalize comma-delimited or JSON model lists into Python lists."""

    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        parsed = _safe_json_loads(stripped)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        parts: list[str] = []
        for segment in stripped.replace(";", ",").split(","):
            piece = segment.strip()
            if piece:
                parts.append(piece)
        return parts or None
    if isinstance(value, (list, tuple, set)):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                for segment in item.replace(";", ",").split(","):
                    piece = segment.strip()
                    if piece:
                        parts.append(piece)
            elif item is not None:
                parts.append(str(item))
        return parts or None
    return None


def _parse_alias_mapping(value: object) -> dict[str, str] | None:
    """Normalize alias mappings from JSON or key=value strings."""

    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        parsed = _safe_json_loads(stripped)
        if isinstance(parsed, dict):
            return {str(key): str(val) for key, val in parsed.items()}
        mapping: dict[str, str] = {}
        for segment in stripped.replace(";", ",").split(","):
            if "=" not in segment:
                continue
            key, alias = segment.split("=", 1)
            key = key.strip()
            alias = alias.strip()
            if key and alias:
                mapping[key] = alias
        return mapping or None
    if isinstance(value, dict):
        return {str(key): str(val) for key, val in value.items()}
    return None


def _normalize_environment() -> None:
    """Preprocess raw environment variables for settings compatibility."""

    defaults = os.getenv("DEFAULT_MODELS")
    parsed_defaults = _parse_model_list(defaults)
    if defaults is not None and parsed_defaults is not None:
        os.environ["DEFAULT_MODELS"] = json.dumps(parsed_defaults)

    aliases = os.getenv("MODEL_ALIASES")
    parsed_aliases = _parse_alias_mapping(aliases)
    if aliases is not None and parsed_aliases is not None:
        os.environ["MODEL_ALIASES"] = json.dumps(parsed_aliases)


_normalize_environment()


class Settings(BaseSettings):
    """Central application settings."""

    app_name: str = "LLMHive"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: str = Field(default="sqlite:///./llmhive.db", alias="DATABASE_URL")
    openai_api_key: str | None = Field(
        default=None,
        alias="OPENAI_API_KEY",
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            "OPENAI_KEY",
            "OPENAI_APIKEY",
            "OPENAI_TOKEN",
        ),
    )
    default_models: List[str] = Field(
        default_factory=lambda: ["gpt-4o-mini", "gpt-3.5-turbo"], alias="DEFAULT_MODELS"
    )
    openai_timeout_seconds: float = Field(default=45.0, alias="OPENAI_TIMEOUT_SECONDS")
    grok_api_key: str | None = Field(
        default=None,
        alias="GROK_API_KEY",
        validation_alias=AliasChoices(
            "GROK_API_KEY",
            "GROCK_API_KEY",
            "XAI_API_KEY",
            "XAI_TOKEN",
        ),
    )
    grok_base_url: str = Field(
        default="https://api.x.ai/v1",
        alias="GROK_BASE_URL",
        validation_alias=AliasChoices("GROK_BASE_URL", "GROCK_BASE_URL", "XAI_BASE_URL"),
    )
    grok_timeout_seconds: float = Field(default=45.0, alias="GROK_TIMEOUT_SECONDS")
    model_aliases: Dict[str, str] = Field(
        default_factory=lambda: {
            "gpt-4": "gpt-4o-mini",
            "gpt4": "gpt-4o-mini",
            "gpt-4o": "gpt-4o",
            "gpt-3": "gpt-3.5-turbo",
            "gpt3": "gpt-3.5-turbo",
            "chatgpt": "gpt-3.5-turbo",
            "gpt-4-turbo": "gpt-4o",
            "grok": "grok-beta",
            "grock": "grok-beta",
            "grok-1": "grok-1",
            "grok-beta": "grok-beta",
        },
        alias="MODEL_ALIASES",
    )
    enable_stub_provider: bool = Field(
        default=False,
        alias="ENABLE_STUB_PROVIDER",
        description="If true, registers the stub provider as a fallback for development environments.",
    )

    @field_validator("default_models", mode="before")
    @classmethod
    def _coerce_default_models(cls, value):  # type: ignore[override]
        parsed = _parse_model_list(value)
        return parsed if parsed is not None else value

    @field_validator("model_aliases", mode="before")
    @classmethod
    def _coerce_model_aliases(cls, value):  # type: ignore[override]
        parsed = _parse_alias_mapping(value)
        return parsed if parsed is not None else value

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""

    _normalize_environment()
    return Settings()


settings = get_settings()


def reset_settings_cache() -> None:
    """Clear the cached settings so environment changes are reloaded."""

    get_settings.cache_clear()
