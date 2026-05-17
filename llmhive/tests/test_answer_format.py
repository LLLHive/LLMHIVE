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
