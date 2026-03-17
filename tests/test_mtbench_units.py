"""Tests for MT-Bench unit normalization (pts 0-10, not percent)."""
import sys
from pathlib import Path

# Add scripts to path
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))


def test_format_best_score_dialogue_uses_pts():
    """Dialogue best score is formatted as x.x / 10, not percent."""
    from run_category_benchmarks import _format_best_score, _is_dialogue_result

    assert _is_dialogue_result({"category": "Dialogue (MT-Bench)"})
    assert _format_best_score("Dialogue (MT-Bench)", 83.5) == "8.3 / 10"  # 83.5/10
    assert _format_best_score("Dialogue (MT-Bench)", 69.0) == "6.9 / 10"


def test_format_best_score_non_dialogue_uses_percent():
    """Non-Dialogue best score is formatted as percent."""
    from run_category_benchmarks import _format_best_score

    assert _format_best_score("General Reasoning (MMLU)", 77.8) == "77.8%"


def test_format_delta_dialogue_uses_pts():
    """Dialogue delta uses pts."""
    from run_category_benchmarks import _format_delta

    # diff = -14.5 (raw score diff) -> -1.45 pts
    assert _format_delta("Dialogue (MT-Bench)", -14.5) == "(-1.4 pts)"
    assert _format_delta("Dialogue (MT-Bench)", 10.0) == "(+1.0 pts)"


def test_format_delta_non_dialogue_uses_pp():
    """Non-Dialogue delta uses pp."""
    from run_category_benchmarks import _format_delta

    assert _format_delta("General Reasoning (MMLU)", -2.8) == "(-2.8pp)"
