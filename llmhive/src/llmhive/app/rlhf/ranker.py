"""Answer Ranking using Reward Model.

This module provides:
- Answer ranking based on reward model scores
- Best answer selection from candidates
- Integration with orchestrator for quality-based routing

Usage:
    ranker = AnswerRanker()
    
    # Rank multiple candidate answers
    ranked = await ranker.rank(
        query="What is ML?",
        candidates=["ML is...", "Machine learning is...", "AI subset..."],
    )
    
    # Get best answer
    best = await ranker.select_best(query, candidates)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .reward_model import RewardModel, RewardScore, get_reward_model

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass(slots=True)
class RankedAnswer:
    """A ranked answer with score."""
    answer: str
    score: float
    rank: int
    confidence: float
    model_source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RankingResult:
    """Result of ranking multiple answers."""
    query: str
    ranked_answers: List[RankedAnswer]
    best_answer: str
    best_score: float
    spread: float  # Difference between best and worst
    
    @property
    def is_confident(self) -> bool:
        """Check if there's a clear winner."""
        return self.spread >= 0.2


# ==============================================================================
# Answer Ranker
# ==============================================================================

class AnswerRanker:
    """Ranks answer candidates using reward model.
    
    Features:
    - Score-based ranking
    - Best answer selection
    - Confidence estimation
    - Model source tracking
    
    Usage:
        ranker = AnswerRanker()
        
        # Rank answers
        result = await ranker.rank(
            query="Explain quantum computing",
            candidates=[
                "Quantum computing uses...",
                "QC is a type of...",
                "It's about qubits...",
            ],
            model_sources=["gpt-4o", "claude-3", "mistral"],
        )
        
        # Use best answer
        print(result.best_answer)
    """
    
    def __init__(
        self,
        reward_model: Optional[RewardModel] = None,
        min_candidates: int = 1,
    ):
        self.reward_model = reward_model or get_reward_model()
        self.min_candidates = min_candidates
    
    async def rank(
        self,
        query: str,
        candidates: List[str],
        context: Optional[str] = None,
        model_sources: Optional[List[str]] = None,
    ) -> RankingResult:
        """
        Rank candidate answers by quality.
        
        Args:
            query: The original question
            candidates: List of candidate answers
            context: Optional context
            model_sources: Optional list of model names that generated each answer
            
        Returns:
            RankingResult with ranked answers
        """
        if not candidates:
            raise ValueError("No candidates provided")
        
        if len(candidates) == 1:
            # Only one candidate, score it anyway
            score = await self.reward_model.score(query, candidates[0], context)
            return RankingResult(
                query=query,
                ranked_answers=[
                    RankedAnswer(
                        answer=candidates[0],
                        score=score.score,
                        rank=1,
                        confidence=score.confidence,
                        model_source=model_sources[0] if model_sources else None,
                    )
                ],
                best_answer=candidates[0],
                best_score=score.score,
                spread=0.0,
            )
        
        # Score all candidates
        tasks = [
            self.reward_model.score(query, answer, context)
            for answer in candidates
        ]
        scores: List[RewardScore] = await asyncio.gather(*tasks)
        
        # Create ranked answers
        answer_scores = [
            (candidates[i], scores[i], model_sources[i] if model_sources else None)
            for i in range(len(candidates))
        ]
        
        # Sort by score descending
        answer_scores.sort(key=lambda x: x[1].score, reverse=True)
        
        ranked_answers = [
            RankedAnswer(
                answer=ans,
                score=sc.score,
                rank=i + 1,
                confidence=sc.confidence,
                model_source=src,
            )
            for i, (ans, sc, src) in enumerate(answer_scores)
        ]
        
        best = ranked_answers[0]
        worst = ranked_answers[-1]
        spread = best.score - worst.score
        
        logger.debug(
            "Ranked %d answers: best=%.3f worst=%.3f spread=%.3f",
            len(candidates), best.score, worst.score, spread,
        )
        
        return RankingResult(
            query=query,
            ranked_answers=ranked_answers,
            best_answer=best.answer,
            best_score=best.score,
            spread=spread,
        )
    
    async def select_best(
        self,
        query: str,
        candidates: List[str],
        context: Optional[str] = None,
        min_score: float = 0.5,
    ) -> Tuple[str, float]:
        """
        Select the best answer from candidates.
        
        Args:
            query: The question
            candidates: Candidate answers
            context: Optional context
            min_score: Minimum acceptable score
            
        Returns:
            (best_answer, score)
        """
        result = await self.rank(query, candidates, context)
        
        if result.best_score < min_score:
            logger.warning(
                "Best answer score (%.3f) below threshold (%.3f)",
                result.best_score, min_score,
            )
        
        return result.best_answer, result.best_score
    
    async def filter_quality(
        self,
        query: str,
        candidates: List[str],
        context: Optional[str] = None,
        min_score: float = 0.5,
    ) -> List[str]:
        """
        Filter answers by quality threshold.
        
        Args:
            query: The question
            candidates: Candidate answers
            context: Optional context
            min_score: Minimum score to include
            
        Returns:
            List of answers meeting the threshold
        """
        result = await self.rank(query, candidates, context)
        
        filtered = [
            ra.answer
            for ra in result.ranked_answers
            if ra.score >= min_score
        ]
        
        logger.debug(
            "Filtered %d/%d answers with score >= %.2f",
            len(filtered), len(candidates), min_score,
        )
        
        return filtered
    
    async def rerank_with_feedback(
        self,
        query: str,
        candidates: List[str],
        user_preferences: Dict[str, float],
        context: Optional[str] = None,
    ) -> RankingResult:
        """
        Rerank answers incorporating user preference history.
        
        Args:
            query: The question
            candidates: Candidate answers
            user_preferences: Dict of {keyword: preference_weight}
            context: Optional context
            
        Returns:
            RankingResult adjusted for user preferences
        """
        # Get base ranking
        result = await self.rank(query, candidates, context)
        
        # Adjust scores based on user preferences
        for ranked in result.ranked_answers:
            adjustment = 0.0
            answer_lower = ranked.answer.lower()
            
            for keyword, weight in user_preferences.items():
                if keyword.lower() in answer_lower:
                    adjustment += weight * 0.1  # Small adjustment
            
            ranked.score = min(1.0, max(0.0, ranked.score + adjustment))
        
        # Re-sort
        result.ranked_answers.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, ranked in enumerate(result.ranked_answers):
            ranked.rank = i + 1
        
        result.best_answer = result.ranked_answers[0].answer
        result.best_score = result.ranked_answers[0].score
        
        return result


# ==============================================================================
# Convenience Functions
# ==============================================================================

_ranker: Optional[AnswerRanker] = None


def get_answer_ranker() -> AnswerRanker:
    """Get global answer ranker."""
    global _ranker
    if _ranker is None:
        _ranker = AnswerRanker()
    return _ranker


async def rank_answers(
    query: str,
    candidates: List[str],
    context: Optional[str] = None,
) -> RankingResult:
    """Quick helper to rank answers."""
    ranker = get_answer_ranker()
    return await ranker.rank(query, candidates, context)


async def select_best_answer(
    query: str,
    candidates: List[str],
    context: Optional[str] = None,
) -> Tuple[str, float]:
    """Quick helper to select best answer."""
    ranker = get_answer_ranker()
    return await ranker.select_best(query, candidates, context)


# ==============================================================================
# Orchestrator Integration
# ==============================================================================

class RewardGuidedSelector:
    """Selector for orchestrator that uses reward model.
    
    Integrates with the consensus/ensemble system to select
    the best answer from multiple model outputs.
    """
    
    def __init__(self, ranker: Optional[AnswerRanker] = None):
        self.ranker = ranker or get_answer_ranker()
    
    async def select_from_ensemble(
        self,
        query: str,
        model_outputs: Dict[str, str],  # {model_name: answer}
        context: Optional[str] = None,
        min_score: float = 0.5,
    ) -> Tuple[str, str, float]:
        """
        Select best answer from ensemble outputs.
        
        Args:
            query: The question
            model_outputs: Dict mapping model names to their answers
            context: Optional context
            min_score: Minimum acceptable score
            
        Returns:
            (best_model, best_answer, score)
        """
        if not model_outputs:
            raise ValueError("No model outputs provided")
        
        models = list(model_outputs.keys())
        answers = list(model_outputs.values())
        
        result = await self.ranker.rank(
            query=query,
            candidates=answers,
            context=context,
            model_sources=models,
        )
        
        best = result.ranked_answers[0]
        
        return best.model_source or "unknown", best.answer, best.score
    
    async def improve_consensus(
        self,
        query: str,
        consensus_answer: str,
        individual_answers: List[str],
        context: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Check if consensus answer is good, or select better alternative.
        
        Args:
            query: The question
            consensus_answer: The synthesized consensus answer
            individual_answers: Original individual model answers
            context: Optional context
            
        Returns:
            (best_answer, was_consensus_best)
        """
        all_answers = [consensus_answer] + individual_answers
        
        result = await self.ranker.rank(query, all_answers, context)
        
        best = result.best_answer
        was_consensus = (best == consensus_answer)
        
        if not was_consensus:
            logger.info(
                "Reward model selected alternative over consensus: %.3f vs %.3f",
                result.best_score,
                result.ranked_answers[
                    next(i for i, r in enumerate(result.ranked_answers) 
                         if r.answer == consensus_answer)
                ].score,
            )
        
        return best, was_consensus

