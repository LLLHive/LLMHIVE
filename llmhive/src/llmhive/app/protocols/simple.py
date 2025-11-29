"""Simple protocol: single-step answer from one model."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from ..planner import ReasoningPlan
    from ..services.base import LLMProvider, LLMResult
    from ..services.web_research import WebDocument

from .base import BaseProtocol, ProtocolResult

logger = logging.getLogger(__name__)


class SimpleProtocol(BaseProtocol):
    """
    Simple protocol for straightforward queries.
    
    Uses a single model to generate a direct answer without multi-step
    refinement or critique. Best for simple Q&A, factual queries, and
    low-complexity requests.
    """
    
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
        Execute simple protocol: single model, direct answer.
        
        Args:
            prompt: User query
            context: Optional conversation context
            knowledge_snippets: Optional knowledge base snippets
            models: Optional list of models (uses first one or default)
            plan: Optional reasoning plan (not used in simple protocol)
            db_session: Optional database session
            user_id: Optional user ID
            use_tools: Whether to enable tool usage
            mode: Query mode ("speed" or "accuracy")
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with single model's answer
        """
        logger.info("Simple Protocol: Executing single-model query")
        
        # Select model
        if models and len(models) > 0:
            selected_model = models[0]
        else:
            # Use model registry to select best model for query
            selected_models = self.model_registry.select_models_for_query(
                prompt, mode=mode, max_models=1
            )
            selected_model = selected_models[0] if selected_models else "gpt-4o-mini"
        
        logger.info("Simple Protocol: Selected model: %s", selected_model)
        
        # Build prompt with context
        augmented_prompt = prompt
        if context:
            augmented_prompt = f"{context}\n\nUser query: {prompt}"
        if knowledge_snippets:
            knowledge_block = "\n\n".join(knowledge_snippets)
            augmented_prompt = f"{augmented_prompt}\n\nRelevant context:\n{knowledge_block}"
        
        # Get provider and generate answer
        provider = self._select_provider(selected_model)
        
        try:
            # Provider.complete is async
            result = await provider.complete(augmented_prompt, model=selected_model)
            logger.info("Simple Protocol: Generated answer from %s", selected_model)
        except Exception as exc:
            logger.error("Simple Protocol: Failed to generate answer: %s", exc)
            # Return error result
            from ..services.base import LLMResult
            result = LLMResult(
                model=selected_model,
                content=f"Error: Failed to generate answer. {str(exc)}",
                tokens=0,
            )
        
        # Return protocol result
        return ProtocolResult(
            final_response=result,
            initial_responses=[result],
            critiques=[],
            improvements=[],
            consensus_notes=[f"Simple protocol: Direct answer from {selected_model}"],
            step_outputs={"answer": [result]},
            supporting_notes=[],
            quality_assessments={},
            evaluation=None,
            refinement_rounds=1,
            accepted_after_refinement=True,
        )

