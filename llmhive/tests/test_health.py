"""Health endpoint tests."""


def test_health_endpoint(client, monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "abc1234")
    monkeypatch.setenv("K_SERVICE", "llmhive-orchestrator")
    monkeypatch.setenv("K_REVISION", "llmhive-orchestrator-00001")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "llmhive-orchestrator")

    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "providers" in payload
    providers = payload["providers"]
    assert providers["stub"]["status"] == "available"
    assert "default_models" in payload
    deployment = payload["deployment"]
    assert deployment["git_commit"] == "abc1234"
    assert deployment["cloud_run"]["service"] == "llmhive-orchestrator"
    assert deployment["cloud_run"]["revision"] == "llmhive-orchestrator-00001"
    assert deployment["cloud_run"]["project"] == "llmhive-orchestrator"
