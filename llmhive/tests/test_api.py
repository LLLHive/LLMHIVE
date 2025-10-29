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


def test_orchestrate_endpoint_strips_invalid_models(client):
    payload = {
        "prompt": "Explain how LLMHive handles orchestration.",
        "models": [" gpt-4o-mini  ", "", "gpt-4o-mini"],
    }

    response = client.post("/api/v1/orchestration/", json=payload)

    assert response.status_code == 200
    data = response.json()
    # Only one unique, non-empty model should remain after normalization
    assert data["models"] == ["gpt-4o-mini"]


def test_orchestrate_endpoint_rejects_missing_models(client):
    payload = {"prompt": "Test", "models": ["", "   "]}

    response = client.post("/api/v1/orchestration/", json=payload)

    assert response.status_code == 400
    assert "No valid model names" in response.json()["detail"]


def test_orchestrate_endpoint_remaps_model_aliases(client):
    payload = {
        "prompt": "List notable OSS LLM orchestrators.",
        "models": ["gpt-4-turbo", "claude-3-opus"],
    }

    response = client.post("/api/v1/orchestration/", json=payload)

    assert response.status_code == 200
    data = response.json()
    returned_models = set(data["models"])

    assert "gpt-4-turbo" not in returned_models
    assert "claude-3-opus" not in returned_models
    assert {"gpt-4o", "claude-3-opus-20240229"}.issubset(returned_models)
