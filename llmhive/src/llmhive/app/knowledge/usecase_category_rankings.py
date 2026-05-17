"""
May 2026 Top-10 rankings for the 12 UI use-case categories.

Mirrors lib/marketing/usecase-category-rankings.ts (single logical source).
Used by orchestration when Pinecone category rankings are unavailable.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# (model_id, display_name, author)
_RankRow = Tuple[str, str, str]

_MODEL_META: Dict[str, Tuple[str, str]] = {
    "openai/gpt-5.5-pro": ("GPT-5.5 Pro", "OpenAI"),
    "openai/gpt-5.5": ("GPT-5.5", "OpenAI"),
    "openai/gpt-5.4-pro": ("GPT-5.4 Pro", "OpenAI"),
    "openai/gpt-5.4": ("GPT-5.4", "OpenAI"),
    "openai/gpt-5.3-codex": ("GPT-5.3 Codex", "OpenAI"),
    "openai/gpt-5.2-pro": ("GPT-5.2 Pro", "OpenAI"),
    "openai/gpt-5.2": ("GPT-5.2", "OpenAI"),
    "openai/gpt-5.1": ("GPT-5.1", "OpenAI"),
    "openai/o3": ("OpenAI o3", "OpenAI"),
    "openai/o1-pro": ("o1-pro", "OpenAI"),
    "openai/o4-mini": ("o4-mini", "OpenAI"),
    "anthropic/claude-opus-4.7": ("Claude Opus 4.7", "Anthropic"),
    "anthropic/claude-opus-4.6": ("Claude Opus 4.6", "Anthropic"),
    "anthropic/claude-opus-4.5": ("Claude Opus 4.5", "Anthropic"),
    "anthropic/claude-sonnet-4.6": ("Claude Sonnet 4.6", "Anthropic"),
    "google/gemini-3.1-pro-preview": ("Gemini 3.1 Pro", "Google"),
    "google/gemini-2.5-pro": ("Gemini 2.5 Pro", "Google"),
    "google/gemini-2.5-pro-preview": ("Gemini 2.5 Pro", "Google"),
    "deepseek/deepseek-v4-pro": ("DeepSeek V4 Pro", "DeepSeek"),
    "deepseek/deepseek-r1": ("DeepSeek R1", "DeepSeek"),
    "meta-llama/llama-4-scout": ("Llama 4 Scout", "Meta"),
    "meta-llama/llama-4-maverick": ("Llama 4 Maverick", "Meta"),
    "moonshotai/kimi-k2.6": ("Kimi K2.6", "Moonshot"),
    "moonshotai/kimi-k2.5": ("Kimi K2.5", "Moonshot"),
    "minimax/minimax-m2.5": ("MiniMax M2.5", "MiniMax"),
    "qwen/qwen3.6-plus": ("Qwen3.6 Plus", "Alibaba"),
    "mistralai/mistral-medium-3.1": ("Mistral Medium 3.1", "Mistral AI"),
    "mistralai/mistral-large-2512": ("Mistral Large 2512", "Mistral AI"),
    "x-ai/grok-4.20": ("Grok 4 Fast", "xAI"),
    "cohere/command-r-plus-08-2024": ("Command R+", "Cohere"),
    "z-ai/glm-4.7": ("GLM 4.7", "Z.ai"),
}

_UI_CATEGORIES = (
    "programming",
    "science",
    "health",
    "legal",
    "marketing",
    "technology",
    "finance",
    "academia",
    "roleplay",
    "creative-writing",
    "translation",
    "reasoning",
)

_CATEGORY_MODEL_IDS: Dict[str, List[str]] = {
    "programming": [
        "openai/gpt-5.5",
        "anthropic/claude-opus-4.7",
        "openai/gpt-5.3-codex",
        "anthropic/claude-opus-4.5",
        "anthropic/claude-opus-4.6",
        "deepseek/deepseek-v4-pro",
        "google/gemini-3.1-pro-preview",
        "moonshotai/kimi-k2.6",
        "minimax/minimax-m2.5",
        "openai/gpt-5.2",
    ],
    "science": [
        "openai/gpt-5.5-pro",
        "openai/gpt-5.4-pro",
        "anthropic/claude-opus-4.7",
        "openai/o3",
        "google/gemini-3.1-pro-preview",
        "anthropic/claude-sonnet-4.6",
        "deepseek/deepseek-v4-pro",
        "meta-llama/llama-4-scout",
        "deepseek/deepseek-r1",
        "openai/o4-mini",
    ],
    "health": [
        "openai/gpt-5.5-pro",
        "openai/gpt-5.4-pro",
        "anthropic/claude-opus-4.7",
        "google/gemini-3.1-pro-preview",
        "anthropic/claude-sonnet-4.6",
        "openai/o1-pro",
        "google/gemini-2.5-pro",
        "meta-llama/llama-4-maverick",
        "mistralai/mistral-medium-3.1",
        "deepseek/deepseek-v4-pro",
    ],
    "legal": [
        "anthropic/claude-opus-4.7",
        "openai/gpt-5.5-pro",
        "openai/gpt-5.4-pro",
        "anthropic/claude-sonnet-4.6",
        "google/gemini-3.1-pro-preview",
        "openai/o3",
        "meta-llama/llama-4-scout",
        "mistralai/mistral-large-2512",
        "deepseek/deepseek-v4-pro",
        "cohere/command-r-plus-08-2024",
    ],
    "marketing": [
        "openai/gpt-5.4",
        "openai/gpt-5.5",
        "anthropic/claude-sonnet-4.6",
        "anthropic/claude-opus-4.7",
        "google/gemini-3.1-pro-preview",
        "openai/gpt-5.4-pro",
        "meta-llama/llama-4-maverick",
        "x-ai/grok-4.20",
        "mistralai/mistral-medium-3.1",
        "moonshotai/kimi-k2.6",
    ],
    "technology": [
        "anthropic/claude-opus-4.7",
        "anthropic/claude-opus-4.5",
        "openai/gpt-5.5",
        "openai/gpt-5.2",
        "google/gemini-3.1-pro-preview",
        "openai/gpt-5.1",
        "openai/gpt-5.3-codex",
        "google/gemini-2.5-pro-preview",
        "deepseek/deepseek-v4-pro",
        "anthropic/claude-sonnet-4.6",
    ],
    "finance": [
        "openai/gpt-5.2",
        "google/gemini-3.1-pro-preview",
        "moonshotai/kimi-k2.5",
        "anthropic/claude-opus-4.7",
        "deepseek/deepseek-v4-pro",
        "qwen/qwen3.6-plus",
        "openai/gpt-5.5-pro",
        "openai/gpt-5.5",
        "openai/o4-mini",
        "deepseek/deepseek-r1",
    ],
    "academia": [
        "openai/gpt-5.5",
        "google/gemini-2.5-pro-preview",
        "openai/gpt-5.5-pro",
        "google/gemini-3.1-pro-preview",
        "anthropic/claude-opus-4.7",
        "openai/gpt-5.4-pro",
        "anthropic/claude-sonnet-4.6",
        "deepseek/deepseek-v4-pro",
        "meta-llama/llama-4-maverick",
        "qwen/qwen3.6-plus",
    ],
    "roleplay": [
        "anthropic/claude-opus-4.6",
        "google/gemini-3.1-pro-preview",
        "openai/gpt-5.4-pro",
        "x-ai/grok-4.20",
        "deepseek/deepseek-v4-pro",
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.4",
        "google/gemini-2.5-pro-preview",
        "qwen/qwen3.6-plus",
        "meta-llama/llama-4-maverick",
    ],
    "creative-writing": [
        "anthropic/claude-opus-4.7",
        "anthropic/claude-opus-4.6",
        "openai/gpt-5.4",
        "anthropic/claude-sonnet-4.6",
        "google/gemini-3.1-pro-preview",
        "meta-llama/llama-4-maverick",
        "mistralai/mistral-large-2512",
        "openai/gpt-5.4-pro",
        "moonshotai/kimi-k2.6",
        "cohere/command-r-plus-08-2024",
    ],
    "translation": [
        "google/gemini-3.1-pro-preview",
        "anthropic/claude-opus-4.7",
        "anthropic/claude-opus-4.6",
        "anthropic/claude-opus-4.5",
        "openai/gpt-5.2",
        "qwen/qwen3.6-plus",
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.4",
        "openai/gpt-5.5-pro",
        "z-ai/glm-4.7",
    ],
    "reasoning": [
        "openai/gpt-5.5-pro",
        "openai/o3",
        "openai/o1-pro",
        "openai/gpt-5.4-pro",
        "anthropic/claude-opus-4.7",
        "deepseek/deepseek-r1",
        "deepseek/deepseek-v4-pro",
        "openai/o4-mini",
        "anthropic/claude-sonnet-4.6",
        "google/gemini-3.1-pro-preview",
    ],
}

_CATEGORY_ALIASES: Dict[str, str] = {
    "coding": "programming",
    "math": "reasoning",
    "analysis": "science",
    "code_generation": "programming",
    "debugging": "programming",
    "health_medical": "health",
    "legal_analysis": "legal",
    "financial_analysis": "finance",
    "science_research": "science",
    "creative_writing": "creative-writing",
    "research_analysis": "academia",
    "math_problem": "reasoning",
}


def _resolve_category(category: str) -> str:
    slug = (category or "programming").strip().lower()
    return _CATEGORY_ALIASES.get(slug, slug)


def get_usecase_category_rankings(
    category: str,
    top_k: int = 10,
) -> List[str]:
    """Return model IDs for a use-case category (May 2026 order)."""
    slug = _resolve_category(category)
    rows = _CATEGORY_MODEL_IDS.get(slug) or _CATEGORY_MODEL_IDS["science"]
    return rows[:top_k]


def get_usecase_category_rankings_detailed(
    category: str,
    top_k: int = 10,
) -> List[Dict[str, object]]:
    """Return ranked dicts matching the frontend category-rankings API shape."""
    slug = _resolve_category(category)
    rows = _CATEGORY_MODEL_IDS.get(slug) or _CATEGORY_MODEL_IDS["science"]
    out: List[Dict[str, object]] = []
    for i, model_id in enumerate(rows[:top_k], start=1):
        name, author = _MODEL_META[model_id]
        out.append({
            "rank": i,
            "model_id": model_id,
            "model_name": name,
            "author": author,
            "is_others_bucket": False,
        })
    return out


def domain_models_from_usecase(
    orchestrator_task_type: str,
    limit: int = 6,
) -> List[str]:
    """Map orchestrator task_type → use-case slug → top model IDs."""
    slug = _CATEGORY_ALIASES.get(orchestrator_task_type, orchestrator_task_type)
    if slug not in _CATEGORY_MODEL_IDS:
        slug = "science"
    return get_usecase_category_rankings(slug, top_k=limit)
