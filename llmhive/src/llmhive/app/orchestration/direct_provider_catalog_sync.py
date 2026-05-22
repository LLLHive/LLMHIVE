"""
Sync free_models_database and PROVIDER_ROUTING from scripts/*-models.json catalogs.

Ensures every OpenRouter slug we can reach via a direct connection is recorded with
preferred_api + native_model_id for ROUTING_V2.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

_REPO_SCRIPTS = Path(__file__).resolve().parents[5] / "scripts"

# catalog file stem -> preferred_api id (provider_chain / orchestrator key)
_CATALOG_API_MAP = {
    "together-models": "together",
    "hyperbolic-models": "hyperbolic",
    "fireworks-models": "fireworks",
    "deepinfra-models": "deepinfra",
    "dashscope-models": "dashscope",
    "mistral-models": "mistral",
    "cloudflare-models": "cloudflare",
    "kimi-models": "kimi",
    "azure-foundry-models": "azure_foundry",
}


def load_catalog_openrouter_maps() -> Dict[str, Tuple[str, str]]:
    """OR slug -> (preferred_api, native logical key from catalog)."""
    out: Dict[str, Tuple[str, str]] = {}
    for filename, api in _CATALOG_API_MAP.items():
        path = _REPO_SCRIPTS / f"{filename}.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            logger.warning("Could not read catalog %s: %s", path, exc)
            continue
        chat = data.get("chat") or {}
        for or_slug, logical in (data.get("openrouter_map") or {}).items():
            native = chat.get(logical, logical)
            out[or_slug] = (api, native)
    return out


def merge_catalog_into_free_models_db() -> int:
    """Add or update FREE_MODELS_DB entries from catalogs (non-destructive)."""
    from .free_models_database import FREE_MODELS_DB, FreeModelInfo, SpeedTier, ModelStrength

    maps = load_catalog_openrouter_maps()
    added = 0
    for or_slug, (api, native) in maps.items():
        if or_slug in FREE_MODELS_DB:
            info = FREE_MODELS_DB[or_slug]
            if info.preferred_api == "openrouter":
                info.preferred_api = api
                info.native_model_id = native
            continue
        FREE_MODELS_DB[or_slug] = FreeModelInfo(
            model_id=or_slug,
            display_name=native.split("/")[-1] if "/" in native else native,
            provider=api.title(),
            context_window=131072,
            speed_tier=SpeedTier.MEDIUM,
            strengths=[ModelStrength.REASONING],
            best_for=[f"Direct API via {api}"],
            notes=f"Auto-registered from direct provider catalog",
            verified_working=True,
            preferred_api=api,
            native_model_id=native,
        )
        added += 1
    if added:
        logger.info("direct_provider_catalog_sync: added %d catalog slugs to FREE_MODELS_DB", added)
    return added


def list_connected_provider_slugs() -> List[str]:
    """All OpenRouter slugs known from direct provider catalogs."""
    return list(load_catalog_openrouter_maps().keys())
