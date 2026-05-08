"""Test that ``/healthz`` echoes build identity for ops verification."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from llmhive.app.main import app

    return TestClient(app)


def test_healthz_minimum_payload(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """When no build env vars are set, /healthz still returns status=ok."""
    monkeypatch.delenv("BUILD_COMMIT", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.delenv("K_REVISION", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)

    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "commit" not in body
    assert "revision" not in body


def test_healthz_includes_commit_and_revision(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """When Cloud Run injects build env, /healthz surfaces them (truncated)."""
    monkeypatch.setenv("BUILD_COMMIT", "abcdef0123456789abcdef0123456789abcdef01")
    monkeypatch.setenv("K_REVISION", "llmhive-orchestrator-00042-abc")
    monkeypatch.setenv("K_SERVICE", "llmhive-orchestrator")

    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["commit"] == "abcdef012345"
    assert body["revision"] == "llmhive-orchestrator-00042-abc"
    assert body["service"] == "llmhive-orchestrator"


def test_healthz_falls_back_to_git_sha(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """If BUILD_COMMIT is unset, GIT_SHA is used."""
    monkeypatch.delenv("BUILD_COMMIT", raising=False)
    monkeypatch.setenv("GIT_SHA", "deadbeefcafe1234")

    response = client.get("/healthz")
    body = response.json()
    assert body["commit"] == "deadbeefcafe"
