"""Tests for synthesis-stage fallback to the stub provider."""

from __future__ import annotations

import asyncio

from llmhive.app.orchestrator import Orchestrator
from llmhive.app.services.base import (
    LLMProvider,
    LLMResult,
    ProviderNotConfiguredError,
)
from llmhive.app.services.stub_provider import StubProvider


class FailingProvider:
    """Provider stub that always raises to simulate misconfiguration."""

    def list_models(self) -> list[str]:
        return ["gpt-4o"]

    async def complete(self, prompt: str, *, model: str) -> LLMResult:  # pragma: no cover - interface requirement
        raise ProviderNotConfiguredError("simulated failure")

    async def critique(
        self,
        subject: str,
        *,
        target_answer: str,
        author: str,
        model: str,
    ) -> LLMResult:  # pragma: no cover - interface requirement
        raise ProviderNotConfiguredError("simulated failure")

    async def improve(
        self,
        subject: str,
        *,
        previous_answer: str,
        critiques: list[str],
        model: str,
    ) -> LLMResult:  # pragma: no cover - interface requirement
        raise ProviderNotConfiguredError("simulated failure")


def test_orchestrator_falls_back_to_stub_when_synthesis_provider_fails() -> None:
    providers: dict[str, LLMProvider] = {
        "openai": FailingProvider(),
        "stub": StubProvider(seed=1234),
    }
    orchestrator = Orchestrator(providers=providers)

    artifacts = asyncio.run(
        orchestrator.orchestrate(
            "What is the capital of Spain?",
            models=["gpt-4o"],
        )
    )

    assert "Madrid" in artifacts.final_response.content
    assert artifacts.final_response.model == "stub-fallback(gpt-4o)"
