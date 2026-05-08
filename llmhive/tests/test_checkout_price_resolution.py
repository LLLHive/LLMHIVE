"""Tests for ``payment_routes._price_id_for_checkout``.

Covers the strict mapping that prevents legacy $9.99 / $29.99 fallbacks:

- ``standard`` / ``lite`` resolve to ``STRIPE_PRICE_ID_STANDARD_*``.
- ``premium`` / ``pro`` resolve to ``STRIPE_PRICE_ID_PREMIUM_*``.
- ``enterprise`` / ``maximum`` resolve to their own slots.
- Annual vs monthly cycle picks the correct env-var slot.
- Unknown tier returns ``None``.

These tests guard the behaviour the user explicitly asked for: a Premium
checkout MUST NOT silently route to the old Pro $29.99 price.
"""
from __future__ import annotations

import pytest

from llmhive.app.api.payment_routes import _price_id_for_checkout
from llmhive.app.config import settings


def _set_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject deterministic price IDs onto the (already-instantiated) settings object."""
    monkeypatch.setattr(
        settings, "stripe_price_id_standard_monthly", "price_std_m", raising=False
    )
    monkeypatch.setattr(
        settings, "stripe_price_id_standard_annual", "price_std_y", raising=False
    )
    monkeypatch.setattr(
        settings, "stripe_price_id_premium_monthly", "price_prem_m", raising=False
    )
    monkeypatch.setattr(
        settings, "stripe_price_id_premium_annual", "price_prem_y", raising=False
    )
    monkeypatch.setattr(
        settings, "stripe_price_id_enterprise_monthly", "price_ent_m", raising=False
    )
    monkeypatch.setattr(
        settings, "stripe_price_id_enterprise_annual", "price_ent_y", raising=False
    )


@pytest.mark.parametrize(
    "tier,cycle,expected",
    [
        ("standard", "monthly", "price_std_m"),
        ("standard", "annual", "price_std_y"),
        ("lite", "monthly", "price_std_m"),
        ("lite", "annual", "price_std_y"),
        ("premium", "monthly", "price_prem_m"),
        ("premium", "annual", "price_prem_y"),
        ("pro", "monthly", "price_prem_m"),
        ("pro", "annual", "price_prem_y"),
        ("enterprise", "monthly", "price_ent_m"),
        ("enterprise", "annual", "price_ent_y"),
    ],
)
def test_price_id_resolution(
    monkeypatch: pytest.MonkeyPatch, tier: str, cycle: str, expected: str
) -> None:
    _set_prices(monkeypatch)
    assert _price_id_for_checkout(tier, cycle) == expected


def test_unknown_tier_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_prices(monkeypatch)
    assert _price_id_for_checkout("free", "monthly") is None
    assert _price_id_for_checkout("bogus", "annual") is None


def test_standard_does_not_collide_with_premium_prices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: a $20 Premium checkout must never resolve to Standard's $10 price.

    This was the user-reported defect that motivated the strict mapping.
    """
    _set_prices(monkeypatch)
    standard_monthly = _price_id_for_checkout("standard", "monthly")
    premium_monthly = _price_id_for_checkout("premium", "monthly")
    standard_annual = _price_id_for_checkout("standard", "annual")
    premium_annual = _price_id_for_checkout("premium", "annual")

    assert standard_monthly != premium_monthly
    assert standard_annual != premium_annual
    assert standard_monthly == "price_std_m"
    assert premium_monthly == "price_prem_m"
