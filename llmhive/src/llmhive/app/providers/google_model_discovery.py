"""
Google Model Auto-Discovery & Safe Production Selection
========================================================
Replaces hardcoded model IDs with dynamic discovery via the
Google AI Studio API.  Caches results for 10 minutes and provides
workload-aware selection with safe fallback logic.

Usage:
    from llmhive.app.providers.google_model_discovery import (
        get_available_google_models,
        select_best_google_model,
        get_google_model_cached,
    )

    models = await get_available_google_models(api_key)
    model  = select_best_google_model(models, workload="reasoning")
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_DISCOVERY_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_CACHE_TTL_SECONDS = 600  # 10 minutes

_REJECT_PATTERNS = re.compile(r"(exp|preview-only|deprecated)", re.IGNORECASE)
_GEMINI_FAMILY = re.compile(r"^gemini-(1\.5|2\.0|2\.5|3)", re.IGNORECASE)

# Tier ordering: higher = newer / preferred
_VERSION_PRIORITY = {
    "3": 400,
    "2.5": 300,
    "2.0": 200,
    "1.5": 100,
}

_VARIANT_PRIORITY = {
    "pro": 20,
    "flash": 10,
    "flash-lite": 5,
}


@dataclass
class GoogleModel:
    """Parsed metadata for a discovered Gemini model."""
    name: str                       # e.g. "models/gemini-2.5-pro"
    display_name: str               # e.g. "Gemini 2.5 Pro"
    model_id: str                   # e.g. "gemini-2.5-pro" (stripped prefix)
    version: str                    # e.g. "2.5"
    variant: str                    # e.g. "pro" | "flash" | "flash-lite"
    supports_generate: bool = True
    deprecated: bool = False
    input_token_limit: int = 0
    output_token_limit: int = 0
    priority: int = 0               # computed sort key (higher = better)


def _parse_model(raw: Dict[str, Any]) -> Optional[GoogleModel]:
    """Parse one model entry from the API list response."""
    name = raw.get("name", "")
    model_id = name.replace("models/", "")
    display = raw.get("displayName", model_id)
    methods = raw.get("supportedGenerationMethods", [])

    if "generateContent" not in methods:
        return None

    if not _GEMINI_FAMILY.search(model_id):
        return None

    lower = model_id.lower()

    if "exp" in lower and "preview" not in lower:
        return None
    if raw.get("deprecated", False):
        return None

    version = ""
    vm = re.search(r"gemini-(\d+\.?\d*)", lower)
    if vm:
        version = vm.group(1)

    variant = "flash" if "flash" in lower else "pro"
    if "flash-lite" in lower:
        variant = "flash-lite"

    ver_pri = _VERSION_PRIORITY.get(version, 0)
    var_pri = _VARIANT_PRIORITY.get(variant, 0)
    is_preview = 1 if "preview" in lower else 2  # prefer non-preview

    priority = ver_pri + var_pri + is_preview

    return GoogleModel(
        name=name,
        display_name=display,
        model_id=model_id,
        version=version,
        variant=variant,
        supports_generate=True,
        deprecated=False,
        input_token_limit=raw.get("inputTokenLimit", 0),
        output_token_limit=raw.get("outputTokenLimit", 0),
        priority=priority,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_available_google_models(
    api_key: Optional[str] = None,
    timeout: float = 15.0,
) -> List[GoogleModel]:
    """
    Discover available Gemini models from the Google AI API.

    Filters to stable, non-deprecated models that support generateContent.
    Returns models sorted by priority (best first).
    """
    key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        logger.warning("google_model_discovery: no API key available")
        return []

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                _DISCOVERY_URL,
                params={"key": key},
            )
            if resp.status_code != 200:
                logger.warning(
                    "google_model_discovery: API returned %d: %s",
                    resp.status_code, resp.text[:200],
                )
                return []

            data = resp.json()
            raw_models = data.get("models", [])
    except Exception as exc:
        logger.warning("google_model_discovery: request failed: %s", exc)
        return []

    parsed: List[GoogleModel] = []
    for raw in raw_models:
        m = _parse_model(raw)
        if m is not None:
            parsed.append(m)

    parsed.sort(key=lambda m: m.priority, reverse=True)
    logger.info(
        "google_model_discovery: found %d models: %s",
        len(parsed), [m.model_id for m in parsed[:8]],
    )
    return parsed


def select_best_google_model(
    models: List[GoogleModel],
    workload: str = "general",
) -> str:
    """
    Select the best Gemini model for a workload.

    workload:
        "reasoning" / "coding" / "math"  -> prefer Pro
        "speed" / "chat"                 -> prefer Flash
        "general" / anything else        -> prefer Pro over Flash

    Raises ValueError if no suitable model is found.
    """
    if not models:
        raise ValueError(
            "google_model_discovery: no models available — "
            "check GOOGLE_AI_API_KEY and network connectivity"
        )

    prefer_pro = workload in ("reasoning", "coding", "math", "general")
    prefer_flash = workload in ("speed", "chat")

    pros = [m for m in models if m.variant == "pro"]
    flashes = [m for m in models if m.variant in ("flash", "flash-lite")]

    if prefer_pro and pros:
        selected = pros[0]
    elif prefer_flash and flashes:
        selected = flashes[0]
    elif pros:
        selected = pros[0]
    elif flashes:
        selected = flashes[0]
    else:
        selected = models[0]

    logger.info(
        "google_model_discovery: selected %s for workload=%s (priority=%d)",
        selected.model_id, workload, selected.priority,
    )
    return selected.model_id


# ---------------------------------------------------------------------------
# Cached wrapper (10-minute TTL)
# ---------------------------------------------------------------------------

_cache_models: List[GoogleModel] = []
_cache_ts: float = 0.0


async def get_google_model_cached(
    api_key: Optional[str] = None,
) -> List[GoogleModel]:
    """Return cached model list, refreshing every 10 minutes."""
    global _cache_models, _cache_ts

    now = time.time()
    if _cache_models and (now - _cache_ts) < _CACHE_TTL_SECONDS:
        return _cache_models

    fresh = await get_available_google_models(api_key)
    if fresh:
        _cache_models = fresh
        _cache_ts = now

    return _cache_models


def invalidate_cache() -> None:
    """Force next call to re-discover models (e.g. after a 404)."""
    global _cache_ts
    _cache_ts = 0.0


# ---------------------------------------------------------------------------
# Fallback-aware selection (Phase 5)
# ---------------------------------------------------------------------------

async def select_with_fallback(
    api_key: Optional[str] = None,
    workload: str = "general",
    failed_model: Optional[str] = None,
) -> str:
    """
    Select a model, excluding a failed one if provided.
    Re-discovers if needed.  Never cascades more than once.
    """
    if failed_model:
        logger.warning(
            "google_model_discovery: model %s failed, re-discovering",
            failed_model,
        )
        invalidate_cache()

    models = await get_google_model_cached(api_key)
    if failed_model:
        models = [m for m in models if m.model_id != failed_model]

    return select_best_google_model(models, workload)
