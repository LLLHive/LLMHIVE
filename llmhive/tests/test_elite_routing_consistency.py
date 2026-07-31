"""Elite routing consistency — frontier models in tool-capable and fallback paths."""
from __future__ import annotations

from llmhive.app.knowledge.usecase_category_rankings import get_usecase_category_rankings
from llmhive.app.orchestration.elite_orchestration import ELITE_MODELS
from llmhive.app.services.orchestrator_adapter import (
    OPENROUTER_CLAUDE_OPUS_4_8,
    OPENROUTER_CLAUDE_OPUS_5,
    TOOL_CAPABLE_MODELS,
)


def test_opus_5_is_tool_capable():
    assert OPENROUTER_CLAUDE_OPUS_5 in TOOL_CAPABLE_MODELS
    assert OPENROUTER_CLAUDE_OPUS_4_8 in TOOL_CAPABLE_MODELS


def test_elite_multimodal_derived_from_benchmark_rankings():
    multimodal = ELITE_MODELS["multimodal"]
    assert "anthropic/claude-opus-5" in multimodal
    assert multimodal[0] == "anthropic/claude-opus-5"


def test_programming_rankings_keep_opus_5_when_tools_required():
    ranked = get_usecase_category_rankings("programming", top_k=10)
    tool_capable = [model_id for model_id in ranked if model_id in TOOL_CAPABLE_MODELS]
    assert "anthropic/claude-opus-5" in tool_capable
    assert tool_capable.index("anthropic/claude-opus-5") < tool_capable.index(
        "anthropic/claude-opus-4.8"
    )
