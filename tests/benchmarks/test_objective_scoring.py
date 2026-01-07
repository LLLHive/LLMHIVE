"""Tests for objective scoring functions.

Tests the deterministic scoring logic for:
- Substring contains matching
- Regex pattern matching
- Numeric value extraction and tolerance
- Anti-pattern (not_contains) checking
"""
import pytest
import sys
from pathlib import Path

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "llmhive" / "src"))

from llmhive.app.benchmarks.scoring import ObjectiveScorer


class TestObjectiveScorer:
    """Test objective scoring functions."""
    
    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return ObjectiveScorer()
    
    # ==========================================================================
    # Contains Tests
    # ==========================================================================
    
    def test_contains_match_case_insensitive(self, scorer):
        """Contains check should be case-insensitive."""
        result = scorer.score(
            answer="The answer is PARIS, the capital.",
            expected={"expected_contains": "paris"},
        )
        
        assert result.checks.get("contains") is True
        assert result.passed is True
    
    def test_contains_match_exact(self, scorer):
        """Contains check should match exact substring."""
        result = scorer.score(
            answer="Alexander Fleming discovered penicillin.",
            expected={"expected_contains": "Alexander Fleming"},
        )
        
        assert result.checks.get("contains") is True
        assert result.passed is True
    
    def test_contains_no_match(self, scorer):
        """Contains check should fail when substring not found."""
        result = scorer.score(
            answer="The capital is London.",
            expected={"expected_contains": "Paris"},
        )
        
        assert result.checks.get("contains") is False
        assert result.passed is False
        assert "Missing" in result.details.get("contains", "")
    
    # ==========================================================================
    # Regex Tests
    # ==========================================================================
    
    def test_regex_match_simple(self, scorer):
        """Regex should match simple patterns."""
        result = scorer.score(
            answer="The population is approximately 67 million people.",
            expected={"expected_regex": "6[0-9]\\s*million"},
        )
        
        assert result.checks.get("regex") is True
        assert result.passed is True
    
    def test_regex_match_alternatives(self, scorer):
        """Regex should match alternative patterns."""
        result = scorer.score(
            answer="Albert Fert and Peter Grünberg won the prize.",
            expected={"expected_regex": "Albert\\s*Fert|Peter\\s*Gr[üu]nberg"},
        )
        
        assert result.checks.get("regex") is True
    
    def test_regex_no_match(self, scorer):
        """Regex should fail when pattern not found."""
        result = scorer.score(
            answer="The answer is unknown.",
            expected={"expected_regex": "\\d+\\s*million"},
        )
        
        assert result.checks.get("regex") is False
    
    def test_regex_invalid_pattern(self, scorer):
        """Invalid regex should fail gracefully."""
        result = scorer.score(
            answer="Some answer",
            expected={"expected_regex": "[invalid(regex"},
        )
        
        assert result.checks.get("regex") is False
        assert "Invalid regex" in result.details.get("regex", "")
    
    # ==========================================================================
    # Not Contains Tests
    # ==========================================================================
    
    def test_not_contains_passes_when_absent(self, scorer):
        """Not contains should pass when text is absent."""
        result = scorer.score(
            answer="The answer is Paris, France.",
            expected={"expected_not_contains": "Sydney"},
        )
        
        assert result.checks.get("not_contains") is True
    
    def test_not_contains_fails_when_present(self, scorer):
        """Not contains should fail when forbidden text present."""
        result = scorer.score(
            answer="Could you clarify what you mean?",
            expected={"expected_not_contains": "clarify"},
        )
        
        assert result.checks.get("not_contains") is False
        assert "Forbidden content found" in result.details.get("not_contains", "")
    
    # ==========================================================================
    # Numeric Tests
    # ==========================================================================
    
    def test_numeric_exact_match(self, scorer):
        """Numeric should match exact value."""
        result = scorer.score(
            answer="The result is 42.",
            expected={
                "expected_numeric": {"value": 42, "tolerance": 0}
            },
        )
        
        assert result.checks.get("numeric") is True
    
    def test_numeric_within_tolerance(self, scorer):
        """Numeric should pass within tolerance."""
        result = scorer.score(
            answer="The answer is approximately 100.",
            expected={
                "expected_numeric": {"value": 100, "tolerance": 5}
            },
        )
        
        assert result.checks.get("numeric") is True
    
    def test_numeric_outside_tolerance(self, scorer):
        """Numeric should fail outside tolerance."""
        result = scorer.score(
            answer="The result is 150.",
            expected={
                "expected_numeric": {"value": 100, "tolerance": 10}
            },
        )
        
        assert result.checks.get("numeric") is False
    
    def test_numeric_with_extraction_pattern(self, scorer):
        """Numeric should use extraction pattern when provided."""
        result = scorer.score(
            answer="It takes 5.4 days to complete the journey.",
            expected={
                "expected_numeric": {
                    "value": 5.4,
                    "tolerance": 0.3,
                    "extract_pattern": "([0-9.]+)\\s*days?"
                }
            },
        )
        
        assert result.checks.get("numeric") is True
    
    def test_numeric_with_commas(self, scorer):
        """Numeric should handle comma-separated numbers."""
        result = scorer.score(
            answer="The population is 1,307,674,368,000.",
            expected={
                "expected_numeric": {
                    "value": 1307674368000,
                    "tolerance": 0,
                    "extract_pattern": "([0-9,]+)"
                }
            },
        )
        
        assert result.checks.get("numeric") is True
    
    def test_numeric_no_number_found(self, scorer):
        """Numeric should fail when no number found."""
        result = scorer.score(
            answer="The answer is unknown.",
            expected={
                "expected_numeric": {"value": 100, "tolerance": 10}
            },
        )
        
        assert result.checks.get("numeric") is False
        assert "Could not extract" in result.details.get("numeric", "")
    
    # ==========================================================================
    # Clarification Requirement Tests
    # ==========================================================================
    
    def test_no_clarification_passes_direct_answer(self, scorer):
        """No clarification check should pass for direct answers."""
        result = scorer.score(
            answer="Alexander Fleming discovered penicillin in 1928.",
            expected={},
            requirements={"requires_no_clarification": True},
        )
        
        assert result.checks.get("no_clarification") is True
    
    def test_no_clarification_fails_when_asking(self, scorer):
        """No clarification check should fail when asking for more info."""
        result = scorer.score(
            answer="Could you clarify what you mean by 'discovered'?",
            expected={},
            requirements={"requires_no_clarification": True},
        )
        
        assert result.checks.get("no_clarification") is False
    
    def test_requires_clarification_passes(self, scorer):
        """Requires clarification should pass when asking."""
        result = scorer.score(
            answer="Could you specify which one you mean?",
            expected={},
            requirements={"requires_clarification": True},
        )
        
        assert result.checks.get("asked_clarification") is True
    
    def test_requires_clarification_fails(self, scorer):
        """Requires clarification should fail with direct answer."""
        result = scorer.score(
            answer="Here is the information you requested.",
            expected={},
            requirements={"requires_clarification": True},
        )
        
        assert result.checks.get("asked_clarification") is False
    
    # ==========================================================================
    # Combined Tests
    # ==========================================================================
    
    def test_multiple_checks_all_pass(self, scorer):
        """All checks should pass when answer is correct."""
        result = scorer.score(
            answer="The capital of France is Paris, with a population of 67 million.",
            expected={
                "expected_contains": "Paris",
                "expected_regex": "6[0-9]\\s*million",
                "expected_not_contains": "London",
            },
        )
        
        assert result.passed is True
        assert result.score == 1.0
    
    def test_multiple_checks_partial_pass(self, scorer):
        """Score should be proportional to passed checks."""
        result = scorer.score(
            answer="The capital is Paris.",  # Missing population
            expected={
                "expected_contains": "Paris",
                "expected_regex": "6[0-9]\\s*million",  # Won't match
            },
        )
        
        assert result.passed is False
        assert result.score == 0.5  # 1 of 2 checks passed
    
    def test_no_checks_passes_by_default(self, scorer):
        """Empty expected dict should pass by default."""
        result = scorer.score(
            answer="Any answer here.",
            expected={},
        )
        
        assert result.passed is True
        assert result.score == 1.0

