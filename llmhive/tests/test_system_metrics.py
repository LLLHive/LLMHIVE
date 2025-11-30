from fastapi.testclient import TestClient

from llmhive.app.main import app


client = TestClient(app)


def test_model_metrics_endpoint():
    response = client.get("/api/v1/system/model-metrics")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], dict)


