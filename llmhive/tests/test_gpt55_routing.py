"""Frontier elite policy + GPT-5.5 registry/equivalence regression."""

from __future__ import annotations

import pytest

from llmhive.app.intelligence.elite_policy import ELITE_POLICY
from llmhive.app.intelligence.model_registry_2026 import CANONICAL_MODELS
from llmhive.app.intelligence.provider_equivalence import (
    SAME_MODEL_PROVIDER_MATRIX,
    get_provider_model_name,
)


@pytest.mark.parametrize(
    "category,expected",
    [
        ("reasoning", "gpt-6-astra"),
        ("coding", "claude-opus-5"),
        ("math", "gpt-6-astra"),
        ("tool_use", "claude-opus-5"),
        ("rag", "gpt-6-astra"),
        ("dialogue", "claude-fable-5.1"),
        ("multilingual", "claude-sonnet-5"),
        ("long_context", "gemini-3.1-pro"),
    ],
)
def test_elite_policy_uses_sep_2026_flagships(category: str, expected: str) -> None:
    assert ELITE_POLICY[category] == expected


def test_canonical_models_include_gpt55_and_gpt6_variants() -> None:
    assert "gpt-5.5-pro" in CANONICAL_MODELS
    assert "gpt-5.5" in CANONICAL_MODELS
    assert "gpt-6-astra" in CANONICAL_MODELS
    assert "gpt-6-astra-pro" in CANONICAL_MODELS


def test_provider_equivalence_maps_gpt55_pro() -> None:
    assert "gpt-5.5-pro" in SAME_MODEL_PROVIDER_MATRIX
    assert get_provider_model_name("gpt-5.5-pro", "openrouter") == "openai/gpt-5.5-pro"
    assert get_provider_model_name("gpt-5.5-pro", "openai") == "gpt-5.5-pro"
