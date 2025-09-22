from fastapi.testclient import TestClient

from llmhive.app.main import app


client = TestClient(app)


def test_orchestrate_endpoint_returns_response():
    payload = {
        "query": "Summarize the benefits of using async orchestration.",
        "options": {"accuracy": 0.7, "speed": 0.5, "creativity": 0.4, "cost": 0.6},
    }
    response = client.post("/api/v1/orchestrate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "final_answer" in data
    assert data["confidence"] >= 0.0
    assert not any(tag in data["final_answer"].lower() for tag in ["openai", "anthropic", "azure", "google"])
    assert data["citations"] == [] or isinstance(data["citations"], list)
