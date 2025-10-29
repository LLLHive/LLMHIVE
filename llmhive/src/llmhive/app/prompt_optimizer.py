"""Prompt optimization heuristics to guide downstream models."""
from __future__ import annotations

import re
from typing import Sequence

_DIRECTIVES = (
    "Deliver a structured answer with sections for context, analysis, and conclusion.",
    "Reference retrieved memory snippets by number when they support the answer.",
    "Flag uncertainties or missing data that require additional research.",
)


def optimize_prompt(prompt: str, knowledge_snippets: Sequence[str] | None = None) -> str:
    """Return a cleaned prompt augmented with orchestration directives."""

    cleaned = re.sub(r"\s+", " ", prompt).strip()
    parts: list[str] = [cleaned]

    if knowledge_snippets:
        parts.append("")
        parts.append("Knowledge snippets available for grounding:")
        for idx, snippet in enumerate(knowledge_snippets, start=1):
            summary = snippet.strip().replace("\n", " ")
            summary = summary[:320] + ("…" if len(summary) > 320 else "")
            parts.append(f"[Memory {idx}] {summary}")

    parts.append("")
    parts.append("Follow these directives:")
    for directive in _DIRECTIVES:
        parts.append(f"- {directive}")

    return "\n".join(parts).strip()
