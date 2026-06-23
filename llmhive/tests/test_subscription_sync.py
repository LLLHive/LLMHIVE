"""Tests for the synchronous subscription upsert helper + the
``ensure-subscription`` endpoint that calls it from the post-checkout success
flow.

These tests do NOT connect to Stripe or Firestore. We hand-craft Stripe-shaped
dicts and patch:

- ``stripe.Subscription.retrieve`` so the helper sees deterministic period
  bounds without a real API call.
- ``llmhive.app.billing.subscription_sync.FirestoreSubscriptionService`` so we
  observe what the helper writes.
- The processor / availability flags consumed by the FastAPI endpoint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from llmhive.app.billing import subscription_sync as sync_mod


class _FakeService:
    """Minimal stand-in for FirestoreSubscriptionService."""

    def __init__(self, existing: Optional[Dict[str, Any]] = None) -> None:
        self._existing = existing
        self.create_calls: List[Dict[str, Any]] = []
        self.update_calls: List[Dict[str, Any]] = []

    def get_subscription_by_stripe_id(self, sid: str) -> Optional[Dict[str, Any]]:
        if self._existing and self._existing.get("stripe_subscription_id") == sid:
            return self._existing
        return None

    def create_subscription(self, **kwargs: Any) -> Dict[str, Any]:
        record = {"id": "sub_doc_new", **kwargs}
        self.create_calls.append(record)
        return record

    def update_subscription(self, sub_id: str, payload: Dict[str, Any]) -> None:
        self.update_calls.append({"id": sub_id, **payload})


def _make_stripe_subscription(sub_id: str = "sub_test_1") -> MagicMock:
    obj = MagicMock()
    obj.customer = "cus_test_1"

    def _get(key, default=None):
        mapping = {
            "current_period_start": 1_700_000_000,
            "current_period_end": 1_702_592_000,
            "customer": "cus_test_1",
        }
        return mapping.get(key, default)

    obj.get = _get
    return obj


def test_helper_creates_new_subscription_when_none_exists():
    """First call (webhook hasn't fired yet) → creates subscription row."""
    service = _FakeService(existing=None)
    session = {
        "id": "cs_test_1",
        "client_reference_id": "user_abc",
        "subscription": "sub_test_1",
        "payment_status": "paid",
        "metadata": {"tier": "pro", "billing_cycle": "monthly", "user_id": "user_abc"},
    }

    fake_stripe = MagicMock()
    fake_stripe.Subscription.retrieve.return_value = _make_stripe_subscription("sub_test_1")

    result = sync_mod.upsert_subscription_from_checkout_session(
        fake_stripe, session, service=service
    )

    assert result.created is True
    assert result.updated is False
    assert result.user_id == "user_abc"
    assert result.tier_name == "pro"
    assert len(service.create_calls) == 1
    created = service.create_calls[0]
    assert created["user_id"] == "user_abc"
    assert created["tier_name"] == "pro"
    assert created["billing_cycle"] == "monthly"
    assert created["stripe_subscription_id"] == "sub_test_1"
    assert created["stripe_customer_id"] == "cus_test_1"
    assert len(service.update_calls) == 0


def test_helper_updates_existing_subscription_idempotently():
    """If the webhook already created the row, the second call updates it."""
    service = _FakeService(
        existing={
            "id": "sub_doc_existing",
            "stripe_subscription_id": "sub_test_1",
            "user_id": "user_abc",
            "tier_name": "pro",
            "status": "active",
        }
    )
    session = {
        "id": "cs_test_1",
        "client_reference_id": "user_abc",
        "subscription": "sub_test_1",
        "payment_status": "paid",
        "metadata": {"tier": "pro", "billing_cycle": "annual"},
    }

    fake_stripe = MagicMock()
    fake_stripe.Subscription.retrieve.return_value = _make_stripe_subscription("sub_test_1")

    result = sync_mod.upsert_subscription_from_checkout_session(
        fake_stripe, session, service=service
    )

    assert result.created is False
    assert result.updated is True
    assert len(service.update_calls) == 1
    update = service.update_calls[0]
    assert update["id"] == "sub_doc_existing"
    assert update["status"] == "active"
    assert update["tier_name"] == "pro"
    assert update["billing_cycle"] == "annual"
    assert update["stripe_customer_id"] == "cus_test_1"
    assert len(service.create_calls) == 0


def test_helper_falls_back_to_metadata_user_id_when_client_reference_missing():
    service = _FakeService(existing=None)
    session = {
        "id": "cs_test_2",
        "subscription": "sub_test_2",
        "payment_status": "paid",
        "metadata": {"tier": "pro", "billing_cycle": "monthly", "user_id": "user_meta"},
    }

    fake_stripe = MagicMock()
    fake_stripe.Subscription.retrieve.return_value = _make_stripe_subscription("sub_test_2")

    result = sync_mod.upsert_subscription_from_checkout_session(
        fake_stripe, session, service=service
    )

    assert result.user_id == "user_meta"
    assert service.create_calls[0]["user_id"] == "user_meta"


def test_helper_rejects_session_without_user_id():
    service = _FakeService(existing=None)
    session = {
        "id": "cs_no_user",
        "subscription": "sub_x",
        "payment_status": "paid",
        "metadata": {},
    }

    with pytest.raises(ValueError, match="client_reference_id"):
        sync_mod.upsert_subscription_from_checkout_session(MagicMock(), session, service=service)


def test_helper_accepts_no_payment_required_trial_session():
    """Trial checkout completes with payment_status=no_payment_required."""
    service = _FakeService(existing=None)
    session = {
        "id": "cs_trial_1",
        "client_reference_id": "user_trial",
        "subscription": "sub_trial_1",
        "payment_status": "no_payment_required",
        "status": "complete",
        "metadata": {"tier": "lite", "billing_cycle": "monthly", "user_id": "user_trial"},
    }

    fake_stripe = MagicMock()
    fake_stripe.Subscription.retrieve.return_value = {
        "customer": "cus_test_1",
        "status": "trialing",
        "current_period_start": 1_700_000_000,
        "current_period_end": 1_702_592_000,
        "trial_start": 1_700_000_000,
        "trial_end": 1_700_259_200,
    }

    result = sync_mod.upsert_subscription_from_checkout_session(
        fake_stripe, session, service=service
    )

    assert result.created is True
    created = service.create_calls[0]
    assert created["status"] == "trialing"
    assert created["tier_name"] == "lite"


def test_helper_rejects_unpaid_session():
    """Sessions not yet paid must NOT promote the user to active."""
    service = _FakeService(existing=None)
    session = {
        "id": "cs_unpaid",
        "client_reference_id": "user_abc",
        "subscription": "sub_x",
        "payment_status": "unpaid",
        "status": "open",
        "metadata": {"tier": "pro"},
    }

    with pytest.raises(ValueError, match="not completed"):
        sync_mod.upsert_subscription_from_checkout_session(MagicMock(), session, service=service)


def test_helper_rejects_session_without_subscription_id():
    service = _FakeService(existing=None)
    session = {
        "id": "cs_no_sub",
        "client_reference_id": "user_abc",
        "payment_status": "paid",
        "metadata": {"tier": "pro"},
    }

    with pytest.raises(ValueError, match="subscription id"):
        sync_mod.upsert_subscription_from_checkout_session(MagicMock(), session, service=service)


# --- Endpoint-level integration ---------------------------------------------


def _client():
    """Build a TestClient with the orchestrator's payment_routes mounted.

    Skips the test when optional deps for the FastAPI app aren't installed
    locally (CI installs the full ``llmhive/requirements.txt``).
    """
    pytest.importorskip("pydantic_settings", reason="FastAPI app deps missing locally")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from llmhive.app.api import payment_routes

    app = FastAPI()
    app.include_router(payment_routes.router, prefix="/api/v1/payments")
    return TestClient(app), payment_routes


def test_endpoint_returns_409_for_unpaid_session(monkeypatch: pytest.MonkeyPatch):
    client, payment_routes = _client()

    monkeypatch.setattr(payment_routes, "STRIPE_AVAILABLE", True)
    monkeypatch.setattr(payment_routes, "get_payment_processor", lambda: object())

    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.retrieve.return_value = {
        "id": "cs_unpaid",
        "client_reference_id": "user_abc",
        "subscription": "sub_x",
        "payment_status": "unpaid",
        "metadata": {"tier": "pro"},
    }
    fake_stripe.Subscription.retrieve.return_value = _make_stripe_subscription("sub_x")

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        resp = client.post("/api/v1/payments/checkout-session/cs_unpaid/ensure-subscription")

    assert resp.status_code == 409
    assert "not completed" in resp.json()["detail"].lower()


def test_endpoint_returns_503_when_stripe_unavailable(monkeypatch: pytest.MonkeyPatch):
    client, payment_routes = _client()
    monkeypatch.setattr(payment_routes, "STRIPE_AVAILABLE", False)

    resp = client.post("/api/v1/payments/checkout-session/cs_xx/ensure-subscription")
    assert resp.status_code == 503


def test_endpoint_creates_subscription_on_paid_session(monkeypatch: pytest.MonkeyPatch):
    client, payment_routes = _client()

    monkeypatch.setattr(payment_routes, "STRIPE_AVAILABLE", True)
    monkeypatch.setattr(payment_routes, "get_payment_processor", lambda: object())

    fake_service = _FakeService(existing=None)
    monkeypatch.setattr(
        sync_mod, "FirestoreSubscriptionService", lambda: fake_service
    )

    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.retrieve.return_value = {
        "id": "cs_ok",
        "client_reference_id": "user_abc",
        "subscription": "sub_ok",
        "payment_status": "paid",
        "metadata": {"tier": "pro", "billing_cycle": "monthly"},
    }
    fake_stripe.Subscription.retrieve.return_value = _make_stripe_subscription("sub_ok")

    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        resp = client.post("/api/v1/payments/checkout-session/cs_ok/ensure-subscription")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] is True
    assert body["updated"] is False
    assert body["user_id"] == "user_abc"
    assert body["tier_name"] == "pro"
    assert len(fake_service.create_calls) == 1
