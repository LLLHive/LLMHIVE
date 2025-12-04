"""Tests for the chat API bridge to FastAPI backend."""
from llmhive.app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


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
    response = client.post("/v1/chat", json=payload)
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
    response = client.post("/v1/chat", json=payload)
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
    response = client.post("/v1/chat", json=payload)
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
