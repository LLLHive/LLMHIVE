"""Tests ensuring GPT-4 requests gracefully fall back to the stub provider."""
from llmhive.app.api.orchestration import MODEL_ALIAS_MAP
from llmhive.app.schemas import OrchestrationRequest


def _canonical(model: str) -> str:
    return MODEL_ALIAS_MAP.get(model.lower(), model)


def test_gpt4_with_stub_provider(client):
    """Test that gpt-4 can be used with stub provider when OpenAI is not configured."""
    payload = OrchestrationRequest(
        prompt="What is the capital of Spain?",
        models=["gpt-4"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == payload.prompt
    expected_model = _canonical("gpt-4")
    assert data["models"] == [expected_model]
    assert len(data["initial_responses"]) == 1
    assert data["initial_responses"][0]["model"] == expected_model
    # Stub provider now returns actual answers for common questions
    assert "Madrid" in data["initial_responses"][0]["content"]


def test_multiple_models_with_stub_provider(client):
    """Test that multiple models can use stub provider when real providers are not configured."""
    payload = OrchestrationRequest(
        prompt="Explain quantum computing",
        models=["gpt-4", "gpt-3.5-turbo", "claude-3"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 3
    expected_models = {_canonical("gpt-4"), _canonical("gpt-3.5-turbo"), _canonical("claude-3")}
    assert set(data["models"]) == expected_models
    assert len(data["initial_responses"]) == 3
    # All should use stub provider
    for resp in data["initial_responses"]:
        # Stub provider returns informative responses (either answers or stub message)
        assert len(resp["content"]) > 0


def test_mixed_stub_and_explicit_stub_models(client):
    """Test mixing models that fall back to stub with explicitly named stub models."""
    payload = OrchestrationRequest(
        prompt="Test prompt",
        models=["gpt-4", "stub-model-a"]
    )
    response = client.post("/api/v1/orchestration/", json=payload.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) == 2
    assert len(data["initial_responses"]) == 2
