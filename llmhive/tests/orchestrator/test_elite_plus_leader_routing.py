"""Unit tests for Elite+ leader-aware routing (ELITE_PLUS_LEADER_HINTS_ENABLED)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

# Import after potential env setup; we patch module-level flag
from llmhive.app.orchestration.elite_plus_orchestrator import (
    choose_paid_anchor,
    _PAID_ANCHORS,
    _leader_hint_anchor,
    _launch_mode_cost_ok,
    _estimate_cost,
    ELITE_PLUS_LEADER_HINTS_ENABLED,
)


class TestLeaderHintsFlagOff:
    """With ELITE_PLUS_LEADER_HINTS_ENABLED=0, behavior is identical to default."""

    def test_choose_paid_anchor_returns_default_when_flag_off(self):
        """Flag OFF: choose_paid_anchor returns _PAID_ANCHORS value, not leader."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LEADER_HINTS_ENABLED",
            False,
        ):
            # Coding default is anthropic/claude-sonnet-4; with leaders ON it would be claude-opus-4.6
            assert choose_paid_anchor("coding", []) == _PAID_ANCHORS["coding"]
            assert choose_paid_anchor("reasoning", []) == _PAID_ANCHORS["reasoning"]
            assert choose_paid_anchor("math", []) == _PAID_ANCHORS["math"]
            assert choose_paid_anchor("tool_use", []) == _PAID_ANCHORS["tool_use"]

    def test_leader_hint_returns_none_when_flag_off(self):
        """_leader_hint_anchor returns None when flag is OFF."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LEADER_HINTS_ENABLED",
            False,
        ):
            assert _leader_hint_anchor("coding") is None
            assert _leader_hint_anchor("reasoning") is None


class TestLeaderHintsFlagOn:
    """With ELITE_PLUS_LEADER_HINTS_ENABLED=1, prefer leader when available."""

    def test_choose_paid_anchor_returns_leader_for_coding_when_available(self):
        """Flag ON: coding category returns Claude Opus 4.6 (leader) when leaders JSON exists."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LEADER_HINTS_ENABLED",
            True,
        ):
            anchor = choose_paid_anchor("coding", [])
            # coding_humaneval leader is Claude Opus 4.6 -> anthropic/claude-opus-4.6
            assert anchor == "anthropic/claude-opus-4.6"

    def test_choose_paid_anchor_returns_leader_for_math_when_available(self):
        """Flag ON: math category returns GLM 4.7 (leader) when leaders JSON exists."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LEADER_HINTS_ENABLED",
            True,
        ):
            anchor = choose_paid_anchor("math", [])
            assert anchor == "zhipuai/glm-4.7"

    def test_choose_paid_anchor_falls_back_for_unknown_category(self):
        """Flag ON: category not in leaders (e.g. speed) falls back to default."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LEADER_HINTS_ENABLED",
            True,
        ):
            anchor = choose_paid_anchor("speed", [])
            assert anchor == _PAID_ANCHORS["speed"]

    def test_leader_hint_returns_none_when_leaders_missing(self):
        """_leader_hint_anchor returns None when leaders JSON is missing."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LEADER_HINTS_ENABLED",
            True,
        ), patch(
            "llmhive.app.orchestration.elite_plus_orchestrator._load_category_leaders",
            return_value=[],
        ):
            assert _leader_hint_anchor("coding") is None


class TestCostSafety:
    """Spend governor / cost ceiling: leader hints cannot cause spend violations."""

    def test_launch_mode_cost_ok_blocks_expensive_model(self):
        """When predicted cost exceeds ceiling, _launch_mode_cost_ok returns False."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LAUNCH_MODE",
            True,
        ), patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_MAX_COST_USD_REQUEST",
            0.025,
        ):
            # Claude Opus 4.6: 75 per 1M -> 500 tokens = 0.0375, exceeds 0.025
            ok = _launch_mode_cost_ok(0.0, "anthropic/claude-opus-4.6")
            assert ok is False

    def test_launch_mode_cost_ok_allows_cheap_model(self):
        """When predicted cost within ceiling, _launch_mode_cost_ok returns True."""
        with patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_LAUNCH_MODE",
            True,
        ), patch(
            "llmhive.app.orchestration.elite_plus_orchestrator.ELITE_PLUS_MAX_COST_USD_REQUEST",
            0.025,
        ):
            ok = _launch_mode_cost_ok(0.0, "openai/gpt-4o-mini")
            assert ok is True

    def test_estimate_cost_uses_leader_model_rates(self):
        """Leader models have cost estimates for budget tracking."""
        cost = _estimate_cost("anthropic/claude-opus-4.6", output_tokens=500)
        assert cost > 0
        cost_mini = _estimate_cost("openai/gpt-4o-mini", output_tokens=500)
        assert cost_mini < cost


class TestDefaultFlagState:
    """Default production: ELITE_PLUS_LEADER_HINTS_ENABLED is OFF."""

    def test_default_flag_is_off(self):
        """By default, leader hints are disabled (no production change)."""
        assert ELITE_PLUS_LEADER_HINTS_ENABLED is False
