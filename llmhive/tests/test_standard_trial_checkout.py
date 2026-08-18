"""Tests for Standard monthly trial Checkout Session flags (card vs no-card)."""

from __future__ import annotations

from llmhive.app.billing.standard_trial_checkout import (
    apply_session_payment_collection,
    apply_trial_subscription_data,
    campaign_cancel_url,
    customer_used_standard_trial,
    is_standard_monthly_trial,
)
from llmhive.app.billing.pricing import get_pricing_manager, TierName
from llmhive.app.api.payment_routes import CreateCheckoutRequest


def test_standard_account_uses_elite_orchestration():
    lite = get_pricing_manager().get_tier(TierName.LITE)
    assert lite is not None
    assert lite.display_name == "Standard"
    assert lite.limits.default_orchestration_tier == "elite"
    assert "elite_orchestration" in lite.features


def test_is_standard_monthly_trial_aliases():
    assert is_standard_monthly_trial("lite", "monthly") is True
    assert is_standard_monthly_trial("standard", "monthly") is True
    assert is_standard_monthly_trial("lite", "annual") is False
    assert is_standard_monthly_trial("pro", "monthly") is False


def test_card_required_checkout_keeps_explicit_card_types():
    kwargs = {"mode": "subscription", "payment_method_types": ["card"]}
    apply_session_payment_collection(kwargs, no_card=False)
    assert kwargs["payment_method_types"] == ["card"]
    assert "payment_method_collection" not in kwargs


def test_no_card_trial_uses_if_required_and_omits_card_types():
    kwargs = {"mode": "subscription", "payment_method_types": ["card"]}
    apply_session_payment_collection(kwargs, no_card=True)
    assert "payment_method_types" not in kwargs
    assert kwargs["payment_method_collection"] == "if_required"


def test_no_card_trial_cancels_without_payment_method():
    data: dict = {"metadata": {"user_id": "u1", "tier": "lite"}}
    apply_trial_subscription_data(data, trial_days=3, no_card=True)
    assert data["trial_period_days"] == 3
    assert data["metadata"]["is_trial"] == "true"
    assert data["metadata"]["trial_without_card"] == "true"
    assert data["trial_settings"]["end_behavior"]["missing_payment_method"] == "cancel"


def test_card_trial_does_not_set_missing_payment_cancel():
    data: dict = {"metadata": {"tier": "lite"}}
    apply_trial_subscription_data(data, trial_days=3, no_card=False)
    assert data["trial_period_days"] == 3
    assert data["metadata"]["is_trial"] == "true"
    assert "trial_without_card" not in data["metadata"]
    assert "trial_settings" not in data


def test_customer_used_standard_trial_detects_prior():
    assert customer_used_standard_trial({"data": []}) is False
    assert (
        customer_used_standard_trial(
            {"data": [{"metadata": {"is_trial": "true", "tier": "lite"}}]}
        )
        is True
    )
    assert (
        customer_used_standard_trial({"data": [{"trial_start": 1, "metadata": {"tier": "lite"}}]})
        is True
    )
    assert (
        customer_used_standard_trial({"data": [{"metadata": {"tier": "pro"}}]})
        is False
    )


def test_create_checkout_defaults_to_card_required():
    req = CreateCheckoutRequest(tier="lite", billing_cycle="monthly", user_id="u1")
    assert req.trial_without_card is False
    assert req.cancel_path is None


def test_campaign_cancel_url_same_origin_only():
    base = "https://llmhive.ai/billing/success"
    assert (
        campaign_cancel_url(base, "/landing/grandmother-free")
        == "https://llmhive.ai/landing/grandmother-free"
    )
    assert campaign_cancel_url(base, None) is None
    assert campaign_cancel_url(base, "//evil.example/phish") is None
    assert campaign_cancel_url(base, "https://evil.example/") is None
    assert campaign_cancel_url(base, "pricing") is None


def test_no_card_flag_is_ignored_for_premium():
    no_card = True and is_standard_monthly_trial("pro", "monthly")
    kwargs = {"mode": "subscription", "payment_method_types": ["card"]}
    apply_session_payment_collection(kwargs, no_card=no_card)
    assert kwargs["payment_method_types"] == ["card"]
    assert "payment_method_collection" not in kwargs
