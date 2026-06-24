"""Monthly query quota enforcement (free tier and other capped tiers)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from ..firestore_db import FirestoreUsageService, is_firestore_available
from ..middleware.tier_check import TierConfig, TierName, get_user_tier

logger = logging.getLogger(__name__)


def _monthly_query_limit(tier: TierName) -> int:
    """Return monthly query cap; 0 or negative means unlimited."""
    limit = TierConfig.get_limit(tier, "queries_per_month")
    try:
        return int(limit)
    except (TypeError, ValueError):
        return 0


def _start_of_utc_month() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_monthly_query_usage(user_id: str) -> int:
    if not is_firestore_available():
        return 0
    try:
        usage = FirestoreUsageService().get_user_usage(
            user_id,
            start_date=_start_of_utc_month(),
        )
        return int(usage.get("requests_count", 0) or 0)
    except Exception as exc:
        logger.error("get_monthly_query_usage failed user_id=%s: %s", user_id, exc)
        return 0


def enforce_monthly_query_quota(user_id: Optional[str]) -> None:
    """Raise HTTP 429 when the user's monthly query cap is exhausted."""
    uid = (user_id or "").strip()
    if not uid:
        return

    tier = get_user_tier(uid)
    limit = _monthly_query_limit(tier)
    if limit <= 0:
        return

    if not is_firestore_available():
        if tier == TierName.FREE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Usage tracking temporarily unavailable. Please retry shortly.",
            )
        return

    used = get_monthly_query_usage(uid)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Monthly query limit reached",
                "message": (
                    f"You have used {used} of {limit} queries this month. "
                    "Upgrade at /pricing for unlimited access."
                ),
                "limit": limit,
                "used": used,
                "tier": tier.value,
            },
        )


def record_monthly_query(user_id: Optional[str]) -> None:
    """Increment monthly query counter for capped tiers."""
    uid = (user_id or "").strip()
    if not uid:
        return

    tier = get_user_tier(uid)
    limit = _monthly_query_limit(tier)
    if limit <= 0:
        return

    if not is_firestore_available():
        return

    try:
        FirestoreUsageService().record_usage(uid, requests_count=1)
    except Exception as exc:
        logger.warning("record_monthly_query failed user_id=%s: %s", uid, exc)
