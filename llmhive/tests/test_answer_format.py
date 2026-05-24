"""Tests for enterprise answer_format pipeline."""
from __future__ import annotations

from llmhive.app.orchestration.answer_format import (
    apply_answer_format,
    format_as_markdown_bullets,
    format_as_markdown_numbered,
    infer_format_from_query,
    looks_like_markdown_list,
    resolve_profile,
    FormatProfile,
)


def test_inline_bullet_paragraph_becomes_vertical_list():
    raw = (
        "Here are the top platforms by users: • Facebook — 2.6B users • "
        "Instagram — 2B users • WeChat — 1.3B users"
    )
    out = format_as_markdown_bullets(raw, "list the top social media platforms")
    assert looks_like_markdown_list(out)
    assert out.count("\n- ") >= 2 or out.startswith("- ")
    assert "•" not in out
    assert "Facebook" in out


def test_infer_format_list_query():
    assert infer_format_from_query("list the top 20 social media platforms") == "bullet"


def test_numbered_from_inline():
    raw = "Steps: 1. Plan 2. Build 3. Ship"
    out = format_as_markdown_numbered(raw, "how to deploy step by step")
    assert "1." in out
    assert "2." in out


def test_automatic_resolves_to_bullet_for_list_query():
    profile = resolve_profile("automatic", "list the best CRM tools")
    assert profile == FormatProfile.BULLET


def test_structured_adds_headings_for_long_multi_paragraph():
    raw = (
        "First topic explanation with enough detail to stand alone.\n\n"
        "Second topic with different focus and more sentences here.\n\n"
        "Third topic closing the response with final thoughts."
    )
    out = apply_answer_format(raw, "structured")
    assert "##" in out


def test_conversational_preserves_existing_markdown_list():
    raw = "- Alpha\n- Beta\n- Gamma"
    out = apply_answer_format(raw, "conversational")
    assert out.count("\n- ") >= 2
    assert "•" not in out


def test_concise_lead_plus_bullets():
    raw = (
        "Social media dominates modern marketing because reach is global. "
        "Platforms differ by audience and features significantly today."
    )
    out = apply_answer_format(
        "• Facebook — largest\n• Instagram — visual\n• TikTok — short video",
        "concise",
    )
    assert looks_like_markdown_list(out)


def test_hyphenated_model_names_are_not_split():
    raw = (
        "Best current free models:\n"
        "- GPT-Neo — legacy baseline, not a top 2026 choice\n"
        "- DeepSeek-V3.2 — strong reasoning and coding\n"
        "- Qwen3-Coder — best for code-heavy agents\n"
        "- Llama-3.3-70B — broad general-purpose fallback"
    )

    out = format_as_markdown_bullets(raw, "rank the best free LLM models")

    assert "**GPT-Neo** — legacy baseline" in out
    assert "**DeepSeek-V3.2** — strong reasoning" in out
    assert "**Qwen3-Coder** — best for code-heavy agents" in out
    assert "**Llama-3.3-70B** — broad general-purpose" in out
    assert "GPT** — Neo" not in out
    assert "DeepSeek** — V3.2" not in out


def test_existing_balanced_markdown_bold_is_preserved():
    raw = "- **DeepSeek-V3.2** — direct DeepSeek API\n- **Qwen3-Coder** — Dashscope"

    out = format_as_markdown_bullets(raw, "list models")

    assert out.count("**DeepSeek-V3.2**") == 1
    assert out.count("**Qwen3-Coder**") == 1


def test_spaced_urls_are_repaired():
    raw = (
        "Docs: https://api-docs. deepseek. com/ and "
        "https://platform. moonshot. ai/docs"
    )

    out = apply_answer_format(raw, "conversational")

    assert "https://api-docs.deepseek.com/" in out
    assert "https://platform.moonshot.ai/docs" in out
    assert "api-docs. deepseek" not in out
    assert "platform. moonshot" not in out


def test_code_copy_and_flattened_numbering_are_repaired():
    raw = (
        "Meta Llama — use slug code Copy meta-llama/llama-3.3-70b-instruct:free.2. "
        "Qwen — use slug code Copy qwen/qwen3-next-80b-a3b-instruct:free."
    )

    out = apply_answer_format(raw, "automatic", "rank the best free LLM models")

    assert "code Copy" not in out
    assert ".2. Qwen" not in out
    assert "\n\n2. Qwen" in out
