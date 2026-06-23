"""Idempotent Stripe checkout-session → Firestore subscription upsert.

This module exists so the upsert can run from two places without duplication or
divergence:

1. The Stripe webhook (``checkout.session.completed`` branch).
2. The synchronous post-checkout verify endpoint, which the frontend calls on
   the success page so the user's Firestore subscription row is written before
   they click through to the app.

The synchronous path closes a race that previously caused a redirect loop:
the success page would fire long before Stripe delivered the
``checkout.session.completed`` webhook, so the entitlement check on ``/`` would
see ``status != "active"`` and bounce the user back to ``/pricing``.

Both call sites are idempotent: if the subscription already exists in
Firestore (because the other path won), we update it with the latest fields
instead of creating a duplicate.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Mapping, Optional

from ..firestore_db import FirestoreSubscriptionService

logger = logging.getLogger(__name__)


def _utc_from_unix(ts: object) -> Optional[dt.datetime]:
    if ts is None:
        return None
    try:
        return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _session_get(session: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a Stripe session or a plain dict uniformly."""
    if session is None:
        return default
    if isinstance(session, Mapping):
        return session.get(key, default)
    value = getattr(session, key, None)
    if value is not None:
        return value
    if hasattr(session, "get"):
        try:
            return session.get(key, default)
        except Exception:
            return default
    return default


def _resolve_user_id(session: Any) -> Optional[str]:
    """Look up the LLMHive user id stored on the checkout session."""
    user_id = _session_get(session, "client_reference_id")
    if user_id:
        return str(user_id)
    metadata = _session_get(session, "metadata") or {}
    if isinstance(metadata, Mapping):
        candidate = metadata.get("user_id")
        if candidate:
            return str(candidate)
    return None


class UpsertResult(dict):
    """Lightweight dict subclass so callers can use either ``["x"]`` or ``.x``."""

    @property
    def created(self) -> bool:
        return bool(self.get("created"))

    @property
    def updated(self) -> bool:
        return bool(self.get("updated"))

    @property
    def user_id(self) -> Optional[str]:
        return self.get("user_id")

    @property
    def tier_name(self) -> Optional[str]:
        return self.get("tier_name")


def upsert_subscription_from_checkout_session(
    stripe_module: Any,
    session: Any,
    *,
    service: Optional[FirestoreSubscriptionService] = None,
) -> UpsertResult:
    """Idempotently create/update a Firestore subscription from a Stripe session.

    Returns an :class:`UpsertResult` describing what happened. Raises ``ValueError``
    on missing fields the caller is expected to surface as a 4xx.
    """
    user_id = _resolve_user_id(session)
    if not user_id:
        raise ValueError("Checkout session missing client_reference_id / metadata.user_id")

    payment_status = (_session_get(session, "payment_status") or "").lower()
    session_status = (_session_get(session, "status") or "").lower()
    if payment_status not in {"paid", "no_payment_required"} and session_status != "complete":
        raise ValueError(
            f"Checkout session not completed (payment_status={payment_status!r}, status={session_status!r})"
        )

    stripe_subscription_id = _session_get(session, "subscription")
    if not stripe_subscription_id:
        raise ValueError("Checkout session missing subscription id")

    try:
        stripe_subscription = stripe_module.Subscription.retrieve(stripe_subscription_id)
    except Exception as exc:
        logger.exception("ensure_subscription: stripe Subscription.retrieve failed: %s", exc)
        raise ValueError(f"Failed to retrieve Stripe subscription: {exc}") from exc

    stripe_customer_id = _session_get(stripe_subscription, "customer")
    period_start = _utc_from_unix(_session_get(stripe_subscription, "current_period_start"))
    period_end = _utc_from_unix(_session_get(stripe_subscription, "current_period_end"))
    trial_start = _utc_from_unix(_session_get(stripe_subscription, "trial_start"))
    trial_end = _utc_from_unix(_session_get(stripe_subscription, "trial_end"))

    stripe_status = str(_session_get(stripe_subscription, "status") or "active").lower()
    status_map = {
        "active": "active",
        "trialing": "trialing",
        "past_due": "past_due",
        "canceled": "cancelled",
        "cancelled": "cancelled",
        "unpaid": "expired",
        "incomplete": "pending",
        "incomplete_expired": "expired",
    }
    firestore_status = status_map.get(stripe_status, "active")

    metadata = _session_get(session, "metadata") or {}
    if not isinstance(metadata, Mapping):
        metadata = {}
    tier_name = str(metadata.get("tier", "pro")).lower()
    billing_cycle = str(metadata.get("billing_cycle", "monthly")).lower()

    svc = service or FirestoreSubscriptionService()

    existing = None
    try:
        existing = svc.get_subscription_by_stripe_id(str(stripe_subscription_id))
    except Exception as exc:
        logger.warning(
            "ensure_subscription: get_subscription_by_stripe_id failed (will create): %s", exc
        )

    if existing:
        update: dict = {
            "status": firestore_status,
            "tier_name": tier_name,
            "billing_cycle": billing_cycle,
            "stripe_customer_id": stripe_customer_id,
        }
        if period_start:
            update["current_period_start"] = period_start
        if period_end:
            update["current_period_end"] = period_end
        if trial_start:
            update["trial_start"] = trial_start
        if trial_end:
            update["trial_end"] = trial_end
        try:
            svc.update_subscription(existing["id"], update)
        except Exception as exc:
            logger.exception("ensure_subscription: update_subscription failed: %s", exc)
            raise
        logger.info(
            "ensure_subscription: updated existing subscription user=%s tier=%s",
            user_id,
            tier_name,
        )
        return UpsertResult(
            created=False,
            updated=True,
            user_id=user_id,
            tier_name=tier_name,
            billing_cycle=billing_cycle,
            stripe_subscription_id=str(stripe_subscription_id),
        )

    try:
        created = svc.create_subscription(
            user_id=user_id,
            tier_name=tier_name,
            billing_cycle=billing_cycle,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            current_period_start=period_start,
            current_period_end=period_end,
            status=firestore_status,
            trial_start=trial_start,
            trial_end=trial_end,
        )
    except Exception as exc:
        logger.exception("ensure_subscription: create_subscription failed: %s", exc)
        raise

    if not created:
        logger.error(
            "ensure_subscription: create_subscription returned None for user=%s", user_id
        )

    logger.info(
        "ensure_subscription: created subscription user=%s tier=%s id=%s",
        user_id,
        tier_name,
        (created or {}).get("id") if isinstance(created, Mapping) else None,
    )
    return UpsertResult(
        created=True,
        updated=False,
        user_id=user_id,
        tier_name=tier_name,
        billing_cycle=billing_cycle,
        stripe_subscription_id=str(stripe_subscription_id),
    )
