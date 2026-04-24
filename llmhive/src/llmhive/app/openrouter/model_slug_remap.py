"""Remap deprecated OpenRouter model IDs to IDs present in the live catalog.

Callers should run `remap_openrouter_model` before POST /chat/completions so
saved preferences, benchmarks, and static lists keep working when OpenRouter
renames or retires a slug.
"""

from __future__ import annotations

# Keys verified missing or replaced on OpenRouter catalog (see /api/v1/models).
OPENROUTER_MODEL_SLUG_REMAP: dict[str, str] = {
    "google/gemini-3-pro-preview": "google/gemini-3.1-pro-preview",
    "meta-llama/llama-4-70b": "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-405b": "meta-llama/llama-4-scout",
    "meta-llama/llama-4-70b-instruct": "meta-llama/llama-4-maverick",
    "meta-llama/llama-4-405b-instruct": "meta-llama/llama-4-scout",
    "mistralai/codestral-2512": "mistralai/codestral-2508",
    "qwen/qwen-3-72b-instruct": "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen3-72b-instruct": "qwen/qwen3-next-80b-a3b-instruct",
    "cohere/command-r-plus": "cohere/command-r-plus-08-2024",
    "google/med-palm-3": "google/gemini-2.5-pro",
}


def remap_openrouter_model(model_id: str) -> str:
    if not model_id:
        return model_id
    return OPENROUTER_MODEL_SLUG_REMAP.get(model_id, model_id)
