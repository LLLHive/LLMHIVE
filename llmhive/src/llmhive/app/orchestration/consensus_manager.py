"""Deep Consensus (DeepConf) Ensemble Framework for LLMHive.

This module implements a comprehensive consensus-building system where multiple
models' answers are combined into a unified response through:

1. Parallel model execution
2. Response comparison and similarity analysis
3. Voting for factual claims
4. Merging for open-ended text
5. Moderated debate for conflict resolution
6. Confidence-weighted final consensus

The ConsensusManager orchestrates the entire process and produces a single
high-quality answer that represents the collective intelligence of multiple models.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class ConsensusStrategy(str, Enum):
    """Strategy for building consensus."""
    VOTING = "voting"           # Majority voting for factual claims
    WEIGHTED_MERGE = "weighted_merge"  # Weighted merging based on confidence
    SYNTHESIZE = "synthesize"   # Synthesize new answer from all responses
    DEBATE = "debate"           # Multi-round debate for conflicts
    BEST_OF = "best_of"         # Select the best single answer


class ResponseType(str, Enum):
    """Type of response content."""
    FACTUAL = "factual"         # Fact-based answer (use voting)
    ANALYTICAL = "analytical"   # Analysis/reasoning (use synthesis)
    CREATIVE = "creative"       # Creative content (use best-of)
    MIXED = "mixed"             # Mixed content (use weighted merge)


class ConflictSeverity(str, Enum):
    """Severity of conflict between responses."""
    NONE = "none"
    MINOR = "minor"      # Different wording, same meaning
    MODERATE = "moderate"  # Some disagreement on details
    MAJOR = "major"      # Fundamental disagreement


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class ModelResponse:
    """Response from a single model."""
    model: str
    content: str
    tokens: int = 0
    latency_ms: float = 0.0
    raw_confidence: float = 0.5  # Model's self-reported confidence
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FactualClaim:
    """A single factual claim extracted from a response."""
    claim: str
    source_model: str
    confidence: float = 0.5
    supporting_models: List[str] = field(default_factory=list)
    contradicting_models: List[str] = field(default_factory=list)
    verified: bool = False


@dataclass(slots=True)
class VotingResult:
    """Result of voting on factual claims."""
    claims: List[FactualClaim]
    consensus_claims: List[str]  # Claims with majority support
    disputed_claims: List[str]   # Claims with disagreement
    voting_confidence: float


@dataclass(slots=True)
class DebateRound:
    """A single round of moderated debate."""
    round_number: int
    topic: str  # What's being debated
    positions: Dict[str, str]  # model -> position
    evaluations: Dict[str, float]  # model -> score
    winner: Optional[str] = None
    resolution: Optional[str] = None


@dataclass(slots=True)
class ConsensusScore:
    """Detailed consensus scoring."""
    overall_score: float  # 0-1
    agreement_rate: float  # Percentage of claims agreed upon
    confidence_weighted_score: float
    quality_score: float
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ConsensusResult:
    """Final result of the consensus building process."""
    final_answer: str
    strategy_used: ConsensusStrategy
    responses: List[ModelResponse]
    participating_models: List[str]
    consensus_score: ConsensusScore
    voting_result: Optional[VotingResult] = None
    debate_rounds: List[DebateRound] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    model_contributions: Dict[str, float] = field(default_factory=dict)
    key_agreements: List[str] = field(default_factory=list)
    key_disagreements: List[str] = field(default_factory=list)
    synthesis_notes: List[str] = field(default_factory=list)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary for UI display."""
        return {
            "final_answer": self.final_answer[:500] + "..." if len(self.final_answer) > 500 else self.final_answer,
            "strategy": self.strategy_used.value,
            "models_used": self.participating_models,
            "consensus_score": self.consensus_score.overall_score,
            "agreement_rate": self.consensus_score.agreement_rate,
            "debate_rounds": len(self.debate_rounds),
            "key_agreements": self.key_agreements[:3],
            "key_disagreements": self.key_disagreements[:3],
        }


# ==============================================================================
# Consensus Manager
# ==============================================================================

class ConsensusManager:
    """Manages the Deep Consensus Framework process.
    
    Orchestrates multiple models to produce a single consensus answer through:
    1. Parallel model execution
    2. Response comparison and conflict detection
    3. Strategy selection (voting, merging, debate)
    4. Confidence-weighted aggregation
    5. Final synthesis
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        performance_tracker: Optional[Any] = None,
        max_debate_rounds: int = 3,
        consensus_threshold: float = 0.75,
        conflict_threshold: float = 0.3,
        min_models_for_voting: int = 3,
    ) -> None:
        """
        Initialize the consensus manager.
        
        Args:
            providers: Dict of LLM providers by name
            performance_tracker: Optional performance tracker for confidence scoring
            max_debate_rounds: Maximum rounds of debate for conflicts
            consensus_threshold: Threshold to consider consensus reached
            conflict_threshold: Similarity below this triggers debate
            min_models_for_voting: Minimum models for voting strategy
        """
        self.providers = providers
        self.performance_tracker = performance_tracker
        self.max_debate_rounds = max_debate_rounds
        self.consensus_threshold = consensus_threshold
        self.conflict_threshold = conflict_threshold
        self.min_models_for_voting = min_models_for_voting
    
    async def build_consensus(
        self,
        prompt: str,
        models: List[str],
        *,
        context: Optional[str] = None,
        existing_responses: Optional[List[Any]] = None,
        force_strategy: Optional[ConsensusStrategy] = None,
        accuracy_level: int = 3,
    ) -> ConsensusResult:
        """
        Build consensus from multiple models.
        
        Args:
            prompt: The query/prompt to answer
            models: List of model names to use
            context: Optional additional context
            existing_responses: Pre-existing responses to include
            force_strategy: Force a specific consensus strategy
            accuracy_level: 1-5 accuracy level (higher = more thorough)
            
        Returns:
            ConsensusResult with final consensus answer
        """
        if not models and not existing_responses:
            raise ValueError("At least one model or existing response required")
        
        logger.info("Building consensus with %d models", len(models))
        
        # Step 1: Collect responses (parallel execution)
        responses = await self._collect_responses(
            prompt, models, context, existing_responses
        )
        
        if not responses:
            raise RuntimeError("No valid responses collected")
        
        # Step 2: Calculate initial confidence scores
        confidence_scores = self._calculate_confidence_scores(responses)
        
        # Step 3: Analyze responses for conflicts
        response_type = self._classify_response_type(prompt, responses)
        conflict_severity = self._detect_conflicts(responses)
        
        logger.info(
            "Response type: %s, Conflict severity: %s",
            response_type.value, conflict_severity.value
        )
        
        # Step 4: Select consensus strategy
        strategy = force_strategy or self._select_strategy(
            response_type, conflict_severity, len(responses), accuracy_level
        )
        
        logger.info("Selected consensus strategy: %s", strategy.value)
        
        # Step 5: Build consensus based on strategy
        if strategy == ConsensusStrategy.VOTING:
            result = await self._build_voting_consensus(
                prompt, responses, confidence_scores, context
            )
        elif strategy == ConsensusStrategy.WEIGHTED_MERGE:
            result = await self._build_weighted_consensus(
                prompt, responses, confidence_scores, context
            )
        elif strategy == ConsensusStrategy.SYNTHESIZE:
            result = await self._build_synthesized_consensus(
                prompt, responses, confidence_scores, context
            )
        elif strategy == ConsensusStrategy.DEBATE:
            result = await self._build_debate_consensus(
                prompt, responses, confidence_scores, context
            )
        else:  # BEST_OF
            result = await self._build_best_of_consensus(
                prompt, responses, confidence_scores
            )
        
        # Step 6: Calculate model contributions
        result.model_contributions = self._calculate_contributions(
            result.final_answer, responses, confidence_scores
        )
        
        logger.info(
            "Consensus built: strategy=%s, score=%.2f, models=%d",
            result.strategy_used.value,
            result.consensus_score.overall_score,
            len(result.participating_models),
        )
        
        return result
    
    # ==========================================================================
    # Response Collection
    # ==========================================================================
    
    async def _collect_responses(
        self,
        prompt: str,
        models: List[str],
        context: Optional[str],
        existing_responses: Optional[List[Any]],
    ) -> List[ModelResponse]:
        """Collect responses from all models in parallel."""
        import time
        
        responses: List[ModelResponse] = []
        
        # Add existing responses
        if existing_responses:
            for resp in existing_responses:
                model = getattr(resp, 'model', 'unknown')
                content = getattr(resp, 'content', str(resp))
                tokens = getattr(resp, 'tokens', 0)
                
                responses.append(ModelResponse(
                    model=model,
                    content=content,
                    tokens=tokens,
                ))
        
        # Collect new responses in parallel
        async def get_response(model: str) -> Optional[ModelResponse]:
            start = time.time()
            try:
                provider = self._select_provider(model)
                
                # Add context to prompt if available
                full_prompt = prompt
                if context:
                    full_prompt = f"Context: {context}\n\nQuestion: {prompt}"
                
                result = await provider.complete(full_prompt, model=model)
                latency = (time.time() - start) * 1000
                
                return ModelResponse(
                    model=model,
                    content=result.content,
                    tokens=getattr(result, 'tokens', 0),
                    latency_ms=latency,
                )
            except Exception as e:
                logger.warning("Failed to get response from %s: %s", model, e)
                return None
        
        # Run all models in parallel
        tasks = [get_response(model) for model in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, ModelResponse):
                responses.append(result)
            elif isinstance(result, Exception):
                logger.warning("Model error: %s", result)
        
        return responses
    
    # ==========================================================================
    # Confidence Scoring
    # ==========================================================================
    
    def _calculate_confidence_scores(
        self,
        responses: List[ModelResponse],
    ) -> Dict[str, float]:
        """Calculate confidence scores for each model."""
        scores: Dict[str, float] = {}
        
        for resp in responses:
            base_score = 0.5
            
            # Performance history component
            if self.performance_tracker:
                try:
                    perf = self.performance_tracker.get_model_performance(resp.model)
                    if perf:
                        base_score = (perf.success_rate + perf.avg_quality) / 2
                except Exception:
                    pass
            
            # Response quality heuristics
            quality_score = self._assess_response_quality(resp.content)
            
            # Combine scores
            confidence = base_score * 0.4 + quality_score * 0.6
            scores[resp.model] = min(1.0, max(0.0, confidence))
        
        return scores
    
    def _assess_response_quality(self, content: str) -> float:
        """Assess response quality using heuristics."""
        if not content:
            return 0.0
        
        score = 0.5
        
        # Length score (prefer substantial but not excessive)
        length = len(content)
        if 100 < length < 2000:
            score += 0.2
        elif 50 < length < 3000:
            score += 0.1
        
        # Quality indicators
        quality_markers = [
            'because', 'therefore', 'however', 'specifically',
            'for example', 'in conclusion', 'according to',
        ]
        marker_count = sum(1 for m in quality_markers if m in content.lower())
        score += min(0.2, marker_count * 0.05)
        
        # Structure (paragraphs, bullet points)
        if '\n' in content:
            score += 0.1
        if any(c in content for c in ['•', '-', '1.', '2.']):
            score += 0.05
        
        return min(1.0, score)
    
    # ==========================================================================
    # Response Analysis
    # ==========================================================================
    
    def _classify_response_type(
        self,
        prompt: str,
        responses: List[ModelResponse],
    ) -> ResponseType:
        """Classify the type of response expected."""
        prompt_lower = prompt.lower()
        
        # Factual indicators
        factual_patterns = [
            r'\bwhat is\b', r'\bwho is\b', r'\bwhen\b', r'\bwhere\b',
            r'\bhow many\b', r'\bdefine\b', r'\bcapital of\b',
        ]
        
        # Analytical indicators
        analytical_patterns = [
            r'\bwhy\b', r'\bhow\b', r'\bexplain\b', r'\banalyze\b',
            r'\bcompare\b', r'\bcontrast\b', r'\bevaluate\b',
        ]
        
        # Creative indicators
        creative_patterns = [
            r'\bwrite\b', r'\bcreate\b', r'\bimagine\b', r'\bstory\b',
            r'\bpoem\b', r'\bdesign\b',
        ]
        
        factual_score = sum(1 for p in factual_patterns if re.search(p, prompt_lower))
        analytical_score = sum(1 for p in analytical_patterns if re.search(p, prompt_lower))
        creative_score = sum(1 for p in creative_patterns if re.search(p, prompt_lower))
        
        if creative_score > factual_score and creative_score > analytical_score:
            return ResponseType.CREATIVE
        elif factual_score > analytical_score:
            return ResponseType.FACTUAL
        elif analytical_score > 0:
            return ResponseType.ANALYTICAL
        
        return ResponseType.MIXED
    
    def _detect_conflicts(
        self,
        responses: List[ModelResponse],
    ) -> ConflictSeverity:
        """Detect conflicts between responses."""
        if len(responses) < 2:
            return ConflictSeverity.NONE
        
        # Calculate pairwise similarities
        similarities = []
        for i, resp1 in enumerate(responses):
            for resp2 in responses[i+1:]:
                sim = self._calculate_similarity(resp1.content, resp2.content)
                similarities.append(sim)
        
        if not similarities:
            return ConflictSeverity.NONE
        
        avg_similarity = sum(similarities) / len(similarities)
        min_similarity = min(similarities)
        
        if avg_similarity >= 0.8:
            return ConflictSeverity.NONE
        elif avg_similarity >= 0.6:
            return ConflictSeverity.MINOR
        elif avg_similarity >= 0.3 or min_similarity >= 0.2:
            return ConflictSeverity.MODERATE
        else:
            return ConflictSeverity.MAJOR
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _select_strategy(
        self,
        response_type: ResponseType,
        conflict_severity: ConflictSeverity,
        num_responses: int,
        accuracy_level: int,
    ) -> ConsensusStrategy:
        """Select the best consensus strategy."""
        # Major conflicts require debate
        if conflict_severity == ConflictSeverity.MAJOR:
            return ConsensusStrategy.DEBATE
        
        # Factual questions with enough responses use voting
        if response_type == ResponseType.FACTUAL and num_responses >= self.min_models_for_voting:
            return ConsensusStrategy.VOTING
        
        # Creative content uses best-of
        if response_type == ResponseType.CREATIVE:
            return ConsensusStrategy.BEST_OF
        
        # High accuracy with moderate conflict uses debate
        if accuracy_level >= 4 and conflict_severity == ConflictSeverity.MODERATE:
            return ConsensusStrategy.DEBATE
        
        # Analytical or mixed with minor/no conflict uses synthesis
        if response_type in (ResponseType.ANALYTICAL, ResponseType.MIXED):
            return ConsensusStrategy.SYNTHESIZE
        
        # Default to weighted merge
        return ConsensusStrategy.WEIGHTED_MERGE
    
    # ==========================================================================
    # Consensus Building Strategies
    # ==========================================================================
    
    async def _build_voting_consensus(
        self,
        prompt: str,
        responses: List[ModelResponse],
        confidence_scores: Dict[str, float],
        context: Optional[str],
    ) -> ConsensusResult:
        """Build consensus through voting on factual claims."""
        # Extract claims from each response
        all_claims: List[FactualClaim] = []
        
        for resp in responses:
            claims = self._extract_claims(resp.content, resp.model)
            all_claims.extend(claims)
        
        # Group similar claims
        claim_groups = self._group_similar_claims(all_claims)
        
        # Vote on each claim group
        consensus_claims = []
        disputed_claims = []
        
        for group in claim_groups:
            supporting = len(group)
            total = len(responses)
            agreement_rate = supporting / total
            
            representative_claim = group[0].claim
            
            if agreement_rate >= 0.5:
                consensus_claims.append(representative_claim)
            else:
                disputed_claims.append(representative_claim)
        
        # Build voting result
        voting_result = VotingResult(
            claims=all_claims,
            consensus_claims=consensus_claims,
            disputed_claims=disputed_claims,
            voting_confidence=len(consensus_claims) / max(len(claim_groups), 1),
        )
        
        # Synthesize final answer from consensus claims
        final_answer = await self._synthesize_from_claims(
            prompt, consensus_claims, responses[0].model if responses else None, context
        )
        
        # Calculate consensus score
        consensus_score = ConsensusScore(
            overall_score=voting_result.voting_confidence,
            agreement_rate=len(consensus_claims) / max(len(claim_groups), 1),
            confidence_weighted_score=sum(confidence_scores.values()) / len(confidence_scores),
            quality_score=0.8,  # Voting typically produces good quality
            breakdown={"voting_confidence": voting_result.voting_confidence},
        )
        
        return ConsensusResult(
            final_answer=final_answer,
            strategy_used=ConsensusStrategy.VOTING,
            responses=responses,
            participating_models=[r.model for r in responses],
            consensus_score=consensus_score,
            voting_result=voting_result,
            confidence_scores=confidence_scores,
            key_agreements=consensus_claims[:5],
            key_disagreements=disputed_claims[:3],
        )
    
    async def _build_weighted_consensus(
        self,
        prompt: str,
        responses: List[ModelResponse],
        confidence_scores: Dict[str, float],
        context: Optional[str],
    ) -> ConsensusResult:
        """Build consensus through weighted merging."""
        if not responses:
            raise ValueError("No responses for weighted consensus")
        
        # Sort by confidence
        sorted_responses = sorted(
            responses,
            key=lambda r: confidence_scores.get(r.model, 0.5),
            reverse=True,
        )
        
        # Use highest confidence response as base
        base_response = sorted_responses[0]
        
        # Extract key points from other responses
        additional_points = []
        for resp in sorted_responses[1:]:
            weight = confidence_scores.get(resp.model, 0.5)
            if weight >= 0.4:  # Only include reasonably confident responses
                points = self._extract_key_points(resp.content)
                for point in points:
                    additional_points.append((point, weight))
        
        # Merge additional points into base
        final_answer = base_response.content
        if additional_points:
            # Add high-weight points not already in base
            for point, weight in sorted(additional_points, key=lambda x: x[1], reverse=True)[:3]:
                if point.lower() not in final_answer.lower():
                    final_answer += f"\n\nAdditionally: {point}"
        
        # Calculate consensus score
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        consensus_score = ConsensusScore(
            overall_score=avg_confidence * 0.8 + 0.2,
            agreement_rate=self._calculate_agreement_rate(responses),
            confidence_weighted_score=avg_confidence,
            quality_score=confidence_scores.get(base_response.model, 0.5),
            breakdown={"base_model": base_response.model},
        )
        
        return ConsensusResult(
            final_answer=final_answer,
            strategy_used=ConsensusStrategy.WEIGHTED_MERGE,
            responses=responses,
            participating_models=[r.model for r in responses],
            consensus_score=consensus_score,
            confidence_scores=confidence_scores,
            synthesis_notes=[f"Base response from {base_response.model}"],
        )
    
    async def _build_synthesized_consensus(
        self,
        prompt: str,
        responses: List[ModelResponse],
        confidence_scores: Dict[str, float],
        context: Optional[str],
    ) -> ConsensusResult:
        """Build consensus by synthesizing all responses."""
        if not responses:
            raise ValueError("No responses for synthesis")
        
        # Select synthesizer model (highest confidence)
        synthesizer_model = max(
            confidence_scores.keys(),
            key=lambda m: confidence_scores.get(m, 0.5),
        )
        
        provider = self._select_provider(synthesizer_model)
        
        # Build synthesis prompt
        synthesis_prompt = self._build_synthesis_prompt(prompt, responses, context)
        
        try:
            result = await provider.complete(synthesis_prompt, model=synthesizer_model)
            final_answer = result.content.strip()
        except Exception as e:
            logger.warning("Synthesis failed: %s", e)
            # Fallback to best response
            best_model = max(responses, key=lambda r: confidence_scores.get(r.model, 0.5))
            final_answer = best_model.content
        
        # Calculate consensus score
        agreement_rate = self._calculate_agreement_rate(responses)
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        
        consensus_score = ConsensusScore(
            overall_score=(agreement_rate + avg_confidence) / 2,
            agreement_rate=agreement_rate,
            confidence_weighted_score=avg_confidence,
            quality_score=0.85,
            breakdown={"synthesizer": synthesizer_model},
        )
        
        return ConsensusResult(
            final_answer=final_answer,
            strategy_used=ConsensusStrategy.SYNTHESIZE,
            responses=responses,
            participating_models=[r.model for r in responses],
            consensus_score=consensus_score,
            confidence_scores=confidence_scores,
            synthesis_notes=[f"Synthesized by {synthesizer_model}"],
        )
    
    async def _build_debate_consensus(
        self,
        prompt: str,
        responses: List[ModelResponse],
        confidence_scores: Dict[str, float],
        context: Optional[str],
    ) -> ConsensusResult:
        """Build consensus through moderated debate."""
        if len(responses) < 2:
            return await self._build_best_of_consensus(prompt, responses, confidence_scores)
        
        debate_rounds: List[DebateRound] = []
        current_positions = {r.model: r.content for r in responses}
        
        # Identify main point of contention
        disagreement_topic = await self._identify_disagreement(
            prompt, responses, context
        )
        
        for round_num in range(1, self.max_debate_rounds + 1):
            logger.info("Debate round %d/%d", round_num, self.max_debate_rounds)
            
            # Each model argues their position
            new_positions: Dict[str, str] = {}
            evaluations: Dict[str, float] = {}
            
            for model, position in current_positions.items():
                try:
                    # Get model to defend/refine their position
                    refined_position = await self._refine_debate_position(
                        prompt, model, position, current_positions, round_num, context
                    )
                    new_positions[model] = refined_position
                    
                    # Evaluate position quality
                    eval_score = await self._evaluate_debate_position(
                        prompt, refined_position, model, context
                    )
                    evaluations[model] = eval_score
                    
                except Exception as e:
                    logger.warning("Debate failed for %s: %s", model, e)
                    new_positions[model] = position
                    evaluations[model] = 0.5
            
            # Determine round winner
            winner = max(evaluations.keys(), key=lambda m: evaluations[m])
            
            debate_round = DebateRound(
                round_number=round_num,
                topic=disagreement_topic,
                positions=new_positions,
                evaluations=evaluations,
                winner=winner,
            )
            debate_rounds.append(debate_round)
            
            # Check for convergence
            if self._check_debate_convergence(new_positions):
                logger.info("Debate converged at round %d", round_num)
                break
            
            current_positions = new_positions
        
        # Final synthesis from debate
        final_answer = await self._synthesize_debate_conclusion(
            prompt, debate_rounds, context
        )
        
        # Calculate consensus score
        final_evaluations = debate_rounds[-1].evaluations if debate_rounds else {}
        avg_eval = sum(final_evaluations.values()) / len(final_evaluations) if final_evaluations else 0.5
        
        consensus_score = ConsensusScore(
            overall_score=avg_eval,
            agreement_rate=self._calculate_agreement_rate(responses),
            confidence_weighted_score=sum(confidence_scores.values()) / len(confidence_scores),
            quality_score=avg_eval,
            breakdown={"debate_rounds": len(debate_rounds)},
        )
        
        return ConsensusResult(
            final_answer=final_answer,
            strategy_used=ConsensusStrategy.DEBATE,
            responses=responses,
            participating_models=[r.model for r in responses],
            consensus_score=consensus_score,
            debate_rounds=debate_rounds,
            confidence_scores=confidence_scores,
            key_disagreements=[disagreement_topic] if disagreement_topic else [],
        )
    
    async def _build_best_of_consensus(
        self,
        prompt: str,
        responses: List[ModelResponse],
        confidence_scores: Dict[str, float],
    ) -> ConsensusResult:
        """Build consensus by selecting the best single response."""
        if not responses:
            raise ValueError("No responses for best-of")
        
        # Score each response
        scored = []
        for resp in responses:
            confidence = confidence_scores.get(resp.model, 0.5)
            quality = self._assess_response_quality(resp.content)
            score = confidence * 0.4 + quality * 0.6
            scored.append((resp, score))
        
        # Select best
        best_response, best_score = max(scored, key=lambda x: x[1])
        
        consensus_score = ConsensusScore(
            overall_score=best_score,
            agreement_rate=1.0,  # Single response = perfect agreement
            confidence_weighted_score=confidence_scores.get(best_response.model, 0.5),
            quality_score=self._assess_response_quality(best_response.content),
            breakdown={"selected_model": best_response.model},
        )
        
        return ConsensusResult(
            final_answer=best_response.content,
            strategy_used=ConsensusStrategy.BEST_OF,
            responses=responses,
            participating_models=[r.model for r in responses],
            consensus_score=consensus_score,
            confidence_scores=confidence_scores,
            synthesis_notes=[f"Selected response from {best_response.model}"],
        )
    
    # ==========================================================================
    # Helper Methods
    # ==========================================================================
    
    def _extract_claims(self, content: str, source_model: str) -> List[FactualClaim]:
        """Extract factual claims from content."""
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Look for factual patterns
            factual_patterns = [
                r'\bis\b', r'\bwas\b', r'\bare\b', r'\bwere\b',
                r'\bhas\b', r'\bhave\b', r'\bcan\b', r'\bwill\b',
            ]
            
            if any(re.search(p, sentence.lower()) for p in factual_patterns):
                claims.append(FactualClaim(
                    claim=sentence,
                    source_model=source_model,
                    confidence=0.7,
                ))
        
        return claims
    
    def _group_similar_claims(self, claims: List[FactualClaim]) -> List[List[FactualClaim]]:
        """Group similar claims together."""
        groups: List[List[FactualClaim]] = []
        used = set()
        
        for i, claim in enumerate(claims):
            if i in used:
                continue
            
            group = [claim]
            used.add(i)
            
            for j, other in enumerate(claims[i+1:], i+1):
                if j in used:
                    continue
                
                sim = self._calculate_similarity(claim.claim, other.claim)
                if sim >= 0.5:
                    group.append(other)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    async def _synthesize_from_claims(
        self,
        prompt: str,
        claims: List[str],
        model: Optional[str],
        context: Optional[str],
    ) -> str:
        """Synthesize answer from consensus claims."""
        if not claims:
            return "No consensus claims found."
        
        if not model:
            return " ".join(claims)
        
        provider = self._select_provider(model)
        
        synthesis_prompt = f"""Based on these verified claims, provide a clear answer:

Question: {prompt}

Verified Claims:
{chr(10).join(f'- {c}' for c in claims)}

Provide a clear, comprehensive answer incorporating these claims."""
        
        try:
            result = await provider.complete(synthesis_prompt, model=model)
            return result.content.strip()
        except Exception:
            return " ".join(claims)
    
    def _build_synthesis_prompt(
        self,
        prompt: str,
        responses: List[ModelResponse],
        context: Optional[str],
    ) -> str:
        """Build prompt for synthesizing multiple responses."""
        lines = [
            "Synthesize a single, comprehensive answer from these multiple AI responses:",
            "",
            f"Original Question: {prompt}",
            "",
        ]
        
        if context:
            lines.append(f"Context: {context}")
            lines.append("")
        
        for i, resp in enumerate(responses, 1):
            lines.append(f"Response {i} ({resp.model}):")
            lines.append(f"{resp.content[:500]}...")
            lines.append("")
        
        lines.extend([
            "Create a unified answer that:",
            "- Incorporates the best points from all responses",
            "- Resolves any contradictions",
            "- Is clear and comprehensive",
            "",
            "Output ONLY the synthesized answer.",
        ])
        
        return "\n".join(lines)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content."""
        points = []
        
        # Look for bullet points or numbered items
        bullet_pattern = r'[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)'
        numbered_pattern = r'\d+[.)]\s*(.+?)(?=\n\d+[.)]|\n\n|$)'
        
        for pattern in [bullet_pattern, numbered_pattern]:
            matches = re.findall(pattern, content, re.DOTALL)
            points.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        # If no structured points, use first sentences
        if not points:
            sentences = content.split('.')[:3]
            points = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        return points[:5]
    
    def _calculate_agreement_rate(self, responses: List[ModelResponse]) -> float:
        """Calculate agreement rate between responses."""
        if len(responses) < 2:
            return 1.0
        
        similarities = []
        for i, resp1 in enumerate(responses):
            for resp2 in responses[i+1:]:
                sim = self._calculate_similarity(resp1.content, resp2.content)
                similarities.append(sim)
        
        return sum(similarities) / len(similarities) if similarities else 1.0
    
    def _calculate_contributions(
        self,
        final_answer: str,
        responses: List[ModelResponse],
        confidence_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """Calculate each model's contribution to the final answer."""
        contributions = {}
        
        for resp in responses:
            # Calculate overlap with final answer
            overlap = self._calculate_similarity(resp.content, final_answer)
            confidence = confidence_scores.get(resp.model, 0.5)
            
            contributions[resp.model] = overlap * 0.6 + confidence * 0.4
        
        # Normalize
        total = sum(contributions.values())
        if total > 0:
            contributions = {k: v/total for k, v in contributions.items()}
        
        return contributions
    
    async def _identify_disagreement(
        self,
        prompt: str,
        responses: List[ModelResponse],
        context: Optional[str],
    ) -> str:
        """Identify the main point of disagreement."""
        if len(responses) < 2:
            return ""
        
        # Simple heuristic: find most different claims
        resp1, resp2 = responses[:2]
        
        words1 = set(resp1.content.lower().split())
        words2 = set(resp2.content.lower().split())
        
        unique1 = words1 - words2
        unique2 = words2 - words1
        
        if unique1 or unique2:
            return f"Different perspectives on: {prompt}"
        
        return ""
    
    async def _refine_debate_position(
        self,
        prompt: str,
        model: str,
        current_position: str,
        all_positions: Dict[str, str],
        round_num: int,
        context: Optional[str],
    ) -> str:
        """Refine a model's position in debate."""
        provider = self._select_provider(model)
        
        other_positions = [
            f"{m}: {p[:200]}..."
            for m, p in all_positions.items()
            if m != model
        ]
        
        debate_prompt = f"""You are in a structured debate (Round {round_num}).

Question: {prompt}

Your current position:
{current_position[:500]}

Other positions:
{chr(10).join(other_positions)}

Defend or refine your position. Address points raised by others.
If you're wrong, acknowledge it. If you're right, explain why.

Output your refined position."""
        
        try:
            result = await provider.complete(debate_prompt, model=model)
            return result.content.strip()
        except Exception:
            return current_position
    
    async def _evaluate_debate_position(
        self,
        prompt: str,
        position: str,
        model: str,
        context: Optional[str],
    ) -> float:
        """Evaluate a debate position."""
        # Simple heuristic evaluation
        quality = self._assess_response_quality(position)
        
        # Check for key quality markers
        markers = ['because', 'evidence', 'however', 'specifically', 'therefore']
        marker_score = sum(1 for m in markers if m in position.lower()) / len(markers)
        
        return quality * 0.7 + marker_score * 0.3
    
    def _check_debate_convergence(self, positions: Dict[str, str]) -> bool:
        """Check if debate positions have converged."""
        if len(positions) < 2:
            return True
        
        position_list = list(positions.values())
        for i, pos1 in enumerate(position_list):
            for pos2 in position_list[i+1:]:
                sim = self._calculate_similarity(pos1, pos2)
                if sim < 0.7:
                    return False
        
        return True
    
    async def _synthesize_debate_conclusion(
        self,
        prompt: str,
        debate_rounds: List[DebateRound],
        context: Optional[str],
    ) -> str:
        """Synthesize final answer from debate."""
        if not debate_rounds:
            return "No conclusion reached."
        
        final_round = debate_rounds[-1]
        
        # Use winning model's position as base
        if final_round.winner and final_round.winner in final_round.positions:
            return final_round.positions[final_round.winner]
        
        # Fallback to highest scored position
        best_model = max(
            final_round.evaluations.keys(),
            key=lambda m: final_round.evaluations.get(m, 0),
        )
        return final_round.positions.get(best_model, "No conclusion reached.")
    
    def _select_provider(self, model: str) -> Any:
        """Select provider for a model."""
        model_lower = model.lower()
        
        provider_map = {
            "gpt": "openai",
            "claude": "anthropic",
            "grok": "grok",
            "gemini": "gemini",
            "deepseek": "deepseek",
        }
        
        for prefix, provider_name in provider_map.items():
            if model_lower.startswith(prefix) and provider_name in self.providers:
                return self.providers[provider_name]
        
        if "stub" in self.providers:
            return self.providers["stub"]
        
        return next(iter(self.providers.values()))


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def build_consensus(
    prompt: str,
    models: List[str],
    providers: Dict[str, Any],
    **kwargs,
) -> ConsensusResult:
    """Convenience function to build consensus."""
    manager = ConsensusManager(providers=providers)
    return await manager.build_consensus(prompt, models, **kwargs)

