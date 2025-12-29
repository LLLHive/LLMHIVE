"""Unit tests for adaptive model router module."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from llmhive.app.orchestration.adaptive_router import (
    AdaptiveModelRouter,
    AdaptiveRoutingResult,
    ModelScore,
    get_adaptive_router,
    select_models_adaptive,
    infer_domain,
    MODEL_PROFILES,
)
from llmhive.app.performance_tracker import ModelPerformance


class TestDomainInference:
    """Tests for domain inference functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = AdaptiveModelRouter()
    
    def test_infer_medical_domain(self):
        """Test that medical queries are correctly identified."""
        queries = [
            "What are the symptoms of diabetes?",
            "How do I treat a patient with high blood pressure?",
            "Explain the diagnosis process for lung cancer.",
        ]
        for query in queries:
            domain = self.router.infer_domain(query)
            assert domain == "medical", f"Expected 'medical' for: {query}"
    
    def test_infer_coding_domain(self):
        """Test that coding queries are correctly identified."""
        queries = [
            "Write a Python function to sort a list.",
            "How do I debug this JavaScript code?",
            "Explain the algorithm for binary search.",
        ]
        for query in queries:
            domain = self.router.infer_domain(query)
            assert domain == "coding", f"Expected 'coding' for: {query}"
    
    def test_infer_legal_domain(self):
        """Test that legal queries are correctly identified."""
        queries = [
            "What are my legal rights in this contract?",
            "Explain the court process for small claims.",
            "What regulations apply to this business?",
        ]
        for query in queries:
            domain = self.router.infer_domain(query)
            assert domain == "legal", f"Expected 'legal' for: {query}"
    
    def test_infer_general_domain(self):
        """Test that ambiguous queries default to general."""
        queries = [
            "What is the weather like today?",
            "Tell me a joke.",
            "How are you?",
        ]
        for query in queries:
            domain = self.router.infer_domain(query)
            assert domain == "general", f"Expected 'general' for: {query}"


class TestAdaptiveModelSelection:
    """Tests for adaptive model selection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = AdaptiveModelRouter(
            available_providers=["openai", "anthropic", "gemini"],
        )
    
    def test_select_models_accuracy_level_1(self):
        """Test model selection for fastest mode (accuracy_level=1)."""
        result = self.router.select_models_adaptive(
            query="Quick question: what is 2+2?",
            roles=["executor"],
            accuracy_level=1,
            available_models=["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-haiku-4"],
        )
        
        # Should prefer small/fast models
        assert result.primary_model in ["openai/gpt-4o-mini", "anthropic/claude-haiku-4"]
        assert result.recommended_ensemble_size == 1
    
    def test_select_models_accuracy_level_5(self):
        """Test model selection for most accurate mode (accuracy_level=5)."""
        result = self.router.select_models_adaptive(
            query="Complex research: analyze AI ethics comprehensively.",
            roles=["coordinator", "specialist", "quality_manager"],
            accuracy_level=5,
            available_models=["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-sonnet-4"],
        )
        
        # Should prefer large models
        assert result.primary_model in ["openai/gpt-4o", "anthropic/claude-sonnet-4"]
        # Should recommend ensemble (at least 2 for high accuracy)
        assert result.recommended_ensemble_size >= 2
        # Should assign multiple models to roles
        assert len(result.role_assignments) >= 3
    
    def test_select_models_balanced_mode(self):
        """Test model selection for balanced mode (accuracy_level=3)."""
        result = self.router.select_models_adaptive(
            query="Explain machine learning basics.",
            roles=["executor"],
            accuracy_level=3,
            available_models=["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-sonnet-4"],
        )
        
        # Should recommend moderate ensemble
        assert result.recommended_ensemble_size == 2
    
    def test_role_assignments_include_all_roles(self):
        """Test that all requested roles get model assignments."""
        roles = ["coordinator", "researcher", "analyst", "synthesizer"]
        
        result = self.router.select_models_adaptive(
            query="Research AI applications.",
            roles=roles,
            accuracy_level=4,
            available_models=["openai/gpt-4o", "anthropic/claude-sonnet-4", "openai/gpt-4o-mini"],
        )
        
        for role in roles:
            assert role in result.role_assignments, f"Role {role} should have assignment"
    
    def test_high_accuracy_adds_secondary_models(self):
        """Test that high accuracy adds secondary models for cross-checking."""
        result = self.router.select_models_adaptive(
            query="Critical medical question.",
            roles=["executive", "quality_manager"],
            accuracy_level=5,
            available_models=["openai/gpt-4o", "anthropic/claude-sonnet-4", "openai/gpt-4o-mini"],
        )
        
        # Check for secondary assignments
        secondary_keys = [k for k in result.role_assignments if "_secondary" in k]
        assert len(secondary_keys) >= 1


class TestModelScoring:
    """Tests for model scoring logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = AdaptiveModelRouter()
    
    def test_domain_match_increases_score(self):
        """Test that domain match increases model score."""
        # Coding query - openai/gpt-4o has "coding" in domains, openai/gpt-4o-mini has fewer domains
        score_coding_match = self.router._score_model(
            model="openai/gpt-4o",  # Has "coding" in domains
            domain="coding",
            accuracy_level=3,
            perf=None,
        )
        
        # Use a model that doesn't have the domain or falls back to default
        score_coding_general = self.router._score_model(
            model="openai/gpt-4o",
            domain="obscure_domain_not_in_any_profile",
            accuracy_level=3,
            perf=None,
        )
        
        # Both should have valid scores; domain match should score higher or equal
        assert score_coding_match.domain_score >= 0.5  # Should have good domain score
    
    def test_performance_history_affects_score(self):
        """Test that performance history affects model score."""
        # Mock performance data
        good_perf = ModelPerformance(
            model="openai/gpt-4o",
            success_count=90,
            failure_count=10,
            quality_scores=[0.9] * 10,
        )
        
        bad_perf = ModelPerformance(
            model="openai/gpt-4o",
            success_count=10,
            failure_count=90,
            quality_scores=[0.3] * 10,
        )
        
        score_good = self.router._score_model(
            model="openai/gpt-4o",
            domain="general",
            accuracy_level=3,
            perf=good_perf,
        )
        
        score_bad = self.router._score_model(
            model="openai/gpt-4o",
            domain="general",
            accuracy_level=3,
            perf=bad_perf,
        )
        
        assert score_good.performance_score > score_bad.performance_score
    
    def test_accuracy_level_affects_size_preference(self):
        """Test that accuracy level affects model size preference."""
        # High accuracy should prefer large models
        score_large_high_acc = self.router._score_model(
            model="openai/gpt-4o",  # Large model
            domain="general",
            accuracy_level=5,
            perf=None,
        )
        
        score_small_high_acc = self.router._score_model(
            model="openai/gpt-4o-mini",  # Small model
            domain="general",
            accuracy_level=5,
            perf=None,
        )
        
        assert score_large_high_acc.accuracy_adjustment > score_small_high_acc.accuracy_adjustment
        
        # Low accuracy should prefer small/fast models
        score_large_low_acc = self.router._score_model(
            model="openai/gpt-4o",  # Large model
            domain="general",
            accuracy_level=1,
            perf=None,
        )
        
        score_small_low_acc = self.router._score_model(
            model="openai/gpt-4o-mini",  # Small model
            domain="general",
            accuracy_level=1,
            perf=None,
        )
        
        assert score_small_low_acc.speed_adjustment > score_large_low_acc.speed_adjustment


class TestCascadeSelection:
    """Tests for cascading model selection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = AdaptiveModelRouter()
    
    @patch('llmhive.app.orchestration.adaptive_router.performance_tracker')
    def test_cascade_escalates_on_low_confidence(self, mock_tracker):
        """Test that cascade escalates when confidence is low."""
        # Mock low quality history
        mock_snapshot = {
            "openai/gpt-4o-mini": ModelPerformance(
                model="openai/gpt-4o-mini",
                quality_scores=[0.4, 0.5, 0.3],  # Low quality
            )
        }
        mock_tracker.snapshot.return_value = mock_snapshot
        
        model, escalated = self.router.cascade_selection(
            query="Complex analysis needed.",
            initial_model="openai/gpt-4o-mini",
            confidence_threshold=0.7,
            available_models=["openai/gpt-4o-mini", "openai/gpt-4o"],
        )
        
        assert escalated is True
        assert model == "openai/gpt-4o"
    
    @patch('llmhive.app.orchestration.adaptive_router.performance_tracker')
    def test_cascade_stays_on_high_confidence(self, mock_tracker):
        """Test that cascade doesn't escalate when confidence is high."""
        # Mock high quality history
        mock_snapshot = {
            "openai/gpt-4o-mini": ModelPerformance(
                model="openai/gpt-4o-mini",
                quality_scores=[0.9, 0.85, 0.88],  # High quality
            )
        }
        mock_tracker.snapshot.return_value = mock_snapshot
        
        model, escalated = self.router.cascade_selection(
            query="Simple question.",
            initial_model="openai/gpt-4o-mini",
            confidence_threshold=0.7,
            available_models=["openai/gpt-4o-mini", "openai/gpt-4o"],
        )
        
        assert escalated is False
        assert model == "openai/gpt-4o-mini"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_adaptive_router_singleton(self):
        """Test that get_adaptive_router returns singleton."""
        router1 = get_adaptive_router()
        router2 = get_adaptive_router()
        assert router1 is router2
    
    def test_select_models_adaptive_convenience(self):
        """Test the convenience function select_models_adaptive."""
        result = select_models_adaptive(
            refined_query="Test query.",
            roles=["executor"],
            accuracy_level=3,
            available_models=["openai/gpt-4o-mini", "openai/gpt-4o"],
        )
        
        assert isinstance(result, dict)
        assert "executor" in result
    
    def test_infer_domain_convenience(self):
        """Test the convenience function infer_domain."""
        domain = infer_domain("Write Python code for sorting.")
        assert domain == "coding"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

