from llmhive.app.orchestration.consensus import ConsensusBuilder
from llmhive.app.orchestration.ensemble import EnsembleOutput
from llmhive.app.orchestration.equalizer import OrchestrationProfile
from llmhive.app.orchestration.factcheck import FactCheckResult
from llmhive.app.orchestration.prompt_opt import PromptPlan
from llmhive.app.orchestration.voting import VoteSummary
from llmhive.app.core.constants import FactCheckMethod, FactCheckVerdict


def test_consensus_builder_generates_key_points():
    outputs = [
        EnsembleOutput(
            model_name="local:llama-3-8b",
            text="Expert synthesis: point one. point two.",
            tokens=120,
            latency_ms=12.0,
            cost_usd=0.0,
            score_quality=0.7,
            score_factuality=0.8,
            metadata={"temperature": 0.2},
        ),
        EnsembleOutput(
            model_name="openai:gpt-4o-mini",
            text="Alternate view discussing nuance.",
            tokens=140,
            latency_ms=50.0,
            cost_usd=0.01,
            score_quality=0.6,
            score_factuality=0.7,
            metadata={"temperature": 0.2},
        ),
    ]
    votes = VoteSummary(
        winner=outputs[0],
        scores={outputs[0].model_name: 0.7, outputs[1].model_name: 0.4},
        total_weight=1.1,
        ranked_outputs=outputs,
    )
    fact_checks = [
        FactCheckResult(
            model_name="local:llama-3-8b",
            claim="point one",
            method=FactCheckMethod.LLM,
            verdict=FactCheckVerdict.PASS,
            score=0.8,
            evidence={"note": "heuristic"},
        )
    ]
    builder = ConsensusBuilder()
    profile = OrchestrationProfile(
        num_models=2,
        num_samples=2,
        challenge_rounds=1,
        factcheck_enabled=True,
        creativity_boost=0.3,
        max_tokens=400,
        json_mode=False,
    )
    plan = PromptPlan(core_prompt="Explain", segments=["Explain"], competing_variants=["Explain"])
    consensus = builder.build(
        query="Explain",
        plan=plan,
        outputs=outputs,
        votes=votes,
        challenges=[],
        fact_checks=fact_checks,
        profile=profile,
    )
    assert consensus.key_points
    assert consensus.style_incognito
