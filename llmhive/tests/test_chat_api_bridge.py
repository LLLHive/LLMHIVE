"""Tests for the chat API bridge to FastAPI backend."""
import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from llmhive.app.main import app
from llmhive.app.models.orchestration import (
    AgentMode,
    ChatMetadata,
    ChatResponse,
    DomainPack,
    ReasoningMode,
    TuningOptions,
)

client = TestClient(app)

_PATCH_CHAT_RUN = "llmhive.app.routers.chat.run_orchestration"

# Fixed key so tests pass whether or not the developer machine has API_KEY in the environment.
_CHAT_TEST_KEY = "llmhive-pytest-chat-bridge-key"


@pytest.fixture(autouse=True)
def _chat_bridge_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", _CHAT_TEST_KEY)


def _chat_headers() -> dict[str, str]:
    return {"X-API-Key": _CHAT_TEST_KEY}


def _ci_chat_response(
    *,
    reasoning_mode: ReasoningMode = ReasoningMode.standard,
    agent_mode: AgentMode = AgentMode.single,
) -> ChatResponse:
    """Deterministic response so CI does not call real LLM providers (no API keys)."""
    return ChatResponse(
        message="Synthetic smoke-test response.",
        models_used=["gpt-4o-mini"],
        reasoning_mode=reasoning_mode,
        reasoning_method=None,
        domain_pack=DomainPack.default,
        agent_mode=agent_mode,
        used_tuning=TuningOptions(),
        metadata=ChatMetadata(chat_id="ci-smoke"),
        tokens_used=1,
        latency_ms=1,
        agent_traces=[],
        extra={},
    )


def test_chat_endpoint_integration():
    """Smoke test that the chat API returns expected response format."""
    payload = {
        "prompt": "Explain the role of pollinators in ecosystems.",
        "reasoning_mode": "standard",
        "domain_pack": "default",
        "agent_mode": "single",
        "tuning": {
            "prompt_optimization": True,
            "output_validation": True,
            "answer_structure": True,
            "learn_from_chat": False,
        },
        "orchestration": {
            "accuracy_level": 3,
            "enable_hrm": False,
            "enable_prompt_diffusion": False,
            "enable_deep_consensus": False,
            "enable_adaptive_ensemble": False,
        },
        "metadata": {},
        "history": [],
    }
    with patch(_PATCH_CHAT_RUN, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _ci_chat_response()
        response = client.post("/v1/chat", json=payload, headers=_chat_headers())
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Core ChatResponse fields
    assert "message" in data, "Response should contain 'message' field"
    assert "models_used" in data, "Response should contain 'models_used' field"
    assert "reasoning_mode" in data, "Response should contain 'reasoning_mode' field"
    assert "domain_pack" in data, "Response should contain 'domain_pack' field"
    assert "agent_mode" in data, "Response should contain 'agent_mode' field"
    
    # Optional metadata fields
    assert "latency_ms" in data, "Response should contain 'latency_ms' field"
    assert "extra" in data, "Response should contain 'extra' field"
    
    # Verify message is not empty
    assert len(data["message"]) > 0, "Message should not be empty"


def test_chat_endpoint_with_models():
    """Test chat endpoint with specific models selected."""
    payload = {
        "prompt": "What is 2 + 2?",
        "models": ["gpt-4o-mini"],
        "reasoning_mode": "fast",
        "domain_pack": "default",
        "agent_mode": "single",
        "tuning": {
            "prompt_optimization": False,
            "output_validation": False,
            "answer_structure": False,
            "learn_from_chat": False,
        },
        "orchestration": {
            "accuracy_level": 1,
        },
        "metadata": {},
        "history": [],
    }
    with patch(_PATCH_CHAT_RUN, new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _ci_chat_response(
            reasoning_mode=ReasoningMode.fast,
        )
        response = client.post("/v1/chat", json=payload, headers=_chat_headers())
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "models_used" in data


def test_chat_endpoint_missing_prompt():
    """Test that missing prompt returns appropriate error."""
    payload = {
        "reasoning_mode": "standard",
        "domain_pack": "default",
        "agent_mode": "single",
    }
    response = client.post("/v1/chat", json=payload, headers=_chat_headers())
    # Should return 422 Unprocessable Entity for missing required field
    assert response.status_code == 422


def test_health_endpoints():
    """Test that health check endpoints are working."""
    # Primary health check
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Alias
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # App Engine style
    response = client.get("/_ah/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
