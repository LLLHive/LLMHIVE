"""Local or OSS model adapter used for development and testing."""
from __future__ import annotations

import asyncio
from typing import Any

from .base import BaseLLMAdapter, GenerationParams, LLMResult


class LocalLLMAdapter(BaseLLMAdapter):
    """Deterministic adapter that simulates a local LLM response."""

    def __init__(self) -> None:
        super().__init__("local:llama-3-8b")

    async def generate(self, prompt: str, params: GenerationParams) -> LLMResult:
        await asyncio.sleep(0.01)
        analysis = self._analyze_prompt(prompt)
        text = f"Local reasoning synthesis: {analysis}"
        tokens = min(len(text) // 3, params.max_tokens)
        metadata: dict[str, Any] = {
            "temperature": params.temperature,
            "analysis": analysis,
            "json_mode": params.json_mode,
        }
        return LLMResult(
            text=text,
            tokens=tokens,
            latency_ms=12.0,
            cost_usd=0.0,
            model_name=self.name,
            metadata=metadata,
        )

    def _analyze_prompt(self, prompt: str) -> str:
        """Produce a concise deterministic summary of the prompt."""

        words = [word.strip().lower() for word in prompt.split() if word.isalpha()]
        unique = sorted(set(words))
        head = ", ".join(unique[:5])
        return f"focus on {head}" if head else "provide clear answer"
