"""Adaptive Ensemble Logic for LLMHive orchestrator.

Adaptive Ensemble implements dynamic model selection and ensemble voting based on
real-time performance metrics. Models are selected and weighted based on their
historical performance, current quality scores, and task-specific capabilities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..performance_tracker import ModelPerformance, performance_tracker
from ..services.base import LLMProvider, LLMResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EnsembleVote:
    """Represents a vote from a model in the ensemble."""

    model: str
    content: str
    weight: float  # Voting weight based on performance
    confidence: float  # Model's confidence in its answer
    quality_score: float  # Quality assessment of this vote


@dataclass(slots=True)
class EnsembleResult:
    """Result of adaptive ensemble voting."""

    final_answer: str
    votes: List[EnsembleVote]
    weighted_consensus: float  # Weighted consensus score
    selected_models: List[str]  # Models that participated
    performance_weights: Dict[str, float]  # Weight assigned to each model
    switching_events: List[Tuple[str, str, str]]  # (from_model, to_model, reason)


class AdaptiveEnsemble:
    """Manages adaptive ensemble model selection and voting."""

    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        min_models: int = 2,
        max_models: int = 5,
        performance_weight_factor: float = 0.6,  # How much performance history matters
        quality_weight_factor: float = 0.4,  # How much current quality matters
    ) -> None:
        self.providers = providers
        self.min_models = min_models
        self.max_models = max_models
        self.performance_weight_factor = performance_weight_factor
        self.quality_weight_factor = quality_weight_factor

    async def orchestrate_ensemble(
        self,
        prompt: str,
        available_models: List[str],
        *,
        context: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
    ) -> EnsembleResult:
        """Orchestrate an adaptive ensemble of models.

        Args:
            prompt: User prompt
            available_models: List of available model names
            context: Optional context
            required_capabilities: Optional required capabilities

        Returns:
            EnsembleResult with final answer and voting details
        """
        if not available_models:
            raise ValueError("At least one model is required for ensemble")

        # Step 1: Select models adaptively based on performance
        selected_models = self._select_adaptive_models(
            available_models,
            required_capabilities=required_capabilities or [],
        )

        logger.info("Adaptive ensemble selected models: %s", selected_models)

        # Step 2: Get initial responses from all selected models
        votes: List[EnsembleVote] = []
        switching_events: List[Tuple[str, str, str]] = []

        for model in selected_models:
            try:
                provider = self._select_provider(model)
                result = await provider.complete(prompt, model=model)

                # Calculate weight for this model
                weight = self._calculate_model_weight(model)

                # Assess quality of this response
                quality_score = await self._assess_response_quality(
                    prompt=prompt,
                    response=result.content,
                    model=model,
                )

                # Estimate confidence (simplified: based on response length and quality)
                confidence = min(1.0, quality_score * 0.7 + (len(result.content) / 1000.0) * 0.3)

                vote = EnsembleVote(
                    model=model,
                    content=result.content,
                    weight=weight,
                    confidence=confidence,
                    quality_score=quality_score,
                )
                votes.append(vote)

                logger.debug(
                    "Model %s: weight=%.2f, quality=%.2f, confidence=%.2f",
                    model,
                    weight,
                    quality_score,
                    confidence,
                )

            except Exception as exc:
                logger.warning("Model %s failed in ensemble: %s", model, exc)
                # Try to switch to backup model
                backup = self._find_backup_model(selected_models, model)
                if backup:
                    switching_events.append((model, backup, f"Failure: {exc}"))
                    # Retry with backup (simplified: just log for now)

        if not votes:
            raise RuntimeError("No models produced valid responses in ensemble")

        # Step 3: Weighted voting to determine final answer
        final_answer = self._weighted_voting(votes)

        # Step 4: Calculate weighted consensus
        weighted_consensus = self._calculate_weighted_consensus(votes)

        # Step 5: Get performance weights for reporting
        performance_weights = {vote.model: vote.weight for vote in votes}

        return EnsembleResult(
            final_answer=final_answer,
            votes=votes,
            weighted_consensus=weighted_consensus,
            selected_models=selected_models,
            performance_weights=performance_weights,
            switching_events=switching_events,
        )

    def _select_adaptive_models(
        self,
        available_models: List[str],
        *,
        required_capabilities: List[str],
    ) -> List[str]:
        """Select models adaptively based on performance history and capabilities."""
        # Get performance snapshot
        perf_snapshot = performance_tracker.snapshot()

        # Score each model
        model_scores: List[Tuple[str, float]] = []
        for model in available_models:
            score = 0.0

            # Performance history component
            perf = perf_snapshot.get(model)
            if perf:
                # Combine success rate and quality
                perf_score = (perf.success_rate + perf.avg_quality) / 2.0
                score += perf_score * self.performance_weight_factor
            else:
                # New model: give baseline score
                score += 0.5 * self.performance_weight_factor

            # Capability match component (simplified)
            # In a full implementation, this would check model capabilities
            score += 0.5 * self.quality_weight_factor

            model_scores.append((model, score))

        # Sort by score (descending)
        model_scores.sort(key=lambda x: x[1], reverse=True)

        # Select top models
        num_to_select = min(self.max_models, max(self.min_models, len(available_models)))
        selected = [model for model, _ in model_scores[:num_to_select]]

        return selected

    def _calculate_model_weight(self, model: str) -> float:
        """Calculate voting weight for a model based on performance."""
        perf_snapshot = performance_tracker.snapshot()
        perf = perf_snapshot.get(model)

        if perf is None:
            # New model: default weight
            return 0.5

        # Weight based on success rate and quality
        success_component = perf.success_rate
        quality_component = perf.avg_quality
        history_component = min(1.0, perf.calls / 10.0)  # More calls = more reliable

        weight = (
            success_component * 0.4
            + quality_component * 0.4
            + history_component * 0.2
        )

        # Normalize to 0.0-1.0 range
        return min(1.0, max(0.1, weight))

    async def _assess_response_quality(
        self,
        prompt: str,
        response: str,
        model: str,
    ) -> float:
        """Assess the quality of a response (simplified heuristic)."""
        # Simple heuristics for quality
        length_score = min(1.0, len(response) / 500.0)  # Prefer substantial responses

        # Check for common quality indicators
        quality_indicators = [
            "because",
            "however",
            "therefore",
            "specifically",
            "example",
            "evidence",
        ]
        indicator_count = sum(1 for ind in quality_indicators if ind.lower() in response.lower())
        indicator_score = min(1.0, indicator_count / 3.0)

        # Combined score
        quality = (length_score * 0.5 + indicator_score * 0.5)

        return min(1.0, max(0.0, quality))

    def _weighted_voting(self, votes: List[EnsembleVote]) -> str:
        """Perform weighted voting to determine final answer."""
        if not votes:
            return "No consensus reached."

        # Sort votes by weighted score (weight * quality * confidence)
        scored_votes = [
            (vote, vote.weight * vote.quality_score * vote.confidence)
            for vote in votes
        ]
        scored_votes.sort(key=lambda x: x[1], reverse=True)

        # Use the highest-scoring vote as the base
        best_vote = scored_votes[0][0]

        # If there's strong consensus (multiple high-scoring votes), synthesize
        top_votes = [vote for vote, score in scored_votes if score >= scored_votes[0][1] * 0.8]
        if len(top_votes) > 1:
            # Synthesize from top votes
            synthesized = self._synthesize_votes(top_votes)
            return synthesized

        return best_vote.content

    def _synthesize_votes(self, votes: List[EnsembleVote]) -> str:
        """Synthesize multiple votes into a single answer."""
        if not votes:
            return "No consensus."

        # Simple synthesis: use the highest-weighted vote, but incorporate key points from others
        best_vote = max(votes, key=lambda v: v.weight * v.quality_score)

        # For now, return the best vote's content
        # In a full implementation, this would merge content from multiple votes
        return best_vote.content

    def _calculate_weighted_consensus(self, votes: List[EnsembleVote]) -> float:
        """Calculate weighted consensus score."""
        if not votes:
            return 0.0

        # Calculate weighted average of quality scores
        total_weight = sum(vote.weight for vote in votes)
        if total_weight == 0:
            return 0.0

        weighted_quality = sum(
            vote.weight * vote.quality_score for vote in votes
        ) / total_weight

        # Factor in confidence
        avg_confidence = sum(vote.confidence for vote in votes) / len(votes)

        consensus = (weighted_quality * 0.7 + avg_confidence * 0.3)

        return min(1.0, max(0.0, consensus))

    def _find_backup_model(
        self, selected_models: List[str], failed_model: str
    ) -> Optional[str]:
        """Find a backup model to replace a failed one."""
        perf_snapshot = performance_tracker.snapshot()

        # Find best-performing model not already selected
        available = [
            model
            for model in self.providers.keys()
            if model not in selected_models and model != "stub"
        ]

        if not available:
            return None

        # Score available models
        scores: List[Tuple[str, float]] = []
        for model in available:
            perf = perf_snapshot.get(model)
            if perf:
                score = (perf.success_rate + perf.avg_quality) / 2.0
            else:
                score = 0.5
            scores.append((model, score))

        if not scores:
            return None

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    def _select_provider(self, model: str) -> LLMProvider:
        """Select provider for a model."""
        model_lower = model.lower()
        if model_lower.startswith("gpt") and "openai" in self.providers:
            return self.providers["openai"]
        if model_lower.startswith("claude") and "anthropic" in self.providers:
            return self.providers["anthropic"]
        if model_lower.startswith("grok") and "grok" in self.providers:
            return self.providers["grok"]
        if model_lower.startswith("gemini") and "gemini" in self.providers:
            return self.providers["gemini"]
        if model_lower.startswith("deepseek") and "deepseek" in self.providers:
            return self.providers["deepseek"]
        return self.providers.get("stub", self.providers.get(list(self.providers.keys())[0]))

