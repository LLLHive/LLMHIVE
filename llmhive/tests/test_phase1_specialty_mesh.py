"""Phase 1 specialty mesh: accuracy≥4 duals; never on LC; spend-safe."""
from __future__ import annotations

from llmhive.app.services.orchestrator_adapter import (
    OPENROUTER_CLAUDE_FABLE_5_1,
    OPENROUTER_CLAUDE_OPUS_5,
    OPENROUTER_DEEPSEEK_V4_1_FLASH,
    OPENROUTER_GPT_6_ASTRA,
    _phase1_specialty_mesh_models,
)
from llmhive.app.services.model_router import is_long_context_query


def test_mesh_skipped_below_accuracy_4():
    assert (
        _phase1_specialty_mesh_models(
            "reasoning",
            use_free_models=False,
            accuracy_level=3,
            prefer_cheaper=False,
        )
        is None
    )


def test_mesh_skipped_prefer_cheaper_on_paid():
    assert (
        _phase1_specialty_mesh_models(
            "coding",
            use_free_models=False,
            accuracy_level=5,
            prefer_cheaper=True,
        )
        is None
    )


def test_mesh_reasoning_astra_fable():
    mesh = _phase1_specialty_mesh_models(
        "reasoning",
        use_free_models=False,
        accuracy_level=4,
        prefer_cheaper=False,
    )
    assert mesh == [OPENROUTER_GPT_6_ASTRA, OPENROUTER_CLAUDE_FABLE_5_1]


def test_mesh_coding_opus_astra():
    mesh = _phase1_specialty_mesh_models(
        "code_generation",
        use_free_models=False,
        accuracy_level=4,
        prefer_cheaper=False,
    )
    assert mesh == [OPENROUTER_CLAUDE_OPUS_5, OPENROUTER_GPT_6_ASTRA]


def test_mesh_math_astra_deepseek():
    mesh = _phase1_specialty_mesh_models(
        "math_problem",
        use_free_models=False,
        accuracy_level=4,
        prefer_cheaper=False,
    )
    assert mesh == [OPENROUTER_GPT_6_ASTRA, OPENROUTER_DEEPSEEK_V4_1_FLASH]


def test_mesh_general_task_returns_none():
    assert (
        _phase1_specialty_mesh_models(
            "general",
            use_free_models=False,
            accuracy_level=5,
            prefer_cheaper=False,
        )
        is None
    )


def test_mesh_free_uses_catalog_only():
    mesh = _phase1_specialty_mesh_models(
        "coding",
        use_free_models=True,
        accuracy_level=4,
        prefer_cheaper=False,
    )
    assert mesh is not None
    assert len(mesh) == 2
    assert mesh[0].startswith("nvidia/nemotron-3-ultra")
    assert "glm" in mesh[1]
    assert all("claude-opus" not in m and "gpt-6-astra" not in m for m in mesh)


def test_mesh_free_skipped_when_prefer_cheaper():
    assert (
        _phase1_specialty_mesh_models(
            "coding",
            use_free_models=True,
            accuracy_level=5,
            prefer_cheaper=True,
        )
        is None
    )


def test_mesh_free_math_ultra_deepseek():
    mesh = _phase1_specialty_mesh_models(
        "math_problem",
        use_free_models=True,
        accuracy_level=4,
        prefer_cheaper=False,
    )
    assert mesh == [
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "deepseek/deepseek-chat",
    ]


def test_long_context_detection_still_independent_of_mesh():
    # Mesh must never be applied when LC gate is on; detection itself unchanged.
    body = "Document:\nThe magic needle value is ALPHA.\n" + (
        "lorem ipsum dolor sit amet. " * 1500
    )
    assert is_long_context_query(body, threshold=30000)
