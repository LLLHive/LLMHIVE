"""DeepSeek provider implementation."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """Access DeepSeek models via their OpenAI-compatible API."""

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key, base_url="https://api.deepseek.com")
