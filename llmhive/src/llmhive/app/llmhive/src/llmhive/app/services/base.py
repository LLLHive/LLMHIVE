"""Base classes and exceptions for LLM providers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, AsyncIterator


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

    def list_models(self) -> list[str]:
        """Return a list of model identifiers supported by this provider.

        Providers should override this method to enumerate all models
        that can be passed to ``complete()``, ``critique()``, and
        ``improve()``. Returning an empty list indicates the provider
        is disabled or not properly configured.
        """
        ...

    async def stream_response(
        self,
        prompt: str,
        *,
        model: str,
    ) -> AsyncIterator[str]:
        """Yield a response as it is generated.

        This method behaves like :meth:`complete` but yields chunks
        of text incrementally as the underlying provider produces
        tokens. Implementations that do not support streaming should
        yield the full response once and then return.
        """
        ...
