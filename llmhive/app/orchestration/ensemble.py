"""Ensemble execution utilities."""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from itertools import cycle
from typing import Dict, List

from .adapters import AdapterRegistry
from .adapters.base import BaseLLMAdapter, GenerationParams, LLMResult
from .equalizer import OrchestrationProfile
from .prompt_opt import PromptPlan
from .routing import ModelRoute


@dataclass
class EnsembleOutput:
    """Normalized representation of a model response."""

    model_name: str
    text: str
    tokens: int
    latency_ms: float
    cost_usd: float
    score_quality: float
    score_factuality: float
    metadata: Dict[str, float] = field(default_factory=dict)


class EnsembleRunner:
    """Execute multiple model calls asynchronously and aggregate results."""

    def __init__(self, registry: AdapterRegistry | None = None) -> None:
        self.registry = registry or AdapterRegistry()

    async def run(
        self,
        plan: PromptPlan,
        routes: List[ModelRoute],
        profile: OrchestrationProfile,
    ) -> List[EnsembleOutput]:
        """Run the ensemble generation given routing decisions."""

        tasks: List[asyncio.Task[EnsembleOutput]] = []
        samples_per_model = max(1, math.ceil(profile.num_samples / max(1, len(routes))))
        variant_cycle = cycle(plan.competing_variants or [plan.core_prompt])

        for route in routes:
            adapter = self._resolve_adapter(route.name)
            params = GenerationParams(
                temperature=route.params.get("temperature", 0.2),
                top_p=route.params.get("top_p", 0.9),
                max_tokens=route.params.get("max_tokens", profile.max_tokens),
                n_samples=samples_per_model,
                json_mode=profile.json_mode,
            )
            for _ in range(samples_per_model):
                variant_prompt = next(variant_cycle)
                prompt = f"{plan.core_prompt}\n\nVariant: {variant_prompt}"
                tasks.append(
                    asyncio.create_task(self._execute(adapter, prompt, params, route))
                )

        outputs = await asyncio.gather(*tasks)
        return outputs

    def _resolve_adapter(self, name: str) -> BaseLLMAdapter:
        adapter = self.registry.get(name)
        if adapter and (adapter.is_available or adapter.name.startswith("local:")):
            return adapter
        fallback = self.registry.get("local:llama-3-8b")
        if fallback is None:
            raise RuntimeError("Local adapter missing")
        return fallback

    async def _execute(
        self,
        adapter: BaseLLMAdapter,
        prompt: str,
        params: GenerationParams,
        route: ModelRoute,
    ) -> EnsembleOutput:
        result: LLMResult = await adapter.generate(prompt, params)
        quality = self._estimate_quality(result, route)
        factuality = self._estimate_factuality(result, route)
        metadata = {
            "temperature": params.temperature,
            "route_weight": route.weight,
            **{k: v for k, v in result.metadata.items() if isinstance(v, (int, float))},
        }
        return EnsembleOutput(
            model_name=result.model_name,
            text=result.text,
            tokens=result.tokens,
            latency_ms=result.latency_ms,
            cost_usd=result.cost_usd,
            score_quality=quality,
            score_factuality=factuality,
            metadata=metadata,
        )

    def _estimate_quality(self, result: LLMResult, route: ModelRoute) -> float:
        base = 0.55 + route.weight * 0.3
        richness = min(0.1, len(result.text) / 1000)
        return max(0.0, min(1.0, base + richness))

    def _estimate_factuality(self, result: LLMResult, route: ModelRoute) -> float:
        base = 0.6 + route.weight * 0.2
        return max(0.0, min(1.0, base - 0.05 * route.params.get("temperature", 0.2)))
