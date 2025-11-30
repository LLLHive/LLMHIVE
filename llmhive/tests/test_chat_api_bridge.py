from llmhive.app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_orchestration_endpoint_integration():
    """Smoke test that the orchestration API returns the extended fields."""
    payload = {"prompt": "Explain the role of pollinators in ecosystems."}
    response = client.post("/api/v1/orchestration/", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Core fields
    assert "prompt" in data
    assert "final_response" in data
    # New metadata fields
    assert "fact_check" in data
    assert "refinement_rounds" in data
    assert "accepted_after_refinement" in data


