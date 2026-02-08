"""Configuration settings for LLMHive."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    available_providers: List[str] = field(default_factory=list)
    
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


class Settings:
    """Application settings loaded from environment variables."""
    
    # Default models for orchestration
    default_models: List[str] = ["gpt-4o-mini", "claude-3-haiku"]
    
    # API key (optional, for authentication)
    api_key: str | None = os.getenv("API_KEY")
    
    # Provider API keys (loaded from environment)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    # Support both ANTHROPIC_API_KEY and CLAUDE_API_KEY for Claude/Anthropic
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    claude_api_key: str | None = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    grok_api_key: str | None = os.getenv("GROK_API_KEY")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    manus_api_key: str | None = os.getenv("MANUS_API_KEY")
    together_api_key: str | None = os.getenv("TOGETHERAI_API_KEY") or os.getenv("TOGETHER_API_KEY")
    
    # Provider timeouts (optional)
    openai_timeout_seconds: int | None = None
    anthropic_timeout_seconds: int | None = None
    grok_timeout_seconds: int | None = None
    gemini_timeout_seconds: int | None = None
    deepseek_timeout_seconds: int | None = None
    manus_timeout_seconds: int | None = None
    together_timeout_seconds: int | None = None
    
    # Vector Database Configuration (Pinecone)
    pinecone_api_key: str | None = os.getenv("PINECONE_API_KEY")
    pinecone_environment: str = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "llmhive-memory")
    
    # Embedding Model Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    # Memory Configuration
    memory_namespace_per_user: bool = os.getenv("MEMORY_NAMESPACE_PER_USER", "true").lower() == "true"
    memory_ttl_days: int = int(os.getenv("MEMORY_TTL_DAYS", "90"))
    memory_max_results: int = int(os.getenv("MEMORY_MAX_RESULTS", "10"))
    memory_min_score: float = float(os.getenv("MEMORY_MIN_SCORE", "0.7"))
    
    # Stripe Configuration (Billing)
    stripe_api_key: str | None = os.getenv("STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = os.getenv("STRIPE_WEBHOOK_SECRET")
    stripe_publishable_key: str | None = os.getenv("STRIPE_PUBLISHABLE_KEY")
    
    # Stripe Price IDs (create these in Stripe Dashboard)
    stripe_price_id_basic_monthly: str | None = os.getenv("STRIPE_PRICE_ID_BASIC_MONTHLY")
    stripe_price_id_basic_annual: str | None = os.getenv("STRIPE_PRICE_ID_BASIC_ANNUAL")
    stripe_price_id_pro_monthly: str | None = os.getenv("STRIPE_PRICE_ID_PRO_MONTHLY")
    stripe_price_id_pro_annual: str | None = os.getenv("STRIPE_PRICE_ID_PRO_ANNUAL")
    stripe_price_id_enterprise_monthly: str | None = os.getenv("STRIPE_PRICE_ID_ENTERPRISE_MONTHLY")
    stripe_price_id_enterprise_annual: str | None = os.getenv("STRIPE_PRICE_ID_ENTERPRISE_ANNUAL")
    
    # Stripe Redirect URLs
    stripe_success_url: str = os.getenv("STRIPE_SUCCESS_URL", "https://llmhive.ai/billing/success")
    stripe_cancel_url: str = os.getenv("STRIPE_CANCEL_URL", "https://llmhive.ai/billing")
    
    # Google Cloud Configuration
    google_cloud_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT"))
    
    # Application Configuration
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_RPM", "60"))
    
    # Memory Settings
    memory_max_entries_per_user: int = int(os.getenv("MEMORY_MAX_ENTRIES", "1000"))
    memory_max_age_days: int = int(os.getenv("MEMORY_MAX_AGE_DAYS", "90"))
    
    @classmethod
    def validate(cls, strict: bool = False) -> ConfigValidationResult:
        """Validate configuration settings.
        
        Args:
            strict: If True, treat warnings as errors
            
        Returns:
            ConfigValidationResult with validation status and messages
        """
        result = ConfigValidationResult(is_valid=True)
        
        # Check LLM provider API keys
        provider_keys = [
            ("openai", cls.openai_api_key, "OPENAI_API_KEY"),
            ("anthropic", cls.anthropic_api_key, "ANTHROPIC_API_KEY or CLAUDE_API_KEY"),
            ("grok", cls.grok_api_key, "GROK_API_KEY"),
            ("gemini", cls.gemini_api_key, "GEMINI_API_KEY"),
            ("deepseek", cls.deepseek_api_key, "DEEPSEEK_API_KEY"),
            ("together", cls.together_api_key, "TOGETHERAI_API_KEY"),
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
        if not cls.pinecone_api_key:
            result.warnings.append(
                "PINECONE_API_KEY not set. RAG/memory features will be disabled."
            )
        
        # Check Stripe for billing
        if not cls.stripe_api_key:
            result.warnings.append(
                "STRIPE_SECRET_KEY not set. Billing features will be disabled."
            )
        
        # Validate embedding configuration
        valid_embedding_models = [
            "text-embedding-3-small", 
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]
        if cls.embedding_model not in valid_embedding_models:
            result.warnings.append(
                f"Unknown embedding model: {cls.embedding_model}. "
                f"Supported: {', '.join(valid_embedding_models)}"
            )
        
        # Validate embedding dimensions
        if cls.embedding_dimension not in [256, 512, 1024, 1536, 3072]:
            result.warnings.append(
                f"Unusual embedding dimension: {cls.embedding_dimension}. "
                "Common values: 256, 512, 1024, 1536, 3072"
            )
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.log_level not in valid_log_levels:
            result.warnings.append(
                f"Invalid LOG_LEVEL: {cls.log_level}. "
                f"Valid levels: {', '.join(valid_log_levels)}"
            )
        
        # Check for debug mode in production
        if cls.debug and os.getenv("ENVIRONMENT", "development") == "production":
            result.warnings.append(
                "DEBUG mode enabled in production. This may expose sensitive information."
            )
        
        # Log validation results
        result.log_results()
        
        return result
    
    @classmethod
    def get_provider_status(cls) -> dict:
        """Get status of all configured providers.
        
        Returns:
            Dict with provider names and their configuration status
        """
        return {
            "openai": {
                "configured": bool(cls.openai_api_key),
                "timeout": cls.openai_timeout_seconds,
            },
            "anthropic": {
                "configured": bool(cls.anthropic_api_key),
                "timeout": cls.anthropic_timeout_seconds,
            },
            "grok": {
                "configured": bool(cls.grok_api_key),
                "timeout": cls.grok_timeout_seconds,
            },
            "gemini": {
                "configured": bool(cls.gemini_api_key),
                "timeout": cls.gemini_timeout_seconds,
            },
            "deepseek": {
                "configured": bool(cls.deepseek_api_key),
                "timeout": cls.deepseek_timeout_seconds,
            },
            "together": {
                "configured": bool(cls.together_api_key),
                "timeout": cls.together_timeout_seconds,
            },
            "pinecone": {
                "configured": bool(cls.pinecone_api_key),
                "index": cls.pinecone_index_name,
            },
            "stripe": {
                "configured": bool(cls.stripe_api_key),
            },
        }


# Global settings instance
settings = Settings()


def validate_startup_config(strict: bool = False) -> ConfigValidationResult:
    """Validate configuration at application startup.
    
    Args:
        strict: If True, raise an exception on configuration errors
        
    Returns:
        ConfigValidationResult with validation status
        
    Raises:
        RuntimeError: If strict=True and configuration is invalid
    """
    result = Settings.validate(strict=strict)
    
    if strict and not result.is_valid:
        raise RuntimeError(
            f"Configuration validation failed: {'; '.join(result.errors)}"
        )
    
    return result

