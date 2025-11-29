"""DeepConf (Deep Consensus Framework) for LLMHive orchestrator.

DeepConf implements a multi-round debate and consensus building system where
models engage in structured debate, evaluate each other's arguments, and
gradually converge toward consensus through iterative refinement.

Deep Consensus multi-round ensemble logic:
1. Analyze initial responses for consensus vs conflict
2. Challenge Loop: For conflicting answers, models critique each other
3. Collect critiques and integrate them
4. Consensus Scoring: Assign confidence scores using performance metrics
5. Finalize consensus: Produce preliminary consensus answer
6. Proceed to verification stage
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from ..services.base import LLMProvider, LLMResult

if TYPE_CHECKING:
    from ..performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DebateRound:
    """Represents a single round of debate."""

    round_number: int
    arguments: Dict[str, str]  # model -> argument
    evaluations: Dict[str, Dict[str, float]]  # evaluator -> {target: score}
    consensus_score: float  # Overall consensus for this round
    key_points: List[str]  # Key points that emerged


@dataclass(slots=True)
class Critique:
    """DeepConf: Represents a critique from one model of another's answer."""

    critic_model: str
    target_model: str
    critique_text: str
    confidence: float  # Critic's confidence in their critique (0.0-1.0)
    identified_errors: List[str] = field(default_factory=list)
    identified_gaps: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ConsensusResult:
    """Result of the DeepConf consensus process."""

    final_consensus: str
    debate_rounds: List[DebateRound]
    consensus_score: float  # Final consensus score (0.0-1.0)
    rounds_completed: int
    convergence_achieved: bool
    key_agreements: List[str]
    key_disagreements: List[str]
    participant_scores: Dict[str, float]  # Model -> contribution score
    critiques: List[Critique] = field(default_factory=list)  # DeepConf: All critiques collected
    confidence_scores: Dict[str, float] = field(default_factory=dict)  # DeepConf: Model -> confidence score


class DeepConf:
    """Manages the Deep Consensus Framework process."""

    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        max_rounds: int = 4,
        consensus_threshold: float = 0.80,
        min_consensus_improvement: float = 0.05,
        conflict_threshold: float = 0.3,  # DeepConf: Similarity threshold below which answers conflict
        performance_tracker: Optional["PerformanceTracker"] = None,  # DeepConf: For confidence scoring
    ) -> None:
        self.providers = providers
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self.min_consensus_improvement = min_consensus_improvement
        self.conflict_threshold = conflict_threshold  # DeepConf: Answers with similarity < this are considered conflicting
        self.performance_tracker = performance_tracker  # DeepConf: For confidence scoring

    async def build_consensus(
        self,
        prompt: str,
        initial_responses: List[LLMResult],
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
    ) -> ConsensusResult:
        """Build consensus through multi-round debate.

        DeepConf: Implements the deep consensus multi-round ensemble logic:
        1. Analyze initial responses for consensus vs conflict
        2. Challenge Loop: For conflicting answers, models critique each other
        3. Collect critiques and integrate them
        4. Consensus Scoring: Assign confidence scores using performance metrics
        5. Finalize consensus: Produce preliminary consensus answer
        6. Proceed to verification stage

        Args:
            prompt: Original user prompt
            initial_responses: Initial responses from models
            context: Optional context
            supporting_notes: Optional supporting information

        Returns:
            ConsensusResult with final consensus and debate history
        """
        if not initial_responses:
            raise ValueError("At least one initial response is required")

        # DeepConf: Step 1 - Analyze initial responses for consensus vs conflict
        logger.info("DeepConf: Analyzing initial responses for consensus vs conflict")
        conflict_pairs = self._detect_conflicts(initial_responses)
        
        # DeepConf: If answers largely agree, skip to simple aggregation
        if not conflict_pairs:
            logger.info("DeepConf: Answers largely agree, using simple aggregation")
            consensus_answer = self._simple_aggregate_answers(initial_responses)
            confidence_scores = self._calculate_confidence_scores(initial_responses)
            
            return ConsensusResult(
                final_consensus=consensus_answer,
                debate_rounds=[],
                consensus_score=1.0,
                rounds_completed=0,
                convergence_achieved=True,
                key_agreements=[],
                key_disagreements=[],
                participant_scores={resp.model: 1.0 for resp in initial_responses},
                critiques=[],
                confidence_scores=confidence_scores,
            )

        logger.info("DeepConf: Found %d conflicting answer pairs, entering challenge loop", len(conflict_pairs))

        # DeepConf: Step 2 - Challenge Loop: For each conflicting pair, have models critique each other
        critiques: List[Critique] = []
        for model_a, model_b in conflict_pairs:
            logger.debug("DeepConf: Challenge loop - %s critiques %s", model_b, model_a)
            critique_ab = await self._generate_critique(
                prompt=prompt,
                critic_model=model_b,
                target_answer=next(r.content for r in initial_responses if r.model == model_a),
                target_model=model_a,
                context=context,
                supporting_notes=supporting_notes,
            )
            if critique_ab:
                critiques.append(critique_ab)
            
            logger.debug("DeepConf: Challenge loop - %s critiques %s", model_a, model_b)
            critique_ba = await self._generate_critique(
                prompt=prompt,
                critic_model=model_a,
                target_answer=next(r.content for r in initial_responses if r.model == model_b),
                target_model=model_b,
                context=context,
                supporting_notes=supporting_notes,
            )
            if critique_ba:
                critiques.append(critique_ba)

        # DeepConf: Step 3 - Collect critiques and integrate them
        logger.info("DeepConf: Integrating %d critiques into answers", len(critiques))
        refined_responses = await self._integrate_critiques(
            prompt=prompt,
            initial_responses=initial_responses,
            critiques=critiques,
            context=context,
            supporting_notes=supporting_notes,
        )

        # DeepConf: Step 4 - Consensus Scoring: Assign confidence scores
        logger.info("DeepConf: Calculating confidence scores for models")
        confidence_scores = self._calculate_confidence_scores(refined_responses)

        # DeepConf: Step 5 - Finalize consensus: Aggregate answers with weights
        logger.info("DeepConf: Finalizing consensus with weighted aggregation")
        consensus_answer = self._aggregate_answers_with_weights(
            answers=refined_responses,
            confidences=confidence_scores,
        )

        # DeepConf: Continue with multi-round debate if needed (existing logic)
        debate_rounds: List[DebateRound] = []
        current_arguments: Dict[str, str] = {
            resp.model: resp.content for resp in refined_responses
        }
        participant_scores: Dict[str, float] = confidence_scores.copy()

        supporting_notes = supporting_notes or []
        previous_consensus = 0.0

        for round_num in range(1, self.max_rounds + 1):
            logger.info("DeepConf debate round %d/%d", round_num, self.max_rounds)

            # Each model evaluates all other models' arguments
            evaluations: Dict[str, Dict[str, float]] = {}
            for evaluator_model in current_arguments.keys():
                eval_scores: Dict[str, float] = {}
                for target_model, argument in current_arguments.items():
                    if evaluator_model == target_model:
                        continue  # Skip self-evaluation
                    score = await self._evaluate_argument(
                        prompt=prompt,
                        argument=argument,
                        evaluator_model=evaluator_model,
                        target_model=target_model,
                        context=context,
                        supporting_notes=supporting_notes,
                        round_num=round_num,
                    )
                    eval_scores[target_model] = score
                evaluations[evaluator_model] = eval_scores

            # Calculate consensus score for this round
            consensus_score = self._calculate_consensus_score(evaluations, current_arguments)

            # Extract key points from arguments
            key_points = self._extract_key_points(list(current_arguments.values()))

            # Create debate round record
            debate_round = DebateRound(
                round_number=round_num,
                arguments=current_arguments.copy(),
                evaluations=evaluations,
                consensus_score=consensus_score,
                key_points=key_points,
            )
            debate_rounds.append(debate_round)

            logger.info(
                "Round %d consensus score: %.2f (improvement: %.2f)",
                round_num,
                consensus_score,
                consensus_score - previous_consensus,
            )

            # Check for convergence
            if consensus_score >= self.consensus_threshold:
                logger.info(
                    "Consensus threshold reached at round %d (score: %.2f)",
                    round_num,
                    consensus_score,
                )
                break

            # Check for stagnation (minimal improvement)
            improvement = consensus_score - previous_consensus
            if improvement < self.min_consensus_improvement and round_num > 1:
                logger.info(
                    "Consensus improvement below threshold (%.2f < %.2f), stopping",
                    improvement,
                    self.min_consensus_improvement,
                )
                break

            # Refine arguments for next round based on evaluations
            if round_num < self.max_rounds:
                refined_arguments = await self._refine_arguments(
                    prompt=prompt,
                    current_arguments=current_arguments,
                    evaluations=evaluations,
                    context=context,
                    supporting_notes=supporting_notes,
                    round_num=round_num,
                )
                current_arguments = refined_arguments

                # Update participant scores based on evaluations
                for model in current_arguments.keys():
                    avg_score = sum(
                        evals.get(model, 0.5)
                        for evals in evaluations.values()
                    ) / max(len(evaluations), 1)
                    participant_scores[model] = (participant_scores.get(model, 1.0) + avg_score) / 2

            previous_consensus = consensus_score

        # DeepConf: Synthesize final consensus (use weighted consensus if no debate rounds)
        if debate_rounds:
            final_consensus = await self._synthesize_consensus(
                prompt=prompt,
                debate_rounds=debate_rounds,
                context=context,
                supporting_notes=supporting_notes,
            )
            final_consensus_score = debate_rounds[-1].consensus_score
        else:
            # Use the consensus answer from weighted aggregation
            final_consensus = consensus_answer
            final_consensus_score = self._calculate_consensus_from_confidence(confidence_scores)

        # Extract agreements and disagreements
        key_agreements, key_disagreements = self._extract_agreements_disagreements(debate_rounds)

        # DeepConf: Return ConsensusResult with critiques and confidence scores
        return ConsensusResult(
            final_consensus=final_consensus,
            debate_rounds=debate_rounds,
            consensus_score=final_consensus_score,
            rounds_completed=len(debate_rounds),
            convergence_achieved=final_consensus_score >= self.consensus_threshold,
            key_agreements=key_agreements,
            key_disagreements=key_disagreements,
            participant_scores=participant_scores,
            critiques=critiques,  # DeepConf: Include critiques
            confidence_scores=confidence_scores,  # DeepConf: Include confidence scores
        )

    async def _evaluate_argument(
        self,
        prompt: str,
        argument: str,
        evaluator_model: str,
        target_model: str,
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
        round_num: int = 1,
    ) -> float:
        """Evaluate an argument from another model.

        Returns a score between 0.0 and 1.0.
        """
        provider = self._select_provider(evaluator_model)

        evaluation_prompt = self._build_evaluation_prompt(
            prompt=prompt,
            argument=argument,
            target_model=target_model,
            context=context,
            supporting_notes=supporting_notes,
            round_num=round_num,
        )

        try:
            result = await provider.complete(evaluation_prompt, model=evaluator_model)
            score_text = result.content.strip()

            # Extract score from response
            import re
            match = re.search(r"(\d+\.?\d*)", score_text)
            if match:
                score = float(match.group(1))
                # Normalize to 0-1 range
                if score > 1.0:
                    score = score / 100.0  # Assume percentage
                return min(1.0, max(0.0, score))
        except Exception as exc:
            logger.warning("Failed to evaluate argument: %s", exc)

        # Default score based on argument quality heuristics
        length_score = min(1.0, len(argument) / 500.0)  # Prefer substantial arguments
        return 0.5 + (length_score - 0.5) * 0.3

    def _build_evaluation_prompt(
        self,
        prompt: str,
        argument: str,
        target_model: str,
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
        round_num: int = 1,
    ) -> str:
        """Build the prompt for evaluating an argument."""
        lines = [
            "You are evaluating an argument from another AI model in a consensus-building debate.",
            "",
            f"Original question: {prompt}",
            "",
            f"Argument from {target_model} (Round {round_num}):",
            f'"{argument}"',
            "",
        ]

        if context:
            lines.append(f"Context: {context}")
            lines.append("")

        if supporting_notes:
            lines.append("Supporting information:")
            for note in supporting_notes[:3]:
                lines.append(f"- {note[:200]}")
            lines.append("")

        lines.extend(
            [
                "Evaluate this argument on a scale of 0.0 to 1.0 considering:",
                "- Accuracy and factual correctness (0.0-0.3)",
                "- Clarity and coherence (0.0-0.2)",
                "- Relevance to the question (0.0-0.2)",
                "- Completeness and depth (0.0-0.2)",
                "- Logical reasoning (0.0-0.1)",
                "",
                "Respond with ONLY a number between 0.0 and 1.0, nothing else.",
            ]
        )

        return "\n".join(lines)

    def _calculate_consensus_score(
        self,
        evaluations: Dict[str, Dict[str, float]],
        arguments: Dict[str, str],
    ) -> float:
        """Calculate overall consensus score from evaluations.

        Higher scores indicate more agreement.
        """
        if not evaluations:
            return 0.0

        # Calculate average evaluation scores
        all_scores: List[float] = []
        for evaluator_scores in evaluations.values():
            all_scores.extend(evaluator_scores.values())

        if not all_scores:
            return 0.0

        avg_score = sum(all_scores) / len(all_scores)

        # Calculate variance (lower variance = higher consensus)
        variance = sum((s - avg_score) ** 2 for s in all_scores) / len(all_scores)
        variance_normalized = min(1.0, variance / 0.25)  # Normalize variance

        # Consensus is high when average is high and variance is low
        consensus = avg_score * (1.0 - variance_normalized * 0.3)

        return min(1.0, max(0.0, consensus))

    def _extract_key_points(self, arguments: List[str]) -> List[str]:
        """Extract key points that appear across multiple arguments."""
        # Simple heuristic: find common words/phrases
        from collections import Counter
        import re

        words: List[str] = []
        for arg in arguments:
            # Extract significant words (3+ chars, not common stop words)
            arg_words = re.findall(r"\b[a-z]{3,}\b", arg.lower())
            words.extend(arg_words)

        word_counts = Counter(words)
        # Get words that appear in at least 2 arguments
        common_words = [word for word, count in word_counts.items() if count >= 2]

        # Return top 5 most common
        return common_words[:5]

    async def _refine_arguments(
        self,
        prompt: str,
        current_arguments: Dict[str, str],
        evaluations: Dict[str, Dict[str, float]],
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
        round_num: int = 1,
    ) -> Dict[str, str]:
        """Refine arguments based on evaluations from other models."""
        refined: Dict[str, str] = {}

        for model, argument in current_arguments.items():
            # Get feedback for this model
            feedback_scores = [
                evals.get(model, 0.5)
                for evals in evaluations.values()
            ]
            avg_feedback = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0.5

            # Only refine if feedback is below threshold
            if avg_feedback < 0.7:
                provider = self._select_provider(model)
                refinement_prompt = self._build_refinement_prompt(
                    prompt=prompt,
                    current_argument=argument,
                    feedback_scores=feedback_scores,
                    context=context,
                    supporting_notes=supporting_notes,
                    round_num=round_num,
                )

                try:
                    result = await provider.complete(refinement_prompt, model=model)
                    refined[model] = result.content.strip()
                except Exception as exc:
                    logger.warning("Failed to refine argument for %s: %s", model, exc)
                    refined[model] = argument  # Keep original
            else:
                refined[model] = argument  # Keep original if feedback is good

        return refined

    def _build_refinement_prompt(
        self,
        prompt: str,
        current_argument: str,
        feedback_scores: List[float],
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
        round_num: int = 1,
    ) -> str:
        """Build prompt for refining an argument based on feedback."""
        avg_score = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0.5

        lines = [
            "You are refining your argument based on feedback from other AI models in a consensus debate.",
            "",
            f"Original question: {prompt}",
            "",
            f"Your current argument (Round {round_num}):",
            f'"{current_argument}"',
            "",
            f"Average evaluation score: {avg_score:.2f}/1.0",
            "",
        ]

        if context:
            lines.append(f"Context: {context}")
            lines.append("")

        if supporting_notes:
            lines.append("Supporting information:")
            for note in supporting_notes[:3]:
                lines.append(f"- {note[:200]}")
            lines.append("")

        lines.extend(
            [
                "Refine your argument to:",
                "- Address any weaknesses identified in evaluations",
                "- Strengthen your reasoning and evidence",
                "- Improve clarity and coherence",
                "- Better align with the consensus direction",
                "",
                "Output ONLY the refined argument, without explanation.",
            ]
        )

        return "\n".join(lines)

    async def _synthesize_consensus(
        self,
        prompt: str,
        debate_rounds: List[DebateRound],
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
    ) -> str:
        """Synthesize final consensus from all debate rounds."""
        if not debate_rounds:
            return "No consensus reached."

        # Use the best model (highest average score) for synthesis
        # For now, use first available model
        synthesis_model = list(debate_rounds[-1].arguments.keys())[0] if debate_rounds else None
        if not synthesis_model:
            return "No consensus reached."

        provider = self._select_provider(synthesis_model)

        synthesis_prompt = self._build_synthesis_prompt(
            prompt=prompt,
            debate_rounds=debate_rounds,
            context=context,
            supporting_notes=supporting_notes,
        )

        try:
            result = await provider.complete(synthesis_prompt, model=synthesis_model)
            return result.content.strip()
        except Exception as exc:
            logger.warning("Failed to synthesize consensus: %s", exc)
            # Fallback: use best argument from last round
            if debate_rounds:
                best_model = max(
                    debate_rounds[-1].arguments.keys(),
                    key=lambda m: sum(
                        evals.get(m, 0.5)
                        for evals in debate_rounds[-1].evaluations.values()
                    ) / max(len(debate_rounds[-1].evaluations), 1),
                )
                return debate_rounds[-1].arguments.get(best_model, "No consensus reached.")
            return "No consensus reached."

    def _build_synthesis_prompt(
        self,
        prompt: str,
        debate_rounds: List[DebateRound],
        *,
        context: Optional[str] = None,
        supporting_notes: Optional[List[str]] = None,
    ) -> str:
        """Build prompt for synthesizing consensus."""
        lines = [
            "You are synthesizing the final consensus from a multi-round AI debate.",
            "",
            f"Original question: {prompt}",
            "",
            f"Debate summary ({len(debate_rounds)} rounds):",
            "",
        ]

        for round_data in debate_rounds[-3:]:  # Show last 3 rounds
            lines.append(f"Round {round_data.round_number} (Consensus: {round_data.consensus_score:.2f}):")
            for model, argument in list(round_data.arguments.items())[:2]:  # Show 2 arguments
                lines.append(f"  {model}: {argument[:200]}...")
            lines.append("")

        if context:
            lines.append(f"Context: {context}")
            lines.append("")

        if supporting_notes:
            lines.append("Supporting information:")
            for note in supporting_notes[:3]:
                lines.append(f"- {note[:200]}")
            lines.append("")

        lines.extend(
            [
                "Synthesize a final consensus answer that:",
                "- Incorporates the best points from all arguments",
                "- Resolves disagreements where possible",
                "- Acknowledges remaining uncertainties",
                "- Provides a clear, comprehensive answer to the original question",
                "",
                "Output the final consensus answer.",
            ]
        )

        return "\n".join(lines)

    def _extract_agreements_disagreements(
        self, debate_rounds: List[DebateRound]
    ) -> Tuple[List[str], List[str]]:
        """Extract key agreements and disagreements from debate."""
        if not debate_rounds:
            return [], []

        # Use key points from last round as agreements
        agreements = debate_rounds[-1].key_points[:3] if debate_rounds else []

        # Disagreements are harder to extract automatically
        # For now, return empty list
        disagreements: List[str] = []

        return agreements, disagreements

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

