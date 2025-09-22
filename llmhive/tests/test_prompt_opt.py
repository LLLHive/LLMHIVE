from llmhive.app.orchestration.equalizer import OrchestrationProfile
from llmhive.app.orchestration.prompt_opt import PromptOptimizer


def test_prompt_optimizer_creates_variants():
    optimizer = PromptOptimizer()
    profile = OrchestrationProfile(
        num_models=2,
        num_samples=3,
        challenge_rounds=1,
        factcheck_enabled=True,
        creativity_boost=0.7,
        max_tokens=300,
        json_mode=False,
    )
    plan = optimizer.optimize("Describe three renewable energy sources and compare them.", profile)
    assert plan.core_prompt.startswith("Describe")
    assert len(plan.competing_variants) >= 2
    assert plan.segments
