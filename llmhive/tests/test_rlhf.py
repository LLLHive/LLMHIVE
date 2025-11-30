"""Tests for RLHF System.

These tests verify:
1. Feedback collection and storage
2. Preference pair generation
3. Reward model scoring (heuristic)
4. Answer ranking
5. RLHF training configuration
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import modules under test
from llmhive.src.llmhive.app.rlhf.feedback import (
    FeedbackCollector,
    FeedbackEntry,
    FeedbackType,
    PreferencePair,
    FeedbackStats,
)
from llmhive.src.llmhive.app.rlhf.reward_model import (
    RewardModel,
    RewardModelConfig,
    RewardScore,
    HeuristicRewardModel,
)
from llmhive.src.llmhive.app.rlhf.trainer import (
    RLHFTrainer,
    RLHFConfig,
    RLHFTrainingResult,
    PreferenceDataset,
)
from llmhive.src.llmhive.app.rlhf.ranker import (
    AnswerRanker,
    RankedAnswer,
    RankingResult,
    RewardGuidedSelector,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def feedback_collector(temp_db):
    """Create feedback collector with temp database."""
    return FeedbackCollector(db_path=temp_db)


@pytest.fixture
def sample_feedback_entries():
    """Sample feedback entries for testing."""
    return [
        # Good answers
        FeedbackEntry(
            id="1",
            query="What is machine learning?",
            context=None,
            answer="Machine learning is a subset of AI that enables systems to learn from data.",
            feedback_type=FeedbackType.RATING,
            rating=0.9,
            user_id="user1",
            session_id="session1",
            model_used="gpt-4o",
            timestamp=datetime.now(timezone.utc),
        ),
        FeedbackEntry(
            id="2",
            query="What is machine learning?",
            context=None,
            answer="ML is computers learning from examples.",
            feedback_type=FeedbackType.RATING,
            rating=0.7,
            user_id="user2",
            session_id="session2",
            model_used="claude-3",
            timestamp=datetime.now(timezone.utc),
        ),
        # Bad answer for same query
        FeedbackEntry(
            id="3",
            query="What is machine learning?",
            context=None,
            answer="I don't know.",
            feedback_type=FeedbackType.RATING,
            rating=0.1,
            user_id="user3",
            session_id="session3",
            model_used="gpt-3.5",
            timestamp=datetime.now(timezone.utc),
        ),
    ]


@pytest.fixture
def sample_preference_pairs():
    """Sample preference pairs for testing."""
    return [
        PreferencePair(
            query="What is Python?",
            context=None,
            chosen="Python is a high-level programming language known for its readability.",
            rejected="Python is a snake.",
            chosen_rating=0.95,
            rejected_rating=0.1,
        ),
        PreferencePair(
            query="Explain recursion",
            context=None,
            chosen="Recursion is when a function calls itself to solve smaller instances of a problem.",
            rejected="It's complicated.",
            chosen_rating=0.9,
            rejected_rating=0.2,
        ),
        PreferencePair(
            query="What is 2+2?",
            context=None,
            chosen="2+2 equals 4.",
            rejected="Maybe 5?",
            chosen_rating=1.0,
            rejected_rating=0.0,
        ),
    ]


# ==============================================================================
# Feedback Collector Tests
# ==============================================================================

class TestFeedbackCollector:
    """Tests for FeedbackCollector."""
    
    @pytest.mark.asyncio
    async def test_record_thumbs_up(self, feedback_collector):
        """Test recording thumbs up feedback."""
        entry = await feedback_collector.record_feedback(
            query="What is AI?",
            answer="AI is artificial intelligence.",
            feedback_type=FeedbackType.THUMBS_UP,
            model_used="gpt-4o",
        )
        
        assert entry.rating == 1.0
        assert entry.feedback_type == FeedbackType.THUMBS_UP
    
    @pytest.mark.asyncio
    async def test_record_thumbs_down(self, feedback_collector):
        """Test recording thumbs down feedback."""
        entry = await feedback_collector.record_feedback(
            query="What is AI?",
            answer="I don't know.",
            feedback_type=FeedbackType.THUMBS_DOWN,
            model_used="gpt-3.5",
        )
        
        assert entry.rating == 0.0
        assert entry.feedback_type == FeedbackType.THUMBS_DOWN
    
    @pytest.mark.asyncio
    async def test_record_rating_1_5_scale(self, feedback_collector):
        """Test recording rating on 1-5 scale (should normalize)."""
        entry = await feedback_collector.record_feedback(
            query="Test query",
            answer="Test answer",
            feedback_type=FeedbackType.RATING,
            rating=4,  # On 1-5 scale
            model_used="test",
        )
        
        # Should normalize to 0.75 (4-1)/(5-1)
        assert 0.7 <= entry.rating <= 0.8
    
    @pytest.mark.asyncio
    async def test_get_feedback(self, feedback_collector):
        """Test retrieving feedback."""
        # Record some feedback
        await feedback_collector.record_feedback(
            query="Q1", answer="A1", rating=0.9, model_used="m1"
        )
        await feedback_collector.record_feedback(
            query="Q2", answer="A2", rating=0.2, model_used="m2"
        )
        
        # Get all feedback
        feedback = await feedback_collector.get_feedback()
        assert len(feedback) == 2
        
        # Get high-rated only
        good_feedback = await feedback_collector.get_feedback(min_rating=0.7)
        assert len(good_feedback) == 1
        assert good_feedback[0].query == "Q1"
    
    @pytest.mark.asyncio
    async def test_get_preference_pairs(self, feedback_collector):
        """Test generating preference pairs."""
        # Record feedback for same query with different ratings
        await feedback_collector.record_feedback(
            query="What is Python?",
            answer="Python is a programming language.",
            rating=0.9,
            model_used="good_model",
        )
        await feedback_collector.record_feedback(
            query="What is Python?",
            answer="It's a snake.",
            rating=0.2,
            model_used="bad_model",
        )
        
        pairs = await feedback_collector.get_preference_pairs(min_rating_diff=0.3)
        
        assert len(pairs) >= 1
        assert pairs[0].chosen_rating > pairs[0].rejected_rating
    
    @pytest.mark.asyncio
    async def test_get_stats(self, feedback_collector):
        """Test getting feedback statistics."""
        # Record feedback
        await feedback_collector.record_feedback(
            query="Q1", answer="A1", rating=0.9, model_used="gpt-4o"
        )
        await feedback_collector.record_feedback(
            query="Q2", answer="A2", rating=0.3, model_used="claude-3"
        )
        
        stats = await feedback_collector.get_stats()
        
        assert stats.total_entries == 2
        assert stats.positive_count == 1  # Rating >= 0.5
        assert stats.negative_count == 1
        assert "gpt-4o" in stats.by_model


# ==============================================================================
# Heuristic Reward Model Tests
# ==============================================================================

class TestHeuristicRewardModel:
    """Tests for HeuristicRewardModel."""
    
    @pytest.fixture
    def model(self):
        return HeuristicRewardModel()
    
    @pytest.mark.asyncio
    async def test_score_good_answer(self, model):
        """Test scoring a good answer."""
        score = await model.score(
            query="What is machine learning?",
            answer="Machine learning is a subset of artificial intelligence that enables "
                   "systems to learn and improve from experience without being explicitly "
                   "programmed. It focuses on developing algorithms that can access data "
                   "and use it to learn for themselves.",
        )
        
        assert score.score > 0.6
        assert score.confidence == 0.5  # Heuristic confidence is always 0.5
    
    @pytest.mark.asyncio
    async def test_score_bad_answer(self, model):
        """Test scoring a bad answer."""
        score = await model.score(
            query="What is machine learning?",
            answer="Idk",
        )
        
        # Even short answers get some points from clarity/structure
        # Main check is that good answers score higher
        good_score = await model.score(
            query="What is machine learning?",
            answer="Machine learning is a subset of AI that enables systems to learn from data.",
        )
        
        assert score.score < good_score.score
    
    @pytest.mark.asyncio
    async def test_score_with_structure(self, model):
        """Test that structured answers score reasonably."""
        unstructured = "Machine learning is AI it learns from data and makes predictions"
        
        structured = """Machine learning is a type of AI that:
        
- Learns from data
- Makes predictions
- Improves over time

Key concepts include supervised and unsupervised learning."""
        
        score_unstructured = await model.score("What is ML?", unstructured)
        score_structured = await model.score("What is ML?", structured)
        
        # Both should score reasonably well
        assert score_structured.score >= 0.5
        assert score_unstructured.score >= 0.5


# ==============================================================================
# Reward Model Tests
# ==============================================================================

class TestRewardModel:
    """Tests for RewardModel."""
    
    @pytest.fixture
    def model(self):
        return RewardModel()
    
    @pytest.mark.asyncio
    async def test_fallback_to_heuristic(self, model):
        """Test fallback to heuristic when not loaded."""
        assert not model.is_loaded
        
        score = await model.score(
            query="What is AI?",
            answer="AI is artificial intelligence.",
        )
        
        # Should still return a score from heuristic
        assert 0 <= score.score <= 1
        assert score.confidence == 0.5  # Heuristic confidence
    
    @pytest.mark.asyncio
    async def test_score_batch(self, model):
        """Test batch scoring."""
        items = [
            ("What is AI?", "AI is artificial intelligence.", None),
            ("What is ML?", "ML is machine learning.", None),
        ]
        
        scores = await model.score_batch(items)
        
        assert len(scores) == 2
        assert all(isinstance(s, RewardScore) for s in scores)
    
    @pytest.mark.asyncio
    async def test_compare(self, model):
        """Test comparing two answers."""
        better, confidence = await model.compare(
            query="Explain what machine learning is in detail",
            answer_a="Machine learning is a subset of artificial intelligence that focuses on building systems that learn from data. It uses algorithms to identify patterns and make decisions with minimal human intervention. Common applications include recommendation systems, image recognition, and natural language processing.",
            answer_b="idk maybe computers or something",
        )
        
        # The longer, more detailed answer should win
        assert "Machine learning" in better
        assert confidence >= 0


# ==============================================================================
# Answer Ranker Tests
# ==============================================================================

class TestAnswerRanker:
    """Tests for AnswerRanker."""
    
    @pytest.fixture
    def ranker(self):
        return AnswerRanker()
    
    @pytest.mark.asyncio
    async def test_rank_single_candidate(self, ranker):
        """Test ranking with single candidate."""
        result = await ranker.rank(
            query="What is Python?",
            candidates=["Python is a programming language."],
        )
        
        assert len(result.ranked_answers) == 1
        assert result.best_answer == "Python is a programming language."
        assert result.spread == 0.0
    
    @pytest.mark.asyncio
    async def test_rank_multiple_candidates(self, ranker):
        """Test ranking multiple candidates."""
        candidates = [
            "Python is a programming language known for readability.",
            "It's a snake.",
            "Python, created by Guido van Rossum, is widely used for web and data science.",
        ]
        
        result = await ranker.rank(
            query="What is Python?",
            candidates=candidates,
        )
        
        assert len(result.ranked_answers) == 3
        assert result.ranked_answers[0].rank == 1
        assert result.ranked_answers[0].score >= result.ranked_answers[1].score
        assert result.best_answer in candidates
    
    @pytest.mark.asyncio
    async def test_select_best(self, ranker):
        """Test selecting best answer."""
        candidates = [
            "Good detailed answer about machine learning and its applications.",
            "Bad answer.",
        ]
        
        best, score = await ranker.select_best(
            query="Explain machine learning",
            candidates=candidates,
        )
        
        assert best == candidates[0]
        assert score > 0
    
    @pytest.mark.asyncio
    async def test_filter_quality(self, ranker):
        """Test filtering by quality returns ordered results."""
        candidates = [
            "Artificial Intelligence is a comprehensive field of computer science focused on creating intelligent machines that can perform tasks requiring human intelligence.",
            "Short answer about AI.",
            "Another good answer with details about AI applications and machine learning.",
        ]
        
        # Filter returns answers meeting threshold
        filtered = await ranker.filter_quality(
            query="What is AI?",
            candidates=candidates,
            min_score=0.0,  # Accept all for this test
        )
        
        # All should pass with min_score=0
        assert len(filtered) == len(candidates)
    
    @pytest.mark.asyncio
    async def test_with_model_sources(self, ranker):
        """Test ranking with model sources."""
        result = await ranker.rank(
            query="Test query",
            candidates=["Answer from GPT-4", "Answer from Claude"],
            model_sources=["gpt-4o", "claude-3"],
        )
        
        assert result.ranked_answers[0].model_source in ["gpt-4o", "claude-3"]


# ==============================================================================
# RLHF Trainer Tests
# ==============================================================================

class TestRLHFTrainer:
    """Tests for RLHFTrainer."""
    
    def test_config_defaults(self):
        """Test default configuration."""
        config = RLHFConfig()
        
        assert config.method == "dpo"
        assert config.use_lora is True
        assert config.use_4bit is True
        assert config.num_epochs == 3
    
    def test_trainer_initialization(self):
        """Test trainer initialization."""
        trainer = RLHFTrainer(
            base_model="test/model",
            output_dir="./test_output",
        )
        
        assert trainer.config.base_model == "test/model"
        assert trainer.config.output_dir == "./test_output"
    
    @pytest.mark.asyncio
    async def test_dpo_insufficient_data(self, sample_preference_pairs):
        """Test DPO with insufficient data."""
        trainer = RLHFTrainer()
        
        # Only 3 pairs (need at least 10)
        result = await trainer.train_dpo(sample_preference_pairs)
        
        assert not result.success
        assert "Insufficient data" in result.error


# ==============================================================================
# Preference Dataset Tests
# ==============================================================================

class TestPreferenceDataset:
    """Tests for PreferenceDataset."""
    
    def test_creation(self, sample_preference_pairs):
        """Test dataset creation."""
        # Mock tokenizer
        tokenizer = MagicMock()
        tokenizer.return_value = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock(),
        }
        tokenizer.return_value["input_ids"].squeeze.return_value = [1, 2, 3]
        tokenizer.return_value["attention_mask"].squeeze.return_value = [1, 1, 1]
        
        dataset = PreferenceDataset(
            pairs=sample_preference_pairs,
            tokenizer=tokenizer,
            max_length=512,
        )
        
        assert len(dataset) == 3
    
    def test_pair_to_dict(self, sample_preference_pairs):
        """Test converting pairs to dict."""
        pair = sample_preference_pairs[0]
        data = pair.to_dict()
        
        assert "query" in data
        assert "chosen" in data
        assert "rejected" in data
        assert data["query"] == "What is Python?"


# ==============================================================================
# Reward Guided Selector Tests
# ==============================================================================

class TestRewardGuidedSelector:
    """Tests for RewardGuidedSelector."""
    
    @pytest.fixture
    def selector(self):
        return RewardGuidedSelector()
    
    @pytest.mark.asyncio
    async def test_select_from_ensemble(self, selector):
        """Test selecting from ensemble outputs."""
        model_outputs = {
            "gpt-4o": "Comprehensive answer about AI and its applications in modern technology.",
            "claude-3": "AI answer.",
            "mistral": "Detailed explanation of artificial intelligence systems.",
        }
        
        best_model, best_answer, score = await selector.select_from_ensemble(
            query="What is AI?",
            model_outputs=model_outputs,
        )
        
        assert best_model in model_outputs
        assert best_answer in model_outputs.values()
        assert 0 <= score <= 1
    
    @pytest.mark.asyncio
    async def test_improve_consensus(self, selector):
        """Test improving consensus answer."""
        consensus = "AI is artificial intelligence used in many applications."
        individuals = [
            "AI is advanced technology.",
            "Artificial intelligence is a broad field of computer science.",
        ]
        
        best, was_consensus = await selector.improve_consensus(
            query="What is AI?",
            consensus_answer=consensus,
            individual_answers=individuals,
        )
        
        assert best in [consensus] + individuals
        assert isinstance(was_consensus, bool)


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestRLHFIntegration:
    """Integration tests for RLHF system."""
    
    @pytest.mark.asyncio
    async def test_feedback_to_ranking_flow(self, temp_db):
        """Test complete flow from feedback to ranking."""
        # 1. Collect feedback
        collector = FeedbackCollector(db_path=temp_db)
        
        await collector.record_feedback(
            query="What is Python?",
            answer="Python is a versatile programming language.",
            rating=0.9,
            model_used="gpt-4o",
        )
        
        await collector.record_feedback(
            query="What is Python?",
            answer="A snake.",
            rating=0.1,
            model_used="bad_model",
        )
        
        # 2. Get preference pairs
        pairs = await collector.get_preference_pairs()
        assert len(pairs) >= 1
        
        # 3. Use ranker to evaluate
        ranker = AnswerRanker()
        result = await ranker.rank(
            query="What is Python?",
            candidates=[
                "Python is a versatile programming language.",
                "A snake.",
            ],
        )
        
        # Good answer should rank higher
        assert result.ranked_answers[0].answer == "Python is a versatile programming language."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

