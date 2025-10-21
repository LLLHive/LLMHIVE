"""API tests for orchestration endpoint."""

from llmhive.app.api.orchestration import get_orchestrator
from llmhive.app.orchestrator import Orchestrator
from llmhive.app.schemas import OrchestrationRequest
from llmhive.app.services.stub_provider import StubProvider


def test_orchestrate_endpoint(client):
    stub_orchestrator = Orchestrator(providers={"stub": StubProvider(seed=21)})
    client.app.dependency_overrides[get_orchestrator] = lambda: stub_orchestrator
    payload = OrchestrationRequest(prompt="List benefits of solar power", models=["stub-model-a", "stub-model-b"])
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    client.app.dependency_overrides.pop(get_orchestrator, None)
    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == payload.prompt
    assert len(data["initial_responses"]) == 2
    assert data["final_response"]
    assert isinstance(data["critiques"], list)
    assert isinstance(data["improvements"], list)
