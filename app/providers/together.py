"""Together AI provider."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class TogetherProvider(OpenAICompatibleProvider):
    """Interact with Together AI's hosted models."""

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key, base_url="https://api.together.xyz/v1")
