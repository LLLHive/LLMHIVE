"""Elite orchestration spend cap vs subscription revenue (profit guard).

Paid subscribers (Lite / Standard paid, Pro / Premium, Enterprise) may use
``elite`` orchestration (premium models) only until **cumulative provider spend**
in the current billing period reaches **ELITE_SPEND_CAP_FRACTION** (default **0.25**)
of that period's **recognized monthly subscription revenue** (e.g. Premium $20/mo → nominal
$5 cap before headroom; the enforced cap is slightly lower by default).

When spend reaches the cap, :func:`get_orchestration_tier` returns ``free`` so routing
matches the certified free stack until the next period.

**Fail-closed:** if Firestore is unavailable, the client cannot be created, **or a spend
read fails** for a **paid** user, we treat the cap as **exceeded** so orchestration falls
back to ``free`` (protects margin).

**Headroom:** the effective cap is ``revenue * fraction * (1 - ELITE_SPEND_HEADROOM_FRACTION)``
(default 3% under the nominal cap) so ledger/estimate noise does not exceed the budget.

**Cost ledger:** when both provider-reported cost and a token estimate exist, we record
``max(reported, estimate)`` so the counter never under-counts vs. true exposure.

Environment:

- ``ELITE_SPEND_GUARD`` — ``1`` (default) enables this guard; ``0`` disables (tests / emergency).
- ``ELITE_SPEND_CAP_FRACTION`` — default ``0.25``.
- ``ELITE_SPEND_HEADROOM_FRACTION`` — default ``0.03`` (tightens cap downward).
- ``ELITE_SPEND_ESTIMATE_USD_PER_MILLION`` — fallback cost when no ``cost_info`` (elite-only path); default ``10.0``.
- ``ELITE_SPEND_WRITE_RETRIES`` — default ``3`` (Firestore transaction retries).
- ``ELITE_SPEND_TRIAL_CAP_USD`` — fixed USD cap during Standard free trial (default ``3.0``).
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from google.cloud import firestore

from ..firestore_db import get_firestore_client, is_firestore_available
from .pricing import PricingTierManager, TierName
from .subscription_access import is_trialing_standard_subscription

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


def spend_headroom_fraction() -> float:
    """Extra tightness below nominal cap (0.03 => use 97% of nominal cap)."""
    try:
        return max(0.0, min(0.5, float(os.getenv("ELITE_SPEND_HEADROOM_FRACTION", "0.03"))))
    except ValueError:
        return 0.03


def spend_write_retries() -> int:
    try:
        return max(1, min(10, int(os.getenv("ELITE_SPEND_WRITE_RETRIES", "3"))))
    except ValueError:
        return 3


def trial_spend_cap_usd() -> float:
    """Fixed elite orchestration cap during Standard 3-day trial."""
    try:
        return max(0.0, float(os.getenv("ELITE_SPEND_TRIAL_CAP_USD", "3.0")))
    except ValueError:
        return 3.0


def resolve_effective_spend_cap_usd(
    tier: TierName,
    subscription: Optional[Dict[str, Any]],
) -> Tuple[float, float]:
    """Return ``(monthly_revenue_usd, effective_cap_usd)`` for gating/UI."""
    if is_trialing_standard_subscription(subscription):
        return (0.0, trial_spend_cap_usd())
    rev = resolve_monthly_revenue_usd(tier, subscription)
    return (rev, effective_spend_cap_usd(rev))


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
        qty = max(1, seats)
        if cycle == "annual":
            return (pt.annual_price_usd / 12.0) * qty
        return pt.monthly_price_usd * qty

    if cycle == "annual":
        return pt.annual_price_usd / 12.0
    return pt.monthly_price_usd


def compute_period_key(subscription: Optional[Dict[str, Any]]) -> str:
    """Stable key for the current Stripe / subscription billing window."""
    sub = subscription or {}
    if is_trialing_standard_subscription(sub):
        start = _as_utc_dt(sub.get("trial_start"))
        end = _as_utc_dt(sub.get("trial_end"))
        if start and end:
            return f"trial_{start.date().isoformat()}_{end.date().isoformat()}"
    start = _as_utc_dt(sub.get("current_period_start"))
    end = _as_utc_dt(sub.get("current_period_end"))
    if start and end:
        return f"{start.date().isoformat()}_{end.date().isoformat()}"
    return datetime.now(timezone.utc).strftime("%Y-%m")


def compute_spend_cap_usd(monthly_revenue_usd: float) -> float:
    """Nominal USD cap before headroom (revenue * fraction)."""
    return max(0.0, float(monthly_revenue_usd) * spend_cap_fraction())


def effective_spend_cap_usd(monthly_revenue_usd: float) -> float:
    """Cap used for gating and stored on docs — tighter than nominal for safety."""
    nominal = compute_spend_cap_usd(monthly_revenue_usd)
    hr = spend_headroom_fraction()
    return max(0.0, nominal * (1.0 - hr))


def _doc_ref(db: Any, user_id: str):
    return db.collection(COLLECTION).document(_sanitize_doc_id(user_id))


def read_spend_document(user_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Read elite spend control doc.

    Returns:
        ``(True, dict)`` — document exists.
        ``(True, None)`` — no document yet (treat spent as 0).
        ``(False, None)`` — Firestore/client/read error: **caller must fail-closed**.
    """
    db = get_firestore_client()
    if not db:
        return (False, None)
    try:
        snap = _doc_ref(db, user_id).get()
        if snap.exists:
            return (True, snap.to_dict() or {})
        return (True, None)
    except Exception as exc:
        logger.error("read_spend_document failed user_id=%s: %s", user_id, exc)
        return (False, None)


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
        rev, cap = resolve_effective_spend_cap_usd(tier, subscription)
        return {
            "guard_active": True,
            "monthly_revenue_usd": rev,
            "cap_usd": cap,
            "spent_usd": cap,
            "period_key": compute_period_key(subscription),
            "fail_closed": True,
            "is_trial": is_trialing_standard_subscription(subscription),
        }

    rev, cap = resolve_effective_spend_cap_usd(tier, subscription)
    expected_pk = compute_period_key(subscription)
    read_ok, doc = read_spend_document(user_id)
    if not read_ok:
        logger.warning("get_spend_status: spend read failed; fail-closed user_id=%s", user_id)
        return {
            "guard_active": True,
            "monthly_revenue_usd": rev,
            "cap_usd": cap,
            "spent_usd": cap,
            "period_key": expected_pk,
            "fail_closed": True,
            "is_trial": is_trialing_standard_subscription(subscription),
        }

    spent = 0.0
    cap_doc = cap
    if doc:
        if doc.get("period_key") == expected_pk:
            spent = float(doc.get("spent_usd", 0.0) or 0.0)
            cap_doc = min(float(doc.get("cap_usd", cap) or cap), cap)
        else:
            spent = 0.0
    return {
        "guard_active": True,
        "monthly_revenue_usd": rev,
        "cap_usd": cap_doc,
        "spent_usd": spent,
        "period_key": expected_pk,
        "fail_closed": False,
        "is_trial": is_trialing_standard_subscription(subscription),
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

    rev, cap = resolve_effective_spend_cap_usd(tier, subscription)
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

    last_exc: Optional[Exception] = None
    for attempt in range(spend_write_retries()):
        try:
            transaction = db.transaction()
            _txn(transaction)
            logger.info(
                "record_elite_spend user_id=%s +$%.4f -> period=%s cap=$%.2f (attempt %d)",
                user_id,
                delta,
                period_key,
                cap,
                attempt + 1,
            )
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "record_elite_spend attempt %d/%d failed user_id=%s: %s",
                attempt + 1,
                spend_write_retries(),
                user_id,
                exc,
            )
            if attempt + 1 < spend_write_retries():
                time.sleep(0.05 * (2**attempt))

    logger.error(
        "record_elite_spend EXHAUSTED retries user_id=%s delta=$%.4f: %s",
        user_id,
        delta,
        last_exc,
    )


def extract_request_cost_usd(
    *,
    cost_info: Optional[Dict[str, Any]],
    elite_total_tokens: Optional[int],
) -> float:
    """Ledger cost: never under-count — ``max(reported, token_estimate)`` when both exist."""
    reported = 0.0
    if cost_info:
        raw = cost_info.get("cost_usd")
        if raw is None:
            raw = cost_info.get("total_cost")
        try:
            reported = max(0.0, float(raw or 0.0))
        except (TypeError, ValueError):
            reported = 0.0

    estimate = 0.0
    tok = int(elite_total_tokens or 0)
    if tok > 0:
        rate = estimate_elite_cost_usd_per_million()
        estimate = (tok / 1_000_000.0) * rate

    return max(reported, estimate)
