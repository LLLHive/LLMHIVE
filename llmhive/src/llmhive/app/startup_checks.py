"""Runtime configuration validation for the orchestrator service.

This module provides comprehensive startup validation including:
- LLM provider API key verification
- Optional service configuration checks (Pinecone, Stripe)
- Environment-specific warnings
- Detailed logging of configuration status
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Provider API keys that enable real LLM connectivity
PROVIDER_KEYS: List[str] = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "GROK_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MANUS_API_KEY",
    "TOGETHERAI_API_KEY",
]

# Optional service keys for extended functionality
OPTIONAL_SERVICE_KEYS = {
    "PINECONE_API_KEY": "RAG/Knowledge Base features",
    "STRIPE_SECRET_KEY": "Billing features",
    "GOOGLE_CLOUD_PROJECT": "Google Cloud integration",
}


@dataclass
class StartupValidationResult:
    """Result of startup configuration validation."""
    is_valid: bool = True
    configured_providers: List[str] = field(default_factory=list)
    missing_providers: List[str] = field(default_factory=list)
    optional_services: dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def validate_startup_config(strict: bool = False) -> StartupValidationResult:
    """Validate that critical environment configuration is present.
    
    Args:
        strict: If True, raise RuntimeError on any configuration errors.
                If False (default), log warnings but continue startup.
                
    Returns:
        StartupValidationResult with detailed configuration status
        
    Raises:
        RuntimeError: If strict=True and configuration is invalid
    """
    result = StartupValidationResult()
    
    # Check LLM provider API keys
    result.configured_providers = [key for key in PROVIDER_KEYS if os.getenv(key)]
    result.missing_providers = [key for key in PROVIDER_KEYS if not os.getenv(key)]
    allow_stub_provider = os.getenv("ALLOW_STUB_PROVIDER", "false").lower() == "true"
    
    # Validate at least one provider is configured
    if not result.configured_providers:
        if allow_stub_provider:
            result.warnings.append(
                "ALLOW_STUB_PROVIDER=true detected. Running with stub provider only. "
                "Do NOT use in production."
            )
            logger.warning(
                "⚠️  STUB MODE: No real LLM providers configured. "
                "Set environment variables: %s",
                ", ".join(PROVIDER_KEYS[:3])  # Show first 3 as examples
            )
        else:
            error_msg = (
                "No LLM provider API keys configured. Set at least one of: "
                f"{', '.join(PROVIDER_KEYS[:3])}..."
            )
            result.errors.append(error_msg)
            result.is_valid = False
            logger.error("❌ CONFIG ERROR: %s", error_msg)
    else:
        logger.info(
            "✓ Configured LLM providers: %s",
            ", ".join([k.replace("_API_KEY", "") for k in result.configured_providers])
        )
    
    # Check optional services
    for key, description in OPTIONAL_SERVICE_KEYS.items():
        is_configured = bool(os.getenv(key))
        result.optional_services[key] = {
            "configured": is_configured,
            "description": description,
        }
        if not is_configured:
            result.warnings.append(f"{key} not set - {description} will be disabled")
            logger.info("ℹ️  Optional: %s not configured (%s disabled)", key, description)
    
    # Check authentication
    if not os.getenv("API_KEY"):
        result.warnings.append(
            "API_KEY not set. Backend requests will not be authenticated."
        )
        logger.warning(
            "⚠️  API_KEY not set. Consider setting it for production deployments."
        )
    
    # Check environment mode
    env = os.getenv("ENVIRONMENT", "development")
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    if env == "production":
        if debug:
            result.warnings.append("DEBUG=true in production environment")
            logger.warning("⚠️  DEBUG mode enabled in production!")
        if allow_stub_provider:
            result.warnings.append("ALLOW_STUB_PROVIDER=true in production")
            logger.warning("⚠️  Stub provider allowed in production!")
    
    # Log summary
    logger.info(
        "Startup validation: %d providers, %d warnings, %d errors",
        len(result.configured_providers),
        len(result.warnings),
        len(result.errors)
    )
    
    # Raise if strict mode and validation failed
    if strict and not result.is_valid:
        raise RuntimeError(
            f"Startup configuration validation failed: {'; '.join(result.errors)}"
        )
    
    return result


def get_config_summary() -> dict:
    """Get a summary of the current configuration for health checks.
    
    Returns:
        Dict with configuration summary (no secrets exposed)
    """
    return {
        "llm_providers": {
            key.replace("_API_KEY", "").lower(): bool(os.getenv(key))
            for key in PROVIDER_KEYS
        },
        "optional_services": {
            key.replace("_API_KEY", "").replace("_SECRET_KEY", "").lower(): bool(os.getenv(key))
            for key in OPTIONAL_SERVICE_KEYS
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "authenticated": bool(os.getenv("API_KEY")),
    }
