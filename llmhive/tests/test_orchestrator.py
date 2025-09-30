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
