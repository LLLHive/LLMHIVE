"""Long-context anti-orchestration: exactly one model, Gemini specialty."""
from __future__ import annotations

from llmhive.app.orchestration.elite_orchestration import FREE_MODELS, MAXIMUM_MODELS, ELITE_MODELS
from llmhive.app.services.model_router import (
    FALLBACK_GEMINI_3_1_PRO,
    FALLBACK_GEMINI_3_8_FLASH,
    get_long_context_model,
    is_long_context_query,
)


def test_is_long_context_query_token_threshold():
    big = "x" * 5000  # estimate_token_count = 1250
    assert is_long_context_query(big, threshold=1000)
    assert not is_long_context_query("short prompt", threshold=1000)


def test_is_long_context_query_document_marker_mid_size():
    # ~10k tokens with document marker should trigger even if under 30k adapter threshold
    body = "Document:\nThe magic needle value is ALPHA.\n" + ("lorem ipsum dolor sit amet. " * 1500)
    assert len(body) // 4 >= 8000
    assert is_long_context_query(body, threshold=30000)


def test_get_long_context_model_elite_prefers_gemini_31():
    model = get_long_context_model(50_000, prefer_free=False)
    assert model == FALLBACK_GEMINI_3_1_PRO


def test_get_long_context_model_free_prefers_gemini_38():
    model = get_long_context_model(50_000, prefer_free=True)
    assert model == FALLBACK_GEMINI_3_8_FLASH


def test_free_long_context_primary_is_gemini_38():
    assert FREE_MODELS["long_context"][0] == "google/gemini-3.8-flash"
    assert "google/gemini-2.5-flash" not in FREE_MODELS["long_context"]


def test_maximum_long_context_primary_is_gemini_31():
    assert MAXIMUM_MODELS["long_context"][0] == "google/gemini-3.1-pro-preview"


def test_elite_rag_no_longer_led_by_gemini_25():
    assert ELITE_MODELS["rag"][0] == "openai/gpt-6-astra"
    assert "google/gemini-2.5-pro-preview" not in ELITE_MODELS["rag"]


def test_elite_tool_use_populated():
    assert len(ELITE_MODELS["tool_use"]) >= 3
