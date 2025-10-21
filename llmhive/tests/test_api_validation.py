"""Validation-focused tests for the orchestration API."""

from llmhive.app.api.orchestration import get_orchestrator
from llmhive.app.orchestrator import Orchestrator
from llmhive.app.services.stub_provider import StubProvider


def test_models_with_commas_are_normalized(client):
    orchestrator = Orchestrator(providers={"stub": StubProvider(seed=99)})
    client.app.dependency_overrides[get_orchestrator] = lambda: orchestrator

    response = client.post(
        "/api/v1/orchestration/",
        json={"prompt": "Diagnose", "models": ["grok, GPT-4"]},
    )

    client.app.dependency_overrides.pop(get_orchestrator, None)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert sorted(detail["models"]) == ["GPT-4", "grok"]
    assert "message" in detail
