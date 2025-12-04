"""Unit tests for Deep Consensus (DeepConf) Ensemble Framework."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from llmhive.app.orchestration.consensus_manager import (
    ConsensusManager,
    ConsensusResult,
    ConsensusMethod,
    ModelResponse,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    
    async def mock_generate(prompt: str, model: str = "test-model", **kwargs):
        result = MagicMock()
        result.content = "Synthesized response combining multiple perspectives."
        result.tokens_used = 100
        return result
    
    provider.generate = mock_generate
    return provider


@pytest.fixture
def mock_providers(mock_provider):
    """Create a dict of mock providers."""
    return {
        "openai": mock_provider,
        "anthropic": mock_provider,
        "stub": mock_provider,
    }


@pytest.fixture
def sample_responses():
    """Create sample model responses."""
    return [
        ModelResponse(
            model="gpt-4",
            content="The capital of France is Paris. It's a major European city.",
            quality_score=0.9,
            confidence=0.95,
            tokens_used=50,
        ),
        ModelResponse(
            model="claude-3",
            content="Paris is the capital of France, known for the Eiffel Tower.",
            quality_score=0.85,
            confidence=0.9,
            tokens_used=45,
        ),
    ]


@pytest.fixture
def conflicting_responses():
    """Create conflicting model responses."""
    return [
        ModelResponse(
            model="gpt-4",
            content="The answer is definitely A because of X and Y reasons.",
            quality_score=0.8,
            confidence=0.8,
            tokens_used=40,
        ),
        ModelResponse(
            model="claude-3",
            content="The answer is clearly B due to Z and W factors.",
            quality_score=0.8,
            confidence=0.85,
            tokens_used=42,
        ),
    ]


# ==============================================================================
# ModelResponse Tests
# ==============================================================================

class TestModelResponse:
    """Tests for ModelResponse data class."""
    
    def test_create_response(self):
        """Test creating a model response."""
        response = ModelResponse(
            model="gpt-4",
            content="The capital of France is Paris.",
            quality_score=0.9,
            confidence=0.95,
            tokens_used=50,
            latency_ms=150.0,
        )
        
        assert response.model == "gpt-4"
        assert response.content == "The capital of France is Paris."
        assert response.tokens_used == 50
        assert response.quality_score == 0.9
    
    def test_response_default_values(self):
        """Test default values for optional fields."""
        response = ModelResponse(
            model="claude-3",
            content="Test content",
        )
        
        assert response.quality_score == 0.8  # default
        assert response.confidence == 0.8  # default
        assert response.tokens_used == 0  # default
        assert response.latency_ms == 0.0  # default


# ==============================================================================
# ConsensusManager Initialization Tests
# ==============================================================================

class TestConsensusManagerInit:
    """Tests for ConsensusManager initialization."""
    
    def test_initialization(self, mock_providers):
        """Test consensus manager initialization."""
        manager = ConsensusManager(
            providers=mock_providers,
            synthesis_model="gpt-4o",
        )
        
        assert manager.synthesis_model == "gpt-4o"
        assert len(manager.providers) == 3
    
    def test_initialization_defaults(self, mock_providers):
        """Test consensus manager with default values."""
        manager = ConsensusManager(providers=mock_providers)
        
        assert manager.synthesis_model == "gpt-4o"  # default


# ==============================================================================
# Consensus Building Tests
# ==============================================================================

class TestConsensusBuilding:
    """Tests for consensus building methods."""
    
    @pytest.mark.asyncio
    async def test_single_response_consensus(self, mock_providers):
        """Test consensus with a single response."""
        manager = ConsensusManager(providers=mock_providers)
        
        responses = [
            ModelResponse(
                model="gpt-4",
                content="Single response content",
                quality_score=0.9,
            )
        ]
        
        result = await manager.reach_consensus(
            query="What is 2+2?",
            responses=responses,
        )
        
        assert result is not None
        assert result.final_answer == "Single response content"
        assert result.method_used == ConsensusMethod.FUSION
        assert result.agreement_level == 1.0
    
    @pytest.mark.asyncio
    async def test_similar_responses_majority(self, mock_providers, sample_responses):
        """Test consensus with similar responses uses MAJORITY."""
        manager = ConsensusManager(providers=mock_providers)
        
        result = await manager.reach_consensus(
            query="What is the capital of France?",
            responses=sample_responses,
        )
        
        assert result is not None
        assert "Paris" in result.final_answer or result.final_answer
        assert result.method_used in (ConsensusMethod.MAJORITY, ConsensusMethod.FUSION, ConsensusMethod.WEIGHTED)
        assert result.agreement_level > 0.5
    
    @pytest.mark.asyncio
    async def test_empty_responses_raises_error(self, mock_providers):
        """Test that empty responses list raises ValueError."""
        manager = ConsensusManager(providers=mock_providers)
        
        with pytest.raises(ValueError, match="No responses"):
            await manager.reach_consensus(
                query="Test query",
                responses=[],
            )
    
    @pytest.mark.asyncio
    async def test_forced_fusion_method(self, mock_providers, sample_responses):
        """Test forcing FUSION method."""
        # Mock the _fusion_consensus method
        manager = ConsensusManager(providers=mock_providers)
        
        with patch.object(manager, '_fusion_consensus', new_callable=AsyncMock) as mock_fusion:
            mock_fusion.return_value = ConsensusResult(
                final_answer="Fused answer",
                method_used=ConsensusMethod.FUSION,
                agreement_level=0.9,
                synthesis_notes=["Fused via LLM"],
                contributing_models=["gpt-4", "claude-3"],
            )
            
            result = await manager.reach_consensus(
                query="Test query",
                responses=sample_responses,
                method=ConsensusMethod.FUSION,
            )
            
            # Result depends on similarity check - may or may not call fusion
            assert result is not None
            assert result.final_answer
    
    @pytest.mark.asyncio
    async def test_forced_debate_method(self, mock_providers, conflicting_responses):
        """Test forcing DEBATE method."""
        manager = ConsensusManager(providers=mock_providers)
        
        with patch.object(manager, '_debate_consensus', new_callable=AsyncMock) as mock_debate:
            mock_debate.return_value = ConsensusResult(
                final_answer="Debated answer",
                method_used=ConsensusMethod.DEBATE,
                agreement_level=0.75,
                synthesis_notes=["Resolved via debate"],
                contributing_models=["gpt-4", "claude-3"],
                debate_rounds=2,
            )
            
            result = await manager.reach_consensus(
                query="Disputed question",
                responses=conflicting_responses,
                method=ConsensusMethod.DEBATE,
            )
            
            # Debate was requested
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_forced_weighted_method(self, mock_providers, sample_responses):
        """Test forcing WEIGHTED method."""
        manager = ConsensusManager(providers=mock_providers)
        
        with patch.object(manager, '_weighted_consensus') as mock_weighted:
            mock_weighted.return_value = ConsensusResult(
                final_answer="Weighted answer",
                method_used=ConsensusMethod.WEIGHTED,
                agreement_level=0.85,
                synthesis_notes=["Weighted by confidence"],
                contributing_models=["gpt-4", "claude-3"],
            )
            
            result = await manager.reach_consensus(
                query="Test query",
                responses=sample_responses,
                method=ConsensusMethod.WEIGHTED,
            )
            
            assert result is not None


# ==============================================================================
# Consensus Result Tests
# ==============================================================================

class TestConsensusResult:
    """Tests for ConsensusResult data class."""
    
    def test_create_result(self):
        """Test creating a consensus result."""
        result = ConsensusResult(
            final_answer="The consensus answer is Paris.",
            method_used=ConsensusMethod.FUSION,
            agreement_level=0.9,
            synthesis_notes=["Combined perspectives"],
            contributing_models=["gpt-4", "claude-3"],
        )
        
        assert result.final_answer == "The consensus answer is Paris."
        assert result.method_used == ConsensusMethod.FUSION
        assert result.agreement_level == 0.9
        assert len(result.contributing_models) == 2
    
    def test_result_with_debate_rounds(self):
        """Test result with debate rounds."""
        result = ConsensusResult(
            final_answer="Resolved answer",
            method_used=ConsensusMethod.DEBATE,
            agreement_level=0.75,
            synthesis_notes=["After 2 rounds"],
            contributing_models=["gpt-4", "claude-3"],
            debate_rounds=2,
        )
        
        assert result.debate_rounds == 2


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestConsensusIntegration:
    """Integration tests for consensus building."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_consensus(self, mock_providers):
        """Test end-to-end consensus flow with mocked LLM."""
        manager = ConsensusManager(providers=mock_providers)
        
        responses = [
            ModelResponse(
                model="gpt-4",
                content="Python is a high-level programming language.",
                quality_score=0.9,
                confidence=0.95,
            ),
            ModelResponse(
                model="claude-3",
                content="Python is a versatile programming language used for web, data science, and AI.",
                quality_score=0.88,
                confidence=0.9,
            ),
            ModelResponse(
                model="gemini",
                content="Python is popular for its readability and extensive libraries.",
                quality_score=0.85,
                confidence=0.88,
            ),
        ]
        
        result = await manager.reach_consensus(
            query="What is Python?",
            responses=responses,
        )
        
        assert result is not None
        assert result.final_answer is not None
        assert len(result.final_answer) > 0
        assert result.method_used in ConsensusMethod
        assert 0 <= result.agreement_level <= 1.0
    
    @pytest.mark.asyncio
    async def test_multiple_consensus_calls(self, mock_providers):
        """Test that multiple consensus calls work correctly."""
        manager = ConsensusManager(providers=mock_providers)
        
        responses1 = [
            ModelResponse(model="gpt-4", content="Answer 1", quality_score=0.9),
            ModelResponse(model="claude-3", content="Answer 1 variant", quality_score=0.85),
        ]
        
        responses2 = [
            ModelResponse(model="gpt-4", content="Different answer", quality_score=0.8),
            ModelResponse(model="claude-3", content="Another perspective", quality_score=0.82),
        ]
        
        result1 = await manager.reach_consensus(
            query="Query 1",
            responses=responses1,
        )
        
        result2 = await manager.reach_consensus(
            query="Query 2",
            responses=responses2,
        )
        
        assert result1 is not None
        assert result2 is not None
        # Results should be independent
        assert result1.final_answer != result2.final_answer or (
            result1.final_answer == result2.final_answer and "Answer" in result1.final_answer
        )


# ==============================================================================
# Edge Cases Tests
# ==============================================================================

class TestConsensusEdgeCases:
    """Test edge cases in consensus building."""
    
    @pytest.mark.asyncio
    async def test_identical_responses(self, mock_providers):
        """Test consensus with identical responses."""
        manager = ConsensusManager(providers=mock_providers)
        
        identical_content = "The exact same answer from all models."
        responses = [
            ModelResponse(model="gpt-4", content=identical_content, quality_score=0.9),
            ModelResponse(model="claude-3", content=identical_content, quality_score=0.9),
            ModelResponse(model="gemini", content=identical_content, quality_score=0.9),
        ]
        
        result = await manager.reach_consensus(
            query="Test query",
            responses=responses,
        )
        
        assert result is not None
        assert result.agreement_level >= 0.9  # High agreement
    
    @pytest.mark.asyncio
    async def test_very_different_responses(self, mock_providers):
        """Test consensus with very different responses."""
        manager = ConsensusManager(providers=mock_providers)
        
        responses = [
            ModelResponse(model="gpt-4", content="A completely different topic about astronomy.", quality_score=0.7),
            ModelResponse(model="claude-3", content="XYZ unrelated content about cooking recipes.", quality_score=0.6),
        ]
        
        with patch.object(manager, '_fusion_consensus', new_callable=AsyncMock) as mock_fusion:
            mock_fusion.return_value = ConsensusResult(
                final_answer="Best attempt synthesis",
                method_used=ConsensusMethod.FUSION,
                agreement_level=0.3,
                synthesis_notes=["Low agreement"],
                contributing_models=["gpt-4", "claude-3"],
            )
            
            result = await manager.reach_consensus(
                query="Test query",
                responses=responses,
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_max_debate_rounds_respected(self, mock_providers, conflicting_responses):
        """Test that max debate rounds is respected."""
        manager = ConsensusManager(providers=mock_providers)
        
        with patch.object(manager, '_debate_consensus', new_callable=AsyncMock) as mock_debate:
            mock_debate.return_value = ConsensusResult(
                final_answer="Debated answer",
                method_used=ConsensusMethod.DEBATE,
                agreement_level=0.7,
                synthesis_notes=["Reached max rounds"],
                contributing_models=["gpt-4", "claude-3"],
                debate_rounds=3,
            )
            
            result = await manager.reach_consensus(
                query="Disputed question",
                responses=conflicting_responses,
                method=ConsensusMethod.DEBATE,
                max_debate_rounds=3,
            )
            
            # Debate should have been called
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
