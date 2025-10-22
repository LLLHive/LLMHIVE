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
    assert data["final_provider"] == "stub"
    assert {item["provider"] for item in data["initial_responses"]} == {"stub"}
    assert {item["provider"] for item in data["improvements"]} == {"stub"}


def test_orchestrate_rejects_unconfigured_models(client):
    stub_orchestrator = Orchestrator(providers={"stub": StubProvider(seed=7)})
    client.app.dependency_overrides[get_orchestrator] = lambda: stub_orchestrator

    response = client.post(
        "/api/v1/orchestration/",
        json={"prompt": "Explain gravity", "models": ["gpt-4"]},
    )

    client.app.dependency_overrides.pop(get_orchestrator, None)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "models" in detail
    assert detail["models"] == ["gpt-4"]
    assert "providers" in detail


def test_orchestrate_raises_when_stub_used_for_real_model(client):
    stub = StubProvider(seed=42)
    orchestrator = Orchestrator(providers={"stub": stub})
    client_dependency = lambda: orchestrator
    client.app.dependency_overrides[get_orchestrator] = client_dependency

    payload = OrchestrationRequest(prompt="Hi", models=["stub-model"])
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())
    assert response.status_code == 200

    response = client.post(
        "/api/v1/orchestration/",
        json={"prompt": "Hi", "models": ["stub-model", "gpt-4"]},
    )

    client.app.dependency_overrides.pop(get_orchestrator, None)

    assert response.status_code == 400
    assert response.json()["detail"]["models"] == ["gpt-4"]


def test_providers_endpoint_lists_stub_provider(client):
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=3)})
    client.app.dependency_overrides[get_orchestrator] = lambda: orchestrator

    response = client.get("/api/v1/providers/")

    client.app.dependency_overrides.pop(get_orchestrator, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["stub_only"] is True
    assert payload["real_providers"] == []
    assert "stub" in payload["available_providers"]
    assert payload["unavailable_providers"] == []
    assert payload["providers"]["stub"]["stub"] is True
    assert payload["fail_on_stub"] is False


def test_orchestrate_raises_503_when_stub_responses_disallowed(client, monkeypatch):
    monkeypatch.setenv("FAIL_ON_STUB_RESPONSES", "1")

    from llmhive.app.config import reset_settings_cache

    reset_settings_cache()
    get_orchestrator.cache_clear()

    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=9)})
    client.app.dependency_overrides[get_orchestrator] = lambda: orchestrator

    try:
        response = client.post(
            "/api/v1/orchestration/",
            json={"prompt": "Ping", "models": ["stub-model"]},
        )
    finally:
        client.app.dependency_overrides.pop(get_orchestrator, None)
        monkeypatch.setenv("FAIL_ON_STUB_RESPONSES", "0")
        reset_settings_cache()
        get_orchestrator.cache_clear()

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["models"] == ["stub-model"]
    assert "Stub provider responses are disabled" in detail["message"]
