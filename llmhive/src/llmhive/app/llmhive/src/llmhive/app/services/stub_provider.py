"""Deterministic stub provider for development and testing."""
from __future__ import annotations

import asyncio
import random
from typing import List, AsyncIterator

from .base import LLMProvider, LLMResult


class StubProvider(LLMProvider):
    """Simple provider that fabricates plausible responses."""

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)

    async def _sleep(self) -> None:
        await asyncio.sleep(self.random.uniform(0.01, 0.05))

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        await self._sleep()
        content = f"[{model}] Response to: {prompt}"[:1500]
        return LLMResult(content=content, model=model)

    async def critique(self, subject: str, *, target_answer: str, author: str, model: str) -> LLMResult:
        await self._sleep()
        feedback = f"{author} suggests clarifying details about '{subject[:48]}...'"
        return LLMResult(content=feedback, model=author)

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: List[str],
        model: str,
    ) -> LLMResult:
        await self._sleep()
        critique_text = "; ".join(critiques) or "No critiques."
        content = f"Improved by {model}: {previous_answer} (considering: {critique_text})"
        return LLMResult(content=content[:1500], model=model)

    def list_models(self) -> list[str]:
        """Return the single stub model name."""
        return ["stub"]

    async def stream_response(
        self,
        prompt: str,
        *,
        model: str,
    ) -> AsyncIterator[str]:
        """Yield the full stub response as a single chunk."""
        result = await self.complete(prompt, model=model)
        yield result.content
