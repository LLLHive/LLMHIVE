"""Grok provider for the lightweight runtime."""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from app.models.llm_provider import LLMProvider as _BaseProvider
else:  # pragma: no cover - runtime placeholder avoids circular import
    class _BaseProvider:  # type: ignore[too-many-ancestors]
        pass

from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger("app.providers.grok")


class GrokProvider(OpenAICompatibleProvider):
    """Interact with xAI's Grok models via the OpenAI-compatible API."""

    _BASE_URL = "https://api.x.ai/v1"

    def __init__(self, api_key: str, *, temperature: float = 0.6) -> None:
        self._temperature = temperature
        super().__init__(
            api_key,
            base_url=self._BASE_URL,
            default_params={"temperature": temperature},
        )

    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs: Any) -> str:
        # Ensure per-request overrides are merged with the default temperature.
        kwargs.setdefault("temperature", kwargs.get("temperature", self._temperature))
        return await super().generate(messages, model, **kwargs)

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        kwargs.setdefault("temperature", kwargs.get("temperature", self._temperature))
        async for chunk in super().generate_stream(messages, model, **kwargs):
            yield chunk
