"""Tier-appropriate routing — frontier when warranted, cost-efficient otherwise."""
from __future__ import annotations

import pytest

from llmhive.app.intelligence.elite_policy import ELITE_POLICY
from llmhive.app.intelligence.routing_engine import get_routing_engine
from llmhive.app.intelligence.tier_routing import (
    map_orchestrator_task_to_category,
    should_use_frontier_primary,
)
from llmhive.app.services.orchestrator_adapter import (
    OPENROUTER_CLAUDE_OPUS_4_8,
    OPENROUTER_GEMINI_3_1_PRO,
    PREMIUM_MODELS,
)


def test_premium_models_include_latest_frontier_slugs():
    assert OPENROUTER_CLAUDE_OPUS_4_8 in PREMIUM_MODELS
    assert OPENROUTER_GEMINI_3_1_PRO in PREMIUM_MODELS


def test_map_orchestrator_task_to_category():
    assert map_orchestrator_task_to_category("code_generation") == "coding"
    assert map_orchestrator_task_to_category("math_problem") == "math"
    assert map_orchestrator_task_to_category("fast_response") == "dialogue"


@pytest.mark.parametrize(
    "accuracy, task, expected",
    [
        (5, "general", True),
        (4, "fast_response", True),
        (3, "code_generation", True),
        (3, "fast_response", False),
        (2, "code_generation", False),
        (3, "general", False),
    ],
)
def test_should_use_frontier_primary_elite_tier(accuracy, task, expected):
    category = map_orchestrator_task_to_category(task)
    assert should_use_frontier_primary(
        category,
        use_elite_tier=True,
        accuracy_level=accuracy,
        prefer_cheaper=False,
        orchestrator_task=task,
    ) is expected


def test_should_not_use_frontier_on_free_tier():
    assert not should_use_frontier_primary(
        "coding",
        use_elite_tier=False,
        accuracy_level=5,
        orchestrator_task="code_generation",
    )


def test_should_not_use_frontier_when_prefer_cheaper():
    assert not should_use_frontier_primary(
        "coding",
        use_elite_tier=True,
        accuracy_level=5,
        prefer_cheaper=True,
        orchestrator_task="code_generation",
    )


def test_select_tier_appropriate_uses_elite_policy_for_demanding_elite_work():
    engine = get_routing_engine()
    scored = engine.select_tier_appropriate(
        "coding",
        use_elite_tier=True,
        accuracy_level=4,
        orchestrator_task="code_generation",
        top_n=1,
    )
    assert scored
    assert scored[0].model_id == ELITE_POLICY["coding"]


def test_select_tier_appropriate_cost_efficient_for_simple_elite_chat():
    engine = get_routing_engine()
    frontier = engine.select_tier_appropriate(
        "dialogue",
        use_elite_tier=True,
        accuracy_level=3,
        orchestrator_task="fast_response",
        top_n=1,
    )
    cheap = engine.select("dialogue", top_n=1)
    assert frontier and cheap
    assert frontier[0].model_id == cheap[0].model_id


def test_select_tier_appropriate_adds_non_frontier_secondary():
    engine = get_routing_engine()
    scored = engine.select_tier_appropriate(
        "reasoning",
        use_elite_tier=True,
        accuracy_level=4,
        orchestrator_task="reasoning",
        top_n=2,
    )
    assert len(scored) >= 1
    assert scored[0].model_id == ELITE_POLICY["reasoning"]
    if len(scored) > 1:
        assert scored[1].model_id != scored[0].model_id
