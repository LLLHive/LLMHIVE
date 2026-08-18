"""Standard (lite) monthly trial Checkout Session flags.

Card-required trial is the historic default (``payment_method_types=["card"]``).
No-card trial uses Stripe ``payment_method_collection=if_required`` plus
``trial_settings.end_behavior.missing_payment_method=cancel`` so access ends
after 3 days unless the customer adds a payment method.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping


def is_standard_monthly_trial(tier: str, billing_cycle: str) -> bool:
    return (tier or "").strip().lower() in {"lite", "standard", "basic", "starter"} and (
        billing_cycle or ""
    ).strip().lower() == "monthly"


def apply_trial_subscription_data(
    subscription_data: MutableMapping[str, Any],
    *,
    trial_days: int,
    no_card: bool,
) -> MutableMapping[str, Any]:
    if trial_days <= 0:
        return subscription_data
    subscription_data["trial_period_days"] = trial_days
    metadata = dict(subscription_data.get("metadata") or {})
    metadata["is_trial"] = "true"
    if no_card:
        metadata["trial_without_card"] = "true"
        subscription_data["trial_settings"] = {
            "end_behavior": {"missing_payment_method": "cancel"}
        }
    subscription_data["metadata"] = metadata
    return subscription_data


def apply_session_payment_collection(
    session_kwargs: MutableMapping[str, Any],
    *,
    no_card: bool,
) -> MutableMapping[str, Any]:
    """Mutate Checkout Session create kwargs. Card-required path stays explicit."""
    if no_card:
        session_kwargs.pop("payment_method_types", None)
        session_kwargs["payment_method_collection"] = "if_required"
    else:
        session_kwargs["payment_method_types"] = ["card"]
        session_kwargs.pop("payment_method_collection", None)
    return session_kwargs


def campaign_cancel_url(success_url: str, cancel_path: str | None) -> str | None:
    """Allow only same-origin relative paths such as ``/landing/grandmother-free``."""
    if not cancel_path or not cancel_path.startswith("/") or cancel_path.startswith("//"):
        return None
    if "://" in cancel_path or "\\" in cancel_path:
        return None
    from urllib.parse import urlparse

    parsed = urlparse(success_url or "")
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{cancel_path}"


def customer_used_standard_trial(subscriptions: Mapping[str, Any] | list) -> bool:
    """True if Stripe already recorded a Standard trial for this customer."""
    rows = subscriptions
    if isinstance(subscriptions, dict):
        rows = subscriptions.get("data") or subscriptions.get("subscriptions") or []
    if not isinstance(rows, list):
        return False
    for sub in rows:
        if not isinstance(sub, dict):
            continue
        metadata = sub.get("metadata") or {}
        if str(metadata.get("is_trial") or "").lower() == "true":
            return True
        if str(metadata.get("trial_without_card") or "").lower() == "true":
            return True
        if sub.get("trial_start") or sub.get("trial_end"):
            tier = str(metadata.get("tier") or "").lower()
            if tier in {"lite", "standard", "basic", "starter", ""}:
                return True
    return False
