"""Tier-aware routing helpers — frontier models when appropriate, not always.

Elite (paid) orchestration may use ELITE_POLICY frontier primaries when accuracy
or task demands justify the token cost. Free tier and low-accuracy / prefer-cheaper
requests stay on cost-efficient registry scoring.
"""
from __future__ import annotations

from typing import FrozenSet

from .elite_policy import ELITE_POLICY

# Internal registry ids treated as frontier (for verifier / secondary selection).
FRONTIER_INTERNAL_IDS: FrozenSet[str] = frozenset(
    set(ELITE_POLICY.values())
    | {
        "claude-opus-4.8",
        "gpt-5.5",
        "gpt-5.5-pro",
        "gpt-5.6-sol-pro",
        "gpt-6-astra",
        "gpt-6-astra-pro",
        "claude-opus-5",
        "claude-fable-5.1",
        "claude-sonnet-5",
        "grok-4.6",
        "gemini-3.1-pro",
    }
)

ORCHESTRATOR_TASK_TO_CATEGORY = {
    "code_generation": "coding",
    "debugging": "coding",
    "math_problem": "math",
    "reasoning": "reasoning",
    "multi_step": "reasoning",
    "science_research": "rag",
    "research_analysis": "rag",
    "factual_question": "rag",
    "health_medical": "reasoning",
    "legal_analysis": "reasoning",
    "financial_analysis": "math",
    "creative_writing": "dialogue",
    "fast_response": "dialogue",
    "high_quality": "reasoning",
    "general": "dialogue",
    "model_catalog_recommendation": "tool_use",
}

_DEMANDING_ORCHESTRATOR_TASKS: FrozenSet[str] = frozenset({
    "code_generation",
    "debugging",
    "math_problem",
    "reasoning",
    "multi_step",
    "health_medical",
    "legal_analysis",
    "financial_analysis",
    "science_research",
    "high_quality",
    "research_analysis",
})

_DEMANDING_CATEGORIES: FrozenSet[str] = frozenset({
    "coding",
    "math",
    "reasoning",
    "rag",
    "tool_use",
})


def map_orchestrator_task_to_category(task: str) -> str:
    """Map orchestrator task_type strings to intelligence-layer categories."""
    normalized = (task or "general").lower().strip()
    if normalized in ELITE_POLICY:
        return normalized
    return ORCHESTRATOR_TASK_TO_CATEGORY.get(normalized, "reasoning")


def should_use_frontier_primary(
    category: str,
    *,
    use_elite_tier: bool,
    accuracy_level: int,
    prefer_cheaper: bool = False,
    orchestrator_task: str = "",
) -> bool:
    """Return True when a frontier ELITE_POLICY primary is warranted."""
    if not use_elite_tier or prefer_cheaper:
        return False

    level = max(1, min(5, int(accuracy_level or 3)))

    if level >= 4:
        return True
    if level <= 2:
        return False

    # accuracy_level == 3: frontier only for demanding work
    task_key = (orchestrator_task or "").lower().strip()
    if task_key in _DEMANDING_ORCHESTRATOR_TASKS:
        return True
    return category in _DEMANDING_CATEGORIES
