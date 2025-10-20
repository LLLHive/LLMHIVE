"""Health endpoint tests."""


def test_health_endpoint(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "providers" in payload
    providers = payload["providers"]
    assert providers["stub"]["status"] == "available"
    assert "default_models" in payload
