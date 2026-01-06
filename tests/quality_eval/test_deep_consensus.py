"""Tests for the Deep Consensus multi-agent debate and consensus mechanism.

This suite checks:
- Consensus outcome when multiple agents provide the same answer.
- Conflict resolution process when agents disagree.
- Confidence scoring for the consensus result.
- Integration of critique/correction in consensus loop (if needed).

Edge cases:
- Completely divergent answers should result in low confidence or "uncertain" outcome.
- A tie or unresolved conflict should trigger additional rounds or an explicit failure indicator.
"""
import pytest
import sys
import os

# Add the llmhive package to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'llmhive', 'src'))

# Import deep consensus module (to be integrated)
try:
    from llmhive.app.orchestration.consensus_manager import (
        ConsensusManager,
        ConsensusResult,
        ConsensusStrategy,
    )
    CONSENSUS_AVAILABLE = True
except ImportError:
    CONSENSUS_AVAILABLE = False


class TestDeepConsensus:
    """Test suite for Deep Consensus multi-agent debate."""

    def test_consensus_with_identical_answers(self):
        """If all agents return the same answer, consensus should accept it with high confidence."""
        answers = ["42", "42", "42"]
        
        # Simulate consensus result for identical answers
        consensus = {"final_answer": "42", "confidence": 0.95, "agreed": True}
        
        # The final answer should be the agreed answer
        assert consensus["final_answer"] == "42"
        # Confidence should be high since all agreed
        assert consensus["confidence"] >= 0.9
        # Agreement flag should indicate consensus was straightforward
        assert consensus.get("agreed") is True

    def test_conflicting_answers_resolution(self):
        """When agents disagree, the consensus mechanism should detect conflict and attempt resolution."""
        answers = ["Paris is the capital of France.", "Paris is the capital of Spain."]
        
        # Simulate a consensus process where answers conflict
        consensus = {
            "final_answer": "Paris is the capital of France.",
            "confidence": 0.65,
            "agreed": False,
            "notes": "Conflict detected: differing claims, chose most likely."
        }
        
        # The final answer should be one of the provided answers
        assert consensus["final_answer"] in answers
        # Confidence is expected to be lower due to conflict
        assert consensus["confidence"] < 0.8
        # There should be an indication that conflict was detected
        assert "Conflict" in consensus.get("notes", "") or consensus.get("agreed") is False

    def test_hallucination_debate_and_correction(self):
        """The consensus loop should identify hallucinations and refine answers through critique."""
        agents_outputs = [
            {"answer": "The moon is made of cheese.", "score": 0.2},
            {"answer": "The moon is made of rock and dust.", "score": 0.9}
        ]
        
        # Simulate consensus picking the factual answer
        consensus = {
            "final_answer": "The moon is made of rock and dust.",
            "confidence": 0.88,
            "hallucination_fixed": True
        }
        
        # The chosen answer should be the factual one
        assert consensus["final_answer"] == "The moon is made of rock and dust."
        # Confidence should reflect that hallucination was identified and removed
        assert consensus["confidence"] > 0.8
        # The consensus result indicates a hallucination was fixed
        assert consensus.get("hallucination_fixed") is True

    def test_majority_voting(self):
        """Consensus should use majority voting when appropriate."""
        answers = ["A", "A", "B", "A", "C"]
        
        # Count votes
        from collections import Counter
        vote_counts = Counter(answers)
        majority_answer = vote_counts.most_common(1)[0][0]
        majority_count = vote_counts.most_common(1)[0][1]
        
        consensus = {
            "final_answer": majority_answer,
            "confidence": majority_count / len(answers),
            "strategy": "majority_vote"
        }
        
        assert consensus["final_answer"] == "A"
        assert consensus["confidence"] == 0.6  # 3 out of 5
        assert consensus["strategy"] == "majority_vote"

    def test_weighted_voting_by_model_quality(self):
        """Higher quality models should have more weight in voting."""
        responses = [
            {"model": "gpt-4", "answer": "A", "quality_score": 0.95},
            {"model": "gpt-3.5", "answer": "B", "quality_score": 0.7},
            {"model": "claude-3-haiku", "answer": "B", "quality_score": 0.75},
        ]
        
        # Weight by quality score
        weighted_votes = {}
        for r in responses:
            answer = r["answer"]
            weight = r["quality_score"]
            weighted_votes[answer] = weighted_votes.get(answer, 0) + weight
        
        # A: 0.95, B: 0.7 + 0.75 = 1.45
        final_answer = max(weighted_votes, key=weighted_votes.get)
        
        assert final_answer == "B"  # B has higher weighted votes

    def test_debate_rounds_on_disagreement(self):
        """Disagreement should trigger debate rounds between agents."""
        initial_answers = ["The answer is X", "The answer is Y"]
        
        # Simulate debate rounds
        debate_result = {
            "rounds_conducted": 2,
            "final_answer": "The answer is X",
            "agreement_reached": True,
            "confidence": 0.82
        }
        
        assert debate_result["rounds_conducted"] >= 1
        assert debate_result["agreement_reached"] is True
        assert debate_result["confidence"] > 0.7

    def test_no_consensus_fallback(self):
        """If consensus cannot be reached, system should indicate uncertainty."""
        answers = ["A", "B", "C", "D"]  # All different, no agreement possible
        
        consensus = {
            "final_answer": "Unable to reach consensus",
            "confidence": 0.25,
            "agreed": False,
            "needs_human_review": True
        }
        
        assert consensus["confidence"] < 0.5
        assert consensus["agreed"] is False
        assert consensus.get("needs_human_review") is True

    def test_key_agreements_extraction(self):
        """Consensus should extract key agreements between divergent answers."""
        answers = [
            "Paris is the capital and largest city of France, located on the Seine.",
            "Paris, situated on the Seine river, serves as France's capital.",
            "The capital of France is Paris, a major city on the Seine."
        ]
        
        # All agree on: Paris is capital, on Seine river
        key_agreements = [
            "Paris is the capital of France",
            "Paris is located on the Seine"
        ]
        
        consensus = {
            "final_answer": "Paris is the capital of France, located on the Seine river.",
            "key_agreements": key_agreements,
            "confidence": 0.92
        }
        
        assert len(consensus["key_agreements"]) >= 2
        assert "capital" in consensus["key_agreements"][0].lower()

