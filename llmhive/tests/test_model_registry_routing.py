from __future__ import annotations

import pytest

from llmhive.app.model_registry import ModelRegistry, performance_tracker, ModelPerformance
from llmhive.app.services.base import LLMProvider


class _DummyProvider(LLMProvider):
    async def complete(self, prompt: str, *, model: str):
        raise NotImplementedError


@pytest.mark.parametrize(
    "required_role,required_caps",
    [
        ("draft", ["reasoning"]),
        ("research", ["retrieval", "analysis"]),
    ],
)
def test_suggest_team_prefers_higher_quality_models(monkeypatch, required_role, required_caps):
    """ModelRegistry.suggest_team should be sensitive to performance tracker metrics.

    We run routing once with no history, then again with biased performance metrics
    and verify that a previously lower-ranked model can be promoted.
    """

    providers = {
        "openai": _DummyProvider(),
        "anthropic": _DummyProvider(),
        "grok": _DummyProvider(),
    }
    registry = ModelRegistry(providers)

    # Start with an empty performance snapshot so selection is purely capability-based.
    monkeypatch.setattr(
        performance_tracker, "snapshot", lambda: {}, raising=False
    )

    baseline_team = registry.suggest_team(
        [required_role],
        [required_caps],
    )

    # We need at least two candidates to observe a change in ordering.
    assert len(baseline_team) >= 2
    initially_best = baseline_team[0]
    candidate_to_promote = baseline_team[1]

    # Construct a biased performance snapshot where the second candidate has
    # extremely strong historical performance and the first one very weak.
    high_perf = ModelPerformance(
        model=candidate_to_promote,
        total_tokens=10_000,
        total_cost=1.0,
        calls=100,
        success_count=95,
        failure_count=5,
        quality_scores=[0.9, 0.95, 0.92],
    )
    low_perf = ModelPerformance(
        model=initially_best,
        total_tokens=10_000,
        total_cost=1.0,
        calls=100,
        success_count=10,
        failure_count=90,
        quality_scores=[0.1, 0.2],
    )

    def _biased_snapshot():
        return {
            candidate_to_promote: high_perf,
            initially_best: low_perf,
        }

    monkeypatch.setattr(
        performance_tracker, "snapshot", _biased_snapshot, raising=False
    )

    promoted_team = registry.suggest_team(
        [required_role],
        [required_caps],
    )

    # Under strongly biased metrics, the previously second model should now be preferred.
    assert promoted_team[0] == candidate_to_promote


