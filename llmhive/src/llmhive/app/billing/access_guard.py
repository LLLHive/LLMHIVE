"""Hard backend gate: require an active paid subscription on user-facing entry points.

This is **defense-in-depth** on top of the frontend entitlement check
(``lib/billing/entitlement.ts`` + ``app/page.tsx`` + ``app/api/chat/route.ts`` +
``app/api/execute/route.ts``). The frontend already redirects unpaid users to
``/pricing`` and returns 402 from its API routes; this module enforces the same
rule at the orchestrator layer so a stale API key, bypassed frontend, or
internal caller cannot use paid orchestration without an active subscription.

Behavior:

- Controlled by ``LLMHIVE_REQUIRE_PAID_BACKEND`` (default ``1``). Set to ``0``
  / ``false`` / ``no`` / ``off`` to disable (kill switch for incidents/tests).
- When enabled, the resolved ``user_id`` MUST resolve to an active subscription
  in Firestore whose ``tier_name`` is in :data:`PAID_TIER_NAMES`. Otherwise we
  raise HTTP 402 Payment Required.
- **Fail-closed:** if Firestore is unreachable or the read raises, we reject
  with HTTP 402. This matches the spend-guard posture in :mod:`spend_guard`.

The list of paid tier names mirrors ``PAID_TIERS`` in
``lib/billing/entitlement.ts``.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import HTTPException, status

from .subscription_access import (
    subscription_grants_app_access,
    subscription_grants_paid_access,
)

logger = logging.getLogger(__name__)

PAID_TIER_NAMES = frozenset(
    {
        "lite",
        "basic",
        "starter",
        "standard",
        "pro",
        "premium",
        "enterprise",
        "maximum",
    }
)

_DETAIL_NO_USER = (
    "Active paid subscription required. Sign in and complete checkout."
)
_DETAIL_NO_SUB = "Active paid subscription required for this endpoint."
_DETAIL_FAIL_CLOSED = (
    "Subscription verification temporarily unavailable. Please retry shortly."
)


def is_paid_access_required() -> bool:
    """True when the backend MUST verify an active paid subscription.

    Defaults to ON in production; flip ``LLMHIVE_REQUIRE_PAID_BACKEND=0`` to
    disable for incidents or unit tests.
    """
    return os.getenv("LLMHIVE_REQUIRE_PAID_BACKEND", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _is_paid_subscription(sub: Optional[dict]) -> bool:
    return subscription_grants_paid_access(sub)


def _has_app_access_subscription(sub: Optional[dict]) -> bool:
    return subscription_grants_app_access(sub)


def require_active_paid_subscription(user_id: Optional[str]) -> None:
    """Raise HTTP 402 unless ``user_id`` has an active paid subscription.

    No-op when :func:`is_paid_access_required` is ``False`` (kill switch off).
    Fail-closed on Firestore errors.
    """
    try:
        from .scheduled_benchmark import is_internal_scheduled_benchmark

        if is_internal_scheduled_benchmark():
            return
    except ImportError:
        pass

    if not is_paid_access_required():
        return

    uid = (user_id or "").strip()
    if not uid:
        logger.warning(
            "paid_access_required: missing user_id; rejecting with 402"
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_NO_USER,
        )

    try:
        from ..firestore_db import (
            FirestoreSubscriptionService,
            is_firestore_available,
        )
    except Exception as exc:
        logger.exception(
            "paid_access_required: firestore module import failed: %s", exc
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_FAIL_CLOSED,
        ) from exc

    if not is_firestore_available():
        logger.error(
            "paid_access_required: firestore unavailable, fail-closed for user_id=%s",
            uid,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_FAIL_CLOSED,
        )

    try:
        sub = FirestoreSubscriptionService().get_user_subscription(uid)
    except Exception as exc:
        logger.exception(
            "paid_access_required: subscription read failed user_id=%s: %s",
            uid,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_FAIL_CLOSED,
        ) from exc

    if not _is_paid_subscription(sub):
        logger.info(
            "paid_access_required: rejected user_id=%s (no active paid subscription)",
            uid,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_NO_SUB,
        )


def require_app_access(user_id: Optional[str]) -> None:
    """Raise HTTP 402 unless ``user_id`` has app access (paid or provisioned free).

    Used on chat/execute entry points so marketing and comp accounts with an
    active ``free`` tier in Firestore can use free orchestration without Stripe.
    """
    try:
        from .scheduled_benchmark import is_internal_scheduled_benchmark

        if is_internal_scheduled_benchmark():
            return
    except ImportError:
        pass

    if not is_paid_access_required():
        return

    uid = (user_id or "").strip()
    if not uid:
        logger.warning("app_access_required: missing user_id; rejecting with 402")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_NO_USER,
        )

    try:
        from ..firestore_db import (
            FirestoreSubscriptionService,
            is_firestore_available,
        )
    except Exception as exc:
        logger.exception(
            "app_access_required: firestore module import failed: %s", exc
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_FAIL_CLOSED,
        ) from exc

    if not is_firestore_available():
        logger.error(
            "app_access_required: firestore unavailable, fail-closed for user_id=%s",
            uid,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_FAIL_CLOSED,
        )

    try:
        sub = FirestoreSubscriptionService().get_user_subscription(uid)
    except Exception as exc:
        logger.exception(
            "app_access_required: subscription read failed user_id=%s: %s",
            uid,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_FAIL_CLOSED,
        ) from exc

    if not _has_app_access_subscription(sub):
        logger.info(
            "app_access_required: rejected user_id=%s (no active app subscription)",
            uid,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=_DETAIL_NO_SUB,
        )
