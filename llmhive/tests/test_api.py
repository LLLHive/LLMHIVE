"""API tests for orchestration endpoint."""
from llmhive.app.config import settings
from llmhive.app.schemas import OrchestrationRequest


def test_orchestrate_endpoint(client):
    payload = OrchestrationRequest(prompt="List benefits of solar power", models=["stub-model-a", "stub-model-b"])
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == payload.prompt
    assert len(data["initial_responses"]) == 2
    assert data["final_response"]
    assert isinstance(data["critiques"], list)
    assert isinstance(data["improvements"], list)


def test_orchestrate_endpoint_uses_default_models(client):
    payload = {"prompt": "Summarize the benefits of electric vehicles."}
    response = client.post("/api/v1/orchestration/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == payload["prompt"]
    assert len(data["initial_responses"]) == len(settings.default_models)
    assert sorted(data["models"]) == sorted(settings.default_models)
