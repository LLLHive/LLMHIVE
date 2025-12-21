"""Cascade Router - Cost-optimized model routing with automatic escalation.

Implements the Cascade/Fallback pattern from the orchestration patterns registry:
- Start with cheap/fast model
- If confidence is low or task fails, escalate to more capable model
- Expected impact: 30-70% cost reduction with <5% quality loss

Usage:
    router = CascadeRouter()
    result = await router.route(query, task_type="general")
    # result.model_used, result.escalated, result.cost_savings

This pattern is ideal for high-volume production deployments where most
queries are simple and can be handled by cheaper models.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """Query complexity classification."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    REASONING = "reasoning"


@dataclass
class CascadeConfig:
    """Configuration for cascade routing."""
    # Confidence thresholds
    min_confidence_to_proceed: float = 0.7
    escalation_confidence_threshold: float = 0.5
    
    # Cost multipliers (relative to tier 1)
    tier1_cost_multiplier: float = 1.0   # Cheap models
    tier2_cost_multiplier: float = 5.0   # Standard models  
    tier3_cost_multiplier: float = 15.0  # Premium/reasoning models
    
    # Escalation limits
    max_escalations: int = 2
    
    # Model tiers (fastest/cheapest first)
    tier1_models: List[str] = field(default_factory=lambda: [
        "openai/gpt-4o-mini",
        "google/gemini-2.0-flash",
        "deepseek/deepseek-chat",
        "anthropic/claude-3-5-haiku-20241022",
    ])
    
    tier2_models: List[str] = field(default_factory=lambda: [
        "openai/gpt-4o",
        "anthropic/claude-3-5-sonnet-20241022",
        "google/gemini-1.5-pro",
        "mistralai/mistral-large-2411",
    ])
    
    tier3_models: List[str] = field(default_factory=lambda: [
        "openai/o1",
        "anthropic/claude-sonnet-4-20250514",
        "anthropic/claude-opus-4-20250514",
        "openai/o3-mini",
    ])


@dataclass
class CascadeResult:
    """Result of cascade routing."""
    response: str
    model_used: str
    tier_used: int
    escalation_count: int
    total_cost_estimate: float
    latency_ms: float
    confidence: float
    escalation_reasons: List[str] = field(default_factory=list)
    
    @property
    def escalated(self) -> bool:
        return self.escalation_count > 0
    
    @property
    def cost_savings_estimate(self) -> float:
        """Estimate cost savings compared to always using tier 3."""
        if self.tier_used == 1:
            return 0.9  # ~90% savings
        elif self.tier_used == 2:
            return 0.5  # ~50% savings
        return 0.0


class CascadeRouter:
    """
    Cost-optimized router that uses cascade routing pattern.
    
    The router starts with the cheapest viable model and escalates
    only when the initial response doesn't meet confidence thresholds.
    """
    
    # Signals that suggest complex reasoning is needed
    REASONING_SIGNALS = [
        "prove", "derive", "why does", "explain step by step", "verify",
        "analyze in depth", "compare and contrast", "evaluate the implications",
        "what are the consequences", "how would you approach", "critically assess",
        "mathematical proof", "formal reasoning", "logical deduction",
    ]
    
    # Signals suggesting simple queries
    SIMPLE_SIGNALS = [
        "what is", "who is", "when did", "define", "list", "summarize briefly",
        "translate", "format", "convert", "hello", "hi", "thanks",
    ]
    
    # Keywords suggesting coding tasks
    CODING_SIGNALS = [
        "code", "function", "implement", "debug", "fix", "refactor",
        "write a script", "python", "javascript", "typescript", "sql",
        "api", "endpoint", "test", "unit test", "integration test",
    ]
    
    def __init__(
        self,
        config: Optional[CascadeConfig] = None,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize cascade router.
        
        Args:
            config: Cascade configuration
            llm_client: LLM client for making calls (if None, uses default)
        """
        self.config = config or CascadeConfig()
        self.llm_client = llm_client
        
        # Metrics
        self._total_requests = 0
        self._tier1_resolved = 0
        self._tier2_resolved = 0
        self._tier3_resolved = 0
        self._escalation_count = 0
    
    def classify_complexity(self, query: str) -> TaskComplexity:
        """
        Classify query complexity to determine starting tier.
        
        Args:
            query: User query text
            
        Returns:
            TaskComplexity enum value
        """
        query_lower = query.lower()
        
        # Check for reasoning signals first (highest priority)
        if any(signal in query_lower for signal in self.REASONING_SIGNALS):
            return TaskComplexity.REASONING
        
        # Check for coding signals
        if any(signal in query_lower for signal in self.CODING_SIGNALS):
            return TaskComplexity.MODERATE
        
        # Check for simple signals
        if any(signal in query_lower for signal in self.SIMPLE_SIGNALS):
            return TaskComplexity.SIMPLE
        
        # Default based on length
        if len(query) < 100:
            return TaskComplexity.SIMPLE
        elif len(query) < 500:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.COMPLEX
    
    def get_starting_tier(self, complexity: TaskComplexity) -> int:
        """Get the starting tier based on complexity classification."""
        if complexity == TaskComplexity.SIMPLE:
            return 1
        elif complexity == TaskComplexity.MODERATE:
            return 1  # Still try tier 1, but be ready to escalate
        elif complexity == TaskComplexity.COMPLEX:
            return 2
        elif complexity == TaskComplexity.REASONING:
            return 3  # Go straight to reasoning models
        return 1
    
    def get_model_for_tier(
        self,
        tier: int,
        task_type: str = "general",
    ) -> Optional[str]:
        """
        Select best available model for a tier.
        
        Args:
            tier: Model tier (1, 2, or 3)
            task_type: Type of task (general, coding, reasoning)
            
        Returns:
            Model ID or None if no models available
        """
        if tier == 1:
            models = self.config.tier1_models
        elif tier == 2:
            models = self.config.tier2_models
        elif tier == 3:
            models = self.config.tier3_models
        else:
            return None
        
        # For coding, prefer models good at coding
        if task_type == "coding" and tier <= 2:
            coding_preferred = [
                "anthropic/claude-3-5-sonnet-20241022",
                "openai/gpt-4o",
                "deepseek/deepseek-chat",
            ]
            for model in coding_preferred:
                if model in models:
                    return model
        
        # Return first available
        return models[0] if models else None
    
    async def estimate_confidence(
        self,
        query: str,
        response: str,
        model_used: str,
    ) -> float:
        """
        Estimate confidence in the response.
        
        Uses heuristics to estimate whether escalation is needed:
        - Response length relative to query
        - Hedging language detection
        - Uncertainty markers
        
        Returns:
            Confidence score 0.0 - 1.0
        """
        confidence = 0.8  # Base confidence
        response_lower = response.lower()
        
        # Hedging language reduces confidence
        hedging_phrases = [
            "i'm not sure", "i don't know", "might be", "possibly",
            "could be wrong", "i think", "maybe", "uncertain",
            "i cannot", "i'm unable to", "beyond my", "i apologize",
        ]
        
        hedge_count = sum(1 for phrase in hedging_phrases if phrase in response_lower)
        confidence -= hedge_count * 0.1
        
        # Very short responses for complex queries reduce confidence
        if len(response) < 100 and len(query) > 200:
            confidence -= 0.2
        
        # Empty or error-like responses
        if len(response) < 20:
            confidence = 0.3
        
        # Explicit uncertainty markers
        if "error" in response_lower or "failed" in response_lower:
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    async def call_model(
        self,
        model_id: str,
        query: str,
        system_prompt: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Call a model and return response with latency.
        
        Args:
            model_id: Model to call
            query: User query
            system_prompt: Optional system prompt
            
        Returns:
            Tuple of (response_text, latency_ms)
        """
        start_time = time.time()
        
        # If no LLM client, return placeholder (for testing)
        if self.llm_client is None:
            # Try to import and use the gateway
            try:
                from ..openrouter.gateway import get_openrouter_gateway
                gateway = get_openrouter_gateway()
                
                response = await gateway.chat_completion(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                        {"role": "user", "content": query},
                    ],
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Extract response text
                if response and "choices" in response:
                    text = response["choices"][0]["message"]["content"]
                    return text, latency_ms
                
            except Exception as e:
                logger.warning(f"Failed to call model via gateway: {e}")
        
        # Fallback for testing
        latency_ms = (time.time() - start_time) * 1000
        return f"[Placeholder response from {model_id}]", latency_ms
    
    async def route(
        self,
        query: str,
        task_type: str = "general",
        system_prompt: Optional[str] = None,
        force_tier: Optional[int] = None,
    ) -> CascadeResult:
        """
        Route a query through the cascade.
        
        Args:
            query: User query
            task_type: Type of task (general, coding, reasoning)
            system_prompt: Optional system prompt
            force_tier: Force starting at a specific tier
            
        Returns:
            CascadeResult with response and metadata
        """
        self._total_requests += 1
        
        # Classify complexity
        complexity = self.classify_complexity(query)
        starting_tier = force_tier or self.get_starting_tier(complexity)
        
        current_tier = starting_tier
        escalation_count = 0
        escalation_reasons: List[str] = []
        total_latency = 0.0
        
        while current_tier <= 3 and escalation_count <= self.config.max_escalations:
            model = self.get_model_for_tier(current_tier, task_type)
            
            if not model:
                logger.warning(f"No model available for tier {current_tier}")
                current_tier += 1
                continue
            
            logger.debug(f"Cascade: Trying tier {current_tier} with {model}")
            
            # Call model
            response, latency_ms = await self.call_model(model, query, system_prompt)
            total_latency += latency_ms
            
            # Estimate confidence
            confidence = await self.estimate_confidence(query, response, model)
            
            # Check if we should escalate
            if confidence >= self.config.min_confidence_to_proceed:
                # Success - return result
                if current_tier == 1:
                    self._tier1_resolved += 1
                elif current_tier == 2:
                    self._tier2_resolved += 1
                else:
                    self._tier3_resolved += 1
                
                # Estimate cost (relative units)
                if current_tier == 1:
                    cost = self.config.tier1_cost_multiplier
                elif current_tier == 2:
                    cost = self.config.tier2_cost_multiplier
                else:
                    cost = self.config.tier3_cost_multiplier
                
                return CascadeResult(
                    response=response,
                    model_used=model,
                    tier_used=current_tier,
                    escalation_count=escalation_count,
                    total_cost_estimate=cost,
                    latency_ms=total_latency,
                    confidence=confidence,
                    escalation_reasons=escalation_reasons,
                )
            
            # Need to escalate
            escalation_count += 1
            self._escalation_count += 1
            reason = f"Low confidence ({confidence:.2f}) from {model}"
            escalation_reasons.append(reason)
            logger.debug(f"Cascade: Escalating - {reason}")
            current_tier += 1
        
        # Exhausted all tiers or max escalations
        logger.warning(f"Cascade exhausted for query: {query[:100]}...")
        
        return CascadeResult(
            response=response if 'response' in locals() else "Unable to generate response",
            model_used=model if 'model' in locals() else "unknown",
            tier_used=current_tier - 1,
            escalation_count=escalation_count,
            total_cost_estimate=self.config.tier3_cost_multiplier,
            latency_ms=total_latency,
            confidence=0.0,
            escalation_reasons=escalation_reasons,
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics."""
        total = self._total_requests or 1
        return {
            "total_requests": self._total_requests,
            "tier1_resolved": self._tier1_resolved,
            "tier2_resolved": self._tier2_resolved,
            "tier3_resolved": self._tier3_resolved,
            "escalation_count": self._escalation_count,
            "tier1_resolution_rate": self._tier1_resolved / total,
            "escalation_rate": self._escalation_count / total,
            "estimated_cost_savings": (
                (self._tier1_resolved * 0.9 + self._tier2_resolved * 0.5) / total
                if total > 0 else 0.0
            ),
        }


# Convenience function
async def cascade_route(
    query: str,
    task_type: str = "general",
    config: Optional[CascadeConfig] = None,
) -> CascadeResult:
    """
    Route a query using cascade pattern.
    
    Args:
        query: User query
        task_type: Task type (general, coding, reasoning)
        config: Optional cascade configuration
        
    Returns:
        CascadeResult with response and metadata
    """
    router = CascadeRouter(config=config)
    return await router.route(query, task_type)


# Singleton instance
_cascade_router: Optional[CascadeRouter] = None


def get_cascade_router() -> CascadeRouter:
    """Get or create the singleton cascade router."""
    global _cascade_router
    if _cascade_router is None:
        _cascade_router = CascadeRouter()
    return _cascade_router

