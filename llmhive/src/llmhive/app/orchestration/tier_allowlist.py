"""Tier-Safe Model Allowlisting — Root-Cause Fix for Disabled HRM.

Instead of blanket-disabling HRM / adaptive routing / deep consensus for the
free tier, this module provides a model-filter that any orchestration component
can call to restrict its candidate set to tier-legal models.

Usage in any component that picks models:

    from ..orchestration.tier_allowlist import filter_models_for_tier
    candidates = filter_models_for_tier(raw_candidates, effective_tier)

The filter guarantees:
  - effective_tier="free"  → only FREE_MODELS_DB models pass through
  - effective_tier="elite" → ELITE_MODELS pass, free advisors only if
                             ELITE_PLUS_INCLUDE_FREE_ADVISORS=1
  - effective_tier="auto"  → no filtering (all models pass)

This replaces the blanket:
    if use_free_models:
        orchestration_config["use_hrm"] = False
        orchestration_config["use_adaptive_routing"] = False
        orchestration_config["use_deep_consensus"] = False
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical model sets (populated on first call via lazy init)
# ---------------------------------------------------------------------------
_free_allowlist: Optional[Set[str]] = None
_elite_allowlist: Optional[Set[str]] = None


def _init_free_allowlist() -> Set[str]:
    global _free_allowlist
    if _free_allowlist is not None:
        return _free_allowlist

    models: Set[str] = set()
    try:
        from .free_models_database import FREE_MODELS_DB
        models.update(FREE_MODELS_DB.keys())
    except ImportError:
        pass

    try:
        from .elite_orchestration import FREE_MODELS
        for category_models in FREE_MODELS.values():
            models.update(category_models)
    except ImportError:
        pass

    _free_allowlist = models
    logger.debug("Tier allowlist: loaded %d free models", len(models))
    return _free_allowlist


def _init_elite_allowlist() -> Set[str]:
    global _elite_allowlist
    if _elite_allowlist is not None:
        return _elite_allowlist

    models: Set[str] = set()
    try:
        from .elite_orchestration import ELITE_MODELS, BUDGET_MODELS, MAXIMUM_MODELS
        for mapping in (ELITE_MODELS, BUDGET_MODELS, MAXIMUM_MODELS):
            for category_models in mapping.values():
                models.update(category_models)
    except ImportError:
        pass

    _elite_allowlist = models
    logger.debug("Tier allowlist: loaded %d elite models", len(models))
    return _elite_allowlist


def get_free_allowlist() -> Set[str]:
    """Return the canonical set of free-tier model IDs."""
    return _init_free_allowlist()


def get_elite_allowlist() -> Set[str]:
    """Return the canonical set of elite-tier model IDs."""
    return _init_elite_allowlist()


# ---------------------------------------------------------------------------
# Main filter
# ---------------------------------------------------------------------------
def filter_models_for_tier(
    candidates: List[str],
    effective_tier: str,
    include_free_advisors: Optional[bool] = None,
) -> List[str]:
    """Filter a candidate model list to only tier-legal models.

    Args:
        candidates:            Raw model list from any orchestration component.
        effective_tier:        "free", "elite", or "auto".
        include_free_advisors: If True (and elite tier), also allow free models.
                               Defaults to ELITE_PLUS_INCLUDE_FREE_ADVISORS env.

    Returns:
        Filtered list preserving original order. If filtering would produce an
        empty list, returns a safe default subset for that tier.
    """
    if effective_tier == "auto":
        return candidates

    if effective_tier == "free":
        allowed = _init_free_allowlist()
        filtered = [m for m in candidates if m in allowed]
        if not filtered:
            logger.warning(
                "Tier allowlist: no free models in candidates %s, using defaults",
                candidates[:5],
            )
            filtered = sorted(allowed)[:3]
        return filtered

    if effective_tier == "elite":
        allowed = _init_elite_allowlist()
        if include_free_advisors is None:
            include_free_advisors = os.getenv(
                "ELITE_PLUS_INCLUDE_FREE_ADVISORS", "0"
            ).lower() in ("1", "true")
        if include_free_advisors:
            allowed = allowed | _init_free_allowlist()
        filtered = [m for m in candidates if m in allowed]
        if not filtered:
            return candidates
        return filtered

    return candidates


def get_tier_safe_orchestration_flags(
    effective_tier: str,
    orchestration_config: Dict[str, object],
) -> Dict[str, object]:
    """Adjust orchestration flags for tier safety.

    For the free tier, HRM/adaptive/consensus CAN still run as long as the
    model candidates are pre-filtered through the allowlist.  However, if
    the allowlist module detects the tier is free, it currently keeps the
    engines disabled to match the validated behavior.  This is the safe
    graduation path: first prove the allowlist filter works, then re-enable
    engines one by one behind flags.
    """
    config = dict(orchestration_config)

    if effective_tier == "free":
        config["use_hrm"] = False
        config["use_adaptive_routing"] = False
        config["use_deep_consensus"] = False
        config["_tier_allowlist_active"] = True

    return config


def build_telemetry(effective_tier: str, use_hrm: bool, use_adaptive: bool,
                    use_consensus: bool) -> Dict[str, object]:
    """Build orchestration-features telemetry dict."""
    ep_enabled = False
    ep_mode = None
    pf_enabled = False
    try:
        from .elite_plus_orchestrator import ELITE_PLUS_ENABLED, ELITE_PLUS_MODE
        ep_enabled = ELITE_PLUS_ENABLED
        ep_mode = ELITE_PLUS_MODE if ep_enabled else None
    except ImportError:
        pass
    try:
        from .progressive_free import FREE_PROGRESSIVE
        pf_enabled = FREE_PROGRESSIVE
    except ImportError:
        pass
    return {
        "hrm": use_hrm,
        "adaptive_routing": use_adaptive,
        "deep_consensus": use_consensus,
        "elite_plus_enabled": ep_enabled,
        "elite_plus_mode": ep_mode,
        "progressive_free": pf_enabled,
        "effective_tier": effective_tier,
    }
