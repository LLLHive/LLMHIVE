"""Tests for July 2026 use-case category rankings (UI + orchestrator parity)."""
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


def test_scores_are_strictly_descending():
    for slug in ("programming", "science", "academia", "finance"):
        entries = get_usecase_category_rankings_detailed(slug, top_k=10)
        scores = [float(e["score"]) for e in entries]
        assert scores == sorted(scores, reverse=True), slug


def test_science_leader_is_claude_opus_5():
    rows = get_usecase_category_rankings("science", top_k=3)
    assert rows[0] == "anthropic/claude-opus-5"
    assert "openai/gpt-5.6-sol-pro" in rows


def test_programming_leader_is_claude_opus_5():
    rows = get_usecase_category_rankings("programming", top_k=3)
    assert rows[0] == "anthropic/claude-opus-5"
    assert "openai/gpt-5.6-sol-pro" in rows


def test_reasoning_includes_sol_pro_and_opus_5():
    rows = get_usecase_category_rankings("reasoning", top_k=5)
    assert rows[0] == "openai/gpt-5.6-sol-pro"
    assert "anthropic/claude-opus-5" in rows


def test_academia_leader_is_gemini_25_pro_by_mrcr_score():
    rows = get_usecase_category_rankings("academia", top_k=1)
    assert rows[0] == "google/gemini-2.5-pro-preview"


def test_detailed_entries_have_contiguous_ranks():
    entries = get_usecase_category_rankings_detailed("legal", top_k=10)
    ranks = [e["rank"] for e in entries]
    assert ranks == list(range(1, 11))


def test_orchestrator_task_alias_maps_to_programming():
    rows = get_usecase_category_rankings("code_generation", top_k=1)
    assert rows[0] == "anthropic/claude-opus-5"
