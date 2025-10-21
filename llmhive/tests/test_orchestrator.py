"""Unit tests for the orchestrator workflow."""
import asyncio

import pytest

from llmhive.app.orchestrator import Orchestrator
from llmhive.app.services.base import ProviderNotConfiguredError
from llmhive.app.services.stub_provider import StubProvider
from llmhive.app.schemas import OrchestrationRequest


def test_orchestrator_generates_all_stages() -> None:
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=42)})
    artifacts = asyncio.run(
        orchestrator.orchestrate("Explain the water cycle.", ["stub-model-a", "stub-model-b"])
    )

    assert len(artifacts.initial_responses) == 2
    assert artifacts.critiques, "Expected critiques to be generated"
    assert len(artifacts.improvements) == 2
    assert artifacts.final_response.content
    for result in artifacts.initial_responses:
        assert "Response" in result.content


def test_provider_status_reports_availability() -> None:
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=123)})
    status = orchestrator.provider_status()
    assert status == {
        "stub": {"status": "available", "provider": "StubProvider"},
    }

    orchestrator.provider_errors["openai"] = "Missing API key"
    status = orchestrator.provider_status()
    assert status["openai"]["status"] == "unavailable"
    assert "Missing API key" in status["openai"]["error"]


def test_orchestrator_allows_explicit_stub_aliases() -> None:
    orchestrator = Orchestrator(
        providers={"stub": StubProvider(seed=7)},
        model_aliases={"stub-debug": "stub-gpt-4"},
    )

    artifacts = asyncio.run(orchestrator.orchestrate("Test alias support", ["stub-debug"]))

    assert artifacts.initial_responses[0].model == "stub-debug"
    assert "stub-debug" in artifacts.final_response.content


def test_orchestrator_blocks_stub_fallback_for_real_models() -> None:
    orchestrator = Orchestrator(
        providers={"stub": StubProvider(seed=21)},
        model_aliases={"gpt-4": "stub-gpt-4"},
    )

    with pytest.raises(ProviderNotConfiguredError) as excinfo:
        asyncio.run(orchestrator.orchestrate("Prevent silent fallback", ["GPT-4"]))

    assert "Stub provider" in str(excinfo.value)


def test_orchestrator_raises_when_provider_missing() -> None:
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=11)})

    with pytest.raises(ProviderNotConfiguredError) as excinfo:
        asyncio.run(orchestrator.orchestrate("Need GPT", ["gpt-4"]))

    assert "OpenAI provider is not configured" in str(excinfo.value)


def test_orchestration_endpoint_returns_503_when_provider_missing(client) -> None:
    response = client.post(
        "/api/v1/orchestration/",
        json={"prompt": "Test", "models": ["gpt-4"]},
    )

    assert response.status_code == 503
    payload = response.json()["detail"]
    assert "OpenAI provider is not configured" in payload["message"]
    assert "providers" in payload


def test_orchestration_request_splits_models() -> None:
    request = OrchestrationRequest(
        prompt="Capital?",
        models=["Grock, GPT-4 , GPT-3.5", "   stub-debug  "],
    )

    assert request.models == ["Grock", "GPT-4", "GPT-3.5", "stub-debug"]
