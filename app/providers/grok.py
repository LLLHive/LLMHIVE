"""Grok provider for the lightweight runtime."""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from app.models.llm_provider import LLMProvider as _BaseProvider
else:  # pragma: no cover - runtime placeholder avoids circular import
    class _BaseProvider:  # type: ignore[too-many-ancestors]
        pass

try:  # pragma: no cover - optional dependency for local dev
    from openai import AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover - handled gracefully at runtime
    AsyncOpenAI = None  # type: ignore

logger = logging.getLogger("app.providers.grok")


class GrokProvider(_BaseProvider):
    """Interact with xAI's Grok models via the OpenAI-compatible API."""

    _BASE_URL = "https://api.x.ai/v1"

    def __init__(self, api_key: str, *, temperature: float = 0.6) -> None:
        if not AsyncOpenAI:
            raise ImportError("The 'openai' package is required to use the Grok provider.")
        if not api_key:
            raise ValueError("Grok API key must be provided.")

        self._client = AsyncOpenAI(api_key=api_key, base_url=self._BASE_URL)
        self._temperature = temperature

    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs: Any) -> str:
        try:
            completion = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=kwargs.get("temperature", self._temperature),
            )
        except Exception as exc:  # pragma: no cover - network failure surface
            logger.warning("Grok generate request failed: %s", exc)
            return f"Error: Could not get response from {model}."

        return completion.choices[0].message.content or ""

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=kwargs.get("temperature", self._temperature),
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as exc:  # pragma: no cover
            logger.warning("Grok streaming request failed: %s", exc)
            yield f"Error: Could not stream from {model}."
