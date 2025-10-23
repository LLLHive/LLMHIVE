"""Health endpoint tests."""

def test_root_health_endpoint(client):
    """Test the root /healthz endpoint required by Cloud Run."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_endpoint(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_duplicate_health_endpoint_removed(client):
    """Verify that the duplicate /api/v1/api/v1/healthz endpoint is removed."""
    response = client.get("/api/v1/api/v1/healthz")
    assert response.status_code == 404
