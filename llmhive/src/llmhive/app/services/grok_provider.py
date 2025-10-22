"""Grok provider implementation using the OpenAI-compatible client."""
from __future__ import annotations

from typing import Dict, List

from ..config import settings
from .base import LLMProvider, LLMResult, ProviderNotConfiguredError


class GrokProvider(LLMProvider):
    """Interact with xAI's Grok models using the OpenAI-compatible API surface."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise ProviderNotConfiguredError(
                "OpenAI client import failed. Install the 'openai' package to use the Grok provider."
            ) from exc

        key = api_key or settings.grok_api_key
        if not key:
            raise ProviderNotConfiguredError("Grok API key is missing.")

        self.client = AsyncOpenAI(
            api_key=key,
            base_url=base_url or settings.grok_base_url,
            timeout=timeout or settings.grok_timeout_seconds,
        )

    async def _chat(self, messages: List[Dict[str, str]], *, model: str) -> LLMResult:
        try:
            completion = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
            )
        except Exception as exc:
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
            {"role": "system", "content": "You are an expert assistant representing xAI's Grok model."},
            {"role": "user", "content": prompt},
        ]
        return await self._chat(messages, model=model)

    async def critique(
        self,
        subject: str,
        *,
        target_answer: str,
        author: str,
        model: str,
    ) -> LLMResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are reviewing another AI's answer on behalf of Grok. Provide constructive, factual critique."
                ),
            },
            {"role": "user", "content": subject},
            {"role": "assistant", "content": target_answer},
            {
                "role": "user",
                "content": "Critique the previous answer, focusing on accuracy, completeness, and clarity.",
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
                    "You are improving your previous Grok answer after receiving critiques."
                    " Incorporate actionable feedback and respond comprehensively."
                ),
            },
            {"role": "user", "content": subject},
            {"role": "assistant", "content": previous_answer},
            {
                "role": "user",
                "content": "Refine your answer using these critiques:\n" + critique_text + "\nReturn the improved answer.",
            },
        ]
        return await self._chat(messages, model=model)
