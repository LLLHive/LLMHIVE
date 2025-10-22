"""Manus provider implementation.

This provider serves as a placeholder for Manus models. Currently it
delegates to the OpenAIProvider but advertises Manus model identifiers.
"""
from __future__ import annotations

from typing import AsyncIterator

from .base import LLMProvider, LLMResult
from .openai_provider import OpenAIProvider


class ManusProvider(LLMProvider):
    """Interact with Manus models via the OpenAI provider."""

    def __init__(self, api_key: str | None = None, timeout: float | None = None) -> None:
        self.provider = OpenAIProvider(api_key=api_key, timeout=timeout)
        self.models: list[str] = ["manus"]

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
