import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_category_benchmarks import (
    _build_multilingual_fallback_config,
    _build_mmlu_alt_recovery_prompt,
    _build_mmlu_primary_prompt,
    _mmlu_yes_no_outcome_guidance,
    _sanitize_regression_score,
)


def test_yes_no_outcome_guidance_added_for_prevail_question() -> None:
    guidance = _mmlu_yes_no_outcome_guidance(
        "Will they likely prevail on their tort claim despite the company's defense that the decedents were trespassers?",
        [
            "Yes, because even though they trespassed, the owner had a duty to warn because it knew that they were in danger.",
            "Yes, because the owner was strictly liable for any injuries caused by the hazardous condition of the water in the lake.",
            "No, because owner owes no duty to trespassers except if it acts with willful or wanton disregard.",
            "No, because an owner of land never has to worry about protecting the safety of trespassers.",
        ],
    )
    assert "YES/NO outcome question" in guidance
    assert "Do NOT reinterpret it as 'which statement is incorrect'" in guidance


def test_yes_no_outcome_guidance_not_added_for_standard_mcq() -> None:
    guidance = _mmlu_yes_no_outcome_guidance(
        "Which federal government transportation change during Eisenhower's administration of the 1950s did the government promote?",
        [
            "urban mass transit",
            "automobile pollution research",
            "interstate highways",
            "national railroad passenger service",
        ],
    )
    assert guidance == ""


def test_primary_prompt_emphasizes_original_question() -> None:
    prompt = _build_mmlu_primary_prompt(
        "Will they likely prevail?\n\nA) Yes, because ...\nB) Yes, because ...\nC) No, because ...\nD) No, because ..."
    )
    assert "Select the single best answer to the original question as written." in prompt
    assert "Do not reinterpret the task." in prompt
    assert "When options begin with Yes/No plus explanations" in prompt


def test_alt_recovery_prompt_requires_re_evaluation_and_elimination() -> None:
    prompt = _build_mmlu_alt_recovery_prompt(
        "Will they likely prevail?\n\nA) Yes, because ...\nB) Yes, because ...\nC) No, because ...\nD) No, because ..."
    )
    assert "Re-evaluate this MMLU multiple-choice question from scratch." in prompt
    assert "Explicitly eliminate the wrong choices" in prompt
    assert "For Yes/No answer choices, decide the real outcome first" in prompt
    assert "FINAL_ANSWER: <letter>" in prompt


def test_multilingual_fallback_config_forces_provider_switch() -> None:
    config = _build_multilingual_fallback_config()

    assert config["accuracy_level"] == 5
    assert config["enable_verification"] is False
    assert config["use_deep_consensus"] is False
    assert config["force_provider_switch"] is True
    assert config["preferred_model"] == "claude-sonnet-4.6"


def test_sanitize_regression_score_clamps_invalid_percentage_baseline() -> None:
    assert _sanitize_regression_score("multilingual", 120.0) == 100.0
    assert _sanitize_regression_score("coding", -5.0) == 0.0
    assert _sanitize_regression_score("dialogue", 12.0) == 10.0
