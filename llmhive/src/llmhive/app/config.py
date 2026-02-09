"""Configuration settings for LLMHive.

IMPORTANT: Uses Pydantic BaseSettings for lazy loading of environment variables.
This prevents race conditions on serverless cold starts where env vars may not
be fully loaded at module import time.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field as dataclass_field
from typing import List, Optional

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    warnings: List[str] = dataclass_field(default_factory=list)
    errors: List[str] = dataclass_field(default_factory=list)
    available_providers: List[str] = dataclass_field(default_factory=list)
    
    def log_results(self) -> None:
        """Log validation results."""
        if self.errors:
            for error in self.errors:
                logger.error("CONFIG ERROR: %s", error)
        if self.warnings:
            for warning in self.warnings:
                logger.warning("CONFIG WARNING: %s", warning)
        if self.available_providers:
            logger.info("Available LLM providers: %s", ", ".join(self.available_providers))


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for lazy loading - environment variables
    are read when Settings() is instantiated, NOT when the module is imported.
    This prevents race conditions on serverless cold starts.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
        # Validate assignment to catch issues early
        validate_assignment=True,
    )
    
    # Default models for orchestration
    default_models: List[str] = Field(
        default=["gpt-4o-mini", "claude-3-haiku"],
        description="Default models for orchestration"
    )
    
    # ==================== API KEYS ====================
    
    # API key (optional, for authentication)
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    
    # Provider API keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    claude_api_key: Optional[str] = Field(default=None, alias="CLAUDE_API_KEY")
    grok_api_key: Optional[str] = Field(default=None, alias="GROK_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    manus_api_key: Optional[str] = Field(default=None, alias="MANUS_API_KEY")
    together_api_key: Optional[str] = Field(default=None, alias="TOGETHERAI_API_KEY")
    
    # ==================== PROVIDER TIMEOUTS ====================
    
    openai_timeout_seconds: Optional[int] = Field(default=None)
    anthropic_timeout_seconds: Optional[int] = Field(default=None)
    grok_timeout_seconds: Optional[int] = Field(default=None)
    gemini_timeout_seconds: Optional[int] = Field(default=None)
    deepseek_timeout_seconds: Optional[int] = Field(default=None)
    manus_timeout_seconds: Optional[int] = Field(default=None)
    together_timeout_seconds: Optional[int] = Field(default=None)
    
    # ==================== PINECONE (VECTOR DB) ====================
    
    pinecone_api_key: Optional[str] = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(
        default="us-west1-gcp",
        alias="PINECONE_ENVIRONMENT"
    )
    pinecone_index_name: str = Field(
        default="llmhive-memory",
        alias="PINECONE_INDEX_NAME"
    )
    
    # ==================== EMBEDDING CONFIGURATION ====================
    
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(
        default=1536,
        alias="EMBEDDING_DIMENSION"
    )
    
    # ==================== MEMORY CONFIGURATION ====================
    
    memory_namespace_per_user: bool = Field(
        default=True,
        alias="MEMORY_NAMESPACE_PER_USER"
    )
    memory_ttl_days: int = Field(
        default=90,
        alias="MEMORY_TTL_DAYS"
    )
    memory_max_results: int = Field(
        default=10,
        alias="MEMORY_MAX_RESULTS"
    )
    memory_min_score: float = Field(
        default=0.7,
        alias="MEMORY_MIN_SCORE"
    )
    memory_max_entries_per_user: int = Field(
        default=1000,
        alias="MEMORY_MAX_ENTRIES"
    )
    memory_max_age_days: int = Field(
        default=90,
        alias="MEMORY_MAX_AGE_DAYS"
    )
    
    # ==================== STRIPE (BILLING) ====================
    
    stripe_api_key: Optional[str] = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_publishable_key: Optional[str] = Field(default=None, alias="STRIPE_PUBLISHABLE_KEY")
    
    # Stripe Price IDs
    stripe_price_id_basic_monthly: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID_BASIC_MONTHLY")
    stripe_price_id_basic_annual: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID_BASIC_ANNUAL")
    stripe_price_id_pro_monthly: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID_PRO_MONTHLY")
    stripe_price_id_pro_annual: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID_PRO_ANNUAL")
    stripe_price_id_enterprise_monthly: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID_ENTERPRISE_MONTHLY")
    stripe_price_id_enterprise_annual: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID_ENTERPRISE_ANNUAL")
    
    # Stripe Redirect URLs
    stripe_success_url: str = Field(
        default="https://llmhive.ai/billing/success",
        alias="STRIPE_SUCCESS_URL"
    )
    stripe_cancel_url: str = Field(
        default="https://llmhive.ai/billing",
        alias="STRIPE_CANCEL_URL"
    )
    
    # ==================== GOOGLE CLOUD ====================
    
    google_cloud_project: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    
    # ==================== APPLICATION CONFIGURATION ====================
    
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins_str: str = Field(default="*", alias="CORS_ORIGINS")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(
        default=60,
        alias="RATE_LIMIT_RPM"
    )
    
    # ==================== VALIDATORS ====================
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is uppercase and valid."""
        v = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            logger.warning(
                f"Invalid LOG_LEVEL: {v}. Using INFO. Valid: {', '.join(valid_levels)}"
            )
            return "INFO"
        return v
    
    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Warn about unusual embedding dimensions."""
        common_dims = [256, 512, 1024, 1536, 3072]
        if v not in common_dims:
            logger.warning(
                f"Unusual embedding dimension: {v}. Common: {', '.join(map(str, common_dims))}"
            )
        return v
    
    # ==================== COMPUTED FIELDS ====================
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]
    
    # ==================== HELPER METHODS ====================
    
    def get_anthropic_key(self) -> Optional[str]:
        """Get Anthropic API key with fallback to CLAUDE_API_KEY."""
        return self.anthropic_api_key or self.claude_api_key
    
    def get_together_key(self) -> Optional[str]:
        """Get Together AI API key with fallback."""
        return self.together_api_key or os.getenv("TOGETHER_API_KEY")
    
    def get_google_cloud_project(self) -> Optional[str]:
        """Get Google Cloud project with fallback to GCP_PROJECT."""
        return self.google_cloud_project or os.getenv("GCP_PROJECT")
    
    def validate(self, strict: bool = False) -> ConfigValidationResult:
        """Validate configuration settings.
        
        Args:
            strict: If True, treat warnings as errors
            
        Returns:
            ConfigValidationResult with validation status and messages
        """
        result = ConfigValidationResult(is_valid=True)
        
        # Check LLM provider API keys
        provider_keys = [
            ("openai", self.openai_api_key, "OPENAI_API_KEY"),
            ("anthropic", self.get_anthropic_key(), "ANTHROPIC_API_KEY or CLAUDE_API_KEY"),
            ("grok", self.grok_api_key, "GROK_API_KEY"),
            ("gemini", self.gemini_api_key, "GEMINI_API_KEY"),
            ("deepseek", self.deepseek_api_key, "DEEPSEEK_API_KEY"),
            ("together", self.get_together_key(), "TOGETHERAI_API_KEY"),
        ]
        
        for provider_name, api_key, env_var in provider_keys:
            if api_key:
                result.available_providers.append(provider_name)
        
        # Warn if no providers configured
        if not result.available_providers:
            msg = "No LLM provider API keys configured. Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY"
            result.warnings.append(msg)
            if strict:
                result.errors.append(msg)
                result.is_valid = False
        
        # Check Pinecone for RAG
        if not self.pinecone_api_key:
            result.warnings.append(
                "PINECONE_API_KEY not set. RAG/memory features will be disabled."
            )
        
        # Check Stripe for billing
        if not self.stripe_api_key:
            result.warnings.append(
                "STRIPE_SECRET_KEY not set. Billing features will be disabled."
            )
        
        # Validate embedding configuration
        valid_embedding_models = [
            "text-embedding-3-small", 
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]
        if self.embedding_model not in valid_embedding_models:
            result.warnings.append(
                f"Unknown embedding model: {self.embedding_model}. "
                f"Supported: {', '.join(valid_embedding_models)}"
            )
        
        # Check for debug mode in production
        if self.debug and self.environment == "production":
            result.warnings.append(
                "DEBUG mode enabled in production. This may expose sensitive information."
            )
        
        # Log validation results
        result.log_results()
        
        return result
    
    def get_provider_status(self) -> dict:
        """Get status of all configured providers.
        
        Returns:
            Dict with provider names and their configuration status
        """
        return {
            "openai": {
                "configured": bool(self.openai_api_key),
                "timeout": self.openai_timeout_seconds,
            },
            "anthropic": {
                "configured": bool(self.get_anthropic_key()),
                "timeout": self.anthropic_timeout_seconds,
            },
            "grok": {
                "configured": bool(self.grok_api_key),
                "timeout": self.grok_timeout_seconds,
            },
            "gemini": {
                "configured": bool(self.gemini_api_key),
                "timeout": self.gemini_timeout_seconds,
            },
            "deepseek": {
                "configured": bool(self.deepseek_api_key),
                "timeout": self.deepseek_timeout_seconds,
            },
            "together": {
                "configured": bool(self.get_together_key()),
                "timeout": self.together_timeout_seconds,
            },
            "pinecone": {
                "configured": bool(self.pinecone_api_key),
                "index": self.pinecone_index_name,
            },
            "stripe": {
                "configured": bool(self.stripe_api_key),
            },
        }


# ==================== SINGLETON PATTERN ====================

_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create Settings singleton instance.
    
    This ensures settings are loaded lazily (at runtime, not import time).
    This prevents race conditions on serverless cold starts where environment
    variables may not be fully loaded when Python modules are first imported.
    
    Returns:
        Settings instance with environment variables loaded
    """
    global _settings_instance
    if _settings_instance is None:
        logger.debug("Initializing Settings from environment variables")
        _settings_instance = Settings()
        logger.debug("Settings initialized successfully")
    return _settings_instance


def reset_settings() -> None:
    """Reset the settings singleton (useful for testing)."""
    global _settings_instance
    _settings_instance = None


# ==================== BACKWARD COMPATIBILITY ====================

# For backward compatibility - lazily create settings instance
# This allows old code like `from config import settings` to still work
settings = get_settings()


def validate_startup_config(strict: bool = False) -> ConfigValidationResult:
    """Validate configuration at application startup.
    
    Args:
        strict: If True, raise an exception on configuration errors
        
    Returns:
        ConfigValidationResult with validation status
        
    Raises:
        RuntimeError: If strict=True and configuration is invalid
    """
    settings = get_settings()
    result = settings.validate(strict=strict)
    
    if strict and not result.is_valid:
        raise RuntimeError(
            f"Configuration validation failed: {'; '.join(result.errors)}"
        )
    
    return result
