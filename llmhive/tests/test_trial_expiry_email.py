"""Unit tests for trial-expiry email helper (no network)."""
from __future__ import annotations

from unittest.mock import patch

from llmhive.app.services.email import send_trial_expiring_email


def test_trial_expiring_email_subject_and_cta():
    with patch("llmhive.app.services.email._post_email") as post:
        post.return_value = {"sent": True, "id": "msg_test"}
        result = send_trial_expiring_email(
            to="user@example.com",
            customer_name="Alex Rivera",
            trial_end_iso="2026-09-20T18:00:00+00:00",
            price_monthly_usd=10,
        )
        assert result["sent"] is True
        kwargs = post.call_args.kwargs
        assert kwargs["to"] == "user@example.com"
        assert "ends tomorrow" in kwargs["subject"]
        assert "$10/month" in kwargs["subject"]
        assert "Continue for $10/month" in kwargs["html"]
        assert "/billing" in kwargs["html"]
        assert "2026-09-20" in kwargs["text"]


def test_trial_expiring_email_requires_recipient():
    result = send_trial_expiring_email(to="")
    assert result["skipped"] is True
    assert result["reason"] == "no_recipient"
