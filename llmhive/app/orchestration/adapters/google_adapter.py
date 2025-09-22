"""Adapter for Google Generative Language models."""
from __future__ import annotations

import asyncio
from typing import Any

from ...core.errors import ProviderNotConfiguredError
from ...core.settings import settings
from .base import BaseLLMAdapter, GenerationParams, LLMResult


class GoogleAdapter(BaseLLMAdapter):
    """Google Gemini adapter stub."""

    def __init__(self) -> None:
        super().__init__("google:gemini-1.5-pro")

    @property
    def is_available(self) -> bool:  # noqa: D401
        return settings.google_api_key is not None

    async def generate(self, prompt: str, params: GenerationParams) -> LLMResult:
        if not self.is_available:
            raise ProviderNotConfiguredError("Google API key missing", context={"adapter": self.name})

        await asyncio.sleep(0.05)
        text = f"[Google simulated answer]: {prompt[:90]}"
        tokens = min(len(prompt) // 5 + 70, params.max_tokens)
        cost = tokens / 1000 * 0.0004
        metadata: dict[str, Any] = {"temperature": params.temperature, "simulated": True}
        return LLMResult(
            text=text,
            tokens=tokens,
            latency_ms=60.0,
            cost_usd=cost,
            model_name=self.name,
            metadata=metadata,
        )
