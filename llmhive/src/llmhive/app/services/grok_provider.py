"""Grok provider implementation for xAI's API with lazy imports.

This module defers importing the OpenAI client (which Grok uses via 
OpenAI-compatible API) until the provider is initialized. This ensures
that a missing dependency fails cleanly by raising 
`ProviderNotConfiguredError`, allowing the orchestrator to fall back 
to the stub provider instead of crashing the application.
"""
from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    # These imports are for type checking only
    try:
        from openai.types.chat import ChatCompletion  # type: ignore
    except Exception:
        pass

from ..config import settings
from .base import LLMProvider, LLMResult, ProviderNotConfiguredError


class GrokProvider(LLMProvider):
    """Interact with xAI's Grok models via OpenAI-compatible API.

    Grok uses an OpenAI-compatible API interface, so we use the OpenAI
    client library pointed at xAI's base URL. This provider lazily imports
    the OpenAI client to avoid crashing applications where the `openai` 
    library is not installed or is incompatible.
    """

    def __init__(self, api_key: str | None = None, timeout: float | None = None) -> None:
        # Attempt to import the OpenAI client when instantiating the provider
        try:
            from openai import AsyncOpenAI  # type: ignore
        except Exception as exc:
            raise ProviderNotConfiguredError(
                f"OpenAI library import failed (required for Grok): {exc}. "
                "Install a compatible 'openai' package or remove Grok models from your configuration."
            ) from exc

        key = api_key or getattr(settings, "grok_api_key", None)
        if not key:
            raise ProviderNotConfiguredError("Grok API key is missing.")
        
        # Grok uses OpenAI-compatible API at api.x.ai
        self.client = AsyncOpenAI(
            api_key=key,
            base_url="https://api.x.ai/v1",
            timeout=timeout or getattr(settings, "grok_timeout_seconds", 45.0)
        )

    async def _chat(self, messages: List[Dict[str, str]], *, model: str) -> LLMResult:
        try:
            completion = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
            )
        except Exception as exc:
            # Convert any network or API error to provider error
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
            {"role": "system", "content": "You are Grok, an expert assistant working in a collaborative AI team."},
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
                    "You are reviewing another AI's answer. Be concise and point out factual errors, "
                    "missing information, and opportunities to improve the response."
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
                    "Provide constructive critique of the previous answer. Address accuracy, completeness, "
                    "and clarity."
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
                    "You are improving your previous answer after receiving critiques from peer models. "
                    "Incorporate actionable feedback and provide a stronger final answer."
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
