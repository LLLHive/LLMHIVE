"""Anthropic Messages API model ID helpers.

Keeps OpenRouter / UI aliases mapped to current Claude API model IDs so direct
Anthropic calls do not 404 on retired dated slugs or provider-prefixed IDs.
"""
from __future__ import annotations

# Anthropic Messages API model aliases → current Claude API IDs.
# OpenRouter-style prefixes and retired dated slugs caused production 404 storms.
ANTHROPIC_MODEL_MAPPING = {
    "anthropic/claude-opus-5": "claude-opus-5",
    "anthropic/claude-opus-5-fast": "claude-opus-5",
    "anthropic/claude-sonnet-5": "claude-sonnet-5",
    "anthropic/claude-sonnet-4.6": "claude-sonnet-4-6",
    "anthropic/claude-sonnet-4-6": "claude-sonnet-4-6",
    "anthropic/claude-haiku-4.5": "claude-haiku-4-5",
    "anthropic/claude-haiku-4-5": "claude-haiku-4-5",
    "anthropic/claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
    "anthropic/claude-sonnet-4": "claude-sonnet-4-6",
    "anthropic/claude-opus-4": "claude-opus-5",
    "anthropic/claude-3-5-sonnet-20241022": "claude-sonnet-4-6",
    "anthropic/claude-3-5-haiku-20241022": "claude-haiku-4-5-20251001",
    "claude-opus-5": "claude-opus-5",
    "claude-sonnet-5": "claude-sonnet-5",
    "claude-sonnet-4.6": "claude-sonnet-4-6",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-haiku-4.5": "claude-haiku-4-5",
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-sonnet-4.5": "claude-sonnet-4-6",
    "claude-sonnet-4": "claude-sonnet-4-6",
    "claude-opus-4": "claude-opus-5",
    "claude-haiku-4": "claude-haiku-4-5",
    "claude-3-5-sonnet": "claude-sonnet-4-6",
    "claude-3-5-haiku": "claude-haiku-4-5",
    "claude-3-sonnet": "claude-sonnet-4-6",
    "claude-3-haiku": "claude-haiku-4-5",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-haiku": "claude-haiku-4-5",
    "claude-sonnet-4-20250514": "claude-sonnet-4-6",
    "claude-opus-4-20250514": "claude-opus-5",
    "claude-3-5-sonnet-20241022": "claude-sonnet-4-6",
    "claude-3-5-haiku-20241022": "claude-haiku-4-5-20251001",
}


def map_anthropic_model_id(model: str) -> str:
    """Map UI / OpenRouter Claude IDs to Anthropic Messages API model IDs."""
    key = (model or "").strip()
    mapped = ANTHROPIC_MODEL_MAPPING.get(key.lower())
    if mapped:
        return mapped
    if "/" in key:
        stripped = key.split("/", 1)[1]
        mapped = ANTHROPIC_MODEL_MAPPING.get(stripped.lower())
        if mapped:
            return mapped
        return stripped
    return key
