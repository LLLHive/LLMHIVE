"""Adapter for Anthropic models."""
from __future__ import annotations

import asyncio
from typing import Any

from ...core.errors import ProviderNotConfiguredError
from ...core.settings import settings
from .base import BaseLLMAdapter, GenerationParams, LLMResult


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic adapter stub used for orchestration tests."""

    def __init__(self) -> None:
        super().__init__("anthropic:claude-3-opus")

    @property
    def is_available(self) -> bool:  # noqa: D401 - inherited description
        return settings.anthropic_api_key is not None

    async def generate(self, prompt: str, params: GenerationParams) -> LLMResult:
        if not self.is_available:
            raise ProviderNotConfiguredError("Anthropic credentials missing", context={"adapter": self.name})

        await asyncio.sleep(0.05)
        text = f"[Anthropic simulated answer]: {prompt[:80]}"
        tokens = min(len(prompt) // 5 + 60, params.max_tokens)
        cost = tokens / 1000 * 0.0006
        metadata: dict[str, Any] = {"temperature": params.temperature, "simulated": True}
        return LLMResult(
            text=text,
            tokens=tokens,
            latency_ms=55.0,
            cost_usd=cost,
            model_name=self.name,
            metadata=metadata,
        )
