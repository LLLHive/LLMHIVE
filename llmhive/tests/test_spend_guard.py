"""Unit tests for elite spend cap vs subscription revenue."""
from __future__ import annotations

import os

import pytest

from llmhive.app.billing import spend_guard as spend_guard_mod
from llmhive.app.billing.spend_guard import (
    compute_spend_cap_usd,
    effective_spend_cap_usd,
    extract_request_cost_usd,
    resolve_monthly_revenue_usd,
    spend_cap_exceeded,
)
from llmhive.app.middleware.tier_check import TierName


def test_premium_monthly_cap_is_quarter_revenue(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_GUARD", "1")
    monkeypatch.setenv("ELITE_SPEND_CAP_FRACTION", "0.25")
    monkeypatch.setenv("ELITE_SPEND_HEADROOM_FRACTION", "0")
    rev = resolve_monthly_revenue_usd(TierName.PRO, {"billing_cycle": "monthly"})
    assert rev == 20.0
    assert compute_spend_cap_usd(rev) == 5.0
    assert effective_spend_cap_usd(rev) == 5.0


def test_effective_cap_default_headroom(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_CAP_FRACTION", "0.25")
    monkeypatch.setenv("ELITE_SPEND_HEADROOM_FRACTION", "0.03")
    rev = 20.0
    assert effective_spend_cap_usd(rev) == pytest.approx(5.0 * 0.97)


def test_standard_paid_monthly_cap(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_GUARD", "1")
    rev = resolve_monthly_revenue_usd(TierName.LITE, {"billing_cycle": "monthly"})
    assert rev == 10.0
    assert compute_spend_cap_usd(rev) == 2.5


def test_enterprise_seats(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_GUARD", "1")
    rev = resolve_monthly_revenue_usd(
        TierName.ENTERPRISE,
        {"billing_cycle": "monthly", "seats": 5},
    )
    assert rev == 35.0 * 5
    assert compute_spend_cap_usd(rev) == pytest.approx(43.75)


def test_extract_cost_prefers_cost_info(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_ESTIMATE_USD_PER_MILLION", "10.0")
    v = extract_request_cost_usd(cost_info={"cost_usd": 0.42}, elite_total_tokens=1_000)
    assert v == pytest.approx(0.42)


def test_extract_cost_max_reported_and_estimate(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_ESTIMATE_USD_PER_MILLION", "10.0")
    v = extract_request_cost_usd(cost_info={"cost_usd": 1.0}, elite_total_tokens=1_000_000)
    assert v == pytest.approx(10.0)


def test_extract_cost_fallback_tokens(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_ESTIMATE_USD_PER_MILLION", "10.0")
    v = extract_request_cost_usd(cost_info=None, elite_total_tokens=500_000)
    assert v == pytest.approx(5.0)


def test_spend_cap_exceeded_free_tier(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_GUARD", "1")
    assert spend_cap_exceeded("any", TierName.FREE, {}) is False


def test_spend_cap_exceeded_on_read_failure(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_GUARD", "1")
    monkeypatch.setenv("ELITE_SPEND_HEADROOM_FRACTION", "0")
    monkeypatch.setattr(spend_guard_mod, "read_spend_document", lambda _uid: (False, None))
    assert spend_cap_exceeded("u1", TierName.PRO, {"billing_cycle": "monthly"}) is True


def test_trialing_standard_uses_fixed_trial_cap(monkeypatch):
    monkeypatch.setenv("ELITE_SPEND_GUARD", "1")
    monkeypatch.setenv("ELITE_SPEND_TRIAL_CAP_USD", "3.0")
    monkeypatch.setenv("ELITE_SPEND_HEADROOM_FRACTION", "0")
    monkeypatch.setattr(spend_guard_mod, "read_spend_document", lambda _uid: (True, None))
    sub = {
        "status": "trialing",
        "tier_name": "lite",
        "trial_start": "2026-06-10T00:00:00+00:00",
        "trial_end": "2026-06-13T00:00:00+00:00",
    }
    status = spend_guard_mod.get_spend_status("u1", TierName.LITE, sub)
    assert status["cap_usd"] == 3.0
    assert status["is_trial"] is True
    assert spend_cap_exceeded("u1", TierName.LITE, sub) is False
