"""Unit tests for ``llmhive.app.billing.access_guard``.

Exercises the kill switch, the missing-user branch, the fail-closed branch
when Firestore is unavailable, the rejection branch for non-paid tiers, and
the happy path for an active paid subscription.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
from fastapi import HTTPException

from llmhive.app.billing import access_guard


def _enable_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "1")


def _patch_firestore(
    monkeypatch: pytest.MonkeyPatch,
    *,
    available: bool = True,
    subscription: Optional[Dict[str, Any]] = None,
    raise_on_read: bool = False,
) -> None:
    """Replace the Firestore module functions referenced by access_guard."""
    import llmhive.app.firestore_db as firestore_db_mod

    monkeypatch.setattr(
        firestore_db_mod, "is_firestore_available", lambda: available
    )

    class _Service:
        def get_user_subscription(self, user_id: str):  # noqa: D401 - test stub
            if raise_on_read:
                raise RuntimeError("simulated firestore failure")
            return subscription

    monkeypatch.setattr(firestore_db_mod, "FirestoreSubscriptionService", _Service)


def test_kill_switch_disables_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLMHIVE_REQUIRE_PAID_BACKEND", "0")
    # No firestore patching needed: helper must short-circuit.
    access_guard.require_active_paid_subscription(None)
    access_guard.require_active_paid_subscription("any-user")


def test_missing_user_id_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_guard(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription(None)
    assert exc.value.status_code == 402


def test_blank_user_id_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_guard(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription("   ")
    assert exc.value.status_code == 402


def test_firestore_unavailable_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_guard(monkeypatch)
    _patch_firestore(monkeypatch, available=False)

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription("user_123")
    assert exc.value.status_code == 402


def test_firestore_read_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_guard(monkeypatch)
    _patch_firestore(monkeypatch, raise_on_read=True)

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription("user_123")
    assert exc.value.status_code == 402


def test_no_subscription_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_guard(monkeypatch)
    _patch_firestore(monkeypatch, subscription=None)

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription("user_123")
    assert exc.value.status_code == 402


def test_inactive_subscription_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_guard(monkeypatch)
    _patch_firestore(
        monkeypatch,
        subscription={"status": "past_due", "tier_name": "premium"},
    )

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription("user_123")
    assert exc.value.status_code == 402


def test_free_tier_rejects_even_if_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_guard(monkeypatch)
    _patch_firestore(
        monkeypatch,
        subscription={"status": "active", "tier_name": "free"},
    )

    with pytest.raises(HTTPException) as exc:
        access_guard.require_active_paid_subscription("user_123")
    assert exc.value.status_code == 402


@pytest.mark.parametrize(
    "tier_name",
    [
        "lite",
        "Lite",
        "STANDARD",
        "premium",
        "pro",
        "enterprise",
        "maximum",
    ],
)
def test_active_paid_subscription_allows(
    monkeypatch: pytest.MonkeyPatch, tier_name: str
) -> None:
    _enable_guard(monkeypatch)
    _patch_firestore(
        monkeypatch,
        subscription={"status": "active", "tier_name": tier_name},
    )

    access_guard.require_active_paid_subscription("user_123")


def test_subscription_alternate_tier_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``tier`` should be honored when ``tier_name`` is absent."""
    _enable_guard(monkeypatch)
    _patch_firestore(
        monkeypatch,
        subscription={"status": "active", "tier": "premium"},
    )

    access_guard.require_active_paid_subscription("user_123")
