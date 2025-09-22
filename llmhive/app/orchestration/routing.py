"""Dynamic model routing and selection logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .equalizer import OrchestrationProfile
from .memory import MemoryStore
from .prompt_opt import PromptPlan


@dataclass
class ModelRoute:
    """Represents a model candidate selected for execution."""

    name: str
    weight: float
    params: Dict[str, float]


class Router:
    """Select models based on performance history and prompt context."""

    DEFAULT_CANDIDATES: List[str] = [
        "openai:gpt-4o-mini",
        "anthropic:claude-3-opus",
        "google:gemini-1.5-pro",
        "azure:gpt-4o",
        "local:llama-3-8b",
    ]

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self._fallback_candidates = [
            "local:llama-3-8b",
            "openai:gpt-4o-mini",
        ]

    def select_models(self, plan: PromptPlan, profile: OrchestrationProfile) -> List[ModelRoute]:
        """Return a ranked list of model routes."""

        scorecards = {sc.model_name: sc.avg_quality for sc in self.memory.get_scorecards()}

        candidates: List[str] = []
        candidates.extend(self.DEFAULT_CANDIDATES)
        for model_name in scorecards:
            if model_name not in candidates:
                candidates.append(model_name)

        if not candidates:
            candidates = list(self._fallback_candidates)

        routes: List[ModelRoute] = []
        temperature = 0.2 + profile.creativity_boost * 0.6
        for name in candidates:
            base_weight = 0.5
            base_weight += scorecards.get(name, 0.05)
            if "local:" in name and profile.factcheck_enabled:
                base_weight -= 0.05
            if any(keyword in plan.core_prompt.lower() for keyword in ["code", "algorithm"]):
                if "openai" in name or "local" in name:
                    base_weight += 0.1
            routes.append(
                ModelRoute(
                    name=name,
                    weight=max(0.1, min(1.0, base_weight)),
                    params={
                        "temperature": max(0.1, min(1.0, temperature)),
                        "top_p": 0.9,
                        "max_tokens": profile.max_tokens,
                    },
                )
            )

        routes.sort(key=lambda r: r.weight, reverse=True)
        return routes[: profile.num_models]
