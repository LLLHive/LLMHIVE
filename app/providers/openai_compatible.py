"""Reusable helpers for providers that expose an OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Mapping, MutableMapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from app.models.llm_provider import LLMProvider as _BaseProvider
else:  # pragma: no cover - runtime placeholder avoids circular import
    class _BaseProvider:  # type: ignore[too-many-ancestors]
        pass

try:  # pragma: no cover - dependency is optional in some environments
    from openai import AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover - handled gracefully at runtime
    AsyncOpenAI = None  # type: ignore

logger = logging.getLogger("app.providers.openai_compatible")


def _merge_dict(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of *base* updated with non-null values from *overrides*."""

    merged: Dict[str, Any] = dict(base)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged


class OpenAICompatibleProvider(_BaseProvider):
    """Base implementation for APIs that mirror OpenAI's chat completions schema."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str,
        default_params: Optional[Mapping[str, Any]] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        if not AsyncOpenAI:
            raise ImportError("The 'openai' package is required to use this provider.")
        if not api_key:
            raise ValueError("An API key is required to initialise the provider.")

        headers: MutableMapping[str, str] | None = None
        if extra_headers:
            headers = dict(extra_headers)

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=headers)
        self._default_params = dict(default_params or {})

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> str:
        params = _merge_dict(self._default_params, kwargs)
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                **params,
            )
        except Exception as exc:  # pragma: no cover - network failures mocked in tests
            logger.warning("OpenAI-compatible generate request failed: %s", exc)
            return f"Error: Could not get response from {model}."

        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        params = _merge_dict(self._default_params, kwargs)
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                **params,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as exc:  # pragma: no cover - best-effort streaming
            logger.warning("OpenAI-compatible streaming request failed: %s", exc)
            yield f"Error: Could not stream from {model}."
