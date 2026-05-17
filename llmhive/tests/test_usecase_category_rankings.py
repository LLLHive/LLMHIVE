"""Tests for May 2026 use-case category rankings (UI + orchestrator parity)."""
from llmhive.app.knowledge.usecase_category_rankings import (
    get_usecase_category_rankings,
    get_usecase_category_rankings_detailed,
)


def test_all_twelve_ui_categories_have_ten_models():
    categories = [
        "programming", "science", "health", "legal", "marketing", "technology",
        "finance", "academia", "roleplay", "creative-writing", "translation", "reasoning",
    ]
    for slug in categories:
        rows = get_usecase_category_rankings(slug, top_k=10)
        assert len(rows) == 10, slug
        assert rows[0].startswith(("openai/", "anthropic/", "google/", "deepseek/", "meta-llama/"))


def test_science_leader_is_gpt_55_pro():
    rows = get_usecase_category_rankings("science", top_k=3)
    assert rows[0] == "openai/gpt-5.5-pro"
    assert rows[1] == "openai/gpt-5.4-pro"


def test_programming_leader_is_gpt_55():
    rows = get_usecase_category_rankings("programming", top_k=1)
    assert rows[0] == "openai/gpt-5.5"


def test_detailed_entries_have_contiguous_ranks():
    entries = get_usecase_category_rankings_detailed("legal", top_k=10)
    ranks = [e["rank"] for e in entries]
    assert ranks == list(range(1, 11))


def test_orchestrator_task_alias_maps_to_programming():
    rows = get_usecase_category_rankings("code_generation", top_k=1)
    assert rows[0] == "openai/gpt-5.5"
