"""OpenRouter slug remaps for retired preview models (May 2026)."""

from llmhive.app.openrouter.model_slug_remap import remap_openrouter_model


def test_gemini_3_pro_remaps_to_31_preview() -> None:
    assert remap_openrouter_model("google/gemini-3-pro") == "google/gemini-3.1-pro-preview"
    assert remap_openrouter_model("google/gemini-3-pro-preview") == "google/gemini-3.1-pro-preview"


def test_muse_spark_remaps_to_llama_4_maverick() -> None:
    assert remap_openrouter_model("meta/muse-spark") == "meta-llama/llama-4-maverick"
    assert remap_openrouter_model("meta-llama/muse-spark") == "meta-llama/llama-4-maverick"


def test_unknown_slug_passes_through() -> None:
    assert remap_openrouter_model("openai/gpt-5.5-pro") == "openai/gpt-5.5-pro"
