"""Critique and Improve protocol: multi-model collaboration with drafting and critiquing."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from ..planner import ReasoningPlan, PlanRole
    from ..services.base import LLMProvider, LLMResult
    from ..services.web_research import WebDocument

from .base import BaseProtocol, ProtocolResult

logger = logging.getLogger(__name__)


class CritiqueAndImproveProtocol(BaseProtocol):
    """
    Critique and Improve protocol for complex queries.
    
    Uses a multi-step, multi-model workflow:
    1. Draft: Multiple models generate initial answers
    2. Critique: Models critique each other's drafts
    3. Improve: Models refine their answers based on critiques
    4. Synthesize: Final answer synthesis from improved drafts
    
    Best for complex, open-ended, or high-stakes queries requiring
    thorough analysis and verification.
    """
    
    def __init__(
        self,
        providers: Dict[str, "LLMProvider"],
        model_registry: any,
        planner: any,
        max_critique_rounds: int = 2,
        min_models: int = 2,
        max_models: int = 4,
        **kwargs,
    ):
        """
        Initialize Critique and Improve protocol.
        
        Args:
            providers: Dictionary of LLM providers
            model_registry: Model registry
            planner: Reasoning planner
            max_critique_rounds: Maximum number of critique rounds
            min_models: Minimum number of models to use
            max_models: Maximum number of models to use
            **kwargs: Additional configuration
        """
        super().__init__(providers, model_registry, planner, **kwargs)
        self.max_critique_rounds = max_critique_rounds
        self.min_models = min_models
        self.max_models = max_models
    
    async def execute(
        self,
        prompt: str,
        *,
        context: Optional[str] = None,
        knowledge_snippets: Optional[Sequence[str]] = None,
        models: Optional[Sequence[str]] = None,
        plan: Optional["ReasoningPlan"] = None,
        db_session: Optional["Session"] = None,
        user_id: Optional[str] = None,
        use_tools: bool = True,
        mode: str = "accuracy",
        **kwargs,
    ) -> ProtocolResult:
        """
        Execute Critique and Improve protocol.
        
        Args:
            prompt: User query
            context: Optional conversation context
            knowledge_snippets: Optional knowledge base snippets
            models: Optional list of models
            plan: Optional reasoning plan
            db_session: Optional database session
            user_id: Optional user ID
            use_tools: Whether to enable tool usage
            mode: Query mode ("speed" or "accuracy")
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with multi-model collaboration artifacts
        """
        logger.info("Critique and Improve Protocol: Starting multi-model collaboration")
        
        # Select models
        if models and len(models) > 0:
            selected_models = list(models[:self.max_models])
        else:
            selected_models = self.model_registry.select_models_for_query(
                prompt, mode=mode, max_models=self.max_models
            )
            # Ensure minimum models
            if len(selected_models) < self.min_models:
                # Add default models if needed
                default_models = ["gpt-4o-mini", "gpt-4o"]
                for model in default_models:
                    if model not in selected_models:
                        selected_models.append(model)
                        if len(selected_models) >= self.min_models:
                            break
        
        selected_models = selected_models[:self.max_models]
        logger.info("Critique and Improve Protocol: Selected models: %s", selected_models)
        
        # Build augmented prompt
        augmented_prompt = prompt
        if context:
            augmented_prompt = f"{context}\n\nUser query: {prompt}"
        if knowledge_snippets:
            knowledge_block = "\n\n".join(knowledge_snippets)
            augmented_prompt = f"{augmented_prompt}\n\nRelevant context:\n{knowledge_block}"
        
        # Step 1: Draft - Generate initial answers in parallel
        logger.info("Critique and Improve Protocol: Step 1 - Drafting initial answers")
        draft_results = await self._generate_drafts(augmented_prompt, selected_models)
        
        if not draft_results:
            logger.error("Critique and Improve Protocol: No drafts generated")
            # Fallback to simple protocol
            from .simple import SimpleProtocol
            simple_protocol = SimpleProtocol(self.providers, self.model_registry, self.planner)
            return await simple_protocol.execute(
                prompt,
                context=context,
                knowledge_snippets=knowledge_snippets,
                models=selected_models[:1] if selected_models else None,
                mode=mode,
            )
        
        initial_responses = draft_results
        critiques: List[Tuple[str, str, "LLMResult"]] = []
        improvements: List["LLMResult"] = []
        consensus_notes: List[str] = []
        refinement_rounds = 0
        
        # Step 2: Critique - Models critique each other's drafts
        logger.info("Critique and Improve Protocol: Step 2 - Critiquing drafts")
        critique_results = await self._generate_critiques(
            augmented_prompt, draft_results, selected_models
        )
        critiques.extend(critique_results)
        
        # Step 3: Improve - Refine answers based on critiques
        logger.info("Critique and Improve Protocol: Step 3 - Improving answers")
        improvement_results = await self._generate_improvements(
            augmented_prompt, draft_results, critique_results, selected_models
        )
        improvements.extend(improvement_results)
        refinement_rounds = 1
        
        # Step 4: Synthesize - Create final answer from improved drafts
        logger.info("Critique and Improve Protocol: Step 4 - Synthesizing final answer")
        final_response = await self._synthesize_answer(
            augmented_prompt, improvement_results or draft_results, selected_models
        )
        
        # Build consensus notes
        consensus_notes = [
            f"Critique and Improve protocol: {len(selected_models)} models collaborated",
            f"Drafts: {len(draft_results)}, Critiques: {len(critique_results)}, Improvements: {len(improvement_results)}",
        ]
        
        # Quality assessments (simplified - could be enhanced)
        quality_assessments: Dict[str, Any] = {}
        for result in draft_results:
            quality_assessments[result.model] = {
                "score": 0.7,  # Default score
                "flags": [],
                "highlights": [f"Draft from {result.model}"],
            }
        
        return ProtocolResult(
            final_response=final_response,
            initial_responses=initial_responses,
            critiques=critiques,
            improvements=improvements,
            consensus_notes=consensus_notes,
            step_outputs={
                "draft": draft_results,
                "critique": [c[2] for c in critiques],
                "improve": improvements,
            },
            supporting_notes=[],
            quality_assessments=quality_assessments,
            evaluation=None,
            refinement_rounds=refinement_rounds,
            accepted_after_refinement=True,
        )
    
    async def _generate_drafts(
        self,
        prompt: str,
        models: List[str],
    ) -> List["LLMResult"]:
        """Generate initial drafts from multiple models in parallel."""
        from ..services.base import LLMResult
        
        async def generate_draft(model: str) -> "LLMResult":
            provider = self._select_provider(model)
            try:
                result = await provider.complete(prompt, model=model)
                return result
            except Exception as exc:
                logger.warning("Critique and Improve: Failed to generate draft from %s: %s", model, exc)
                return LLMResult(
                    model=model,
                    content=f"Error generating draft: {str(exc)}",
                    tokens=0,
                )
        
        # Generate drafts in parallel
        tasks = [generate_draft(model) for model in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and empty results
        drafts = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Critique and Improve: Exception in draft generation: %s", result)
                continue
            if result and result.content and result.content.strip():
                drafts.append(result)
        
        return drafts
    
    async def _generate_critiques(
        self,
        prompt: str,
        drafts: List["LLMResult"],
        models: List[str],
    ) -> List[Tuple[str, str, "LLMResult"]]:
        """Generate critiques where each model critiques other models' drafts."""
        from ..services.base import LLMResult
        
        critiques: List[Tuple[str, str, "LLMResult"]] = []
        
        # For each draft, have other models critique it
        for draft in drafts:
            if draft.model not in models:
                continue
            
            # Select a different model to critique this draft
            critic_models = [m for m in models if m != draft.model]
            if not critic_models:
                continue
            
            # Use first available critic model
            critic_model = critic_models[0]
            
            critique_prompt = f"""You are a critical reviewer. Please review the following answer to the user's question and provide constructive feedback.

User's question: {prompt}

Answer to review:
{draft.content}

Please provide:
1. What the answer does well
2. Any inaccuracies, gaps, or areas for improvement
3. Suggestions for enhancement

Be specific and constructive in your critique."""

            provider = self._select_provider(critic_model)
            try:
                critique_result = await provider.complete(critique_prompt, model=critic_model)
                critiques.append((critic_model, draft.model, critique_result))
            except Exception as exc:
                logger.warning("Critique and Improve: Failed to generate critique: %s", exc)
        
        return critiques
    
    async def _generate_improvements(
        self,
        prompt: str,
        drafts: List["LLMResult"],
        critiques: List[Tuple[str, str, "LLMResult"]],
        models: List[str],
    ) -> List["LLMResult"]:
        """Generate improved answers based on critiques."""
        from ..services.base import LLMResult
        
        improvements: List["LLMResult"] = []
        
        # For each draft, find its critiques and generate improvement
        for draft in drafts:
            # Find critiques for this draft
            draft_critiques = [c for c in critiques if c[1] == draft.model]
            
            if not draft_critiques:
                # No critiques, use original draft
                improvements.append(draft)
                continue
            
            # Build improvement prompt
            critique_text = "\n\n".join([f"Critique from {c[0]}:\n{c[2].content}" for c in draft_critiques])
            
            improvement_prompt = f"""You previously provided this answer to the user's question:

User's question: {prompt}

Your original answer:
{draft.content}

You received the following critiques:
{critique_text}

Please revise your answer to address the critiques while maintaining what was good about your original answer. Provide an improved version."""

            provider = self._select_provider(draft.model)
            try:
                improvement_result = await provider.complete(improvement_prompt, model=draft.model)
                improvements.append(improvement_result)
            except Exception as exc:
                logger.warning("Critique and Improve: Failed to generate improvement: %s", exc)
                # Fallback to original draft
                improvements.append(draft)
        
        return improvements
    
    async def _synthesize_answer(
        self,
        prompt: str,
        improved_drafts: List["LLMResult"],
        models: List[str],
    ) -> "LLMResult":
        """Synthesize final answer from improved drafts."""
        from ..services.base import LLMResult
        
        if not improved_drafts:
            # Fallback
            return LLMResult(
                model="synthesis",
                content="Error: No improved drafts available for synthesis.",
                tokens=0,
            )
        
        if len(improved_drafts) == 1:
            # Single draft, return as-is
            return improved_drafts[0]
        
        # Build synthesis prompt
        drafts_text = "\n\n---\n\n".join([
            f"Draft from {draft.model}:\n{draft.content}"
            for draft in improved_drafts
        ])
        
        synthesis_prompt = f"""You are synthesizing multiple improved answers to create a final, comprehensive response.

User's question: {prompt}

Here are the improved drafts from different models:

{drafts_text}

Please synthesize these into a single, coherent, and comprehensive answer that:
1. Combines the best elements from each draft
2. Resolves any contradictions
3. Provides a clear, well-structured response
4. Maintains accuracy and completeness

Provide the final synthesized answer:"""

        # Use the first model for synthesis (or a designated synthesizer)
        synthesizer_model = models[0] if models else "gpt-4o-mini"
        provider = self._select_provider(synthesizer_model)
        
        try:
            synthesis_result = await provider.complete(synthesis_prompt, model=synthesizer_model)
            synthesis_result.model = "synthesis"
            return synthesis_result
        except Exception as exc:
            logger.error("Critique and Improve: Failed to synthesize answer: %s", exc)
            # Fallback: return best improved draft (longest/most detailed)
            best_draft = max(improved_drafts, key=lambda d: len(d.content) if d.content else 0)
            return best_draft

