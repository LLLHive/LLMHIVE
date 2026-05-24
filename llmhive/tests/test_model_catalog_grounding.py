"""Regression tests for scoped model-catalog grounding."""
from __future__ import annotations

from llmhive.app.services.orchestrator_adapter import (
    _apply_answer_quality_guardrails,
    _build_model_catalog_grounding,
    _build_deterministic_model_catalog_answer,
    _extract_consensus_guidance,
    _extract_correction_constraints,
    _is_model_catalog_recommendation_query,
)


def test_model_catalog_query_detector_skips_benchmarks():
    prompt = "rank the best free LLM models and connect them to our agent"

    assert _is_model_catalog_recommendation_query(prompt)
    assert _is_model_catalog_recommendation_query(
        prompt,
        {"benchmark_category": "answer_quality_replay"},
    )
    assert not _is_model_catalog_recommendation_query(
        prompt,
        {"benchmark_category": "multi_hop_reasoning"},
    )


def test_model_catalog_query_detector_catches_kimi_connection_checks():
    prompt = "review whether our Kimi connection through Moonshot.ai is working"

    assert _is_model_catalog_recommendation_query(
        prompt,
        {"benchmark_category": "answer_quality_replay"},
    )


def test_model_catalog_grounding_uses_exact_current_slugs():
    prompt = "rank the best free LLM Models as of 5/23/26 and connect them to our agent"

    context, info = _build_model_catalog_grounding(prompt, {})

    assert info["applied"] is True
    assert "deepseek/deepseek-chat" in context
    assert "qwen/qwen3" in context
    assert "exact model IDs" in context
    assert "GPT-Neo" in context  # included only as an explicit anti-recommendation
    assert "Do not recommend legacy models like GPT-Neo" in context


def test_paid_model_catalog_grounding_uses_frontier_slugs():
    context, info = _build_model_catalog_grounding(
        "rank the best paid LLM Models as of 5/23/26 and connect them to our agent",
        {},
    )

    assert info["applied"] is True
    assert info["tier"] == "paid"
    assert "anthropic/claude-opus-4.7" in context
    assert "openai/gpt-5.5-pro" in context
    assert "google/gemini-3.1-pro-preview" in context
    assert "moonshotai/kimi-k2.6" in context
    assert "Do not recommend stale paid models like GPT-4 Turbo" in context


def test_deterministic_paid_catalog_answer_uses_current_frontier_models():
    answer = _build_deterministic_model_catalog_answer(
        "rank the best paid LLM Models as of 5/23/26 and include the best way to connect to them to our agent",
        {},
    )

    assert "anthropic/claude-opus-4.7" in answer
    assert "openai/gpt-5.5-pro" in answer
    assert "google/gemini-3.1-pro-preview" in answer
    assert "moonshotai/kimi-k2.6" in answer
    assert "GPT-4 Turbo" in answer
    assert "stale" in answer
    assert ".Caveat" not in answer
    assert "v1.7." not in answer


def test_deterministic_free_catalog_answer_has_public_free_distinction():
    answer = _build_deterministic_model_catalog_answer(
        "rank the best free LLM Models as of 5/23/26 and include the best way to connect to them to our agent",
        {},
    )

    assert "meta-llama/llama-3.3-70b-instruct:free" in answer
    assert "qwen/qwen3-next-80b-a3b-instruct:free" in answer
    assert "deepseek/deepseek-chat" in answer
    assert "kimi-k2.6" in answer
    assert "public-free" in answer
    assert ".Caveat" not in answer


def test_kimi_is_not_marked_public_free_when_missing_from_catalog():
    context, info = _build_model_catalog_grounding(
        "include Kimi, DeepSeek, Llama, and Qwen with exact model numbers",
        {},
    )

    assert info["applied"] is True
    assert "Kimi/Moonshot note" in context
    assert "kimi-k2.6" in context
    assert "Kimi_K26_Api_Key" in context
    assert "https://api.moonshot.ai/v1" in context
    assert "must not be described as verified public-free" in context
    assert "https://platform.moonshot.ai/docs" in context


def test_correction_constraints_capture_user_requirements():
    history = [
        {"role": "assistant", "content": "Here are some models."},
        {"role": "user", "content": "Your answer is incomplete. Include Kimi, DeepSeek, Llama, Qwen, exact model numbers, and links."},
    ]

    context = _extract_correction_constraints(history)

    assert "USER CORRECTIONS" in context
    assert "exact model numbers" in context
    assert "Kimi" in context


def test_consensus_guidance_caveats_backend_confidence():
    context = _extract_consensus_guidance(
        "Explain why the app showed high consensus.",
        [
            {
                "role": "assistant",
                "content": "The backend consensus score was lexical/model agreement, not factual verification.",
            }
        ],
    )

    assert "model agreement" in context
    assert "not factual verification" in context
    assert "confidence" in context
    assert "quality" in context


def test_answer_quality_guardrails_append_missing_caveats():
    answer = "Kimi uses Moonshot through LLMHive. Consensus is model agreement."

    out = _apply_answer_quality_guardrails(
        answer,
        "Explain Kimi Moonshot and consensus confidence.",
        [],
    )

    assert "public free" in out
    assert "not factual verification, confidence, or quality" in out
