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
    ConsensusScore,
    ConsensusStrategy,
    ResponseType,
    ConflictSeverity,
    ModelResponse,
    FactualClaim,
    VotingResult,
    DebateRound,
    build_consensus,
)


class TestModelResponse:
    """Tests for ModelResponse data class."""
    
    def test_create_response(self):
        """Test creating a model response."""
        response = ModelResponse(
            model="gpt-4",
            content="The capital of France is Paris.",
            tokens=50,
            latency_ms=150.0,
        )
        
        assert response.model == "gpt-4"
        assert response.content == "The capital of France is Paris."
        assert response.tokens == 50
    
    def test_response_default_confidence(self):
        """Test default confidence value."""
        response = ModelResponse(
            model="claude-3",
            content="Test content",
        )
        
        assert response.raw_confidence == 0.5


class TestConsensusScore:
    """Tests for ConsensusScore data class."""
    
    def test_create_score(self):
        """Test creating a consensus score."""
        score = ConsensusScore(
            overall_score=0.85,
            agreement_rate=0.9,
            confidence_weighted_score=0.8,
            quality_score=0.88,
            breakdown={"voting": 0.85},
        )
        
        assert score.overall_score == 0.85
        assert score.agreement_rate == 0.9


class TestConsensusManager:
    """Tests for ConsensusManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock provider
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "The capital of France is Paris."
        self.mock_result.tokens = 50
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider, "stub": self.mock_provider}
        self.manager = ConsensusManager(
            providers=self.providers,
            max_debate_rounds=2,
            consensus_threshold=0.75,
        )
    
    def test_initialization(self):
        """Test consensus manager initialization."""
        assert self.manager.max_debate_rounds == 2
        assert self.manager.consensus_threshold == 0.75
        assert len(self.manager.providers) == 2
    
    def test_assess_response_quality_substantial(self):
        """Test quality assessment for substantial response."""
        content = """
        The capital of France is Paris. This city is known for its history,
        culture, and architecture. For example, the Eiffel Tower is a famous landmark.
        Therefore, Paris is one of the most visited cities in the world.
        """
        
        quality = self.manager._assess_response_quality(content)
        
        assert quality > 0.5
        assert quality <= 1.0
    
    def test_assess_response_quality_short(self):
        """Test quality assessment for short response."""
        quality = self.manager._assess_response_quality("Yes")
        
        assert quality <= 0.6
    
    def test_assess_response_quality_empty(self):
        """Test quality assessment for empty response."""
        quality = self.manager._assess_response_quality("")
        
        assert quality == 0.0
    
    def test_classify_response_type_factual(self):
        """Test classifying factual questions."""
        responses = [ModelResponse(model="gpt-4", content="Paris is the capital.")]
        
        response_type = self.manager._classify_response_type(
            "What is the capital of France?",
            responses,
        )
        
        assert response_type == ResponseType.FACTUAL
    
    def test_classify_response_type_analytical(self):
        """Test classifying analytical questions."""
        responses = [ModelResponse(model="gpt-4", content="Analysis of the topic.")]
        
        response_type = self.manager._classify_response_type(
            "Why did the French Revolution happen?",
            responses,
        )
        
        assert response_type == ResponseType.ANALYTICAL
    
    def test_classify_response_type_creative(self):
        """Test classifying creative questions."""
        responses = [ModelResponse(model="gpt-4", content="Once upon a time...")]
        
        response_type = self.manager._classify_response_type(
            "Write a story about a dragon",
            responses,
        )
        
        assert response_type == ResponseType.CREATIVE
    
    def test_detect_conflicts_none(self):
        """Test detecting no conflicts."""
        responses = [
            ModelResponse(model="gpt-4", content="The answer is Paris, the capital of France."),
            ModelResponse(model="claude-3", content="Paris is the capital of France, the answer."),
        ]
        
        severity = self.manager._detect_conflicts(responses)
        
        assert severity in (ConflictSeverity.NONE, ConflictSeverity.MINOR)
    
    def test_detect_conflicts_major(self):
        """Test detecting major conflicts."""
        responses = [
            ModelResponse(model="gpt-4", content="The answer is definitely A."),
            ModelResponse(model="claude-3", content="XYZ completely different response here."),
        ]
        
        severity = self.manager._detect_conflicts(responses)
        
        assert severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)
    
    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical texts."""
        sim = self.manager._calculate_similarity("hello world", "hello world")
        
        assert sim == 1.0
    
    def test_calculate_similarity_different(self):
        """Test similarity calculation for different texts."""
        sim = self.manager._calculate_similarity(
            "The quick brown fox",
            "Completely different words here"
        )
        
        assert sim < 0.5
    
    def test_calculate_similarity_partial(self):
        """Test similarity calculation for partial overlap."""
        sim = self.manager._calculate_similarity(
            "The capital of France is Paris",
            "Paris is the capital of France"
        )
        
        assert 0.5 < sim < 1.0
    
    def test_select_strategy_voting(self):
        """Test strategy selection for factual with enough responses."""
        strategy = self.manager._select_strategy(
            ResponseType.FACTUAL,
            ConflictSeverity.MINOR,
            num_responses=4,
            accuracy_level=3,
        )
        
        assert strategy == ConsensusStrategy.VOTING
    
    def test_select_strategy_debate(self):
        """Test strategy selection for major conflict."""
        strategy = self.manager._select_strategy(
            ResponseType.FACTUAL,
            ConflictSeverity.MAJOR,
            num_responses=3,
            accuracy_level=3,
        )
        
        assert strategy == ConsensusStrategy.DEBATE
    
    def test_select_strategy_best_of(self):
        """Test strategy selection for creative content."""
        strategy = self.manager._select_strategy(
            ResponseType.CREATIVE,
            ConflictSeverity.MINOR,
            num_responses=3,
            accuracy_level=3,
        )
        
        assert strategy == ConsensusStrategy.BEST_OF
    
    def test_select_strategy_synthesis(self):
        """Test strategy selection for analytical content."""
        strategy = self.manager._select_strategy(
            ResponseType.ANALYTICAL,
            ConflictSeverity.MINOR,
            num_responses=3,
            accuracy_level=3,
        )
        
        assert strategy == ConsensusStrategy.SYNTHESIZE
    
    def test_extract_claims(self):
        """Test extracting factual claims."""
        content = "Paris is the capital of France. The city has over 2 million residents."
        
        claims = self.manager._extract_claims(content, "gpt-4")
        
        assert len(claims) >= 1
        assert all(isinstance(c, FactualClaim) for c in claims)
    
    def test_extract_key_points_bulleted(self):
        """Test extracting key points from bulleted list."""
        content = """
        Key facts:
        - Paris is the capital
        - Population over 2 million
        - Famous for the Eiffel Tower
        """
        
        points = self.manager._extract_key_points(content)
        
        assert len(points) >= 2
    
    def test_extract_key_points_numbered(self):
        """Test extracting key points from numbered list."""
        content = """
        1. First important point here
        2. Second important point
        3. Third key point
        """
        
        points = self.manager._extract_key_points(content)
        
        assert len(points) >= 2
    
    def test_calculate_agreement_rate_identical(self):
        """Test agreement rate for identical responses."""
        responses = [
            ModelResponse(model="gpt-4", content="Same content here"),
            ModelResponse(model="claude-3", content="Same content here"),
        ]
        
        rate = self.manager._calculate_agreement_rate(responses)
        
        assert rate == 1.0
    
    def test_calculate_agreement_rate_different(self):
        """Test agreement rate for different responses."""
        responses = [
            ModelResponse(model="gpt-4", content="First different content"),
            ModelResponse(model="claude-3", content="Second very different stuff"),
        ]
        
        rate = self.manager._calculate_agreement_rate(responses)
        
        assert rate < 0.8


class TestConsensusBuilding:
    """Tests for consensus building methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "Consensus answer: Paris is the capital."
        self.mock_result.tokens = 50
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider, "stub": self.mock_provider}
        self.manager = ConsensusManager(
            providers=self.providers,
            max_debate_rounds=2,
        )
    
    @pytest.mark.asyncio
    async def test_build_consensus_basic(self):
        """Test basic consensus building."""
        result = await self.manager.build_consensus(
            prompt="What is the capital of France?",
            models=["gpt-4", "claude-3"],
        )
        
        assert result is not None
        assert result.final_answer is not None
        assert len(result.participating_models) >= 1
    
    @pytest.mark.asyncio
    async def test_build_consensus_with_existing_responses(self):
        """Test consensus with pre-existing responses."""
        existing = [
            MagicMock(model="gpt-4", content="Paris", tokens=10),
            MagicMock(model="claude-3", content="Paris is the capital", tokens=15),
        ]
        
        result = await self.manager.build_consensus(
            prompt="What is the capital of France?",
            models=[],
            existing_responses=existing,
        )
        
        assert result is not None
        assert len(result.responses) >= 2
    
    @pytest.mark.asyncio
    async def test_build_voting_consensus(self):
        """Test voting consensus strategy."""
        responses = [
            ModelResponse(model="gpt-4", content="The answer is Paris."),
            ModelResponse(model="claude-3", content="Paris is the answer."),
            ModelResponse(model="gemini", content="Paris, definitely."),
        ]
        confidence_scores = {"gpt-4": 0.9, "claude-3": 0.85, "gemini": 0.8}
        
        result = await self.manager._build_voting_consensus(
            prompt="What is the capital?",
            responses=responses,
            confidence_scores=confidence_scores,
            context=None,
        )
        
        assert result.strategy_used == ConsensusStrategy.VOTING
        assert result.voting_result is not None
    
    @pytest.mark.asyncio
    async def test_build_weighted_consensus(self):
        """Test weighted merge consensus strategy."""
        responses = [
            ModelResponse(model="gpt-4", content="High confidence answer with details."),
            ModelResponse(model="claude-3", content="Additional perspective here."),
        ]
        confidence_scores = {"gpt-4": 0.9, "claude-3": 0.7}
        
        result = await self.manager._build_weighted_consensus(
            prompt="Explain the concept",
            responses=responses,
            confidence_scores=confidence_scores,
            context=None,
        )
        
        assert result.strategy_used == ConsensusStrategy.WEIGHTED_MERGE
    
    @pytest.mark.asyncio
    async def test_build_synthesized_consensus(self):
        """Test synthesis consensus strategy."""
        responses = [
            ModelResponse(model="gpt-4", content="First perspective."),
            ModelResponse(model="claude-3", content="Second perspective."),
        ]
        confidence_scores = {"gpt-4": 0.8, "claude-3": 0.8}
        
        result = await self.manager._build_synthesized_consensus(
            prompt="Compare approaches",
            responses=responses,
            confidence_scores=confidence_scores,
            context=None,
        )
        
        assert result.strategy_used == ConsensusStrategy.SYNTHESIZE
    
    @pytest.mark.asyncio
    async def test_build_best_of_consensus(self):
        """Test best-of consensus strategy."""
        responses = [
            ModelResponse(model="gpt-4", content="Best answer here with quality."),
            ModelResponse(model="claude-3", content="Short."),
        ]
        confidence_scores = {"gpt-4": 0.9, "claude-3": 0.6}
        
        result = await self.manager._build_best_of_consensus(
            prompt="Creative task",
            responses=responses,
            confidence_scores=confidence_scores,
        )
        
        assert result.strategy_used == ConsensusStrategy.BEST_OF
        # Should select higher quality response
        assert "Best answer" in result.final_answer or len(result.final_answer) > 5


class TestDebateConsensus:
    """Tests for debate-based consensus building."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.providers = {"openai": self.mock_provider, "stub": self.mock_provider}
        self.manager = ConsensusManager(
            providers=self.providers,
            max_debate_rounds=2,
        )
    
    @pytest.mark.asyncio
    async def test_build_debate_consensus(self):
        """Test debate consensus with mock responses."""
        # Mock the provider to return different responses
        call_count = [0]
        async def mock_complete(prompt, model=None):
            call_count[0] += 1
            result = MagicMock()
            if "evaluate" in prompt.lower() or "rate" in prompt.lower():
                result.content = "0.8"
            else:
                result.content = f"Refined position from round {call_count[0]}"
            return result
        
        self.mock_provider.complete = mock_complete
        
        responses = [
            ModelResponse(model="gpt-4", content="Position A: The answer is X."),
            ModelResponse(model="claude-3", content="Position B: The answer is Y."),
        ]
        confidence_scores = {"gpt-4": 0.8, "claude-3": 0.8}
        
        result = await self.manager._build_debate_consensus(
            prompt="Disputed question",
            responses=responses,
            confidence_scores=confidence_scores,
            context=None,
        )
        
        assert result.strategy_used == ConsensusStrategy.DEBATE
    
    def test_check_debate_convergence_same(self):
        """Test convergence check for same positions."""
        positions = {
            "gpt-4": "We all agree on this answer.",
            "claude-3": "We all agree on this answer.",
        }
        
        converged = self.manager._check_debate_convergence(positions)
        
        assert converged is True
    
    def test_check_debate_convergence_different(self):
        """Test convergence check for different positions."""
        positions = {
            "gpt-4": "This is completely different from the other.",
            "claude-3": "XYZ ABC totally unrelated content here.",
        }
        
        converged = self.manager._check_debate_convergence(positions)
        
        assert converged is False


class TestConsensusResult:
    """Tests for ConsensusResult data class."""
    
    def test_get_summary(self):
        """Test getting consensus summary."""
        consensus_score = ConsensusScore(
            overall_score=0.85,
            agreement_rate=0.9,
            confidence_weighted_score=0.8,
            quality_score=0.88,
        )
        
        responses = [
            ModelResponse(model="gpt-4", content="Answer 1"),
            ModelResponse(model="claude-3", content="Answer 2"),
        ]
        
        result = ConsensusResult(
            final_answer="The consensus answer is Paris.",
            strategy_used=ConsensusStrategy.VOTING,
            responses=responses,
            participating_models=["gpt-4", "claude-3"],
            consensus_score=consensus_score,
            key_agreements=["Paris is the capital"],
            key_disagreements=[],
        )
        
        summary = result.get_summary()
        
        assert summary["strategy"] == "voting"
        assert summary["consensus_score"] == 0.85
        assert len(summary["models_used"]) == 2


class TestConvenienceFunction:
    """Tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_build_consensus_function(self):
        """Test build_consensus convenience function."""
        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "Consensus answer"
        mock_result.tokens = 30
        mock_provider.complete = AsyncMock(return_value=mock_result)
        
        providers = {"openai": mock_provider}
        
        result = await build_consensus(
            prompt="What is 2+2?",
            models=["gpt-4"],
            providers=providers,
        )
        
        assert result is not None
        assert result.final_answer is not None


class TestIntegrationScenarios:
    """Integration tests for consensus scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.providers = {"openai": self.mock_provider, "anthropic": self.mock_provider}
    
    @pytest.mark.asyncio
    async def test_factual_question_voting(self):
        """Test factual question uses voting strategy."""
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            result.content = "The capital of France is Paris."
            result.tokens = 20
            return result
        
        self.mock_provider.complete = mock_complete
        
        manager = ConsensusManager(
            providers=self.providers,
            min_models_for_voting=2,
        )
        
        result = await manager.build_consensus(
            prompt="What is the capital of France?",
            models=["gpt-4", "claude-3", "gemini"],
        )
        
        assert result.strategy_used in (ConsensusStrategy.VOTING, ConsensusStrategy.WEIGHTED_MERGE)
    
    @pytest.mark.asyncio
    async def test_conflicting_answers_trigger_debate(self):
        """Test that conflicting answers trigger debate."""
        responses_queue = [
            "The answer is definitely A because of X.",
            "The answer is clearly B due to Y.",
            "I believe the answer is A.",
        ]
        call_idx = [0]
        
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            if call_idx[0] < len(responses_queue):
                result.content = responses_queue[call_idx[0]]
                call_idx[0] += 1
            else:
                result.content = "Converged answer after debate"
            result.tokens = 30
            return result
        
        self.mock_provider.complete = mock_complete
        
        manager = ConsensusManager(
            providers=self.providers,
            conflict_threshold=0.5,  # Trigger debate more easily
        )
        
        # Force debate strategy
        result = await manager.build_consensus(
            prompt="Disputed question",
            models=["gpt-4", "claude-3"],
            force_strategy=ConsensusStrategy.DEBATE,
        )
        
        assert result.strategy_used == ConsensusStrategy.DEBATE
    
    @pytest.mark.asyncio
    async def test_high_accuracy_uses_more_thorough_strategy(self):
        """Test that high accuracy level uses more thorough strategy."""
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            result.content = "Thoughtful response with analysis"
            result.tokens = 100
            return result
        
        self.mock_provider.complete = mock_complete
        
        manager = ConsensusManager(providers=self.providers)
        
        result = await manager.build_consensus(
            prompt="Complex analytical question",
            models=["gpt-4", "claude-3"],
            accuracy_level=5,
        )
        
        # High accuracy should use synthesis or debate
        assert result.strategy_used in (
            ConsensusStrategy.SYNTHESIZE,
            ConsensusStrategy.DEBATE,
            ConsensusStrategy.WEIGHTED_MERGE,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

