"""Mistral provider implementation."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    """Access Mistral AI models using their chat completions endpoint."""

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key, base_url="https://api.mistral.ai/v1")
