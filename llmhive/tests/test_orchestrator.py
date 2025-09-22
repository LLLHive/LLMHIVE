import pytest

from llmhive.app.orchestration.orchestrator import OrchestrationOptions, Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_run_produces_confident_answer():
    orchestrator = Orchestrator()
    options = OrchestrationOptions(
        accuracy=0.6,
        speed=0.4,
        creativity=0.5,
        cost=0.5,
        max_tokens=400,
    )
    result = await orchestrator.run("Explain test-time scaling in LLM ensembles", options)
    assert result.final_answer
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.key_points, list)
    assert isinstance(result.timings, dict)
