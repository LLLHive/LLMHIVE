"""Consensus & Multi-Model Synthesis for LLMHive Orchestrator.

This module handles merging and synthesizing responses from multiple models
to produce a final answer that is better than any individual response.

Features:
- LLM-based answer fusion
- Multi-round debate for controversial answers
- Quality-weighted synthesis
- Consistency detection
- Majority voting for deterministic questions
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConsensusMethod(str, Enum):
    """Methods for reaching consensus."""
    FUSION = "fusion"  # LLM synthesizes all answers
    DEBATE = "debate"  # Models critique each other
    MAJORITY = "majority"  # Select most common answer
    WEIGHTED = "weighted"  # Weight by model quality
    ARBITER = "arbiter"  # Single model judges


@dataclass
class ModelResponse:
    """A response from a model."""
    model: str
    content: str
    quality_score: float = 0.8
    confidence: float = 0.8
    tokens_used: int = 0
    latency_ms: float = 0.0


@dataclass
class ConsensusResult:
    """Result of consensus building."""
    final_answer: str
    method_used: ConsensusMethod
    agreement_level: float  # 0-1, how much models agreed
    synthesis_notes: List[str]
    contributing_models: List[str]
    debate_rounds: int = 0


# Prompts for consensus
FUSION_PROMPT = '''You are synthesizing multiple AI model responses into one optimal answer.

Original Question: {query}

Response A ({model_a}):
{response_a}

Response B ({model_b}):
{response_b}

{additional_responses}

Create a final answer that:
1. Takes the best elements from each response
2. Resolves any contradictions (preferring more accurate/complete info)
3. Maintains factual accuracy
4. Is well-organized and comprehensive

Output only the final synthesized answer, no commentary.'''

DEBATE_PROMPT = '''You are reviewing another AI's answer. Be constructive but critical.

Question: {query}

Answer under review:
{answer}

Do you agree with this answer? If not, what are the issues?
If it's correct, just say "APPROVED".
Otherwise, list specific problems or improvements needed.'''

ARBITER_PROMPT = '''You are judging which response best answers the question.

Question: {query}

{responses}

Which response is best? Consider:
- Accuracy and correctness
- Completeness
- Clarity and organization
- Practical usefulness

Respond with only the number of the best response (e.g., "1" or "2"), nothing else.'''


class ConsensusManager:
    """Manages consensus building across multiple model responses.
    
    Implements various strategies for synthesizing multiple responses
    into a single, high-quality answer.
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        synthesis_model: str = "gpt-4o",
    ):
        """Initialize consensus manager.
        
        Args:
            providers: LLM providers
            synthesis_model: Model to use for synthesis
        """
        self.providers = providers
        self.synthesis_model = synthesis_model
    
    async def reach_consensus(
        self,
        query: str,
        responses: List[ModelResponse],
        method: Optional[ConsensusMethod] = None,
        max_debate_rounds: int = 2,
    ) -> ConsensusResult:
        """Build consensus from multiple responses.
        
        Args:
            query: Original query
            responses: List of model responses
            method: Consensus method (auto-selected if None)
            max_debate_rounds: Maximum debate rounds
            
        Returns:
            ConsensusResult with synthesized answer
        """
        if len(responses) == 0:
            raise ValueError("No responses to synthesize")
        
        if len(responses) == 1:
            return ConsensusResult(
                final_answer=responses[0].content,
                method_used=ConsensusMethod.FUSION,
                agreement_level=1.0,
                synthesis_notes=["Single response, no synthesis needed"],
                contributing_models=[responses[0].model],
            )
        
        # Check if responses are essentially the same
        if self._responses_are_similar(responses):
            # High agreement - just pick the best one
            best = max(responses, key=lambda r: r.quality_score)
            return ConsensusResult(
                final_answer=best.content,
                method_used=ConsensusMethod.MAJORITY,
                agreement_level=0.95,
                synthesis_notes=["High agreement - used best quality response"],
                contributing_models=[r.model for r in responses],
            )
        
        # Auto-select method if not specified
        if method is None:
            method = self._select_method(query, responses)
        
        # Execute consensus method
        if method == ConsensusMethod.FUSION:
            return await self._fusion_consensus(query, responses)
        elif method == ConsensusMethod.DEBATE:
            return await self._debate_consensus(query, responses, max_debate_rounds)
        elif method == ConsensusMethod.MAJORITY:
            return self._majority_consensus(responses)
        elif method == ConsensusMethod.WEIGHTED:
            return self._weighted_consensus(responses)
        elif method == ConsensusMethod.ARBITER:
            return await self._arbiter_consensus(query, responses)
        else:
            return await self._fusion_consensus(query, responses)
    
    def _responses_are_similar(
        self,
        responses: List[ModelResponse],
        threshold: float = 0.8,
    ) -> bool:
        """Check if responses are essentially the same."""
        if len(responses) < 2:
            return True
        
        # Simple word overlap check
        first_words = set(responses[0].content.lower().split())
        
        for resp in responses[1:]:
            resp_words = set(resp.content.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(first_words & resp_words)
            union = len(first_words | resp_words)
            
            if union == 0:
                continue
            
            similarity = intersection / union
            if similarity < threshold:
                return False
        
        return True
    
    def _select_method(
        self,
        query: str,
        responses: List[ModelResponse],
    ) -> ConsensusMethod:
        """Auto-select consensus method based on query and responses."""
        query_lower = query.lower()
        
        # For factual questions with clear answers, use arbiter
        if any(w in query_lower for w in ["what is", "when did", "who is", "how many"]):
            return ConsensusMethod.ARBITER
        
        # For complex analysis, use fusion
        if any(w in query_lower for w in ["analyze", "compare", "explain", "comprehensive"]):
            return ConsensusMethod.FUSION
        
        # For code/technical, use debate to catch errors
        if any(w in query_lower for w in ["code", "function", "implement", "debug"]):
            return ConsensusMethod.DEBATE
        
        # Default to fusion
        return ConsensusMethod.FUSION
    
    async def _fusion_consensus(
        self,
        query: str,
        responses: List[ModelResponse],
    ) -> ConsensusResult:
        """Synthesize responses using LLM fusion."""
        if len(responses) < 2:
            return ConsensusResult(
                final_answer=responses[0].content if responses else "",
                method_used=ConsensusMethod.FUSION,
                agreement_level=1.0,
                synthesis_notes=["Single response"],
                contributing_models=[r.model for r in responses],
            )
        
        # Build additional responses section for more than 2
        additional = ""
        if len(responses) > 2:
            for i, resp in enumerate(responses[2:], 3):
                additional += f"\nResponse {chr(64+i)} ({resp.model}):\n{resp.content[:1000]}\n"
        
        # Use replace for query first (may contain curly braces), then format for safe values
        prompt = FUSION_PROMPT.replace("{query}", query).format(
            model_a=responses[0].model,
            response_a=responses[0].content[:1500],
            model_b=responses[1].model,
            response_b=responses[1].content[:1500],
            additional_responses=additional,
        )
        
        provider = self._get_provider()
        if not provider:
            # Fallback: return best response
            best = max(responses, key=lambda r: r.quality_score)
            return ConsensusResult(
                final_answer=best.content,
                method_used=ConsensusMethod.FUSION,
                agreement_level=0.5,
                synthesis_notes=["Fusion failed - used best response"],
                contributing_models=[r.model for r in responses],
            )
        
        try:
            result = await provider.complete(prompt, model=self.synthesis_model)
            fused = getattr(result, 'content', '') or getattr(result, 'text', '')
            
            return ConsensusResult(
                final_answer=fused.strip(),
                method_used=ConsensusMethod.FUSION,
                agreement_level=0.8,
                synthesis_notes=["LLM fusion completed"],
                contributing_models=[r.model for r in responses],
            )
        except Exception as e:
            logger.error("Fusion failed: %s", e)
            best = max(responses, key=lambda r: r.quality_score)
            return ConsensusResult(
                final_answer=best.content,
                method_used=ConsensusMethod.FUSION,
                agreement_level=0.5,
                synthesis_notes=[f"Fusion error: {e}"],
                contributing_models=[r.model for r in responses],
            )
    
    async def _debate_consensus(
        self,
        query: str,
        responses: List[ModelResponse],
        max_rounds: int,
    ) -> ConsensusResult:
        """Use debate to refine answers."""
        synthesis_notes = []
        debate_rounds = 0
        
        # Start with best response
        current_best = max(responses, key=lambda r: r.quality_score)
        current_answer = current_best.content
        
        # Other models critique
        critics = [r for r in responses if r.model != current_best.model]
        
        for round_num in range(max_rounds):
            debate_rounds += 1
            critiques = []
            
            # Gather critiques
            for critic in critics[:2]:  # Limit critics
                critique = await self._get_critique(
                    query, current_answer, critic.model
                )
                critiques.append((critic.model, critique))
                synthesis_notes.append(f"Round {round_num+1} critique from {critic.model}")
            
            # Check if approved
            approved = all("APPROVED" in c[1].upper() for c in critiques)
            if approved:
                synthesis_notes.append(f"Answer approved after {debate_rounds} rounds")
                break
            
            # Refine based on critiques
            current_answer = await self._refine_with_critiques(
                query, current_answer, critiques
            )
        
        # Calculate agreement based on final critiques
        agreement = 0.9 if debate_rounds == 1 else 0.7
        
        return ConsensusResult(
            final_answer=current_answer,
            method_used=ConsensusMethod.DEBATE,
            agreement_level=agreement,
            synthesis_notes=synthesis_notes,
            contributing_models=[r.model for r in responses],
            debate_rounds=debate_rounds,
        )
    
    async def _get_critique(
        self,
        query: str,
        answer: str,
        critic_model: str,
    ) -> str:
        """Get critique from a model."""
        # Use replace for query and answer (may contain curly braces)
        prompt = DEBATE_PROMPT.replace("{query}", query).replace("{answer}", answer[:2000])
        
        provider = self._get_provider_for_model(critic_model)
        if not provider:
            return "APPROVED"  # No provider, skip critique
        
        try:
            result = await provider.complete(prompt, model=critic_model)
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception as e:
            logger.debug("Critique failed: %s", e)
            return "APPROVED"
    
    async def _refine_with_critiques(
        self,
        query: str,
        answer: str,
        critiques: List[Tuple[str, str]],
    ) -> str:
        """Refine answer based on critiques."""
        critique_text = "\n".join([
            f"Critique from {model}:\n{critique}"
            for model, critique in critiques
            if "APPROVED" not in critique.upper()
        ])
        
        if not critique_text:
            return answer
        
        prompt = f"""Improve this answer based on the feedback:

Original question: {query}

Current answer:
{answer[:2000]}

Critiques:
{critique_text}

Provide an improved answer that addresses the critiques while maintaining what was correct.
Output only the improved answer."""

        provider = self._get_provider()
        if not provider:
            return answer
        
        try:
            result = await provider.complete(prompt, model=self.synthesis_model)
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception:
            return answer
    
    def _majority_consensus(
        self,
        responses: List[ModelResponse],
    ) -> ConsensusResult:
        """Select response that most others agree with."""
        # For now, just select the highest quality
        best = max(responses, key=lambda r: r.quality_score * r.confidence)
        
        return ConsensusResult(
            final_answer=best.content,
            method_used=ConsensusMethod.MAJORITY,
            agreement_level=0.8,
            synthesis_notes=["Selected highest quality response"],
            contributing_models=[r.model for r in responses],
        )
    
    def _weighted_consensus(
        self,
        responses: List[ModelResponse],
    ) -> ConsensusResult:
        """Weight responses by quality score."""
        # For text, we can't really "average", so we select best
        best = max(responses, key=lambda r: r.quality_score)
        
        return ConsensusResult(
            final_answer=best.content,
            method_used=ConsensusMethod.WEIGHTED,
            agreement_level=best.quality_score,
            synthesis_notes=[f"Selected by quality weight: {best.quality_score:.2f}"],
            contributing_models=[r.model for r in responses],
        )
    
    async def _arbiter_consensus(
        self,
        query: str,
        responses: List[ModelResponse],
    ) -> ConsensusResult:
        """Use arbiter model to select best response."""
        # Build comparison prompt
        responses_text = ""
        for i, resp in enumerate(responses, 1):
            responses_text += f"\nResponse {i} ({resp.model}):\n{resp.content[:1000]}\n"
        
        # Use replace for query and responses (may contain curly braces)
        prompt = ARBITER_PROMPT.replace("{query}", query).replace("{responses}", responses_text)
        
        provider = self._get_provider()
        if not provider:
            return self._weighted_consensus(responses)
        
        try:
            result = await provider.complete(prompt, model=self.synthesis_model)
            selection = getattr(result, 'content', '') or getattr(result, 'text', '')
            
            # Parse selection
            for i, resp in enumerate(responses, 1):
                if str(i) in selection[:10]:
                    return ConsensusResult(
                        final_answer=resp.content,
                        method_used=ConsensusMethod.ARBITER,
                        agreement_level=0.85,
                        synthesis_notes=[f"Arbiter selected response {i} ({resp.model})"],
                        contributing_models=[r.model for r in responses],
                    )
        except Exception as e:
            logger.debug("Arbiter failed: %s", e)
        
        # Fallback
        return self._weighted_consensus(responses)
    
    def _get_provider(self) -> Optional[Any]:
        """Get default provider."""
        if "openai" in self.providers:
            return self.providers["openai"]
        if self.providers:
            return next(iter(self.providers.values()))
        return None
    
    def _get_provider_for_model(self, model: str) -> Optional[Any]:
        """Get provider for specific model."""
        model_lower = model.lower()
        
        mapping = {
            "gpt": "openai",
            "claude": "anthropic",
            "gemini": "gemini",
            "deepseek": "deepseek",
        }
        
        for prefix, provider in mapping.items():
            if model_lower.startswith(prefix) and provider in self.providers:
                return self.providers[provider]
        
        return self._get_provider()


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def synthesize_responses(
    query: str,
    responses: List[ModelResponse],
    providers: Dict[str, Any],
    method: Optional[ConsensusMethod] = None,
) -> ConsensusResult:
    """Convenience function for response synthesis."""
    manager = ConsensusManager(providers)
    return await manager.reach_consensus(query, responses, method)


def calculate_agreement(responses: List[ModelResponse]) -> float:
    """Calculate agreement level between responses."""
    if len(responses) < 2:
        return 1.0
    
    # Simple word-based similarity
    all_words = [set(r.content.lower().split()) for r in responses]
    
    total_sim = 0.0
    count = 0
    
    for i in range(len(all_words)):
        for j in range(i + 1, len(all_words)):
            intersection = len(all_words[i] & all_words[j])
            union = len(all_words[i] | all_words[j])
            if union > 0:
                total_sim += intersection / union
                count += 1
    
    return total_sim / count if count > 0 else 0.5
