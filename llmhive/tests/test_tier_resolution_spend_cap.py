"""Tests for spend-cap tier resolution (explicit elite downgrade)."""
from __future__ import annotations

import os

import pytest

from llmhive.app.models.orchestration import ChatMetadata, ChatRequest, ModelTier
from llmhive.app.services import orchestrator_adapter as adapter_mod
from llmhive.app.services.orchestrator_adapter import _resolve_request_model_tier_from_subscription


@pytest.fixture(autouse=True)
def _enable_tier_resolution(monkeypatch):
    monkeypatch.setenv("ORCH_RESOLVE_TIER_FROM_USER", "1")


def _chat_request(tier: ModelTier = ModelTier.auto) -> ChatRequest:
    return ChatRequest(
        prompt="hello",
        metadata=ChatMetadata(user_id="user_test_1"),
        tier=tier,
    )


def test_explicit_elite_downgraded_when_spend_cap_forces_free(monkeypatch):
    monkeypatch.setattr(
        adapter_mod,
        "is_internal_scheduled_benchmark",
        lambda: False,
        raising=False,
    )
    monkeypatch.setattr(
        "llmhive.app.middleware.tier_check.get_orchestration_tier",
        lambda _uid: "free",
    )
    req = _resolve_request_model_tier_from_subscription(_chat_request(ModelTier.elite))
    assert req.tier == ModelTier.free


def test_auto_resolves_to_elite_when_allowed(monkeypatch):
    monkeypatch.setattr(
        "llmhive.app.middleware.tier_check.get_orchestration_tier",
        lambda _uid: "elite",
    )
    req = _resolve_request_model_tier_from_subscription(_chat_request(ModelTier.auto))
    assert req.tier == ModelTier.elite


def test_explicit_free_honored_even_when_elite_available(monkeypatch):
    monkeypatch.setattr(
        "llmhive.app.middleware.tier_check.get_orchestration_tier",
        lambda _uid: "elite",
    )
    req = _resolve_request_model_tier_from_subscription(_chat_request(ModelTier.free))
    assert req.tier == ModelTier.free


def test_skips_resolution_when_flag_off(monkeypatch):
    monkeypatch.setenv("ORCH_RESOLVE_TIER_FROM_USER", "0")
    monkeypatch.setattr(
        "llmhive.app.middleware.tier_check.get_orchestration_tier",
        lambda _uid: "free",
    )
    req = _resolve_request_model_tier_from_subscription(_chat_request(ModelTier.elite))
    assert req.tier == ModelTier.elite
