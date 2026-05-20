"""Orchestrator-facing Mistral provider (wraps catalog client)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .mistral_client import get_mistral_client

logger = logging.getLogger(__name__)

ORCHESTRATION_KWARGS = frozenset({
    "use_hrm", "use_adaptive_routing", "use_deep_consensus",
    "use_prompt_diffusion", "use_memory", "accuracy_level",
    "session_id", "user_id", "user_tier", "enable_tools",
    "knowledge_snippets", "context", "plan", "db_session",
    "skip_injection_check", "history", "max_tokens", "temperature",
})


class MistralProvider:
    """Thin adapter so Orchestrator.providers['mistral'] can call Mistral direct."""

    name = "mistral"

    def __init__(self) -> None:
        self._client = get_mistral_client()
        if not self._client:
            raise ValueError("MISTRAL_API_KEY not set")

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        api_kwargs = {k: v for k, v in kwargs.items() if k not in ORCHESTRATION_KWARGS}
        max_tokens = int(api_kwargs.pop("max_tokens", 2048))
        temperature = float(api_kwargs.pop("temperature", 0.7))
        slug = model or "mistralai/mistral-small-3.1-24b-instruct:free"
        text = await self._client.generate(
            prompt,
            slug,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        native = self._client.resolve_model(slug)

        class Result:
            def __init__(self, content: str, model_id: str, tokens: int = 0):
                self.content = content
                self.text = content
                self.model = model_id
                self.tokens_used = tokens

        return Result(text, native)

    async def complete(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        return await self.generate(prompt, model=model, **kwargs)
