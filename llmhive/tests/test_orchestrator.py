"""Unit tests for the orchestrator workflow."""
import pytest

from llmhive.app.orchestrator import Orchestrator
from llmhive.app.services.stub_provider import StubProvider


@pytest.mark.asyncio
async def test_orchestrator_generates_all_stages() -> None:
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=42)})
    artifacts = await orchestrator.orchestrate("Explain the water cycle.", ["stub-model-a", "stub-model-b"])

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


@pytest.mark.asyncio
async def test_orchestrator_resolves_model_aliases() -> None:
    orchestrator = Orchestrator(
        providers={"stub": StubProvider(seed=7)},
        model_aliases={"gpt-4": "gpt-4o-mini"},
    )

    artifacts = await orchestrator.orchestrate("Test alias support", ["GPT-4"])

    assert artifacts.initial_responses[0].model == "GPT-4"
    assert "GPT-4" in artifacts.final_response.content
