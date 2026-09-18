"""Regression tests for Sentry production issues.

Covers:
1. Synthetic fallback-* model IDs must never be passed through as OpenRouter slugs
   (issue: OpenRouter 400 for fallback-router-chain-for-openai/gpt-4o-mini).
2. Elite empty content must fail closed rather than succeed with "".
"""
from __future__ import annotations

import pytest

from llmhive.app.services.orchestrator_adapter import _map_model_to_provider


def test_map_model_strips_fallback_router_chain_tag():
    recovered = _map_model_to_provider(
        "fallback-router-chain-for-openai/gpt-4o-mini",
        available_providers=["openrouter"],
    )
    assert recovered == "openai/gpt-4o-mini"
    assert not recovered.startswith("fallback-")


def test_map_model_strips_direct_fallback_tag():
    recovered = _map_model_to_provider(
        "fallback-direct-Together.ai-for-openai/gpt-4o",
        available_providers=["openrouter"],
    )
    assert recovered == "openai/gpt-4o"


def test_map_model_passthrough_real_openrouter_slug():
    assert (
        _map_model_to_provider("openai/gpt-4o", available_providers=["openrouter"])
        == "openai/gpt-4o"
    )
    assert (
        _map_model_to_provider(
            "google/gemini-2.5-pro", available_providers=["openrouter"]
        )
        == "google/gemini-2.5-pro"
    )


@pytest.mark.asyncio
async def test_elite_call_model_rejects_empty_content():
    from llmhive.app.orchestration.elite_orchestrator import EliteOrchestrator

    class _EmptyProvider:
        async def complete(self, prompt, model=None, **kwargs):
            class R:
                content = ""
                text = ""
                tokens_used = 0

            return R()

    elite = EliteOrchestrator.__new__(EliteOrchestrator)
    elite.providers = {"openrouter": _EmptyProvider()}
    elite.model_providers = {"openai/gpt-4o": "openrouter"}

    with pytest.raises(ValueError, match="Empty response"):
        await elite._call_model("openai/gpt-4o", "hello")
