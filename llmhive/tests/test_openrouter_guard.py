"""Tests for OpenRouter inference access guards."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from llmhive.app.billing import openrouter_guard as guard_mod
from llmhive.app.billing.openrouter_guard import (
    default_max_cost_usd_for_user,
    enforce_openrouter_inference,
    resolve_openrouter_max_cost_usd,
)
from llmhive.app.middleware.tier_check import TierName


def test_enforce_requires_user_id():
    with pytest.raises(HTTPException) as exc:
        enforce_openrouter_inference(None)
    assert exc.value.status_code == 402


def test_enforce_blocks_throttled_paid_user(monkeypatch):
    monkeypatch.setattr(guard_mod, "require_app_access", lambda _uid: None)
    monkeypatch.setattr(guard_mod, "get_user_tier", lambda _uid: TierName.PRO)
    monkeypatch.setattr(guard_mod, "is_user_throttled", lambda _uid: True)
    with pytest.raises(HTTPException) as exc:
        enforce_openrouter_inference("paid_user")
    assert exc.value.status_code == 402


def test_default_max_cost_by_tier(monkeypatch):
    monkeypatch.setattr(guard_mod, "get_user_tier", lambda _uid: TierName.FREE)
    assert default_max_cost_usd_for_user("u1") == pytest.approx(0.10)
    monkeypatch.setattr(guard_mod, "get_user_tier", lambda _uid: TierName.PRO)
    assert default_max_cost_usd_for_user("u1") == pytest.approx(0.75)


def test_resolve_respects_client_max_cost():
    assert resolve_openrouter_max_cost_usd("u1", 0.05) == pytest.approx(0.05)
