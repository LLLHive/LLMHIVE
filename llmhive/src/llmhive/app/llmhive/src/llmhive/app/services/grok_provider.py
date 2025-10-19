"""Grok provider implementation.

This provider acts as a shim around the OpenAIProvider to expose
models offered by xAI's Grok system.
"""
from __future__ import annotations

from typing import AsyncIterator

from .base import LLMProvider, LLMResult
from .openai_provider import OpenAIProvider


class GrokProvider(LLMProvider):
    """Interact with xAI's Grok models via the OpenAI provider."""

    def __init__(self, api_key: str | None = None, timeout: float | None = None) -> None:
        self.provider = OpenAIProvider(api_key=api_key, timeout=timeout)
        self.models: list[str] = ["grok-1"]

    def list_models(self) -> list[str]:
        return self.models

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        return await self.provider.complete(prompt, model=model)

    async def critique(self, subject: str, *, target_answer: str, author: str, model: str) -> LLMResult:
        return await self.provider.critique(subject, target_answer=target_answer, author=author, model=model)

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: list[str],
        model: str,
    ) -> LLMResult:
        return await self.provider.improve(subject, previous_answer=previous_answer, critiques=critiques, model=model)

    async def stream_response(self, prompt: str, *, model: str) -> AsyncIterator[str]:
        async for chunk in self.provider.stream_response(prompt, model=model):
            yield chunk
