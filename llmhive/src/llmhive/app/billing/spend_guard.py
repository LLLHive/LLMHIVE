"""Elite orchestration spend cap vs subscription revenue (profit guard).

Paid subscribers (Lite / Standard paid, Pro / Premium, Enterprise) may use
``elite`` orchestration (premium models) only until **cumulative provider spend**
in the current billing period reaches **ELITE_SPEND_CAP_FRACTION** (default **0.25**)
of that period's **recognized monthly subscription revenue** (e.g. Premium $20/mo → $5 cap).

When spend reaches the cap, :func:`get_orchestration_tier` returns ``free`` so routing
matches the certified free stack until the next period.

**Fail-closed:** if Firestore is unavailable or reads fail for a **paid** user, we treat
the cap as **exceeded** so orchestration falls back to ``free`` (protects margin).

Environment:

- ``ELITE_SPEND_GUARD`` — ``1`` (default) enables this guard; ``0`` disables (tests / emergency).
- ``ELITE_SPEND_CAP_FRACTION`` — default ``0.25``.
- ``ELITE_SPEND_ESTIMATE_USD_PER_MILLION`` — fallback cost when no ``cost_info`` (elite-only path); default ``10.0``.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from google.cloud import firestore

from ..firestore_db import get_firestore_client, is_firestore_available
from .pricing import PricingTierManager, TierName

logger = logging.getLogger(__name__)

COLLECTION = "elite_spend_control"
_DOC_ID_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _sanitize_doc_id(user_id: str) -> str:
    s = _DOC_ID_RE.sub("_", (user_id or "").strip())
    return s[:800] or "anonymous"


def _as_utc_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    # Firestore Timestamp
    if hasattr(value, "timestamp") and callable(value.timestamp):
        try:
            return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)
        except Exception:
            return None
    return None


def is_spend_guard_enabled() -> bool:
    return os.getenv("ELITE_SPEND_GUARD", "1").lower() not in ("0", "false", "no", "off")


def spend_cap_fraction() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("ELITE_SPEND_CAP_FRACTION", "0.25"))))
    except ValueError:
        return 0.25


def estimate_elite_cost_usd_per_million() -> float:
    try:
        return max(0.0, float(os.getenv("ELITE_SPEND_ESTIMATE_USD_PER_MILLION", "10.0")))
    except ValueError:
        return 10.0


def _pricing() -> PricingTierManager:
    return PricingTierManager()


def resolve_monthly_revenue_usd(tier: TierName, subscription: Optional[Dict[str, Any]]) -> float:
    """Recognized monthly-equivalent revenue for cap math (USD)."""
    pt = _pricing().get_tier(tier)
    if pt is None:
        return 0.0
    sub = subscription or {}
    cycle = str(sub.get("billing_cycle") or "monthly").lower()
    seats_raw = sub.get("seats") or sub.get("seat_count") or 1
    try:
        seats = max(1, int(seats_raw))
    except (TypeError, ValueError):
        seats = 1

    if tier == TierName.ENTERPRISE:
        qty = max(seats, pt.limits.min_seats or 1)
        if cycle == "annual":
            return (pt.annual_price_usd / 12.0) * qty
        return pt.monthly_price_usd * qty

    if cycle == "annual":
        return pt.annual_price_usd / 12.0
    return pt.monthly_price_usd


def compute_period_key(subscription: Optional[Dict[str, Any]]) -> str:
    """Stable key for the current Stripe / subscription billing window."""
    sub = subscription or {}
    start = _as_utc_dt(sub.get("current_period_start"))
    end = _as_utc_dt(sub.get("current_period_end"))
    if start and end:
        return f"{start.date().isoformat()}_{end.date().isoformat()}"
    return datetime.now(timezone.utc).strftime("%Y-%m")


def compute_spend_cap_usd(monthly_revenue_usd: float) -> float:
    return max(0.0, float(monthly_revenue_usd) * spend_cap_fraction())


def _doc_ref(db: Any, user_id: str):
    return db.collection(COLLECTION).document(_sanitize_doc_id(user_id))


def read_spend_document(user_id: str) -> Optional[Dict[str, Any]]:
    db = get_firestore_client()
    if not db:
        return None
    try:
        snap = _doc_ref(db, user_id).get()
        if snap.exists:
            return snap.to_dict()
    except Exception as exc:
        logger.error("read_spend_document failed user_id=%s: %s", user_id, exc)
    return None


def get_spend_status(
    user_id: str,
    tier: TierName,
    subscription: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Snapshot for UI / diagnostics (non-transactional read)."""
    if tier == TierName.FREE or not is_spend_guard_enabled():
        rev = 0.0
        cap = 0.0
        spent = 0.0
        return {
            "guard_active": False,
            "monthly_revenue_usd": rev,
            "cap_usd": cap,
            "spent_usd": spent,
            "period_key": compute_period_key(subscription),
            "fail_closed": False,
        }

    if not is_firestore_available():
        rev = resolve_monthly_revenue_usd(tier, subscription)
        cap = compute_spend_cap_usd(rev)
        return {
            "guard_active": True,
            "monthly_revenue_usd": rev,
            "cap_usd": cap,
            "spent_usd": cap,
            "period_key": compute_period_key(subscription),
            "fail_closed": True,
        }

    rev = resolve_monthly_revenue_usd(tier, subscription)
    cap = compute_spend_cap_usd(rev)
    expected_pk = compute_period_key(subscription)
    doc = read_spend_document(user_id)
    spent = 0.0
    cap_doc = cap
    if doc:
        if doc.get("period_key") == expected_pk:
            spent = float(doc.get("spent_usd", 0.0) or 0.0)
            cap_doc = float(doc.get("cap_usd", cap) or cap)
        else:
            spent = 0.0
    return {
        "guard_active": True,
        "monthly_revenue_usd": rev,
        "cap_usd": cap_doc,
        "spent_usd": spent,
        "period_key": expected_pk,
        "fail_closed": False,
    }


def spend_cap_exceeded(
    user_id: str,
    tier: TierName,
    subscription: Optional[Dict[str, Any]],
) -> bool:
    """Return True if paid user must be forced to free orchestration (spend ≥ cap)."""
    if tier == TierName.FREE:
        return False
    if not is_spend_guard_enabled():
        return False

    status = get_spend_status(user_id, tier, subscription)
    if status.get("fail_closed"):
        return True

    cap = float(status.get("cap_usd") or 0.0)
    spent = float(status.get("spent_usd") or 0.0)
    if cap <= 0.0:
        return True
    # Tiny epsilon so float noise does not strand users past cap
    return spent >= cap - 1e-9


def record_elite_spend(
    user_id: str,
    cost_usd: float,
    subscription: Optional[Dict[str, Any]],
) -> None:
    """Atomically add ``cost_usd`` to this user's elite spend for the current period."""
    if not is_spend_guard_enabled() or cost_usd <= 0:
        return
    db = get_firestore_client()
    if not db:
        logger.warning("record_elite_spend: no Firestore client; skip user_id=%s", user_id)
        return

    tier_s = (subscription or {}).get("tier_name") or "free"
    try:
        tier = TierName(str(tier_s).lower())
    except ValueError:
        tier = TierName.FREE
    if tier == TierName.FREE:
        return

    rev = resolve_monthly_revenue_usd(tier, subscription)
    cap = compute_spend_cap_usd(rev)
    period_key = compute_period_key(subscription)
    doc_ref = _doc_ref(db, user_id)
    delta = float(cost_usd)

    @firestore.transactional
    def _txn(transaction) -> None:
        snap = doc_ref.get(transaction=transaction)
        data = snap.to_dict() if snap.exists else {}
        spent = float(data.get("spent_usd", 0.0) or 0.0)
        if data.get("period_key") != period_key:
            spent = 0.0
        spent += delta
        transaction.set(
            doc_ref,
            {
                "user_id": user_id,
                "period_key": period_key,
                "spent_usd": spent,
                "cap_usd": cap,
                "monthly_revenue_usd": rev,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

    try:
        transaction = db.transaction()
        _txn(transaction)
        logger.info(
            "record_elite_spend user_id=%s +$%.4f -> period=%s cap=$%.2f",
            user_id,
            delta,
            period_key,
            cap,
        )
    except Exception as exc:
        logger.error("record_elite_spend failed user_id=%s: %s", user_id, exc)


def extract_request_cost_usd(
    *,
    cost_info: Optional[Dict[str, Any]],
    elite_total_tokens: Optional[int],
) -> float:
    """Best-effort actual cost; conservative estimate when providers omit cost."""
    if cost_info:
        raw = cost_info.get("cost_usd")
        if raw is None:
            raw = cost_info.get("total_cost")
        try:
            v = float(raw or 0.0)
            if v > 0.0:
                return v
        except (TypeError, ValueError):
            pass
    tok = int(elite_total_tokens or 0)
    if tok <= 0:
        return 0.0
    rate = estimate_elite_cost_usd_per_million()
    return (tok / 1_000_000.0) * rate
