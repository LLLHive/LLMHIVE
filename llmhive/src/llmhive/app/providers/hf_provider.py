"""Orchestrator-facing HuggingFace provider (wraps hf_client)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .hf_client import HuggingFaceClient, get_hf_client

logger = logging.getLogger(__name__)

ORCHESTRATION_KWARGS = frozenset({
    "use_hrm", "use_adaptive_routing", "use_deep_consensus",
    "use_prompt_diffusion", "use_memory", "accuracy_level",
    "session_id", "user_id", "user_tier", "enable_tools",
    "knowledge_snippets", "context", "plan", "db_session",
    "skip_injection_check", "history", "max_tokens", "temperature",
})


class HuggingFaceProvider:
    """Thin adapter so Orchestrator.providers['huggingface'] can call HF Inference."""

    name = "huggingface"

    def __init__(self) -> None:
        self._client = get_hf_client()
        if not self._client:
            raise ValueError("HF_TOKEN not set")

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        api_kwargs = {k: v for k, v in kwargs.items() if k not in ORCHESTRATION_KWARGS}
        max_tokens = int(api_kwargs.pop("max_tokens", 2048))
        temperature = float(api_kwargs.pop("temperature", 0.7))
        slug = model or HuggingFaceClient.DEFAULT_MODEL
        text = await self._client.generate_with_retry(
            prompt,
            slug,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if not text:
            raise RuntimeError(f"HuggingFace returned no content for {slug}")
        native = self._client._get_native_model_id(slug)

        class Result:
            def __init__(self, content: str, model_id: str, tokens: int = 0):
                self.content = content
                self.text = content
                self.model = model_id
                self.tokens_used = tokens

        return Result(text, native)

    async def complete(self, prompt: str, model: Optional[str] = None, **kwargs: Any):
        return await self.generate(prompt, model=model, **kwargs)
