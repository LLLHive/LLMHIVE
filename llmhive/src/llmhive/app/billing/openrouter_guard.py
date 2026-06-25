"""Access and spend guards for the OpenRouter inference gateway."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from ..billing.access_guard import require_app_access
from ..billing.tier_cost_caps import per_request_max_cost_usd, resolve_per_request_max_cost_usd
from ..middleware.tier_check import (
    TierName,
    get_user_tier,
    is_user_throttled,
)

logger = logging.getLogger(__name__)


def enforce_openrouter_inference(user_id: Optional[str]) -> None:
    """Require app access and block paid users who exhausted the elite spend cap."""
    uid = (user_id or "").strip()
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="user_id is required for OpenRouter inference.",
        )

    require_app_access(uid)

    try:
        tier = get_user_tier(uid)
        if tier != TierName.FREE and is_user_throttled(uid):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Premium orchestration budget exhausted for this billing period. "
                    "Use main chat (free orchestration) or upgrade."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("openrouter guard tier check failed user_id=%s: %s", uid, exc)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription verification temporarily unavailable. Please retry shortly.",
        ) from exc


def default_max_cost_usd_for_user(user_id: str) -> float:
    tier = get_user_tier(user_id)
    return per_request_max_cost_usd(tier.value)


def resolve_openrouter_max_cost_usd(
    user_id: Optional[str],
    requested: Optional[float],
) -> float:
    uid = (user_id or "").strip()
    tier = get_user_tier(uid).value if uid else "free"
    return resolve_per_request_max_cost_usd(tier, requested)


def record_openrouter_spend(user_id: Optional[str], response: Dict[str, Any]) -> None:
    """Record provider cost from an OpenRouter completion toward the elite spend ledger."""
    uid = (user_id or "").strip()
    if not uid:
        return
    try:
        from ..billing import spend_guard as spend_guard_mod
        from ..billing.scheduled_benchmark import is_internal_scheduled_benchmark
        from ..firestore_db import FirestoreSubscriptionService

        if not spend_guard_mod.is_spend_guard_enabled() or is_internal_scheduled_benchmark():
            return

        tier = get_user_tier(uid)
        if tier == TierName.FREE:
            return

        usage = response.get("usage") if isinstance(response, dict) else None
        cost_usd = None
        if isinstance(usage, dict):
            raw = usage.get("cost")
            if raw is not None:
                try:
                    cost_usd = float(raw)
                except (TypeError, ValueError):
                    cost_usd = None

        total_tokens = None
        if isinstance(usage, dict) and usage.get("total_tokens") is not None:
            try:
                total_tokens = int(usage["total_tokens"])
            except (TypeError, ValueError):
                total_tokens = None

        extracted = spend_guard_mod.extract_request_cost_usd(
            cost_info={"cost_usd": cost_usd} if cost_usd is not None else None,
            elite_total_tokens=total_tokens,
        )
        if extracted <= 0:
            return

        sub = FirestoreSubscriptionService().get_user_subscription(uid)
        spend_guard_mod.record_elite_spend(uid, extracted, sub)
    except Exception as exc:
        logger.warning("record_openrouter_spend skipped user_id=%s: %s", uid, exc)
