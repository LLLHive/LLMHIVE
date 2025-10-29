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
    assert "Follow these directives" in data["optimized_prompt"]
    assert isinstance(data["knowledge_hits"], list)
    assert isinstance(data["web_results"], list)
    assert isinstance(data["confirmation"], list)
    assert isinstance(data["quality"], list)
    assert data["usage"]["response_count"] >= 1
    assert isinstance(data["usage"]["per_model"], dict)


def test_orchestrate_endpoint_uses_default_models(client):
    payload = {"prompt": "Summarize the benefits of electric vehicles."}
    response = client.post("/api/v1/orchestration/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == payload["prompt"]
    assert len(data["initial_responses"]) == len(settings.default_models)
    assert sorted(data["models"]) == sorted(settings.default_models)
    assert data["optimized_prompt"]


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
    assert data["confirmation"], "Confirmation layer should emit guidance"
    assert data["usage"]["response_count"] >= 1


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


def test_orchestrate_endpoint_handles_empty_initial_responses(monkeypatch, client):
    """If every upstream provider fails, the API should still return 200 with stub synthesis."""

    from llmhive.app.api import orchestration as orchestration_api
    from llmhive.app.orchestrator import Orchestrator
    from llmhive.app.services.base import LLMProvider, LLMResult, ProviderNotConfiguredError

    class _FailingProvider(LLMProvider):
        def list_models(self) -> list[str]:
            return ["gpt-4o"]

        async def complete(self, prompt: str, *, model: str) -> LLMResult:  # pragma: no cover - raising path
            raise ProviderNotConfiguredError("simulated failure")

        async def critique(
            self,
            subject: str,
            *,
            target_answer: str,
            author: str,
            model: str,
        ) -> LLMResult:  # pragma: no cover - raising path
            raise ProviderNotConfiguredError("simulated failure")

        async def improve(
            self,
            subject: str,
            *,
            previous_answer: str,
            critiques: list[str],
            model: str,
        ) -> LLMResult:  # pragma: no cover - raising path
            raise ProviderNotConfiguredError("simulated failure")

    orchestrator = Orchestrator(providers={"openai": _FailingProvider()})
    monkeypatch.setattr(orchestration_api, "_orchestrator", orchestrator)

    payload = OrchestrationRequest(prompt="What is the capital of Spain?", models=["gpt-4o"])
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    # All upstream calls failed, so no initial responses were produced.
    assert data["initial_responses"] == []
    # Stub synthesis still produces the correct answer for common prompts.
    assert "Madrid" in data["final_response"]
    assert data["usage"]["response_count"] >= 1
