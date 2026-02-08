"""Lightweight models endpoint for availability checks.

Provides a minimal model list without relying on external databases.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter, status

router = APIRouter(prefix="/models", tags=["models"])


def _provider_configured(provider: str) -> bool:
    env_map = {
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "google": ["GEMINI_API_KEY", "GOOGLE_AI_API_KEY"],
        "xai": ["GROK_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "together": ["TOGETHERAI_API_KEY", "TOGETHER_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
    }
    keys = env_map.get(provider, [])
    return any(os.getenv(k) for k in keys)


@router.get("", status_code=status.HTTP_200_OK)
def list_models() -> Dict[str, Any]:
    """Return a minimal model list for smoke tests and health checks."""
    models: List[Dict[str, Any]] = [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai"},
        {"id": "claude-3.5-haiku", "name": "Claude 3.5 Haiku", "provider": "anthropic"},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "google"},
        {"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek"},
        {"id": "together/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "name": "Llama 3.1 70B Turbo", "provider": "together"},
        {"id": "openrouter/openrouter", "name": "OpenRouter Catalog", "provider": "openrouter"},
    ]
    for model in models:
        model["available"] = _provider_configured(model["provider"])
    return {"data": models, "total": len(models), "source": "lightweight"}
