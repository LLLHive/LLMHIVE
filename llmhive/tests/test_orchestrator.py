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
        # Stub provider returns informative responses
        assert len(result.content) > 0


@pytest.mark.asyncio
async def test_orchestrator_infers_models_when_only_stub_available() -> None:
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=7)})
    artifacts = await orchestrator.orchestrate("Summarize the role of pollinators in ecosystems.")

    assert artifacts.initial_responses, "Expected at least one draft response"
    returned_models = {result.model for result in artifacts.initial_responses}
    # The orchestrator should fall back to the stub model when no real providers exist.
    assert "stub-v1" in returned_models
    assert artifacts.final_response.content
