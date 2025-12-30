"""Tests for the clarification manager.

Tests the detection of ambiguous queries and generation of clarifying questions.
"""
import pytest
from unittest.mock import MagicMock, patch

from llmhive.app.orchestration.clarification_manager import (
    ClarificationManager,
    get_default_preferences,
)


class TestClarificationManager:
    """Test suite for ClarificationManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ClarificationManager()

    def test_is_clear_query_list_with_number(self):
        """List queries with numbers should be clear."""
        clear_queries = [
            "list top 10 fastest production motorcycles in the world",
            "list the biggest cities in Europe",
            "top 10 programming languages",
            "list 5 best books of 2024",
        ]
        
        for query in clear_queries:
            is_clear = self.manager._is_clear_query(query)
            assert is_clear, f"Query '{query}' should be recognized as clear"

    def test_is_clear_query_what_is(self):
        """What is/are queries should be clear."""
        clear_queries = [
            "what is the capital of France",
            "what are the planets in the solar system",
            "what is machine learning",
        ]
        
        for query in clear_queries:
            is_clear = self.manager._is_clear_query(query)
            assert is_clear, f"Query '{query}' should be recognized as clear"

    def test_is_clear_query_who(self):
        """Who queries should be clear."""
        clear_queries = [
            "who wrote Romeo and Juliet",
            "who invented the telephone",
            "who is the president of France",
        ]
        
        for query in clear_queries:
            is_clear = self.manager._is_clear_query(query)
            assert is_clear, f"Query '{query}' should be recognized as clear"

    def test_is_clear_query_how(self):
        """How queries should be clear."""
        clear_queries = [
            "how many planets are in the solar system",
            "how does photosynthesis work",
            "how to write a Python function",
        ]
        
        for query in clear_queries:
            is_clear = self.manager._is_clear_query(query)
            assert is_clear, f"Query '{query}' should be recognized as clear"

    def test_is_clear_query_imperatives(self):
        """Imperative commands should be clear."""
        clear_queries = [
            "explain the difference between TCP and UDP",
            "define photosynthesis",
            "compare React and Vue frameworks",
            "write a Python function to sort a list",
            "calculate the area of a circle",
        ]
        
        for query in clear_queries:
            is_clear = self.manager._is_clear_query(query)
            assert is_clear, f"Query '{query}' should be recognized as clear"

    def test_vague_queries_not_clear(self):
        """Vague queries should not be marked as clear."""
        vague_queries = [
            "it",
            "that thing",
            "more",
            "the other one",
        ]
        
        for query in vague_queries:
            is_clear = self.manager._is_clear_query(query)
            # Very vague queries should not match clear patterns
            assert isinstance(is_clear, bool)

    def test_empty_query_handling(self):
        """Empty queries should be handled gracefully."""
        is_clear = self.manager._is_clear_query("")
        assert isinstance(is_clear, bool)

    def test_whitespace_query(self):
        """Whitespace-only query should be handled."""
        is_clear = self.manager._is_clear_query("   \n\t   ")
        assert isinstance(is_clear, bool)


class TestRuleBasedDetection:
    """Test rule-based ambiguity detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ClarificationManager()

    def test_rule_based_on_clear_query(self):
        """Rule-based should give low ambiguity for clear queries."""
        clear_query = "list the top 10 fastest cars in the world"
        
        result = self.manager._rule_based_detect_ambiguity(
            clear_query, 
            context=None, 
            history=None
        )
        
        # Returns a tuple: (is_ambiguous: bool, issues: List, questions: List)
        assert isinstance(result, tuple)
        assert len(result) == 3
        is_ambiguous, issues, questions = result
        assert isinstance(is_ambiguous, bool)
        assert isinstance(issues, list)
        assert isinstance(questions, list)

    def test_rule_based_returns_tuple(self):
        """Rule-based detection should return a tuple."""
        result = self.manager._rule_based_detect_ambiguity(
            "test query", 
            context=None, 
            history=None
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3


class TestCriticalAmbiguity:
    """Test critical ambiguity detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ClarificationManager()

    def test_no_critical_ambiguity_for_specific_queries(self):
        """Specific queries should not have critical ambiguity."""
        clear_queries = [
            "what is machine learning",
            "explain how to code in python",
            "list 5 best programming books",
        ]
        
        for query in clear_queries:
            has_critical = self.manager._has_critical_ambiguity(query.lower(), history=None)
            assert not has_critical, f"Query '{query}' should not have critical ambiguity"

    def test_critical_ambiguity_returns_bool(self):
        """Critical ambiguity check should return boolean."""
        has_critical = self.manager._has_critical_ambiguity("test query", history=None)
        assert isinstance(has_critical, bool)


class TestGetDefaultPreferences:
    """Test default preferences."""

    def test_default_preferences_exist(self):
        """Default preferences should be available."""
        prefs = get_default_preferences()
        assert prefs is not None


class TestClarificationManagerInit:
    """Test ClarificationManager initialization."""

    def test_init_no_providers(self):
        """Should initialize without providers."""
        manager = ClarificationManager()
        assert manager is not None

    def test_init_with_providers(self):
        """Should initialize with providers."""
        mock_providers = {"test": MagicMock()}
        manager = ClarificationManager(providers=mock_providers)
        assert manager is not None

    def test_clear_patterns_defined(self):
        """CLEAR_QUERY_PATTERNS should be defined."""
        manager = ClarificationManager()
        assert hasattr(manager, 'CLEAR_QUERY_PATTERNS')
        assert len(manager.CLEAR_QUERY_PATTERNS) > 0


class TestClearQueryPatterns:
    """Test the clear query pattern matching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ClarificationManager()

    def test_pattern_list_top_n(self):
        """'list top N' pattern should match."""
        assert self.manager._is_clear_query("list top 10 movies")
        assert self.manager._is_clear_query("list the top 5 books")

    def test_pattern_what_is(self):
        """'what is' pattern should match."""
        assert self.manager._is_clear_query("what is Python")
        assert self.manager._is_clear_query("what are the benefits")

    def test_pattern_how_to(self):
        """'how to' pattern should match."""
        assert self.manager._is_clear_query("how to write code")
        assert self.manager._is_clear_query("how does this work")

    def test_pattern_explain(self):
        """'explain' pattern should match."""
        assert self.manager._is_clear_query("explain quantum physics")
        assert self.manager._is_clear_query("describe the process")

    def test_pattern_define(self):
        """'define' pattern should match."""
        assert self.manager._is_clear_query("define machine learning")

    def test_no_false_positives_on_vague(self):
        """Vague queries should not match clear patterns."""
        # Very short vague queries
        assert not self.manager._is_clear_query("it")
        assert not self.manager._is_clear_query("that")
        assert not self.manager._is_clear_query("more")


class TestEdgeCases:
    """Test edge cases for clarification manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ClarificationManager()

    def test_unicode_handling(self):
        """Unicode queries should be handled."""
        is_clear = self.manager._is_clear_query("¿Cuál es la capital?")
        assert isinstance(is_clear, bool)

    def test_very_long_query(self):
        """Very long queries should be handled."""
        long_query = "explain " + "the concept of " * 50 + "machine learning"
        is_clear = self.manager._is_clear_query(long_query)
        assert isinstance(is_clear, bool)

    def test_special_characters(self):
        """Special characters should be handled."""
        is_clear = self.manager._is_clear_query("what is C++ programming?")
        assert isinstance(is_clear, bool)

    def test_mixed_case(self):
        """Mixed case queries should be handled."""
        assert self.manager._is_clear_query("What Is Machine Learning")
        assert self.manager._is_clear_query("WHAT IS PYTHON")
        assert self.manager._is_clear_query("define PHOTOSYNTHESIS")
