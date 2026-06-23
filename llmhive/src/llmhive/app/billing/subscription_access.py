"""Shared subscription access rules for app/paid/trial gating."""
from __future__ import annotations

from typing import Optional

# Mirrors lib/billing/entitlement.ts PAID_TIERS
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

# Standard trial is offered on lite (Stripe product: LLMHive Standard)
STANDARD_TRIAL_TIER_NAMES = frozenset({"lite", "standard", "basic", "starter"})

GRANTING_APP_ACCESS_STATUSES = frozenset({"active", "trialing"})


def _tier_name(sub: dict) -> str:
    return str(sub.get("tier_name") or sub.get("tier") or "").strip().lower()


def _status(sub: dict) -> str:
    return str(sub.get("status") or "").strip().lower()


def subscription_grants_app_access(sub: Optional[dict]) -> bool:
    """Active paid plan, trialing Standard, or provisioned free tier."""
    if not sub:
        return False
    if _status(sub) not in GRANTING_APP_ACCESS_STATUSES:
        return False
    tier = _tier_name(sub)
    return tier in PAID_TIER_NAMES or tier == "free"


def subscription_grants_paid_access(sub: Optional[dict]) -> bool:
    """Active or trialing paid subscription."""
    if not sub:
        return False
    if _status(sub) not in GRANTING_APP_ACCESS_STATUSES:
        return False
    return _tier_name(sub) in PAID_TIER_NAMES


def is_trialing_standard_subscription(sub: Optional[dict]) -> bool:
    """True when user is in Stripe trial on Standard (lite) tier."""
    if not sub:
        return False
    if _status(sub) != "trialing":
        return False
    return _tier_name(sub) in STANDARD_TRIAL_TIER_NAMES
