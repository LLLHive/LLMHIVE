"""Base classes and exceptions for LLM providers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ProviderError(Exception):
    """Base exception for provider failures."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a provider lacks credentials or cannot be used."""


@dataclass(slots=True)
class LLMResult:
    """Container for responses returned by providers."""

    content: str
    model: str
    tokens: int | None = None
    cost: float | None = None


class LLMProvider(Protocol):
    """Protocol implemented by provider clients."""

    async def complete(self, prompt: str, *, model: str) -> LLMResult:
        """Generate a response for the supplied prompt."""

    async def critique(self, subject: str, *, target_answer: str, author: str, model: str) -> LLMResult:
        """Return a critique of ``target_answer`` given ``subject``."""

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: list[str],
        model: str,
    ) -> LLMResult:
        """Return an improved answer given critiques."""
