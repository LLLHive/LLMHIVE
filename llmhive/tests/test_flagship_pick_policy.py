"""Enterprise-only single flagship model pick policy."""
from __future__ import annotations

import pytest

from llmhive.app.billing.flagship_pick import (
    apply_flagship_pick_policy,
    is_explicit_model_selection,
    subscription_allows_single_flagship_pick,
)
from llmhive.app.models.orchestration import AgentMode, ChatRequest, DomainPack


class TestSubscriptionAllowsSingleFlagshipPick:
    @pytest.mark.parametrize("tier,allowed", [
        ("enterprise", True),
        ("maximum", True),
        ("pro", False),
        ("lite", False),
        ("free", False),
    ])
    def test_tier_gate(self, tier: str, allowed: bool):
        assert subscription_allows_single_flagship_pick(tier) is allowed


class TestExplicitModelSelection:
    def test_automatic_is_not_explicit(self):
        assert is_explicit_model_selection(None) is False
        assert is_explicit_model_selection([]) is False
        assert is_explicit_model_selection(["automatic"]) is False

    def test_openrouter_slug_is_explicit(self):
        assert is_explicit_model_selection(["openai/gpt-5.5-pro"]) is True


def _base_request(**updates):
    payload = {
        "prompt": "Hello",
        "domain_pack": DomainPack.default,
        "agent_mode": AgentMode.team,
        "models": None,
    }
    payload.update(updates)
    return ChatRequest(**payload)


class TestApplyFlagshipPickPolicy:
    def test_enterprise_allows_single_and_explicit_models(self):
        req = _base_request(
            agent_mode=AgentMode.single,
            models=["openai/gpt-5.5-pro"],
        )
        out, gated = apply_flagship_pick_policy(req, "enterprise")
        assert gated is False
        assert out.agent_mode == AgentMode.single
        assert out.models == ["openai/gpt-5.5-pro"]

    def test_pro_downgrades_single_mode(self):
        req = _base_request(agent_mode=AgentMode.single)
        out, gated = apply_flagship_pick_policy(req, "pro")
        assert gated is True
        assert out.agent_mode == AgentMode.team
        assert out.models is None

    def test_pro_downgrades_explicit_models(self):
        req = _base_request(models=["openai/o3"])
        out, gated = apply_flagship_pick_policy(req, "pro")
        assert gated is True
        assert out.agent_mode == AgentMode.team
        assert out.models is None

    def test_pro_allows_automatic_team(self):
        req = _base_request(agent_mode=AgentMode.team, models=None)
        out, gated = apply_flagship_pick_policy(req, "pro")
        assert gated is False
        assert out.agent_mode == AgentMode.team
