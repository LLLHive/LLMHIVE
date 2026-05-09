"""Regression tests for ``GET /api/v1/billing/subscription/{user_id}``.

These tests pin the contract that the entitlement endpoint reads from
**Firestore first** (where the Stripe webhook + the synchronous
``ensure-subscription`` helper write completed purchases) and only falls
back to the SQL ``SubscriptionService`` for legacy rows.

A regression here is what produced the customer-visible bug: card was
charged, Firestore had the active subscription, but the endpoint queried
SQL only, returned 404, and the frontend bounced the paid user to
``/pricing``.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from llmhive.app.api import billing as billing_api


@pytest.fixture()
def app_with_billing() -> FastAPI:
    """Mount only the billing router on a fresh app, with the SQL Session
    dependency overridden so we don't need a real database for these tests.
    """
    app = FastAPI()
    app.include_router(billing_api.router)

    # The endpoint declares ``db: Session = Depends(get_db)`` but we never
    # let the SQL path actually run (we patch SubscriptionService below),
    # so a sentinel value is fine.
    from llmhive.app.database import get_db

    def _fake_db() -> Any:
        yield MagicMock(name="fake-db")

    app.dependency_overrides[get_db] = _fake_db
    return app


def _firestore_doc(user_id: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "tier_name": "premium",
        "status": "active",
        "billing_cycle": "monthly",
        "current_period_start": dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc),
        "current_period_end": dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc),
        "stripe_customer_id": "cus_live_1",
        "stripe_subscription_id": "sub_live_1",
        "cancel_at_period_end": False,
    }


def test_endpoint_returns_active_subscription_from_firestore(app_with_billing):
    """Customer charged today: Firestore has the active subscription, SQL
    is empty. The endpoint MUST resolve the customer as paid.
    """
    user_id = "user_paid_today"

    fake_firestore = MagicMock()
    fake_firestore.get_user_subscription.return_value = _firestore_doc(user_id)

    fake_sql = MagicMock()
    fake_sql.get_user_subscription.return_value = None  # SQL has no record

    with (
        patch.object(billing_api, "is_firestore_available", return_value=True),
        patch.object(billing_api, "FirestoreSubscriptionService", return_value=fake_firestore),
        patch.object(billing_api, "SubscriptionService", return_value=fake_sql),
    ):
        client = TestClient(app_with_billing)
        resp = client.get(f"/subscription/{user_id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["user_id"] == user_id
    assert body["status"] == "active"
    assert body["tier_name"] == "premium"
    assert body["tier"] == "premium"
    assert body["billing_cycle"] == "monthly"
    assert body["stripe_subscription_id"] == "sub_live_1"
    assert body["source"] == "firestore"

    # SQL must NOT be consulted when Firestore answered.
    fake_sql.get_user_subscription.assert_not_called()


def test_endpoint_falls_back_to_sql_when_firestore_empty(app_with_billing):
    """Legacy users (subscription written before the Firestore migration)
    must still resolve through the SQL fallback.
    """
    user_id = "user_legacy_sql_only"

    fake_firestore = MagicMock()
    fake_firestore.get_user_subscription.return_value = None  # not in Firestore

    sql_sub = MagicMock()
    sql_sub.tier_name = "lite"
    sql_sub.status = MagicMock(value="active")
    sql_sub.billing_cycle = "annual"
    sql_sub.current_period_start = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    sql_sub.current_period_end = dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc)
    sql_sub.cancel_at_period_end = False
    sql_sub.stripe_customer_id = "cus_legacy_1"
    sql_sub.stripe_subscription_id = "sub_legacy_1"

    fake_sql = MagicMock()
    fake_sql.get_user_subscription.return_value = sql_sub

    with (
        patch.object(billing_api, "is_firestore_available", return_value=True),
        patch.object(billing_api, "FirestoreSubscriptionService", return_value=fake_firestore),
        patch.object(billing_api, "SubscriptionService", return_value=fake_sql),
    ):
        client = TestClient(app_with_billing)
        resp = client.get(f"/subscription/{user_id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "active"
    assert body["tier_name"] == "lite"
    assert body["billing_cycle"] == "annual"
    assert body["stripe_subscription_id"] == "sub_legacy_1"
    assert body["source"] == "sql"


def test_endpoint_returns_404_when_neither_store_has_user(app_with_billing):
    """Anonymous / never-paid user: both stores empty -> 404 so the frontend
    paywall correctly bounces them to /pricing.
    """
    user_id = "user_never_paid"

    fake_firestore = MagicMock()
    fake_firestore.get_user_subscription.return_value = None

    fake_sql = MagicMock()
    fake_sql.get_user_subscription.return_value = None

    with (
        patch.object(billing_api, "is_firestore_available", return_value=True),
        patch.object(billing_api, "FirestoreSubscriptionService", return_value=fake_firestore),
        patch.object(billing_api, "SubscriptionService", return_value=fake_sql),
    ):
        client = TestClient(app_with_billing)
        resp = client.get(f"/subscription/{user_id}")

    assert resp.status_code == 404


def test_endpoint_falls_back_when_firestore_lookup_raises(app_with_billing):
    """Defence-in-depth: if Firestore raises (network blip, bad creds, etc.)
    the endpoint must fall through to SQL rather than 500.
    """
    user_id = "user_with_legacy_record"

    fake_firestore = MagicMock()
    fake_firestore.get_user_subscription.side_effect = RuntimeError("firestore boom")

    sql_sub = MagicMock()
    sql_sub.tier_name = "premium"
    sql_sub.status = MagicMock(value="active")
    sql_sub.billing_cycle = "monthly"
    sql_sub.current_period_start = None
    sql_sub.current_period_end = None
    sql_sub.cancel_at_period_end = False
    sql_sub.stripe_customer_id = None
    sql_sub.stripe_subscription_id = None

    fake_sql = MagicMock()
    fake_sql.get_user_subscription.return_value = sql_sub

    with (
        patch.object(billing_api, "is_firestore_available", return_value=True),
        patch.object(billing_api, "FirestoreSubscriptionService", return_value=fake_firestore),
        patch.object(billing_api, "SubscriptionService", return_value=fake_sql),
    ):
        client = TestClient(app_with_billing)
        resp = client.get(f"/subscription/{user_id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["source"] == "sql"
