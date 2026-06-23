"""Tests for shared subscription access rules (trial + paid gating)."""
from llmhive.app.billing.subscription_access import (
    is_trialing_standard_subscription,
    subscription_grants_app_access,
    subscription_grants_paid_access,
)


def test_trialing_lite_grants_access():
    sub = {"status": "trialing", "tier_name": "lite"}
    assert subscription_grants_app_access(sub) is True
    assert subscription_grants_paid_access(sub) is True
    assert is_trialing_standard_subscription(sub) is True


def test_trialing_pro_not_standard_trial():
    sub = {"status": "trialing", "tier_name": "pro"}
    assert subscription_grants_paid_access(sub) is True
    assert is_trialing_standard_subscription(sub) is False


def test_cancelled_does_not_grant_access():
    sub = {"status": "cancelled", "tier_name": "lite"}
    assert subscription_grants_app_access(sub) is False
    assert subscription_grants_paid_access(sub) is False
