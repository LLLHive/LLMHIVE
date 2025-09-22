"""Adapter for Azure OpenAI deployments."""
from __future__ import annotations

import asyncio
from typing import Any

from ...core.errors import ProviderNotConfiguredError
from ...core.settings import settings
from .base import BaseLLMAdapter, GenerationParams, LLMResult


class AzureAdapter(BaseLLMAdapter):
    """Azure OpenAI adapter stub."""

    def __init__(self) -> None:
        super().__init__("azure:gpt-4o")

    @property
    def is_available(self) -> bool:  # noqa: D401
        return settings.azure_openai_api_key is not None and settings.azure_openai_endpoint is not None

    async def generate(self, prompt: str, params: GenerationParams) -> LLMResult:
        if not self.is_available:
            raise ProviderNotConfiguredError("Azure OpenAI credentials missing", context={"adapter": self.name})

        await asyncio.sleep(0.05)
        text = f"[Azure simulated answer]: {prompt[:85]}"
        tokens = min(len(prompt) // 5 + 65, params.max_tokens)
        cost = tokens / 1000 * 0.00055
        metadata: dict[str, Any] = {"temperature": params.temperature, "simulated": True}
        return LLMResult(
            text=text,
            tokens=tokens,
            latency_ms=58.0,
            cost_usd=cost,
            model_name=self.name,
            metadata=metadata,
        )
