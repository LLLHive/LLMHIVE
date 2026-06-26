"""Shared per-tier request cost caps (loaded from data/billing/tier_cost_caps.json)."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from ..middleware.tier_check import normalize_rate_limit_tier

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    # .../llmhive/src/llmhive/app/billing/tier_cost_caps.py -> repo root
    return Path(__file__).resolve().parents[5]


def _caps_path() -> Path:
    return _repo_root() / "data" / "billing" / "tier_cost_caps.json"


@lru_cache(maxsize=1)
def load_tier_cost_caps() -> Dict[str, Any]:
    path = _caps_path()
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("tier_cost_caps.json unavailable (%s); using defaults", exc)
        return {
            "per_request_max_cost_usd": {
                "free": 0.10,
                "lite": 0.35,
                "pro": 0.75,
                "enterprise": 0.75,
            },
            "prefer_cheaper_default": {"free": True, "lite": True, "standard": True},
        }


def per_request_max_cost_usd(tier: str) -> float:
    caps = load_tier_cost_caps().get("per_request_max_cost_usd") or {}
    key = normalize_rate_limit_tier(tier)
    try:
        return float(caps.get(key, caps.get("free", 0.10)))
    except (TypeError, ValueError):
        return 0.10


def prefer_cheaper_default(tier: str) -> bool:
    prefs = load_tier_cost_caps().get("prefer_cheaper_default") or {}
    key = normalize_rate_limit_tier(tier)
    return bool(prefs.get(key, False))


def resolve_per_request_max_cost_usd(tier: str, requested: Optional[float]) -> float:
    if requested is not None and requested > 0:
        return float(requested)
    return per_request_max_cost_usd(tier)
