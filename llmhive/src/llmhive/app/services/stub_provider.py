"""Deterministic stub provider for development and testing."""
from __future__ import annotations

import asyncio
import random
from typing import List

from .base import LLMProvider, LLMResult, ProviderNotConfiguredError


class StubProvider(LLMProvider):
    """Simple provider that fabricates plausible responses."""

    def __init__(self, seed: int | None = None, *, allow_real_model_names: bool = False) -> None:
        self.random = random.Random(seed)
        self.allow_real_model_names = allow_real_model_names

    def _ensure_stub_model(self, model: str) -> None:
        """Prevent the stub provider from impersonating real models."""

        if self.allow_real_model_names:
            return
        if "stub" not in model.lower():
            raise ProviderNotConfiguredError(
                "Stub provider cannot serve non-stub model names. Configure a real provider for"
                f" '{model}'."
            )

    async def _sleep(self) -> None:
        await asyncio.sleep(self.random.uniform(0.01, 0.05))

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        self._ensure_stub_model(model)
        await self._sleep()
        content = f"[{model}] Response to: {prompt}"[:1500]
        return LLMResult(content=content, model=model)

    async def critique(self, subject: str, *, target_answer: str, author: str, model: str) -> LLMResult:
        self._ensure_stub_model(author)
        self._ensure_stub_model(model)
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
        self._ensure_stub_model(model)
        await self._sleep()
        critique_text = "; ".join(critiques) or "No critiques."
        content = f"Improved by {model}: {previous_answer} (considering: {critique_text})"
        return LLMResult(content=content[:1500], model=model)
