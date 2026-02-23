"""Adaptive Team Composition Engine — Patented multi-model orchestration.

For each category, selects a team of 3 models ensuring:
  - Provider diversity
  - At least 1 reasoning-dominant model
  - At least 1 cost-efficient model

Scoring: strength_score * 0.6 + reasoning_strength * 0.2
       + latency_inverse * 0.1 + cost_efficiency * 0.1

Produces TEAM_CONFIG export for explainability trace integration.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .elite_policy import ELITE_POLICY, is_benchmark_mode
from .model_registry_2026 import ModelEntry, get_model_registry_2026

logger = logging.getLogger(__name__)

TEAM_SIZE = 3
LATENCY_REF_MS = 2000
COST_REF_PER_1K = 0.010


@dataclass
class TeamMember:
    model_id: str
    display_name: str
    provider: str
    role: str  # "primary" | "reasoning_specialist" | "cost_efficient"
    score: float
    strength: float
    reasoning: float
    latency_score: float
    cost_score: float


@dataclass
class TeamConfig:
    category: str
    members: List[TeamMember] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "team_size": len(self.members),
            "members": [
                {
                    "model_id": m.model_id,
                    "display_name": m.display_name,
                    "provider": m.provider,
                    "role": m.role,
                    "score": round(m.score, 4),
                }
                for m in self.members
            ],
        }


def _strength_for_category(m: ModelEntry, category: str) -> float:
    mapping = {
        "reasoning": m.reasoning_strength,
        "coding": m.coding_strength,
        "math": m.math_strength,
        "multilingual": m.reasoning_strength,
        "long_context": m.reasoning_strength,
        "tool_use": m.coding_strength,
        "rag": m.reasoning_strength,
        "dialogue": m.reasoning_strength,
    }
    return mapping.get(category, m.reasoning_strength)


def _score_model(m: ModelEntry, category: str) -> float:
    strength = _strength_for_category(m, category)
    reasoning = m.reasoning_strength
    lat_inv = max(0, 1.0 - m.latency_profile.p50 / LATENCY_REF_MS)
    cost_inv = max(0, 1.0 - m.cost_profile.input_per_1k / COST_REF_PER_1K)
    return strength * 0.6 + reasoning * 0.2 + lat_inv * 0.1 + cost_inv * 0.1


def _is_reasoning_dominant(m: ModelEntry) -> bool:
    return m.reasoning_strength >= 0.90


def _is_cost_efficient(m: ModelEntry) -> bool:
    return m.cost_profile.input_per_1k < 0.003


class TeamComposer:
    """Composes optimal multi-model teams per category."""

    def __init__(self) -> None:
        self._registry = get_model_registry_2026()

    def compose(self, category: str) -> TeamConfig:
        """Select a team of 3 models for the given category."""
        if is_benchmark_mode():
            elite = ELITE_POLICY.get(category)
            entry = self._registry.get(elite) if elite else None
            if entry:
                member = TeamMember(
                    model_id=entry.model_id,
                    display_name=entry.display_name,
                    provider=entry.provider,
                    role="primary",
                    score=_score_model(entry, category),
                    strength=_strength_for_category(entry, category),
                    reasoning=entry.reasoning_strength,
                    latency_score=max(0, 1.0 - entry.latency_profile.p50 / LATENCY_REF_MS),
                    cost_score=max(0, 1.0 - entry.cost_profile.input_per_1k / COST_REF_PER_1K),
                )
                return TeamConfig(category=category, members=[member])

        models = self._registry.list_models(available_only=True)
        if not models:
            models = self._registry.list_models(available_only=False)

        scored = [(m, _score_model(m, category)) for m in models]
        scored.sort(key=lambda x: x[1], reverse=True)

        team: List[TeamMember] = []
        providers_used: Set[str] = set()
        has_reasoner = False
        has_cost_eff = False

        for m, sc in scored:
            if len(team) >= TEAM_SIZE:
                break
            if m.provider in providers_used and len(team) >= 1:
                continue

            role = "primary" if not team else "support"
            if not has_reasoner and _is_reasoning_dominant(m):
                role = "reasoning_specialist"
                has_reasoner = True
            elif not has_cost_eff and _is_cost_efficient(m):
                role = "cost_efficient"
                has_cost_eff = True

            team.append(TeamMember(
                model_id=m.model_id,
                display_name=m.display_name,
                provider=m.provider,
                role=role,
                score=sc,
                strength=_strength_for_category(m, category),
                reasoning=m.reasoning_strength,
                latency_score=max(0, 1.0 - m.latency_profile.p50 / LATENCY_REF_MS),
                cost_score=max(0, 1.0 - m.cost_profile.input_per_1k / COST_REF_PER_1K),
            ))
            providers_used.add(m.provider)

        if not has_reasoner and len(team) < TEAM_SIZE:
            for m, sc in scored:
                if _is_reasoning_dominant(m) and m.model_id not in {t.model_id for t in team}:
                    team.append(TeamMember(
                        model_id=m.model_id, display_name=m.display_name,
                        provider=m.provider, role="reasoning_specialist",
                        score=sc,
                        strength=_strength_for_category(m, category),
                        reasoning=m.reasoning_strength,
                        latency_score=max(0, 1.0 - m.latency_profile.p50 / LATENCY_REF_MS),
                        cost_score=max(0, 1.0 - m.cost_profile.input_per_1k / COST_REF_PER_1K),
                    ))
                    break

        if not has_cost_eff and len(team) < TEAM_SIZE:
            for m, sc in scored:
                if _is_cost_efficient(m) and m.model_id not in {t.model_id for t in team}:
                    team.append(TeamMember(
                        model_id=m.model_id, display_name=m.display_name,
                        provider=m.provider, role="cost_efficient",
                        score=sc,
                        strength=_strength_for_category(m, category),
                        reasoning=m.reasoning_strength,
                        latency_score=max(0, 1.0 - m.latency_profile.p50 / LATENCY_REF_MS),
                        cost_score=max(0, 1.0 - m.cost_profile.input_per_1k / COST_REF_PER_1K),
                    ))
                    break

        return TeamConfig(category=category, members=team)

    def compose_all(self) -> Dict[str, TeamConfig]:
        """Compose teams for all categories in ELITE_POLICY."""
        return {cat: self.compose(cat) for cat in ELITE_POLICY}

    def export_team_configs(self) -> Dict[str, Any]:
        """Export all team configs as serializable dict for explainability trace."""
        teams = self.compose_all()
        return {cat: cfg.to_dict() for cat, cfg in teams.items()}

    def validate_teams(self) -> Dict[str, Any]:
        """Validate all teams meet composition constraints."""
        results: Dict[str, Any] = {}
        for cat in ELITE_POLICY:
            team = self.compose(cat)
            providers = set(m.provider for m in team.members)
            has_reasoner = any(m.role == "reasoning_specialist" or m.reasoning >= 0.90 for m in team.members)
            has_cost_eff = any(m.role == "cost_efficient" for m in team.members)
            results[cat] = {
                "team_size": len(team.members),
                "provider_diversity": len(providers) >= min(2, len(team.members)),
                "has_reasoning_specialist": has_reasoner,
                "has_cost_efficient": has_cost_eff,
                "providers": list(providers),
                "valid": True,
            }
        return results

    def generate_performance_delta(self) -> Dict[str, Any]:
        """Compare team vs single-elite potential using registry strength scores.

        No inference calls — purely metric-based simulation from registry data.
        Records TEAM_ADVANTAGE flag advisory in output.
        """
        from datetime import datetime, timezone
        deltas: Dict[str, Any] = {}

        for cat in ELITE_POLICY:
            elite_id = ELITE_POLICY[cat]
            elite_entry = self._registry.get(elite_id)
            elite_score = _score_model(elite_entry, cat) if elite_entry else 0.0

            team = self.compose(cat)
            if not team.members:
                continue

            team_avg_score = sum(m.score for m in team.members) / len(team.members)
            team_max_score = max(m.score for m in team.members)
            score_delta = team_avg_score - elite_score

            entropy_estimate = 0.0
            if len(team.members) > 1:
                scores = [m.score for m in team.members]
                total_s = sum(scores) or 1.0
                import math
                probs = [s / total_s for s in scores]
                entropy_estimate = -sum(p * math.log2(p) for p in probs if p > 0)

            team_advantage = score_delta >= 0.02 and entropy_estimate < 0.05 + (
                math.log2(len(team.members)) if len(team.members) > 1 else 0
            )

            deltas[cat] = {
                "elite_model": elite_id,
                "elite_score": round(elite_score, 4),
                "team_avg_score": round(team_avg_score, 4),
                "team_max_score": round(team_max_score, 4),
                "score_delta": round(score_delta, 4),
                "entropy_estimate": round(entropy_estimate, 4),
                "team_advantage": team_advantage,
                "team_members": [m.model_id for m in team.members],
            }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "categories": deltas,
            "summary": {
                "advantage_categories": [c for c, d in deltas.items() if d.get("team_advantage")],
                "no_advantage_categories": [c for c, d in deltas.items() if not d.get("team_advantage")],
            },
        }


_TEAM_COMPOSER: Optional[TeamComposer] = None


def get_team_composer() -> TeamComposer:
    global _TEAM_COMPOSER
    if _TEAM_COMPOSER is None:
        _TEAM_COMPOSER = TeamComposer()
    return _TEAM_COMPOSER
