"""Provider for the OpenRouter aggregation API."""

from __future__ import annotations

from typing import Mapping

from .openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Expose OpenRouter's OpenAI-compatible endpoint via the shared provider base."""

    _BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        headers = {
            "HTTP-Referer": "https://github.com/llmhive/llmhive",
            "X-Title": "LLMHive",
        }
        if extra_headers:
            headers.update(dict(extra_headers))

        super().__init__(
            api_key,
            base_url=self._BASE_URL,
            extra_headers=headers,
        )
