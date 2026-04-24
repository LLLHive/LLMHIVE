from llmhive.app.orchestration.elite_plus_orchestrator import (
    _benchmark_free_majority_can_override_base,
)


def test_conflicting_simple_majority_does_not_override_locked_base():
    assert _benchmark_free_majority_can_override_base("C", "A", 2, 3) is False
    assert _benchmark_free_majority_can_override_base("C", "A", 2, 4) is False


def test_strong_conflicting_majority_can_override_locked_base():
    assert _benchmark_free_majority_can_override_base("C", "A", 3, 4) is True
    assert _benchmark_free_majority_can_override_base("C", "A", 4, 4) is True


def test_matching_base_letter_never_needs_override():
    assert _benchmark_free_majority_can_override_base("C", "C", 3, 4) is False


def test_no_base_letter_allows_normal_majority():
    assert _benchmark_free_majority_can_override_base(None, "B", 2, 3) is True
