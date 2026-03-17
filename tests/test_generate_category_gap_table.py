"""Unit tests for generate_category_gap_table.py — delta validation, sign conventions, MT-Bench pts."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Import from scripts (add parent to path)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.generate_category_gap_table import (
    _compute_delta,
    _format_delta,
    _load_results,
    _INDUSTRY_TO_BENCH,
)


class TestDeltaComputation:
    """Validate each delta equals subtraction."""

    def test_delta_equals_subtraction(self):
        """Elite+ − Leader = elite_score - leader_score."""
        assert _compute_delta(95.0, 92.8) == 2.2
        assert _compute_delta(92.8, 95.0) == -2.2
        assert _compute_delta(88.5, 88.5) == 0.0

    def test_delta_rounds_to_one_decimal(self):
        """Deltas round to 1 decimal."""
        assert _compute_delta(95.33, 92.87) == 2.5
        assert _compute_delta(9.45, 9.5) == -0.1

    def test_delta_none_when_missing(self):
        """Delta is None when either operand is None."""
        assert _compute_delta(None, 92.8) is None
        assert _compute_delta(95.0, None) is None
        assert _compute_delta(None, None) is None


class TestSignConventions:
    """Validate sign conventions (positive = Elite+ beats reference)."""

    def test_positive_delta_elite_beats_leader(self):
        """Elite+ − Leader > 0 means Elite+ beats leader."""
        d = _compute_delta(95.0, 92.8)
        assert d is not None and d > 0

    def test_negative_delta_leader_beats_elite(self):
        """Elite+ − Leader < 0 means leader beats Elite+."""
        d = _compute_delta(90.0, 92.8)
        assert d is not None and d < 0

    def test_format_delta_sign(self):
        """Formatted delta includes + for positive."""
        assert "+" in _format_delta(2.2, "pp")
        assert "-" in _format_delta(-1.3, "pp")


class TestMTBenchUnits:
    """Validate MT-Bench uses pts label."""

    def test_mtbench_uses_pts(self):
        """Dialogue (MT-Bench) category uses pts unit."""
        bench_cat, unit = _INDUSTRY_TO_BENCH["dialogue_mtbench"]
        assert "Dialogue" in bench_cat or "MT" in bench_cat
        assert unit == "pts"

    def test_percent_categories_use_pp(self):
        """Percent-based categories use pp (percentage points)."""
        for ind_key, (_, unit) in _INDUSTRY_TO_BENCH.items():
            if ind_key == "dialogue_mtbench":
                assert unit == "pts"
            else:
                assert unit == "pp"


class TestLoadResults:
    """Validate _load_results handles different JSON structures."""

    def test_load_results_array(self):
        """Load from results array (benchmark format)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "results": [
                    {"category": "General Reasoning (MMLU)", "accuracy": 91.5},
                    {"category": "Dialogue (MT-Bench)", "accuracy": 8.2, "extra": {"raw_score_out_of_10": 8.2}},
                ],
            }, f)
            path = Path(f.name)
        try:
            out = _load_results(path)
            assert "General Reasoning (MMLU)" in out
            assert out["General Reasoning (MMLU)"]["score"] == 91.5
            assert out["General Reasoning (MMLU)"]["format"] == "%"
            assert "Dialogue (MT-Bench)" in out
            assert out["Dialogue (MT-Bench)"]["format"] == "x/10"
        finally:
            path.unlink()
