"""Base protocol interface for orchestration strategies."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
import asyncio
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from ..orchestrator import OrchestrationArtifacts
    from ..planner import ReasoningPlan
    from ..services.base import LLMProvider, LLMResult
    from ..services.web_research import WebDocument

logger = logging.getLogger(__name__)


@dataclass
class ProtocolResult:
    """Result from protocol execution."""
    
    final_response: "LLMResult"
    initial_responses: List["LLMResult"]
    critiques: List[tuple[str, str, "LLMResult"]]  # (author, target, result)
    improvements: List["LLMResult"]
    consensus_notes: List[str]
    step_outputs: Dict[str, List["LLMResult"]]
    supporting_notes: List[str]
    quality_assessments: Dict[str, any]  # ResponseAssessment objects
    suggestions: List[any] = None  # Proactive suggestions from dialogue system
    evaluation: Optional["LLMResult"] = None
    refinement_rounds: int = 1
    accepted_after_refinement: bool = True
    
    def __post_init__(self):
        """Initialize suggestions to empty list if None."""
        if self.suggestions is None:
            self.suggestions = []


class BaseProtocol(ABC):
    """Base class for all orchestration protocols."""
    
    def __init__(
        self,
        providers: Dict[str, "LLMProvider"],
        model_registry: any,  # ModelRegistry
        planner: any,  # ReasoningPlanner
        **kwargs,
    ):
        """
        Initialize protocol.
        
        Args:
            providers: Dictionary of LLM providers
            model_registry: Model registry for model selection
            planner: Reasoning planner for creating plans
            **kwargs: Additional protocol-specific configuration
        """
        self.providers = providers
        self.model_registry = model_registry
        self.planner = planner
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
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
        Execute the protocol to answer the query.
        
        Args:
            prompt: User query
            context: Optional conversation context
            knowledge_snippets: Optional knowledge base snippets
            models: Optional list of models to use
            plan: Optional reasoning plan (if already created)
            db_session: Optional database session
            user_id: Optional user ID
            use_tools: Whether to enable tool usage
            mode: Query mode ("speed" or "accuracy")
            **kwargs: Additional protocol-specific parameters
            
        Returns:
            ProtocolResult with all artifacts from execution
        """
        raise NotImplementedError
    
    def _select_provider(self, model: str) -> "LLMProvider":
        """Select provider for a model."""
        # Try to find provider that supports this model
        for provider_name, provider in self.providers.items():
            if hasattr(provider, "supports_model") and provider.supports_model(model):
                return provider
            # Fallback: check if model name contains provider name
            if provider_name.lower() in model.lower():
                return provider
        
        # Default to first provider or stub
        return self.providers.get("stub") or next(iter(self.providers.values()))
    
    async def _gather_with_handling(
        self,
        coroutines: Sequence[any],
    ) -> List["LLMResult"]:
        """
        Gather async results with error handling.
        
        Args:
            coroutines: List of async coroutines or futures
            
        Returns:
            List of LLMResult objects (empty results for failed tasks)
        """
        from ..services.base import LLMResult, ProviderNotConfiguredError
        
        results: List["LLMResult"] = []
        for coro in asyncio.as_completed(coroutines):
            try:
                result = await coro
                if result:
                    results.append(result)
            except ProviderNotConfiguredError as exc:
                self.logger.warning("Provider misconfiguration during call: %s", exc)
            except Exception as exc:
                self.logger.exception("Provider call failed", exc_info=exc)
        return results

