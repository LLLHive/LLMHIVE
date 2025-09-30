"""Health endpoint tests."""

def test_health_endpoint(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
