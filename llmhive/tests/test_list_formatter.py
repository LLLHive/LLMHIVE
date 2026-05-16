"""Tests for list_formatter — bullet/numbered output quality."""
from __future__ import annotations

from llmhive.app.orchestration.list_formatter import (
    format_as_markdown_bullets,
    format_as_markdown_numbered,
    infer_format_from_query,
    looks_like_markdown_list,
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
