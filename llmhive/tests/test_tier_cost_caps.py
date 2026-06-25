"""Tests for shared tier per-request cost caps."""
from __future__ import annotations

from llmhive.app.billing.tier_cost_caps import (
    per_request_max_cost_usd,
    prefer_cheaper_default,
    resolve_per_request_max_cost_usd,
)


def test_per_request_caps_by_tier():
    assert per_request_max_cost_usd("free") == 0.1
    assert per_request_max_cost_usd("standard") == 0.35
    assert per_request_max_cost_usd("premium") == 0.75
    assert per_request_max_cost_usd("enterprise") == 2.0


def test_prefer_cheaper_defaults():
    assert prefer_cheaper_default("free") is True
    assert prefer_cheaper_default("pro") is False


def test_resolve_honors_client_override():
    assert resolve_per_request_max_cost_usd("free", 0.5) == 0.5
    assert resolve_per_request_max_cost_usd("free", None) == 0.1
