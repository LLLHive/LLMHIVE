"""Model registry and dynamic team selection utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

from .services.base import LLMProvider


@dataclass(slots=True)
class ModelProfile:
    """Metadata describing a model's strengths and operational characteristics."""

    name: str
    provider_key: str
    capabilities: Sequence[str]
    cost_rating: int
    latency_rating: int
    max_context: int
    preferred_roles: Sequence[str]

    def score_for_capabilities(self, requested: Iterable[str]) -> float:
        requested_set = set(requested)
        available = requested_set.intersection(self.capabilities)
        coverage = len(available) / max(len(requested_set), 1)
        # Guard against zero cost/latency values which we use for stub providers.
        # Treat a zero total as "best possible" efficiency instead of raising.
        denominator = self.cost_rating + self.latency_rating
        efficiency = 1.0 / denominator if denominator else 1.0
        return coverage + 0.15 * efficiency


class ModelRegistry:
    """Holds model metadata and provides dynamic selection helpers."""

    def __init__(self, providers: Mapping[str, LLMProvider]):
        self.providers = providers
        self._profiles: List[ModelProfile] = self._bootstrap_profiles()

    def _bootstrap_profiles(self) -> List[ModelProfile]:
        """Return baseline metadata for all supported models."""

        profiles = [
            ModelProfile(
                name="gpt-4.1",
                provider_key="openai",
                capabilities=("reasoning", "coding", "analysis", "synthesis"),
                cost_rating=3,
                latency_rating=3,
                max_context=128_000,
                preferred_roles=("draft", "synthesize"),
            ),
            ModelProfile(
                name="gpt-4o",
                provider_key="openai",
                capabilities=("reasoning", "multimodal", "editing"),
                cost_rating=2,
                latency_rating=2,
                max_context=96_000,
                preferred_roles=("draft", "fact_check"),
            ),
            ModelProfile(
                name="gpt-4o-mini",
                provider_key="openai",
                capabilities=("reasoning", "fast", "editing"),
                cost_rating=1,
                latency_rating=1,
                max_context=32_000,
                preferred_roles=("critique", "fact_check"),
            ),
            ModelProfile(
                name="gpt-3.5-turbo",
                provider_key="openai",
                capabilities=("fast", "chat"),
                cost_rating=1,
                latency_rating=1,
                max_context=16_000,
                preferred_roles=("draft",),
            ),
            ModelProfile(
                name="claude-3-opus-20240229",
                provider_key="anthropic",
                capabilities=("reasoning", "long_context", "writing"),
                cost_rating=3,
                latency_rating=2,
                max_context=200_000,
                preferred_roles=("draft", "synthesize"),
            ),
            ModelProfile(
                name="claude-3-sonnet-20240229",
                provider_key="anthropic",
                capabilities=("reasoning", "analysis", "retrieval"),
                cost_rating=2,
                latency_rating=2,
                max_context=200_000,
                preferred_roles=("research", "draft"),
            ),
            ModelProfile(
                name="claude-3-haiku-20240307",
                provider_key="anthropic",
                capabilities=("fast", "summarization"),
                cost_rating=1,
                latency_rating=1,
                max_context=200_000,
                preferred_roles=("draft", "critique"),
            ),
            ModelProfile(
                name="grok-1",
                provider_key="grok",
                capabilities=("reasoning", "critical_thinking"),
                cost_rating=2,
                latency_rating=2,
                max_context=32_000,
                preferred_roles=("critique", "fact_check"),
            ),
            ModelProfile(
                name="gemini-1.5-pro",
                provider_key="gemini",
                capabilities=("retrieval", "analysis", "multimodal"),
                cost_rating=2,
                latency_rating=2,
                max_context=100_000,
                preferred_roles=("research", "draft"),
            ),
            ModelProfile(
                name="gemini-1.5-flash",
                provider_key="gemini",
                capabilities=("fast", "summarization"),
                cost_rating=1,
                latency_rating=1,
                max_context=100_000,
                preferred_roles=("critique", "fact_check"),
            ),
            ModelProfile(
                name="deepseek-chat",
                provider_key="deepseek",
                capabilities=("fast", "coding", "analysis"),
                cost_rating=1,
                latency_rating=1,
                max_context=32_000,
                preferred_roles=("fact_check", "critique"),
            ),
            ModelProfile(
                name="deepseek-reasoner",
                provider_key="deepseek",
                capabilities=("reasoning", "analysis", "math"),
                cost_rating=1,
                latency_rating=2,
                max_context=64_000,
                preferred_roles=("draft", "critique"),
            ),
            ModelProfile(
                name="manus-gpt-ensemble",
                provider_key="manus",
                capabilities=("reasoning", "aggregation"),
                cost_rating=2,
                latency_rating=2,
                max_context=64_000,
                preferred_roles=("synthesize", "draft"),
            ),
            ModelProfile(
                name="stub-v1",
                provider_key="stub",
                capabilities=("fallback",),
                cost_rating=0,
                latency_rating=0,
                max_context=8_000,
                preferred_roles=("draft",),
            ),
        ]
        return profiles

    def available_profiles(self) -> List[ModelProfile]:
        keys = set(self.providers.keys())
        return [profile for profile in self._profiles if profile.provider_key in keys]

    def suggest_team(self, required_roles: Sequence[str], required_capabilities: Sequence[Sequence[str]]) -> List[str]:
        """Return an ordered list of models covering required roles/capabilities."""

        available = self.available_profiles()
        selected: List[ModelProfile] = []

        for role, capabilities in zip(required_roles, required_capabilities):
            best: ModelProfile | None = None
            best_score = -1.0
            for profile in available:
                if profile in selected:
                    continue
                role_bonus = 0.2 if role in profile.preferred_roles else 0.0
                score = profile.score_for_capabilities(capabilities) + role_bonus
                if score > best_score:
                    best = profile
                    best_score = score
            if best:
                selected.append(best)

        # Ensure at least one model is returned even if no matches found
        if not selected and available:
            selected.append(available[0])

        return [profile.name for profile in selected]

    def summarize(self) -> Dict[str, Dict[str, Sequence[str]]]:
        summary: Dict[str, Dict[str, Sequence[str]]] = {}
        for profile in self.available_profiles():
            summary.setdefault(profile.provider_key, {})[profile.name] = profile.capabilities
        return summary
