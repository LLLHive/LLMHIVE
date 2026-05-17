"""Backward-compatible re-exports — prefer ``answer_format`` for new code."""
from __future__ import annotations

from .answer_format import (
    apply_answer_format,
    format_as_markdown_bullets,
    format_as_markdown_numbered,
    format_style_prompt_instructions,
    infer_format_from_query,
    looks_like_markdown_list,
    resolve_profile,
)

__all__ = [
    "apply_answer_format",
    "format_as_markdown_bullets",
    "format_as_markdown_numbered",
    "format_style_prompt_instructions",
    "infer_format_from_query",
    "looks_like_markdown_list",
    "resolve_profile",
]
