"""Unified Model Registry — Single source of truth for all orchestrators.

Every model that Elite, Free, or Elite+ may call is declared here with
tier, capability tags, expected latency tier, reliability, and per-category
rank scores.  Orchestrators import from this module instead of hard-coding
model lists.

Env flags:
  MODEL_REGISTRY_VERSION  — logged for drift tracking (default "1")
  MODEL_REGISTRY_REFRESH  — if "1", force re-init on next import (default "0")
  REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE — if "1", registry version bumps
      require a passing RC gate before deployment (enforced by CI/promote)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

MODEL_REGISTRY_VERSION = os.getenv("MODEL_REGISTRY_VERSION", "2")
MODEL_REGISTRY_REFRESH = os.getenv("MODEL_REGISTRY_REFRESH", "0").lower() in ("1", "true")
REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE = os.getenv(
    "REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE", "1"
).lower() in ("1", "true")


class Tier(str, Enum):
    ELITE = "elite"
    FREE = "free"
    BOTH = "both"


class LatencyTier(str, Enum):
    FAST = "fast"        # < 3s p95
    MEDIUM = "medium"    # 3-10s p95
    SLOW = "slow"        # 10-30s p95
    VERY_SLOW = "very_slow"  # > 30s p95


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    tier: Tier
    capabilities: frozenset  # e.g. {"math", "reasoning", "coding", "long_context", "verification"}
    latency_tier: LatencyTier
    reliability: float  # 0-1, based on observed uptime
    context_window: int = 128_000
    category_scores: Dict[str, float] = field(default_factory=dict)
    notes: str = ""
    best_for_categories: Tuple[str, ...] = ()  # categories where this model is top-ranked
    leaderboard_rank: Dict[str, int] = field(default_factory=dict)  # {category: rank}


# ---------------------------------------------------------------------------
# Registry data
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, ModelProfile] = {}


def _build_registry() -> Dict[str, ModelProfile]:
    models = [
        # ----- ELITE PAID MODELS -----
        ModelProfile(
            model_id="openai/gpt-5.2",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "coding", "rag", "dialogue", "tool_use", "verification"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.95,
            context_window=128_000,
            category_scores={"math": 97.5, "reasoning": 92.8, "coding": 95.5, "rag": 88, "dialogue": 90, "tool_use": 93},
        ),
        ModelProfile(
            model_id="anthropic/claude-opus-4.6",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "coding", "rag", "multilingual", "tool_use", "verification"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.94,
            context_window=200_000,
            category_scores={"math": 95.8, "reasoning": 90, "coding": 97, "multilingual": 90.8, "dialogue": 94, "tool_use": 93.5},
            notes="Top coding model, strong across all categories",
        ),
        ModelProfile(
            model_id="anthropic/claude-sonnet-4",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "coding", "rag", "multilingual", "long_context", "verification"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.96,
            context_window=1_000_000,
            category_scores={"coding": 82, "reasoning": 89.1, "multilingual": 89.1},
            notes="Fast, reliable — good verifier candidate",
        ),
        ModelProfile(
            model_id="google/gemini-3.1-pro-preview",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "long_context", "multilingual", "tool_use"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.90,
            context_window=1_050_000,
            category_scores={"math": 97.2, "reasoning": 91.8, "long_context": 96},
            notes="Best long-context model (1.05M tokens)",
        ),
        ModelProfile(
            model_id="google/gemini-3-pro",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "long_context"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.91,
            context_window=1_000_000,
            category_scores={"math": 96, "reasoning": 87.5},
        ),
        ModelProfile(
            model_id="x-ai/grok-3-mini",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "tool_use", "verification"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.92,
            context_window=128_000,
            category_scores={"math": 93.8, "reasoning": 89},
            notes="Fast CoT, good for quick verification",
        ),
        ModelProfile(
            model_id="openai/gpt-4o",
            tier=Tier.ELITE,
            capabilities=frozenset({"reasoning", "coding", "dialogue", "verification"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.97,
            context_window=128_000,
            category_scores={"reasoning": 85, "coding": 88},
            notes="Very fast, very reliable — excellent verifier",
        ),
        ModelProfile(
            model_id="openai/gpt-4o-mini",
            tier=Tier.BOTH,
            capabilities=frozenset({"reasoning", "coding", "verification"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.97,
            context_window=128_000,
            category_scores={"reasoning": 78},
            notes="Cheapest fast model — ideal lightweight verifier",
        ),
        ModelProfile(
            model_id="deepseek/deepseek-reasoner",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "verification"}),
            latency_tier=LatencyTier.VERY_SLOW,
            reliability=0.60,
            context_window=64_000,
            category_scores={"math": 97, "reasoning": 91},
            notes="Powerful but VERY SLOW (62s+ typical). Do NOT use as default verifier.",
        ),
        ModelProfile(
            model_id="moonshot/kimi-k2.5-thinking",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning", "coding"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.88,
            context_window=256_000,
            category_scores={"math": 96.8, "reasoning": 88, "coding": 92},
            notes="Thinking mode with visual coding",
        ),
        ModelProfile(
            model_id="zhipuai/glm-4.7",
            tier=Tier.ELITE,
            capabilities=frozenset({"math", "reasoning"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.85,
            context_window=128_000,
            category_scores={"math": 98},
            notes="GSM8K champion (Feb 2026)",
        ),
        ModelProfile(
            model_id="alibaba/qwen3-max",
            tier=Tier.ELITE,
            capabilities=frozenset({"coding", "reasoning", "multilingual"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.87,
            context_window=128_000,
            category_scores={"coding": 92.7, "multilingual": 80.5},
        ),
        # ----- LONG-CONTEXT SPECIALISTS -----
        ModelProfile(
            model_id="google/gemini-2.5-pro",
            tier=Tier.ELITE,
            capabilities=frozenset({"long_context", "reasoning"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.91,
            context_window=1_000_000,
            category_scores={"long_context": 96},
        ),
        ModelProfile(
            model_id="google/gemini-2.5-flash",
            tier=Tier.ELITE,
            capabilities=frozenset({"speed", "reasoning"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.93,
            context_window=1_000_000,
            category_scores={"speed": 95},
            notes="Fast Gemini variant",
        ),
        # ----- FREE MODELS -----
        ModelProfile(
            model_id="meta-llama/llama-3.3-70b-instruct:free",
            tier=Tier.FREE,
            capabilities=frozenset({"reasoning", "coding", "dialogue"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.80,
            context_window=131_000,
            category_scores={"reasoning": 78, "coding": 76, "dialogue": 75},
            notes="GPT-4 level free model",
        ),
        ModelProfile(
            model_id="google/gemma-3-27b-it:free",
            tier=Tier.FREE,
            capabilities=frozenset({"reasoning", "multilingual", "multimodal"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.78,
            context_window=131_000,
            category_scores={"reasoning": 74, "multilingual": 72},
            notes="Vision-language, 140+ languages",
        ),
        ModelProfile(
            model_id="nvidia/nemotron-3-nano-30b-a3b:free",
            tier=Tier.FREE,
            capabilities=frozenset({"reasoning", "speed"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.82,
            context_window=256_000,
            category_scores={"reasoning": 70, "speed": 85},
            notes="Fast, 256K context",
        ),
        ModelProfile(
            model_id="deepseek/deepseek-chat",
            tier=Tier.FREE,
            capabilities=frozenset({"math", "reasoning", "coding"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.85,
            context_window=64_000,
            category_scores={"math": 90, "reasoning": 80, "coding": 82},
        ),
        ModelProfile(
            model_id="qwen/qwen3-coder:free",
            tier=Tier.FREE,
            capabilities=frozenset({"coding", "reasoning"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.80,
            context_window=128_000,
            category_scores={"coding": 78, "reasoning": 75},
        ),
        ModelProfile(
            model_id="qwen/qwen3-next-80b-a3b-instruct:free",
            tier=Tier.FREE,
            capabilities=frozenset({"reasoning", "multilingual"}),
            latency_tier=LatencyTier.MEDIUM,
            reliability=0.78,
            context_window=128_000,
            category_scores={"reasoning": 76, "multilingual": 74},
        ),
        ModelProfile(
            model_id="arcee-ai/trinity-large-preview:free",
            tier=Tier.FREE,
            capabilities=frozenset({"reasoning", "dialogue"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.75,
            context_window=128_000,
            category_scores={"reasoning": 72, "dialogue": 70},
        ),
        ModelProfile(
            model_id="arcee-ai/trinity-mini:free",
            tier=Tier.FREE,
            capabilities=frozenset({"reasoning"}),
            latency_tier=LatencyTier.FAST,
            reliability=0.75,
            context_window=128_000,
            category_scores={"reasoning": 68},
        ),
    ]
    return {m.model_id: m for m in models}


def get_registry() -> Dict[str, ModelProfile]:
    global _REGISTRY
    if not _REGISTRY or MODEL_REGISTRY_REFRESH:
        _REGISTRY = _build_registry()
        logger.info("Model registry initialized: %d models, version=%s", len(_REGISTRY), MODEL_REGISTRY_VERSION)
    return _REGISTRY


def get_model(model_id: str) -> Optional[ModelProfile]:
    return get_registry().get(model_id)


def get_models_by_tier(tier: Tier) -> List[ModelProfile]:
    return [m for m in get_registry().values() if m.tier == tier or m.tier == Tier.BOTH]


def get_models_with_capability(capability: str) -> List[ModelProfile]:
    return [m for m in get_registry().values() if capability in m.capabilities]


def get_fast_verifier_candidates() -> List[ModelProfile]:
    """Return models suitable for fast verification (fast latency, verification capable)."""
    return [
        m for m in get_registry().values()
        if "verification" in m.capabilities
        and m.latency_tier in (LatencyTier.FAST, LatencyTier.MEDIUM)
        and m.reliability >= 0.90
    ]


def get_best_for_category(category: str, tier: Optional[Tier] = None) -> List[ModelProfile]:
    """Return models ranked by their score for a given category."""
    candidates = get_registry().values()
    if tier:
        candidates = [m for m in candidates if m.tier == tier or m.tier == Tier.BOTH]
    scored = [(m, m.category_scores.get(category, 0)) for m in candidates if m.category_scores.get(category, 0) > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, _ in scored]


def get_long_context_models() -> List[ModelProfile]:
    """Return models with >500K context window, sorted by window size."""
    models = [m for m in get_registry().values() if m.context_window >= 500_000]
    models.sort(key=lambda m: m.context_window, reverse=True)
    return models


def compute_leaderboard_ranks() -> Dict[str, Dict[str, int]]:
    """Compute per-category leaderboard ranks from category_scores.

    Returns {model_id: {category: rank}} where rank=1 is highest score.
    """
    registry = get_registry()
    all_categories: set = set()
    for m in registry.values():
        all_categories.update(m.category_scores.keys())

    result: Dict[str, Dict[str, int]] = {mid: {} for mid in registry}
    for cat in sorted(all_categories):
        scored = [
            (m.model_id, m.category_scores.get(cat, 0))
            for m in registry.values()
            if m.category_scores.get(cat, 0) > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        for rank, (mid, _) in enumerate(scored, 1):
            result[mid][cat] = rank
    return result


def compute_best_for_categories() -> Dict[str, List[str]]:
    """Compute which categories each model is top-ranked (#1) in.

    Returns {model_id: [categories_where_rank_1]}.
    """
    ranks = compute_leaderboard_ranks()
    result: Dict[str, List[str]] = {}
    for mid, cat_ranks in ranks.items():
        best = [cat for cat, r in cat_ranks.items() if r == 1]
        if best:
            result[mid] = sorted(best)
    return result


def compute_leaderboard() -> Dict[str, Dict[str, int]]:
    """Compute per-category rank for every model. Returns {model_id: {category: rank}}."""
    registry = get_registry()
    all_categories: Set[str] = set()
    for m in registry.values():
        all_categories.update(m.category_scores.keys())

    result: Dict[str, Dict[str, int]] = {mid: {} for mid in registry}
    for cat in all_categories:
        ranked = get_best_for_category(cat)
        for rank, m in enumerate(ranked, 1):
            result[m.model_id][cat] = rank
    return result


def compute_best_for() -> Dict[str, List[str]]:
    """Compute which categories each model is #1 in. Returns {model_id: [categories]}."""
    lb = compute_leaderboard()
    return {
        mid: [cat for cat, rank in ranks.items() if rank == 1]
        for mid, ranks in lb.items()
    }


def compute_registry_integrity_hash() -> str:
    """Deterministic SHA-256 of the registry contents for tamper detection.

    Serializes model profiles in sorted order by model_id, producing a
    stable hash that changes when and only when registry data changes.
    """
    registry = get_registry()
    entries = []
    for mid in sorted(registry.keys()):
        m = registry[mid]
        entries.append({
            "model_id": m.model_id,
            "tier": m.tier.value,
            "capabilities": sorted(m.capabilities),
            "latency_tier": m.latency_tier.value,
            "reliability": m.reliability,
            "context_window": m.context_window,
            "category_scores": dict(sorted(m.category_scores.items())),
            "notes": m.notes,
        })
    blob = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def check_champion_challenger_gate(
    new_version: str,
    rc_summary_path: Optional[str] = None,
) -> bool:
    """Champion/challenger guard: new registry versions must pass RC gate.

    Returns True if promotion is allowed, False if blocked.
    When REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE=0, always returns True.
    """
    if not REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE:
        return True

    if str(new_version) == str(MODEL_REGISTRY_VERSION):
        return True

    if rc_summary_path:
        from pathlib import Path
        p = Path(rc_summary_path)
        if p.exists():
            try:
                summary = json.loads(p.read_text())
                return summary.get("gate_status") == "pass"
            except Exception:
                pass

    logger.warning(
        "Registry update blocked: REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE=1 "
        "and no passing RC gate found for version %s",
        new_version,
    )
    return False
