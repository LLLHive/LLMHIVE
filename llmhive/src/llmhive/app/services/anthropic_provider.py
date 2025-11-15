"""Anthropic provider implementation for Claude models with lazy imports.

This module defers importing the Anthropic client until the provider is
initialized. Importing the library at module import time can cause
container start failures if the `anthropic` package is missing or
incompatible. Moving imports inside `__init__` ensures that a missing
dependency fails cleanly by raising `ProviderNotConfiguredError`,
allowing the orchestrator to fall back to the stub provider instead
of crashing the application.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports are for type checking only
    try:
        from anthropic.types import Message  # type: ignore
    except Exception:
        pass

from ..config import settings
from .base import LLMProvider, LLMResult, ProviderNotConfiguredError


class AnthropicProvider(LLMProvider):
    """Interact with Anthropic Claude chat models.

    This provider lazily imports the Anthropic client to avoid crashing
    applications where the `anthropic` library is not installed or is
    incompatible. If the import fails, the constructor will raise
    `ProviderNotConfiguredError` to signal that this provider cannot
    be used, allowing the orchestrator to fall back to another provider.
    """

    def __init__(self, api_key: str | None = None, timeout: float | None = None) -> None:
        # Attempt to import the Anthropic client when instantiating the provider
        try:
            from anthropic import AsyncAnthropic  # type: ignore
        except Exception as exc:
            raise ProviderNotConfiguredError(
                f"Anthropic library import failed: {exc}. "
                "Install 'anthropic' package or remove Anthropic models from your configuration."
            ) from exc

        key = api_key or getattr(settings, "anthropic_api_key", None)
        if not key:
            raise ProviderNotConfiguredError("Anthropic API key is missing.")
        
        self.client = AsyncAnthropic(
            api_key=key,
            timeout=timeout or getattr(settings, "anthropic_timeout_seconds", 45.0)
        )
        self._models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    def list_models(self) -> list[str]:
        return list(self._models)

    async def _chat(self, messages: list[dict[str, str]], *, model: str, system: str | None = None) -> LLMResult:
        try:
            # Anthropic API uses a different format - separate system message
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0.6,
                system=system or "You are a helpful assistant.",
                messages=messages,
            )
        except Exception as exc:
            # Convert any network or API error to provider error
            raise ProviderNotConfiguredError(str(exc)) from exc
        
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        
        return LLMResult(
            content=content,
            model=model,
            tokens=response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
            cost=None,
        )

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        messages = [
            {"role": "user", "content": prompt},
        ]
        return await self._chat(
            messages, 
            model=model,
            system="You are an expert assistant working in a collaborative AI team."
        )

    async def critique(
        self,
        subject: str,
        *,
        target_answer: str,
        author: str,
        model: str,
    ) -> LLMResult:
        messages = [
            {"role": "user", "content": subject},
            {"role": "assistant", "content": target_answer},
            {
                "role": "user",
                "content": (
                    "Provide constructive critique of the previous answer. Address accuracy, completeness, "
                    "and clarity."
                ),
            },
        ]
        result = await self._chat(
            messages, 
            model=model,
            system=(
                "You are reviewing another AI's answer. Be concise and point out factual errors, "
                "missing information, and opportunities to improve the response."
            )
        )
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
            {"role": "user", "content": subject},
            {"role": "assistant", "content": previous_answer},
            {
                "role": "user",
                "content": (
                    "Refine your answer using these critiques:\n" + critique_text + "\nReturn the improved answer."
                ),
            },
        ]
        return await self._chat(
            messages, 
            model=model,
            system=(
                "You are improving your previous answer after receiving critiques from peer models. "
                "Incorporate actionable feedback and provide a stronger final answer."
            )
        )
