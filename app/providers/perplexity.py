"""Perplexity.ai provider."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class PerplexityProvider(OpenAICompatibleProvider):
    """Provide access to Perplexity's reasoning models."""

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key, base_url="https://api.perplexity.ai")
