"""Tests for monthly query quota enforcement."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from llmhive.app.billing import query_quota as quota_mod
from llmhive.app.billing.query_quota import enforce_monthly_query_quota
from llmhive.app.middleware.tier_check import TierName


def test_paid_tier_unlimited_skips_quota(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_tier", lambda _uid: TierName.PRO)
    enforce_monthly_query_quota("paid_user")


def test_free_tier_blocks_at_limit(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_tier", lambda _uid: TierName.FREE)
    monkeypatch.setattr(quota_mod, "is_firestore_available", lambda: True)
    monkeypatch.setattr(quota_mod, "get_monthly_query_usage", lambda _uid: 50)
    with pytest.raises(HTTPException) as exc:
        enforce_monthly_query_quota("free_user")
    assert exc.value.status_code == 429


def test_free_tier_allows_under_limit(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_tier", lambda _uid: TierName.FREE)
    monkeypatch.setattr(quota_mod, "is_firestore_available", lambda: True)
    monkeypatch.setattr(quota_mod, "get_monthly_query_usage", lambda _uid: 10)
    enforce_monthly_query_quota("free_user")
