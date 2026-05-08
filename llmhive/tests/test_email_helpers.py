"""Tests for ``llmhive.app.services.email`` (Resend HTTP client).

We don't hit Resend during tests. We mock ``httpx.post`` and assert:

- When ``RESEND_API_KEY`` is unset, the helper short-circuits and returns
  ``{"sent": False, "skipped": True}`` without making a network call.
- When ``RESEND_API_KEY`` is set, the helper POSTs the expected payload
  (recipient, subject, multipart body) to the Resend endpoint.
- HTTP errors are caught and returned, never raised, so webhook callers
  can stay 2xx for Stripe.
"""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import patch

import pytest

from llmhive.app.services import email as email_module


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: Dict[str, Any] | None = None, text: str = "{}"):
        self.status_code = status_code
        self._payload = payload or {"id": "msg_abc123"}
        self.text = text

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_payment_failed_email_skips_when_api_key_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with patch.object(email_module.httpx, "post") as mock_post:
        result = email_module.send_payment_failed_email(
            to="user@example.com",
            customer_name="Test User",
        )

    assert result == {"sent": False, "skipped": True, "reason": "no_api_key"}
    mock_post.assert_not_called()


def test_payment_failed_email_posts_when_api_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_xyz")
    monkeypatch.setenv("EMAIL_FROM", "LLMHive <test@llmhive.ai>")

    with patch.object(
        email_module.httpx, "post", return_value=_FakeResponse(200)
    ) as mock_post:
        result = email_module.send_payment_failed_email(
            to="user@example.com",
            customer_name="Test User",
            invoice_url="https://stripe.example/invoice/abc",
        )

    assert result["sent"] is True
    assert result["id"] == "msg_abc123"
    mock_post.assert_called_once()
    _, call_kwargs = mock_post.call_args
    body = call_kwargs["json"]
    assert body["from"] == "LLMHive <test@llmhive.ai>"
    assert body["to"] == "user@example.com"
    assert "payment failed" in body["subject"].lower()
    assert "https://stripe.example/invoice/abc" in body["html"]
    assert "https://stripe.example/invoice/abc" in body["text"]
    assert call_kwargs["headers"]["Authorization"] == "Bearer re_test_xyz"


def test_payment_failed_email_returns_error_on_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_xyz")

    with patch.object(
        email_module.httpx,
        "post",
        return_value=_FakeResponse(422, payload={}, text="bad recipient"),
    ):
        result = email_module.send_payment_failed_email(to="bad@example.com")

    assert result["sent"] is False
    assert result["status_code"] == 422
    assert "bad recipient" in result["error"]


def test_payment_failed_email_swallows_network_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_xyz")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("connection refused")

    with patch.object(email_module.httpx, "post", side_effect=_boom):
        result = email_module.send_payment_failed_email(to="user@example.com")

    assert result["sent"] is False
    assert "connection refused" in result["error"]


def test_payment_failed_email_no_recipient_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_xyz")
    with patch.object(email_module.httpx, "post") as mock_post:
        result = email_module.send_payment_failed_email(to="")
    assert result == {"sent": False, "skipped": True, "reason": "no_recipient"}
    mock_post.assert_not_called()


def test_subscription_cancelled_email_includes_period_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_xyz")

    with patch.object(
        email_module.httpx, "post", return_value=_FakeResponse(200)
    ) as mock_post:
        result = email_module.send_subscription_cancelled_email(
            to="user@example.com",
            customer_name="Test User",
            period_end_iso="2026-12-01",
        )

    assert result["sent"] is True
    body = mock_post.call_args.kwargs["json"]
    assert "2026-12-01" in body["html"]
    assert "2026-12-01" in body["text"]


def test_subscription_cancelled_email_skips_with_no_recipient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test_xyz")
    with patch.object(email_module.httpx, "post") as mock_post:
        result = email_module.send_subscription_cancelled_email(to=None)  # type: ignore[arg-type]
    assert result == {"sent": False, "skipped": True, "reason": "no_recipient"}
    mock_post.assert_not_called()
