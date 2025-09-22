"""Adapter for OpenAI's completion APIs."""
from __future__ import annotations

import asyncio
from typing import Any

from ...core.errors import ProviderNotConfiguredError
from ...core.settings import settings
from .base import BaseLLMAdapter, GenerationParams, LLMResult


class OpenAIAdapter(BaseLLMAdapter):
    """Minimal OpenAI adapter that defers to the HTTP API when configured."""

    def __init__(self) -> None:
        super().__init__("openai:gpt-4o-mini")

    @property
    def is_available(self) -> bool:  # noqa: D401 - short description inherits
        return settings.openai_api_key is not None

    async def generate(self, prompt: str, params: GenerationParams) -> LLMResult:
        if not self.is_available:
            raise ProviderNotConfiguredError("OpenAI credentials missing", context={"adapter": self.name})

        # Placeholder implementation: simulate latency and produce deterministic text.
        await asyncio.sleep(0.05)
        text = f"[OpenAI simulated answer]: {prompt[:100]}"
        tokens = min(len(prompt) // 4 + 50, params.max_tokens)
        cost = tokens / 1000 * 0.0005
        metadata: dict[str, Any] = {"temperature": params.temperature, "simulated": True}
        return LLMResult(
            text=text,
            tokens=tokens,
            latency_ms=50.0,
            cost_usd=cost,
            model_name=self.name,
            metadata=metadata,
        )
