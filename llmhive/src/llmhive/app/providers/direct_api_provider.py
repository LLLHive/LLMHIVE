"""Unified orchestrator adapters for direct API clients (catalog + Groq/Cerebras)."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Protocol

logger = logging.getLogger(__name__)

ORCHESTRATION_KWARGS = frozenset({
    "use_hrm", "use_adaptive_routing", "use_deep_consensus",
    "use_prompt_diffusion", "use_memory", "accuracy_level",
    "session_id", "user_id", "user_tier", "enable_tools",
    "knowledge_snippets", "context", "plan", "db_session",
    "skip_injection_check", "history", "max_tokens", "temperature",
})


class _GenerateClient(Protocol):
    async def generate_with_retry(
        self, prompt: str, model: str, **kwargs: Any
    ) -> Optional[str]: ...


def _result(text: str, model_id: str):
    class Result:
        def __init__(self, content: str, mid: str, tokens: int = 0):
            self.content = content
            self.text = content
            self.model = mid
            self.tokens_used = tokens

    return Result(text, model_id)


class CatalogAPIProvider:
    """Wraps a CatalogClient for Orchestrator.providers[key]."""

    def __init__(self, name: str, client: _GenerateClient, default_slug: str):
        self.name = name
        self._client = client
        self._default_slug = default_slug

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        api_kwargs = {k: v for k, v in kwargs.items() if k not in ORCHESTRATION_KWARGS}
        slug = model or self._default_slug
        text = await self._client.generate_with_retry(prompt, slug, **api_kwargs)
        if not text:
            raise RuntimeError(f"{self.name}: empty response for {slug}")
        native = slug
        if hasattr(self._client, "resolve_model"):
            native = self._client.resolve_model(slug)
        return _result(text, native)

    async def complete(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        return await self.generate(prompt, model=model, **kwargs)


class RetryClientProvider:
    """Wraps clients with generate_with_retry(prompt, model) only."""

    def __init__(self, name: str, client: _GenerateClient, default_slug: str):
        self.name = name
        self._client = client
        self._default_slug = default_slug

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        api_kwargs = {k: v for k, v in kwargs.items() if k not in ORCHESTRATION_KWARGS}
        slug = model or self._default_slug
        text = await self._client.generate_with_retry(prompt, slug, **api_kwargs)
        if not text:
            raise RuntimeError(f"{self.name}: empty response for {slug}")
        native = slug
        if hasattr(self._client, "_get_native_model_id"):
            native = self._client._get_native_model_id(slug)
        return _result(text, native)

    async def complete(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        return await self.generate(prompt, model=model, **kwargs)


def build_provider(
    name: str,
    getter: Callable[[], Optional[Any]],
    *,
    default_slug: str,
    catalog: bool = True,
) -> Optional[CatalogAPIProvider | RetryClientProvider]:
    client = getter()
    if not client:
        return None
    if catalog:
        return CatalogAPIProvider(name, client, default_slug)
    return RetryClientProvider(name, client, default_slug)
