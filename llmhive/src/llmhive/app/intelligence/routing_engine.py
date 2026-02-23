"""Capability-Aware Routing Engine — Intelligent model selection for production.

Scoring formula:
  score = benchmark_strength(category) * 0.50
        + reasoning_strength          * 0.20
        + latency_inverse_weight      * 0.15
        + cost_efficiency_weight      * 0.15

In BENCHMARK_MODE: bypasses all ranking — returns ELITE_POLICY model only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from .elite_policy import ELITE_POLICY, is_benchmark_mode
from .model_registry_2026 import ModelEntry, get_model_registry_2026

logger = logging.getLogger(__name__)

LATENCY_REFERENCE_MS = 2000
COST_REFERENCE_PER_1K = 0.010


@dataclass
class ScoredModel:
    model_id: str
    display_name: str
    provider: str
    total_score: float
    strength_score: float
    reasoning_score: float
    latency_score: float
    cost_score: float


class RoutingEngine:
    """Deterministic, capability-aware model selector."""

    def __init__(self) -> None:
        self._registry = get_model_registry_2026()

    def select(
        self,
        category: str,
        *,
        required_tags: Optional[Set[str]] = None,
        min_context: int = 0,
        require_tools: bool = False,
        top_n: int = 1,
    ) -> List[ScoredModel]:
        """Select the best model(s) for a category.

        In BENCHMARK_MODE, returns the locked elite model without scoring.
        """
        if is_benchmark_mode():
            elite_id = ELITE_POLICY.get(category)
            if elite_id:
                entry = self._registry.get(elite_id)
                if entry:
                    return [ScoredModel(
                        model_id=entry.model_id,
                        display_name=entry.display_name,
                        provider=entry.provider,
                        total_score=1.0,
                        strength_score=entry.strength_for_category(category),
                        reasoning_score=entry.reasoning_strength,
                        latency_score=1.0,
                        cost_score=1.0,
                    )]
            raise RuntimeError(
                f"Elite model {elite_id} not found in registry for category={category}"
            )

        candidates = self._registry.list_models(available_only=True)

        if required_tags:
            candidates = [
                m for m in candidates
                if required_tags.issubset(set(m.capability_tags))
            ]
        if min_context > 0:
            candidates = [m for m in candidates if m.context_window >= min_context]
        if require_tools:
            candidates = [m for m in candidates if m.supports_tools]

        scored = [self._score(m, category) for m in candidates]
        scored.sort(key=lambda s: s.total_score, reverse=True)
        return scored[:top_n]

    def _score(self, entry: ModelEntry, category: str) -> ScoredModel:
        strength = entry.strength_for_category(category)
        reasoning = entry.reasoning_strength

        latency_inv = max(0.0, 1.0 - entry.latency_profile.p50 / LATENCY_REFERENCE_MS)
        cost_inv = max(0.0, 1.0 - entry.cost_profile.output_per_1k / COST_REFERENCE_PER_1K)

        total = (
            strength * 0.50
            + reasoning * 0.20
            + latency_inv * 0.15
            + cost_inv * 0.15
        )

        return ScoredModel(
            model_id=entry.model_id,
            display_name=entry.display_name,
            provider=entry.provider,
            total_score=round(total, 4),
            strength_score=round(strength, 3),
            reasoning_score=round(reasoning, 3),
            latency_score=round(latency_inv, 3),
            cost_score=round(cost_inv, 3),
        )

    def print_ranking(self, category: str, top_n: int = 5) -> None:
        """Print a human-readable ranking table."""
        scored = self.select(category, top_n=top_n)
        bm = " [BENCHMARK]" if is_benchmark_mode() else ""
        print(f"\n  Routing: {category}{bm}")
        print(f"  {'Rank':<5} {'Model':<20} {'Provider':<12} {'Total':<8} "
              f"{'Str':<7} {'Reas':<7} {'Lat':<7} {'Cost':<7}")
        print("  " + "-" * 73)
        for i, s in enumerate(scored, 1):
            print(f"  {i:<5} {s.model_id:<20} {s.provider:<12} "
                  f"{s.total_score:<8.4f} {s.strength_score:<7.3f} "
                  f"{s.reasoning_score:<7.3f} {s.latency_score:<7.3f} "
                  f"{s.cost_score:<7.3f}")
        print()


_engine: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    global _engine
    if _engine is None:
        _engine = RoutingEngine()
    return _engine
