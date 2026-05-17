"""GPT-5.5 alignment: registry, elite policy, and provider equivalence."""

from __future__ import annotations

import pytest

from llmhive.app.intelligence.elite_policy import ELITE_POLICY
from llmhive.app.intelligence.model_registry_2026 import CANONICAL_MODELS
from llmhive.app.intelligence.provider_equivalence import (
    SAME_MODEL_PROVIDER_MATRIX,
    get_provider_model_name,
)


@pytest.mark.parametrize(
    "category",
    ["reasoning", "coding", "math", "tool_use", "rag", "dialogue"],
)
def test_elite_policy_openai_categories_use_gpt55_pro(category: str) -> None:
    assert ELITE_POLICY[category] == "gpt-5.5-pro"


def test_canonical_models_include_gpt55_variants() -> None:
    assert "gpt-5.5-pro" in CANONICAL_MODELS
    assert "gpt-5.5" in CANONICAL_MODELS


def test_provider_equivalence_maps_gpt55_pro() -> None:
    assert "gpt-5.5-pro" in SAME_MODEL_PROVIDER_MATRIX
    assert get_provider_model_name("gpt-5.5-pro", "openrouter") == "openai/gpt-5.5-pro"
    assert get_provider_model_name("gpt-5.5-pro", "openai") == "gpt-5.5-pro"
