"""OpenAI provider implementation."""
from __future__ import annotations

from typing import Dict, List

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..config import settings
from .base import LLMProvider, LLMResult, ProviderNotConfiguredError


class OpenAIProvider(LLMProvider):
    """Interact with OpenAI chat completion models."""

    def __init__(self, api_key: str | None = None, timeout: float | None = None) -> None:
        key = api_key or settings.openai_api_key
        if not key:
            raise ProviderNotConfiguredError("OpenAI API key is missing.")
        self.client = AsyncOpenAI(api_key=key, timeout=timeout or settings.openai_timeout_seconds)

    async def _chat(self, messages: List[Dict[str, str]], *, model: str) -> LLMResult:
        try:
            completion: ChatCompletion = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
            )
        except Exception as exc:  # pragma: no cover - network errors
            raise ProviderNotConfiguredError(str(exc)) from exc
        choice = completion.choices[0]
        usage = completion.usage or None
        return LLMResult(
            content=choice.message.content or "",
            model=model,
            tokens=usage.total_tokens if usage else None,
            cost=None,
        )

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        messages = [
            {"role": "system", "content": "You are an expert assistant working in a collaborative AI team."},
            {"role": "user", "content": prompt},
        ]
        return await self._chat(messages, model=model)

    async def critique(self, subject: str, *, target_answer: str, author: str, model: str) -> LLMResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are reviewing another AI's answer. Be concise and point out factual errors,"
                    " missing information, and opportunities to improve the response."
                ),
            },
            {"role": "user", "content": subject},
            {
                "role": "assistant",
                "content": target_answer,
            },
            {
                "role": "user",
                "content": (
                    "Provide constructive critique of the previous answer. Address accuracy, completeness,"
                    " and clarity."
                ),
            },
        ]
        result = await self._chat(messages, model=model)
        result.model = author
        return result

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: list[str],
        model: str,
    ) -> LLMResult:
        critique_text = "\n".join(f"- {item}" for item in critiques) or "No critiques provided."
        messages = [
            {
                "role": "system",
                "content": (
                    "You are improving your previous answer after receiving critiques from peer models."
                    " Incorporate actionable feedback and provide a stronger final answer."
                ),
            },
            {"role": "user", "content": subject},
            {
                "role": "assistant",
                "content": previous_answer,
            },
            {
                "role": "user",
                "content": (
                    "Refine your answer using these critiques:\n" + critique_text + "\nReturn the improved answer."
                ),
            },
        ]
        return await self._chat(messages, model=model)
