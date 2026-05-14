"""Tests for optional chat document uploads (GCS)."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from llmhive.app.main import app


@pytest.fixture
def client_upload_not_configured(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "0")
    monkeypatch.delenv("LLMHIVE_CHAT_UPLOAD_BUCKET", raising=False)
    with TestClient(app) as c:
        yield c


def test_upload_chat_document_returns_503_when_bucket_unset(
    client_upload_not_configured: TestClient,
) -> None:
    files = {"file": ("note.pdf", io.BytesIO(b"%PDF-1.4 minimal"), "application/pdf")}
    data = {"user_id": "user_test_uploads_1"}
    r = client_upload_not_configured.post(
        "/v1/uploads/chat-document",
        files=files,
        data=data,
    )
    assert r.status_code == 503
    body = r.json()
    assert body["detail"]["error"] == "upload_not_configured"
