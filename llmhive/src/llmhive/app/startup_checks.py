"""Runtime configuration validation for the orchestrator service."""
from __future__ import annotations

import logging
import os
from typing import List

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
]


def validate_startup_config() -> None:
    """Validate that critical environment configuration is present."""
    configured_providers = [key for key in PROVIDER_KEYS if os.getenv(key)]
    missing_providers = [key for key in PROVIDER_KEYS if not os.getenv(key)]
    allow_stub_provider = os.getenv("ALLOW_STUB_PROVIDER", "false").lower() == "true"

    if not configured_providers and not allow_stub_provider:
        # No real providers means the orchestrator will fall back to stub mode.
        # Raise a clear error to avoid silently shipping a broken build.
        raise RuntimeError(
            "No provider API keys configured. Set at least one of: "
            f"{', '.join(PROVIDER_KEYS)}"
        )
    elif not configured_providers:
        logger.warning(
            "ALLOW_STUB_PROVIDER=true detected. The orchestrator will run using the stub provider only. "
            "Do not use this mode in production."
        )

    if missing_providers:
        logger.info(
            "Optional providers not configured: %s",
            ", ".join(missing_providers),
        )

    if not os.getenv("API_KEY"):
        logger.warning(
            "API_KEY not set. Requests will not be authenticated. "
            "Set API_KEY to enforce backend authentication."
        )
