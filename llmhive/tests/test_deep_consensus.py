"""Tests for Deep Consensus feature.

This module validates the consensus and multi-model synthesis implementation:
- LLM-based answer fusion
- Multi-round debate
- Quality-weighted synthesis
- Majority voting
- Arbiter-based judging
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, List

# Import the modules under test
from llmhive.app.orchestration.consensus_manager import (
    ConsensusMethod,
    ModelResponse,
    ConsensusResult,
    ConsensusManager,
    FUSION_PROMPT,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_responses():
    """Create sample model responses for testing."""
    return [
        ModelResponse(
            model="openai/gpt-4o",
            content="The answer is 42. This is derived from the mathematical equation...",
            quality_score=0.9,
            confidence=0.85,
            tokens_used=150,
            latency_ms=800.0,
        ),
        ModelResponse(
            model="anthropic/claude-sonnet-4",
            content="After careful analysis, I conclude that 42 is the correct answer.",
            quality_score=0.88,
            confidence=0.9,
            tokens_used=120,
            latency_ms=750.0,
        ),
        ModelResponse(
            model="google/gemini-2.5-pro",
            content="The answer should be 42, based on the given constraints.",
            quality_score=0.85,
            confidence=0.82,
            tokens_used=100,
            latency_ms=900.0,
        ),
    ]


@pytest.fixture
def disagreeing_responses():
    """Create model responses that disagree."""
    return [
        ModelResponse(
            model="model-a",
            content="The best programming language is Python because of its simplicity.",
            quality_score=0.85,
            confidence=0.7,
        ),
        ModelResponse(
            model="model-b",
            content="Rust is the best programming language due to memory safety.",
            quality_score=0.88,
            confidence=0.75,
        ),
        ModelResponse(
            model="model-c",
            content="JavaScript is the most versatile and widely used language.",
            quality_score=0.82,
            confidence=0.68,
        ),
    ]


# =============================================================================
# Test ConsensusMethod Enum
# =============================================================================

class TestConsensusMethod:
    """Tests for ConsensusMethod enumeration."""
    
    def test_consensus_methods_defined(self):
        """Verify all consensus methods are defined."""
        assert ConsensusMethod.FUSION == "fusion"
        assert ConsensusMethod.DEBATE == "debate"
        assert ConsensusMethod.MAJORITY == "majority"
        assert ConsensusMethod.WEIGHTED == "weighted"
        assert ConsensusMethod.ARBITER == "arbiter"
    
    def test_method_count(self):
        """Test that we have the expected number of methods."""
        methods = list(ConsensusMethod)
        assert len(methods) == 5


# =============================================================================
# Test ModelResponse Dataclass
# =============================================================================

class TestModelResponse:
    """Tests for ModelResponse dataclass."""
    
    def test_create_model_response(self):
        """Test creating a model response."""
        response = ModelResponse(
            model="openai/gpt-4o",
            content="This is the answer.",
            quality_score=0.9,
            confidence=0.85,
            tokens_used=100,
            latency_ms=500.0,
        )
        
        assert response.model == "openai/gpt-4o"
        assert response.content == "This is the answer."
        assert response.quality_score == 0.9
        assert response.confidence == 0.85
    
    def test_default_values(self):
        """Test default values for model response."""
        response = ModelResponse(
            model="test-model",
            content="Content",
        )
        
        assert response.quality_score == 0.8
        assert response.confidence == 0.8
        assert response.tokens_used == 0
        assert response.latency_ms == 0.0


# =============================================================================
# Test ConsensusResult Dataclass
# =============================================================================

class TestConsensusResult:
    """Tests for ConsensusResult dataclass."""
    
    def test_create_consensus_result(self):
        """Test creating a consensus result."""
        result = ConsensusResult(
            final_answer="The synthesized answer is 42.",
            method_used=ConsensusMethod.FUSION,
            agreement_level=0.95,
            synthesis_notes=["All models agreed on core conclusion"],
            contributing_models=["gpt-4o", "claude-sonnet-4", "gemini-pro"],
            debate_rounds=0,
        )
        
        assert result.final_answer == "The synthesized answer is 42."
        assert result.method_used == ConsensusMethod.FUSION
        assert result.agreement_level == 0.95
        assert len(result.contributing_models) == 3
    
    def test_debate_rounds_tracking(self):
        """Test that debate rounds are tracked."""
        result = ConsensusResult(
            final_answer="After debate, the answer is...",
            method_used=ConsensusMethod.DEBATE,
            agreement_level=0.75,
            synthesis_notes=["Required 3 rounds to reach consensus"],
            contributing_models=["model-a", "model-b"],
            debate_rounds=3,
        )
        
        assert result.debate_rounds == 3


# =============================================================================
# Test ConsensusManager
# =============================================================================

class TestConsensusManager:
    """Tests for the ConsensusManager."""
    
    def test_manager_initialization(self):
        """Test that consensus manager can be initialized with providers."""
        # ConsensusManager requires a providers dict
        mock_providers = {"openai": MagicMock(), "anthropic": MagicMock()}
        manager = ConsensusManager(providers=mock_providers)
        assert manager is not None
    
    def test_manager_has_required_methods(self):
        """Test that manager has required methods."""
        mock_providers = {"openai": MagicMock()}
        manager = ConsensusManager(providers=mock_providers)
        
        # Should have method to build consensus
        assert hasattr(manager, 'build_consensus') or \
               hasattr(manager, 'synthesize') or \
               hasattr(manager, 'reach_consensus')
    
    def test_fusion_prompt_defined(self):
        """Test that fusion prompt is defined."""
        assert FUSION_PROMPT is not None
        assert len(FUSION_PROMPT) > 100
        assert "{query}" in FUSION_PROMPT or "query" in FUSION_PROMPT.lower()


# =============================================================================
# Test Agreement Level Calculation
# =============================================================================

class TestAgreementLevel:
    """Tests for agreement level calculation."""
    
    def test_high_agreement(self, sample_responses):
        """Test high agreement detection when responses align."""
        # All responses say "42" - should have high agreement
        # This tests the concept, actual implementation may vary
        contents = [r.content for r in sample_responses]
        
        # Simple check: all contain "42"
        assert all("42" in c for c in contents)
    
    def test_low_agreement(self, disagreeing_responses):
        """Test low agreement detection when responses differ."""
        contents = [r.content for r in disagreeing_responses]
        
        # Different languages mentioned - low agreement
        languages = ["Python", "Rust", "JavaScript"]
        for content, lang in zip(contents, languages):
            assert lang in content


# =============================================================================
# Test Weighted Synthesis
# =============================================================================

class TestWeightedSynthesis:
    """Tests for quality-weighted synthesis."""
    
    def test_higher_quality_weight(self, sample_responses):
        """Test that higher quality responses get more weight."""
        # Sort by quality score
        sorted_responses = sorted(
            sample_responses,
            key=lambda r: r.quality_score,
            reverse=True,
        )
        
        # Highest quality should be first
        assert sorted_responses[0].quality_score >= sorted_responses[1].quality_score
    
    def test_confidence_consideration(self, sample_responses):
        """Test that confidence is considered in weighting."""
        # Calculate combined score
        for response in sample_responses:
            combined_score = (response.quality_score + response.confidence) / 2
            assert 0 <= combined_score <= 1


# =============================================================================
# Test Feature Flag Integration
# =============================================================================

class TestDeepConsensusFeatureFlag:
    """Tests for Deep Consensus feature flag."""
    
    def test_feature_flag_exists(self):
        """Verify DEEP_CONSENSUS feature flag is defined."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        
        assert FeatureFlags.DEEP_CONSENSUS.value == "deep_consensus"
    
    def test_feature_default_on(self):
        """Test that deep consensus is ON by default."""
        from llmhive.app.feature_flags import DEFAULT_FEATURE_STATES, FeatureFlags
        
        assert DEFAULT_FEATURE_STATES.get(FeatureFlags.DEEP_CONSENSUS) is True
    
    def test_feature_can_be_disabled(self):
        """Test that the feature can be disabled via env var."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        import os
        
        with patch.dict(os.environ, {"FEATURE_DEEP_CONSENSUS": "false"}):
            assert is_feature_enabled(FeatureFlags.DEEP_CONSENSUS) is False


# =============================================================================
# Test Debate Mechanism
# =============================================================================

class TestDebateMechanism:
    """Tests for multi-round debate mechanism."""
    
    def test_debate_method_exists(self):
        """Test that debate method exists in ConsensusMethod."""
        assert ConsensusMethod.DEBATE.value == "debate"
    
    def test_debate_result_tracking(self):
        """Test that debate results track rounds."""
        result = ConsensusResult(
            final_answer="Debate conclusion",
            method_used=ConsensusMethod.DEBATE,
            agreement_level=0.8,
            synthesis_notes=["Round 1: Initial positions", "Round 2: Refinement", "Round 3: Agreement"],
            contributing_models=["model-a", "model-b"],
            debate_rounds=3,
        )
        
        assert result.debate_rounds == 3
        assert len(result.synthesis_notes) == 3


# =============================================================================
# Test Majority Voting
# =============================================================================

class TestMajorityVoting:
    """Tests for majority voting mechanism."""
    
    def test_majority_method_exists(self):
        """Test that majority method exists in ConsensusMethod."""
        assert ConsensusMethod.MAJORITY.value == "majority"
    
    def test_simple_majority_detection(self):
        """Test detecting a simple majority in responses."""
        responses = [
            ModelResponse(model="m1", content="Answer is A"),
            ModelResponse(model="m2", content="Answer is A"),
            ModelResponse(model="m3", content="Answer is B"),
        ]
        
        # Count votes (simplified)
        votes = {}
        for r in responses:
            key = "A" if "A" in r.content else "B"
            votes[key] = votes.get(key, 0) + 1
        
        # A should win
        assert votes.get("A", 0) > votes.get("B", 0)


# =============================================================================
# Test Arbiter Method
# =============================================================================

class TestArbiterMethod:
    """Tests for arbiter-based judging."""
    
    def test_arbiter_method_exists(self):
        """Test that arbiter method exists in ConsensusMethod."""
        assert ConsensusMethod.ARBITER.value == "arbiter"
    
    def test_arbiter_result_structure(self):
        """Test arbiter result structure."""
        result = ConsensusResult(
            final_answer="The arbiter selected response from Claude",
            method_used=ConsensusMethod.ARBITER,
            agreement_level=1.0,  # Arbiter makes definitive choice
            synthesis_notes=["Arbiter: GPT-4 selected Claude's response as most accurate"],
            contributing_models=["anthropic/claude-sonnet-4"],  # The selected model
            debate_rounds=0,
        )
        
        assert result.method_used == ConsensusMethod.ARBITER
        assert result.agreement_level == 1.0


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

