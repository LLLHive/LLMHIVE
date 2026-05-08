"""Tests for the Stripe webhook handler's subscription-lifecycle branches.

We don't connect to Stripe or Firestore. Instead we patch:

- ``stripe.Webhook.construct_event`` so signature verification is bypassed and
  we can hand-craft event payloads.
- The ``FirestoreSubscriptionService`` instance returned from
  ``llmhive.app.api.webhooks.get_subscription_service`` so we can inspect what
  the handler tried to write.
- The two email helpers so we assert the handler invokes them with the
  resolved customer email.

What's covered:

- ``customer.subscription.updated`` with ``status=past_due`` updates the
  local subscription status to ``past_due``.
- ``customer.subscription.deleted`` cancels the subscription AND fires the
  cancellation email.
- ``invoice.payment_failed`` flips status to ``past_due`` AND fires the
  payment-failed email with the invoice URL.
- A missing recipient or a Resend failure does not break the webhook
  response (the handler still returns 200 and processed=True).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from llmhive.app.api import webhooks as webhooks_mod


class _FakeService:
    """Minimal stand-in for FirestoreSubscriptionService."""

    def __init__(self, existing: Optional[Dict[str, Any]] = None) -> None:
        self._existing = existing
        self.update_calls: List[Dict[str, Any]] = []
        self.status_updates: List[tuple[str, str]] = []
        self.cancellations: List[str] = []

    def get_subscription_by_stripe_id(self, sid: str) -> Optional[Dict[str, Any]]:
        if self._existing and self._existing.get("stripe_subscription_id") == sid:
            return self._existing
        return None

    def update_subscription(self, sub_id: str, payload: Dict[str, Any]) -> None:
        self.update_calls.append({"id": sub_id, **payload})

    def update_subscription_status(self, sub_id: str, status: str) -> None:
        self.status_updates.append((sub_id, status))

    def cancel_subscription(self, sub_id: str) -> None:
        self.cancellations.append(sub_id)


def _build_request(payload: bytes = b"{}") -> MagicMock:
    """Build a fake Starlette ``Request`` good enough for the webhook handler."""
    request = MagicMock()
    request.headers = {"stripe-signature": "test_signature"}

    async def _body() -> bytes:
        return payload

    request.body = _body
    return request


def _patch_environment(
    monkeypatch: pytest.MonkeyPatch,
    fake_service: _FakeService,
    fake_event: Dict[str, Any],
    *,
    customer_email: str = "user@example.com",
    customer_name: str = "Test User",
    firestore_available: bool = True,
):
    """Wire patches that all webhook tests share."""
    monkeypatch.setattr(
        webhooks_mod,
        "STRIPE_AVAILABLE",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        webhooks_mod, "is_firestore_available", lambda: firestore_available
    )
    monkeypatch.setattr(
        webhooks_mod, "get_subscription_service", lambda: fake_service
    )
    monkeypatch.setattr(
        webhooks_mod.settings, "stripe_webhook_secret", "whsec_test", raising=False
    )

    fake_stripe = MagicMock()
    fake_stripe.Webhook.construct_event = MagicMock(return_value=fake_event)

    fake_customer = MagicMock()
    fake_customer.email = customer_email
    fake_customer.name = customer_name
    fake_stripe.Customer.retrieve = MagicMock(return_value=fake_customer)

    return fake_stripe


@pytest.mark.asyncio
async def test_subscription_updated_past_due_flips_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeService(
        existing={
            "id": "sub_local_1",
            "stripe_subscription_id": "sub_stripe_1",
            "user_id": "user_123",
        }
    )
    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe_1",
                "status": "past_due",
                "current_period_start": 1_780_000_000,
                "current_period_end": 1_790_000_000,
            }
        },
    }
    fake_stripe = _patch_environment(monkeypatch, fake, event)

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = await webhooks_mod.stripe_webhook(_build_request())

    assert result["processed"] is True
    assert result["event_type"] == "customer.subscription.updated"
    assert fake.update_calls and fake.update_calls[-1]["status"] == "past_due"


@pytest.mark.asyncio
async def test_subscription_deleted_cancels_and_emails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeService(
        existing={
            "id": "sub_local_2",
            "stripe_subscription_id": "sub_stripe_2",
            "user_id": "user_123",
        }
    )
    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_stripe_2",
                "customer": "cus_test_2",
                "current_period_end": 1_790_000_000,
                "status": "canceled",
            }
        },
    }
    fake_stripe = _patch_environment(
        monkeypatch, fake, event, customer_email="cancel@example.com"
    )

    sent: Dict[str, Any] = {}

    def _fake_cancel_email(**kwargs):
        sent.update(kwargs)
        return {"sent": True, "skipped": False, "id": "msg_1"}

    monkeypatch.setattr(
        webhooks_mod,
        "send_subscription_cancelled_email",
        _fake_cancel_email,
    )

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = await webhooks_mod.stripe_webhook(_build_request())

    assert result["processed"] is True
    assert fake.cancellations == ["sub_local_2"]
    assert sent.get("to") == "cancel@example.com"
    assert sent.get("period_end_iso")  # ISO date present


@pytest.mark.asyncio
async def test_invoice_payment_failed_flips_status_and_emails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeService(
        existing={
            "id": "sub_local_3",
            "stripe_subscription_id": "sub_stripe_3",
            "user_id": "user_456",
        }
    )
    event = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": "sub_stripe_3",
                "customer": "cus_test_3",
                "customer_email": "billing@example.com",
                "hosted_invoice_url": "https://stripe.example/invoice/xyz",
            }
        },
    }
    fake_stripe = _patch_environment(monkeypatch, fake, event)

    sent: Dict[str, Any] = {}

    def _fake_failed_email(**kwargs):
        sent.update(kwargs)
        return {"sent": True, "skipped": False, "id": "msg_2"}

    monkeypatch.setattr(
        webhooks_mod, "send_payment_failed_email", _fake_failed_email
    )

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = await webhooks_mod.stripe_webhook(_build_request())

    assert result["processed"] is True
    assert fake.status_updates == [("sub_local_3", "past_due")]
    assert sent.get("to") == "billing@example.com"
    assert sent.get("invoice_url") == "https://stripe.example/invoice/xyz"


@pytest.mark.asyncio
async def test_checkout_completed_creates_subscription_and_emails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """checkout.session.completed creates a subscription and fires the welcome-paid email."""
    fake = _FakeService()  # no existing subscription -> create path

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "client_reference_id": "user_new_1",
                "subscription": "sub_stripe_new_1",
                "customer": "cus_test_new",
                "customer_email": "newuser@example.com",
                "amount_total": 2000,
                "metadata": {
                    "tier": "premium",
                    "billing_cycle": "monthly",
                    "user_id": "user_new_1",
                },
            }
        },
    }
    fake_stripe = _patch_environment(
        monkeypatch, fake, event, customer_email="newuser@example.com"
    )

    # Stripe.Subscription.retrieve must look like the real object.
    stripe_sub = MagicMock()
    stripe_sub.customer = "cus_test_new"
    stripe_sub.get = lambda key, default=None: {
        "current_period_start": 1_790_000_000,
        "current_period_end": 1_792_500_000,
    }.get(key, default)
    fake_stripe.Subscription.retrieve = MagicMock(return_value=stripe_sub)

    # Replace create_subscription on the fake service so we can assert it was called.
    created: Dict[str, Any] = {}

    def _fake_create(**kwargs):
        created.update(kwargs)
        return {"id": "sub_local_new_1", **kwargs}

    fake.create_subscription = _fake_create  # type: ignore[attr-defined]

    sent: Dict[str, Any] = {}

    def _fake_confirm(**kwargs):
        sent.update(kwargs)
        return {"sent": True, "skipped": False, "id": "msg_confirm"}

    monkeypatch.setattr(
        webhooks_mod, "send_subscription_confirmed_email", _fake_confirm
    )

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = await webhooks_mod.stripe_webhook(_build_request())

    assert result["processed"] is True
    assert created["user_id"] == "user_new_1"
    assert created["tier_name"] == "premium"
    assert created["billing_cycle"] == "monthly"
    assert sent.get("to") == "newuser@example.com"
    assert sent.get("tier") == "premium"
    assert sent.get("amount_cents") == 2000


@pytest.mark.asyncio
async def test_checkout_completed_email_failure_does_not_5xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing confirmation email must not break the webhook."""
    fake = _FakeService()
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_2",
                "client_reference_id": "user_new_2",
                "subscription": "sub_stripe_new_2",
                "customer": "cus_test_new_2",
                "customer_email": "boom@example.com",
                "metadata": {"tier": "standard", "billing_cycle": "annual", "user_id": "user_new_2"},
            }
        },
    }
    fake_stripe = _patch_environment(monkeypatch, fake, event)
    stripe_sub = MagicMock()
    stripe_sub.customer = "cus_test_new_2"
    stripe_sub.get = lambda *_a, **_k: None
    fake_stripe.Subscription.retrieve = MagicMock(return_value=stripe_sub)

    fake.create_subscription = lambda **kw: {"id": "sub_local_new_2"}  # type: ignore[attr-defined]

    def _exploder(**_kwargs):
        raise RuntimeError("resend exploded")

    monkeypatch.setattr(
        webhooks_mod, "send_subscription_confirmed_email", _exploder
    )

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = await webhooks_mod.stripe_webhook(_build_request())

    assert result["processed"] is True


@pytest.mark.asyncio
async def test_invoice_payment_failed_email_failure_does_not_5xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the email send raises, the webhook still returns 200/processed."""
    fake = _FakeService(
        existing={
            "id": "sub_local_4",
            "stripe_subscription_id": "sub_stripe_4",
            "user_id": "user_789",
        }
    )
    event = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": "sub_stripe_4",
                "customer": "cus_test_4",
                "customer_email": "boom@example.com",
            }
        },
    }
    fake_stripe = _patch_environment(monkeypatch, fake, event)

    def _exploder(**_kwargs):
        raise RuntimeError("resend refused the connection")

    monkeypatch.setattr(webhooks_mod, "send_payment_failed_email", _exploder)

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = await webhooks_mod.stripe_webhook(_build_request())

    assert result["processed"] is True
    assert fake.status_updates == [("sub_local_4", "past_due")]
