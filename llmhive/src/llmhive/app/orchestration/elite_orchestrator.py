"""Elite Orchestration Engine for LLMHive.

This module implements advanced orchestration strategies designed to beat
individual model performance through intelligent coordination, parallel
execution, and quality-weighted synthesis.

Key Performance Strategies:
1. MODEL SPECIALIZATION - Route sub-tasks to the best model for each capability
2. PARALLEL EXECUTION - Run independent tasks concurrently for speed
3. QUALITY-WEIGHTED FUSION - Combine outputs weighted by proven model quality
4. MULTI-PERSPECTIVE SYNTHESIS - Merge best elements from multiple responses
5. ADAPTIVE CHALLENGE THRESHOLD - Adjust verification strictness by confidence
6. LEARNING FROM HISTORY - Use performance data to improve routing
7. BEST-OF-N WITH JUDGE - Generate multiple options, select best
8. DYNAMIC ROUTING - Real-time model selection from OpenRouter rankings

The goal: Ensemble performance > Best individual model performance
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from .openrouter_selector import OpenRouterModelSelector, SelectionResult

logger = logging.getLogger(__name__)


# ==============================================================================
# Model Capability Profiles
# ==============================================================================

class ModelCapability(str, Enum):
    """Model capabilities for specialized routing."""
    CODING = "coding"
    REASONING = "reasoning"
    MATH = "math"
    CREATIVE = "creative"
    FACTUAL = "factual"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    INSTRUCTION_FOLLOWING = "instruction_following"
    SPEED = "speed"
    QUALITY = "quality"


# Model capability scores (0-1, higher is better)
# Based on benchmark data and empirical observations
MODEL_CAPABILITIES: Dict[str, Dict[ModelCapability, float]] = {
    # GPT-4o: Best overall, excellent reasoning and coding
    "gpt-4o": {
        ModelCapability.CODING: 0.95,
        ModelCapability.REASONING: 0.95,
        ModelCapability.MATH: 0.90,
        ModelCapability.CREATIVE: 0.85,
        ModelCapability.FACTUAL: 0.90,
        ModelCapability.ANALYSIS: 0.92,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.95,
        ModelCapability.SPEED: 0.70,
        ModelCapability.QUALITY: 0.95,
    },
    # GPT-4o-mini: Fast with good quality
    "gpt-4o-mini": {
        ModelCapability.CODING: 0.82,
        ModelCapability.REASONING: 0.80,
        ModelCapability.MATH: 0.78,
        ModelCapability.CREATIVE: 0.75,
        ModelCapability.FACTUAL: 0.80,
        ModelCapability.ANALYSIS: 0.78,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.85,
        ModelCapability.SPEED: 0.95,
        ModelCapability.QUALITY: 0.80,
    },
    # Claude Sonnet 4: Excellent reasoning and coding
    "claude-sonnet-4-20250514": {
        ModelCapability.CODING: 0.96,
        ModelCapability.REASONING: 0.94,
        ModelCapability.MATH: 0.88,
        ModelCapability.CREATIVE: 0.90,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.93,
        ModelCapability.SUMMARIZATION: 0.90,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.94,
        ModelCapability.SPEED: 0.65,
        ModelCapability.QUALITY: 0.94,
    },
    # Claude Haiku: Fast and efficient
    "claude-3-5-haiku-20241022": {
        ModelCapability.CODING: 0.78,
        ModelCapability.REASONING: 0.75,
        ModelCapability.MATH: 0.72,
        ModelCapability.CREATIVE: 0.70,
        ModelCapability.FACTUAL: 0.75,
        ModelCapability.ANALYSIS: 0.73,
        ModelCapability.SUMMARIZATION: 0.80,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.82,
        ModelCapability.SPEED: 0.92,
        ModelCapability.QUALITY: 0.75,
    },
    # Gemini 2.5 Pro: Good for research and analysis
    "gemini-2.5-pro": {
        ModelCapability.CODING: 0.88,
        ModelCapability.REASONING: 0.90,
        ModelCapability.MATH: 0.92,
        ModelCapability.CREATIVE: 0.82,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.91,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.75,
        ModelCapability.QUALITY: 0.90,
    },
    # Gemini Flash: Very fast
    "gemini-2.5-flash": {
        ModelCapability.CODING: 0.80,
        ModelCapability.REASONING: 0.78,
        ModelCapability.MATH: 0.80,
        ModelCapability.CREATIVE: 0.75,
        ModelCapability.FACTUAL: 0.82,
        ModelCapability.ANALYSIS: 0.78,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.80,
        ModelCapability.SPEED: 0.96,
        ModelCapability.QUALITY: 0.78,
    },
    # DeepSeek: Excellent for coding and reasoning
    "deepseek-chat": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.92,
        ModelCapability.MATH: 0.93,
        ModelCapability.CREATIVE: 0.75,
        ModelCapability.FACTUAL: 0.85,
        ModelCapability.ANALYSIS: 0.88,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.85,
        ModelCapability.SPEED: 0.80,
        ModelCapability.QUALITY: 0.90,
    },
    # Grok 2: Good reasoning
    "grok-2": {
        ModelCapability.CODING: 0.85,
        ModelCapability.REASONING: 0.88,
        ModelCapability.MATH: 0.85,
        ModelCapability.CREATIVE: 0.82,
        ModelCapability.FACTUAL: 0.85,
        ModelCapability.ANALYSIS: 0.85,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.85,
        ModelCapability.SPEED: 0.78,
        ModelCapability.QUALITY: 0.85,
    },
    # DeepSeek V3.2: Latest version
    "deepseek-v3.2": {
        ModelCapability.CODING: 0.95,
        ModelCapability.REASONING: 0.93,
        ModelCapability.MATH: 0.94,
        ModelCapability.CREATIVE: 0.78,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.90,
        ModelCapability.SUMMARIZATION: 0.85,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.82,
        ModelCapability.QUALITY: 0.92,
    },
    # DeepSeek R1: Reasoning specialist
    "deepseek-r1-0528": {
        ModelCapability.CODING: 0.92,
        ModelCapability.REASONING: 0.96,
        ModelCapability.MATH: 0.95,
        ModelCapability.CREATIVE: 0.72,
        ModelCapability.FACTUAL: 0.85,
        ModelCapability.ANALYSIS: 0.92,
        ModelCapability.SUMMARIZATION: 0.80,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.85,
        ModelCapability.SPEED: 0.70,
        ModelCapability.QUALITY: 0.94,
    },
    # Claude Sonnet 4 (without date suffix)
    "claude-sonnet-4": {
        ModelCapability.CODING: 0.96,
        ModelCapability.REASONING: 0.94,
        ModelCapability.MATH: 0.88,
        ModelCapability.CREATIVE: 0.90,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.93,
        ModelCapability.SUMMARIZATION: 0.90,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.94,
        ModelCapability.SPEED: 0.65,
        ModelCapability.QUALITY: 0.94,
    },
    # Claude Opus 4: Best for complex reasoning
    "claude-opus-4": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.97,
        ModelCapability.MATH: 0.92,
        ModelCapability.CREATIVE: 0.95,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.96,
        ModelCapability.SUMMARIZATION: 0.92,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.95,
        ModelCapability.SPEED: 0.55,
        ModelCapability.QUALITY: 0.97,
    },
    # Grok 4: Latest
    "grok-4": {
        ModelCapability.CODING: 0.88,
        ModelCapability.REASONING: 0.92,
        ModelCapability.MATH: 0.88,
        ModelCapability.CREATIVE: 0.85,
        ModelCapability.FACTUAL: 0.90,
        ModelCapability.ANALYSIS: 0.88,
        ModelCapability.SUMMARIZATION: 0.85,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.80,
        ModelCapability.QUALITY: 0.90,
    },
}

# Create aliases for full OpenRouter IDs (maps to same capabilities)
_MODEL_ALIASES = {
    "openai/gpt-4o": "gpt-4o",
    "openai/gpt-4o-mini": "gpt-4o-mini",
    "anthropic/claude-sonnet-4": "claude-sonnet-4",
    "anthropic/claude-opus-4": "claude-opus-4",
    "anthropic/claude-3-5-sonnet-20241022": "claude-sonnet-4",  # Map old to new
    "google/gemini-2.5-pro": "gemini-2.5-pro",
    "google/gemini-2.5-flash": "gemini-2.5-flash",
    "deepseek/deepseek-v3.2": "deepseek-v3.2",
    "deepseek/deepseek-chat": "deepseek-chat",
    "deepseek/deepseek-r1-0528": "deepseek-r1-0528",
    "x-ai/grok-4": "grok-4",
    "x-ai/grok-2": "grok-2",
}

# Add aliases to MODEL_CAPABILITIES
for alias, base in _MODEL_ALIASES.items():
    if base in MODEL_CAPABILITIES:
        MODEL_CAPABILITIES[alias] = MODEL_CAPABILITIES[base]

# Task type to required capabilities mapping
# Aligned with _detect_task_type() in orchestrator_adapter.py
TASK_CAPABILITIES: Dict[str, List[ModelCapability]] = {
    # Code/Programming
    "code_generation": [ModelCapability.CODING, ModelCapability.INSTRUCTION_FOLLOWING],
    "debugging": [ModelCapability.CODING, ModelCapability.REASONING],
    # Math/Quantitative
    "math_problem": [ModelCapability.MATH, ModelCapability.REASONING],
    # Health/Medical - CRITICAL: Requires accuracy, factual, and reasoning
    "health_medical": [ModelCapability.FACTUAL, ModelCapability.REASONING, ModelCapability.QUALITY],
    # Science/Academic
    "science_research": [ModelCapability.ANALYSIS, ModelCapability.FACTUAL, ModelCapability.REASONING],
    # Legal
    "legal_analysis": [ModelCapability.REASONING, ModelCapability.FACTUAL, ModelCapability.ANALYSIS],
    # Finance/Business
    "financial_analysis": [ModelCapability.ANALYSIS, ModelCapability.MATH, ModelCapability.REASONING],
    # Research/Analysis
    "research_analysis": [ModelCapability.ANALYSIS, ModelCapability.FACTUAL, ModelCapability.REASONING],
    # Creative
    "creative_writing": [ModelCapability.CREATIVE, ModelCapability.QUALITY],
    # General
    "explanation": [ModelCapability.REASONING, ModelCapability.INSTRUCTION_FOLLOWING],
    "summarization": [ModelCapability.SUMMARIZATION, ModelCapability.FACTUAL],
    "factual_question": [ModelCapability.FACTUAL, ModelCapability.REASONING],
    "planning": [ModelCapability.REASONING, ModelCapability.ANALYSIS],
    "comparison": [ModelCapability.ANALYSIS, ModelCapability.REASONING],
    "fast_response": [ModelCapability.SPEED],
    "high_quality": [ModelCapability.QUALITY, ModelCapability.REASONING],
    "general": [ModelCapability.QUALITY, ModelCapability.REASONING],
}


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class ModelResponse:
    """A response from a single model."""
    model: str
    content: str
    latency_ms: float
    tokens_used: int
    quality_score: float = 0.0  # Assessed quality
    confidence: float = 0.0  # Model's stated confidence


@dataclass(slots=True)
class EliteResult:
    """Result of elite orchestration."""
    final_answer: str
    models_used: List[str]
    primary_model: str
    strategy_used: str
    total_latency_ms: float
    total_tokens: int
    quality_score: float
    confidence: float
    responses_generated: int
    synthesis_method: str
    performance_notes: List[str]
    consensus_score: float = 0.0


@dataclass(slots=True)
class TaskDecomposition:
    """Decomposed task for parallel execution."""
    task_id: str
    description: str
    required_capabilities: List[ModelCapability]
    best_model: str
    fallback_model: str
    depends_on: List[str]
    parallelizable: bool


# ==============================================================================
# Elite Orchestrator Implementation
# ==============================================================================

class EliteOrchestrator:
    """Elite orchestration engine for maximum performance.
    
    Strategies:
    1. SINGLE_BEST: Route to best model for task type
    2. PARALLEL_RACE: Run multiple models, take fastest good answer
    3. BEST_OF_N: Generate N responses, judge selects best
    4. QUALITY_WEIGHTED_FUSION: Combine responses weighted by model quality
    5. EXPERT_PANEL: Different models for different aspects, then synthesize
    6. CHALLENGE_AND_REFINE: Generate, challenge, improve iteratively
    7. DYNAMIC: Use real-time OpenRouter rankings for model selection
    
    Dynamic Mode:
        When use_openrouter_rankings=True, the orchestrator will:
        - Fetch real-time rankings from OpenRouter
        - Select models based on current performance data
        - Adapt to new models as they become available
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        performance_tracker: Optional[Any] = None,
        enable_learning: bool = True,
        *,
        use_openrouter_rankings: bool = False,
        db_session: Optional["Session"] = None,
    ) -> None:
        """Initialize elite orchestrator.
        
        Args:
            providers: LLM providers by name
            performance_tracker: Performance tracker for learning
            enable_learning: Whether to use historical performance data
            use_openrouter_rankings: Enable dynamic model selection from OpenRouter
            db_session: Database session for OpenRouter rankings
        """
        self.providers = providers
        self.performance_tracker = performance_tracker
        self.enable_learning = enable_learning
        self.use_openrouter_rankings = use_openrouter_rankings
        self.db_session = db_session
        
        # OpenRouter selector (lazy initialization)
        self._openrouter_selector: Optional["OpenRouterModelSelector"] = None
        
        # Build model-to-provider mapping
        self.model_providers = self._build_model_provider_map()
    
    def _get_openrouter_selector(self) -> Optional["OpenRouterModelSelector"]:
        """Get or create OpenRouter model selector."""
        if not self.use_openrouter_rankings:
            return None
        
        if self._openrouter_selector is None:
            from .openrouter_selector import OpenRouterModelSelector
            self._openrouter_selector = OpenRouterModelSelector(self.db_session)
        
        return self._openrouter_selector
    
    def _build_model_provider_map(self) -> Dict[str, str]:
        """Build mapping of model names to providers.
        
        Handles both formats:
        - Short names: "gpt-4o" -> "openai"
        - Full OpenRouter IDs: "openai/gpt-4o" -> "openai"
        """
        mapping = {}
        
        # Map of provider -> (short names, full OpenRouter IDs)
        provider_models = {
            "openai": [
                "gpt-4o", "gpt-4o-mini", "gpt-5", "o1", "o1-pro", "o3",
                "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-5", 
                "openai/o1-pro", "openai/o3",
            ],
            "anthropic": [
                "claude-sonnet-4", "claude-opus-4", "claude-3-5-sonnet-20241022", 
                "claude-3-5-haiku-20241022", "claude-sonnet-4-20250514",
                "anthropic/claude-sonnet-4", "anthropic/claude-opus-4",
                "anthropic/claude-3-5-sonnet-20241022",
            ],
            "gemini": [
                "gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-pro-preview",
                "google/gemini-2.5-pro", "google/gemini-2.5-flash",
                "google/gemini-3-pro-preview",
            ],
            "deepseek": [
                "deepseek-chat", "deepseek-v3.2", "deepseek-r1-0528",
                "deepseek/deepseek-chat", "deepseek/deepseek-v3.2",
                "deepseek/deepseek-r1-0528",
            ],
            "grok": [
                "grok-2", "grok-4",
                "x-ai/grok-2", "x-ai/grok-4",
            ],
        }
        
        for provider, models in provider_models.items():
            if provider in self.providers:
                for model in models:
                    mapping[model] = provider
        
        return mapping
    
    async def _get_dynamic_models(
        self,
        task_type: str,
        count: int = 5,
        domain: Optional[str] = None,
    ) -> Optional[List[str]]:
        """Get dynamically selected models from OpenRouter.
        
        Args:
            task_type: Type of task for model selection
            count: Number of models to select
            domain: Optional domain filter
            
        Returns:
            List of model IDs or None if unavailable
        """
        selector = self._get_openrouter_selector()
        if selector is None:
            return None
        
        try:
            from .openrouter_selector import SelectionStrategy
            
            # Map task type to strategy
            if task_type in ("fast_response", "quick-tasks"):
                strategy = SelectionStrategy.SPEED
            elif task_type in ("coding", "research", "analysis"):
                strategy = SelectionStrategy.QUALITY
            else:
                strategy = SelectionStrategy.BALANCED
            
            result = await selector.select_models(
                task_type=task_type,
                count=count,
                strategy=strategy,
                domain=domain,
            )
            
            return result.all_model_ids
            
        except Exception as e:
            logger.warning("Failed to get dynamic models: %s", e)
            return None
    
    async def _register_openrouter_models(self, model_ids: List[str]) -> None:
        """Register OpenRouter models with their providers.
        
        OpenRouter models use the format: provider/model-name
        This method maps them to the OpenRouter provider.
        
        Args:
            model_ids: List of OpenRouter model IDs
        """
        # Check if we have an OpenRouter provider
        if "openrouter" not in self.providers:
            # Try to create one
            try:
                from ..openrouter.gateway import OpenRouterGateway
                gateway = OpenRouterGateway()
                self.providers["openrouter"] = gateway
            except Exception as e:
                logger.debug("Could not create OpenRouter gateway: %s", e)
                return
        
        # Register all OpenRouter models
        for model_id in model_ids:
            if model_id not in self.model_providers:
                self.model_providers[model_id] = "openrouter"
                
                # Also add capability scores for new models
                if model_id not in MODEL_CAPABILITIES:
                    # Use default scores for unknown models
                    MODEL_CAPABILITIES[model_id] = self._get_default_capabilities(model_id)
    
    def _get_default_capabilities(self, model_id: str) -> Dict[ModelCapability, float]:
        """Get default capability scores for an unknown model.
        
        Uses model ID patterns to infer capabilities.
        """
        model_lower = model_id.lower()
        
        # Default scores
        caps = {
            ModelCapability.CODING: 0.7,
            ModelCapability.REASONING: 0.7,
            ModelCapability.MATH: 0.7,
            ModelCapability.CREATIVE: 0.7,
            ModelCapability.FACTUAL: 0.7,
            ModelCapability.ANALYSIS: 0.7,
            ModelCapability.SUMMARIZATION: 0.7,
            ModelCapability.INSTRUCTION_FOLLOWING: 0.7,
            ModelCapability.SPEED: 0.7,
            ModelCapability.QUALITY: 0.7,
        }
        
        # Boost scores based on model name patterns
        if "gpt-4" in model_lower or "claude" in model_lower:
            for cap in caps:
                caps[cap] += 0.15
        
        if "code" in model_lower or "coder" in model_lower:
            caps[ModelCapability.CODING] = 0.9
        
        if "mini" in model_lower or "small" in model_lower or "flash" in model_lower:
            caps[ModelCapability.SPEED] = 0.95
            caps[ModelCapability.QUALITY] -= 0.1
        
        if "pro" in model_lower or "opus" in model_lower or "large" in model_lower:
            caps[ModelCapability.QUALITY] = 0.9
            caps[ModelCapability.SPEED] = 0.6
        
        # Clamp values
        for cap in caps:
            caps[cap] = max(0.0, min(1.0, caps[cap]))
        
        return caps
    
    async def orchestrate(
        self,
        prompt: str,
        task_type: str = "general",
        *,
        available_models: Optional[List[str]] = None,
        strategy: str = "auto",
        quality_threshold: float = 0.7,
        max_parallel: int = 3,
        timeout_seconds: float = 60.0,
        domain_filter: Optional[str] = None,
    ) -> EliteResult:
        """
        Orchestrate models to produce the best possible response.
        
        Args:
            prompt: User prompt
            task_type: Type of task for capability matching
            available_models: Models to use (default: all available or dynamic from OpenRouter)
            strategy: Orchestration strategy (auto|dynamic|single_best|parallel_race|best_of_n|expert_panel)
            quality_threshold: Minimum acceptable quality
            max_parallel: Maximum parallel model calls
            timeout_seconds: Total timeout
            domain_filter: Optional domain filter for OpenRouter ranking selection
            
        Returns:
            EliteResult with optimized response
        """
        start_time = time.time()
        performance_notes: List[str] = []
        
        # Handle dynamic/auto strategy with OpenRouter
        if strategy in ("auto", "automatic", "dynamic") and self.use_openrouter_rankings:
            dynamic_models = await self._get_dynamic_models(
                task_type=task_type,
                count=max_parallel + 2,
                domain=domain_filter,
            )
            if dynamic_models:
                models = dynamic_models
                performance_notes.append(f"Dynamic models from OpenRouter: {len(models)}")
                # Also update model providers for new models
                await self._register_openrouter_models(models)
            else:
                # Fallback to static
                models = available_models or list(self.model_providers.keys())
                performance_notes.append("OpenRouter unavailable, using static models")
        else:
            # Get available models from static list
            models = available_models or list(self.model_providers.keys())
        
        models = [m for m in models if m in self.model_providers]
        
        if not models:
            raise ValueError("No available models for orchestration")
        
        performance_notes.append(f"Available models: {len(models)}")
        
        # Auto-select strategy based on task type
        if strategy in ("auto", "automatic", "dynamic"):
            strategy = self._select_strategy(task_type, len(models), prompt)
        
        performance_notes.append(f"Strategy: {strategy}")
        
        # Execute strategy
        if strategy == "single_best":
            result = await self._single_best_strategy(
                prompt, task_type, models, quality_threshold
            )
        elif strategy == "parallel_race":
            result = await self._parallel_race_strategy(
                prompt, task_type, models, max_parallel, timeout_seconds
            )
        elif strategy == "best_of_n":
            result = await self._best_of_n_strategy(
                prompt, task_type, models, n=min(3, len(models))
            )
        elif strategy == "quality_weighted_fusion":
            result = await self._quality_weighted_fusion_strategy(
                prompt, task_type, models, max_parallel
            )
        elif strategy == "expert_panel":
            result = await self._expert_panel_strategy(
                prompt, task_type, models
            )
        elif strategy == "challenge_and_refine":
            result = await self._challenge_and_refine_strategy(
                prompt, task_type, models, quality_threshold
            )
        else:
            # Default to single_best
            result = await self._single_best_strategy(
                prompt, task_type, models, quality_threshold
            )
        
        total_latency = (time.time() - start_time) * 1000
        result.total_latency_ms = total_latency
        result.strategy_used = strategy
        result.performance_notes = performance_notes
        
        # Log performance for learning
        if self.performance_tracker and self.enable_learning:
            self._log_performance(result, task_type)
        
        return result
    
    def _select_strategy(
        self,
        task_type: str,
        num_models: int,
        prompt: str,
    ) -> str:
        """Auto-select the best strategy for the task."""
        prompt_lower = prompt.lower()
        
        # Fast response needed
        if any(word in prompt_lower for word in ["quick", "fast", "brief", "simple"]):
            return "single_best"
        
        # Complex tasks benefit from multiple perspectives
        if task_type in ["research_analysis", "comparison", "planning"]:
            if num_models >= 3:
                return "expert_panel"
            return "quality_weighted_fusion"
        
        # Coding tasks - challenge and refine works well
        if task_type in ["code_generation", "debugging"]:
            return "challenge_and_refine"
        
        # High-quality requirement
        if any(word in prompt_lower for word in ["comprehensive", "detailed", "thorough"]):
            return "best_of_n"
        
        # Default: quality-weighted fusion for most tasks
        if num_models >= 2:
            return "quality_weighted_fusion"
        
        return "single_best"
    
    async def _single_best_strategy(
        self,
        prompt: str,
        task_type: str,
        models: List[str],
        quality_threshold: float,
    ) -> EliteResult:
        """Route to the single best model for this task type."""
        best_model = self._select_best_model(task_type, models)
        
        response = await self._call_model(best_model, prompt)
        
        return EliteResult(
            final_answer=response.content,
            models_used=[best_model],
            primary_model=best_model,
            strategy_used="single_best",
            total_latency_ms=response.latency_ms,
            total_tokens=response.tokens_used,
            quality_score=response.quality_score,
            confidence=0.85,
            responses_generated=1,
            synthesis_method="direct",
            performance_notes=[],
        )
    
    async def _parallel_race_strategy(
        self,
        prompt: str,
        task_type: str,
        models: List[str],
        max_parallel: int,
        timeout_seconds: float,
    ) -> EliteResult:
        """Race multiple models, return first good response."""
        # Select top models for this task
        selected = self._select_top_models(task_type, models, max_parallel)
        
        # Create tasks
        tasks = [
            self._call_model_with_timeout(model, prompt, timeout_seconds)
            for model in selected
        ]
        
        # Wait for first successful response
        responses: List[ModelResponse] = []
        for coro in asyncio.as_completed(tasks):
            try:
                response = await coro
                if response and response.content:
                    responses.append(response)
                    # Quick quality check
                    if response.quality_score >= 0.7:
                        break  # Good enough, stop waiting
            except Exception as e:
                logger.debug("Model failed in race: %s", e)
        
        if not responses:
            raise RuntimeError("All models failed in parallel race")
        
        # Use best response
        best = max(responses, key=lambda r: r.quality_score)
        
        return EliteResult(
            final_answer=best.content,
            models_used=[r.model for r in responses],
            primary_model=best.model,
            strategy_used="parallel_race",
            total_latency_ms=best.latency_ms,
            total_tokens=sum(r.tokens_used for r in responses),
            quality_score=best.quality_score,
            confidence=0.85,
            responses_generated=len(responses),
            synthesis_method="first_good",
            performance_notes=[],
        )
    
    async def _best_of_n_strategy(
        self,
        prompt: str,
        task_type: str,
        models: List[str],
        n: int = 3,
    ) -> EliteResult:
        """Generate N responses, judge selects best."""
        selected = self._select_top_models(task_type, models, n)
        
        # Generate all responses in parallel
        tasks = [self._call_model(model, prompt) for model in selected]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful responses
        valid_responses = [
            r for r in responses 
            if isinstance(r, ModelResponse) and r.content
        ]
        
        if not valid_responses:
            raise RuntimeError("All models failed in best-of-n")
        
        if len(valid_responses) == 1:
            best = valid_responses[0]
        else:
            # Use a judge model to select the best
            best = await self._judge_best_response(prompt, valid_responses)
        
        return EliteResult(
            final_answer=best.content,
            models_used=[r.model for r in valid_responses],
            primary_model=best.model,
            strategy_used="best_of_n",
            total_latency_ms=max(r.latency_ms for r in valid_responses),
            total_tokens=sum(r.tokens_used for r in valid_responses),
            quality_score=best.quality_score,
            confidence=0.90,  # Higher confidence from selection
            responses_generated=len(valid_responses),
            synthesis_method="judge_selection",
            performance_notes=[],
        )
    
    async def _quality_weighted_fusion_strategy(
        self,
        prompt: str,
        task_type: str,
        models: List[str],
        max_parallel: int,
    ) -> EliteResult:
        """Combine responses weighted by model quality scores."""
        selected = self._select_top_models(task_type, models, max_parallel)
        
        # Generate responses in parallel
        tasks = [self._call_model(model, prompt) for model in selected]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = [
            r for r in responses 
            if isinstance(r, ModelResponse) and r.content
        ]
        
        if not valid_responses:
            raise RuntimeError("All models failed in fusion")
        
        if len(valid_responses) == 1:
            fused = valid_responses[0].content
            primary = valid_responses[0].model
        else:
            # Synthesize responses with quality weighting
            fused, primary = await self._synthesize_responses(
                prompt, valid_responses, task_type
            )
        
        avg_quality = sum(r.quality_score for r in valid_responses) / len(valid_responses)
        
        return EliteResult(
            final_answer=fused,
            models_used=[r.model for r in valid_responses],
            primary_model=primary,
            strategy_used="quality_weighted_fusion",
            total_latency_ms=max(r.latency_ms for r in valid_responses),
            total_tokens=sum(r.tokens_used for r in valid_responses),
            quality_score=min(1.0, avg_quality + 0.1),  # Fusion bonus
            confidence=0.88,
            responses_generated=len(valid_responses),
            synthesis_method="weighted_fusion",
            performance_notes=[],
        )
    
    async def _expert_panel_strategy(
        self,
        prompt: str,
        task_type: str,
        models: List[str],
    ) -> EliteResult:
        """Different models handle different aspects, then synthesize."""
        # Define expert roles with scoped instructions
        # CRITICAL: Each role must answer directly without asking clarifying questions
        roles = [
            ("domain_expert", ModelCapability.ANALYSIS, "You are the Domain Expert. Provide accurate, concise facts and reasoning. Avoid speculation. Answer directly - do NOT ask clarifying questions."),
            ("devils_advocate", ModelCapability.REASONING, "You are the Devil's Advocate. Find flaws, risks, missing assumptions, and edge cases. Provide your critique directly - do NOT ask clarifying questions."),
            ("synthesizer", ModelCapability.QUALITY, "You are the Synthesizer. Combine all perspectives into a balanced final answer. Provide the answer directly - do NOT ask clarifying questions."),
        ]
        
        # Assign best model per role
        role_models: Dict[str, str] = {}
        for role, capability, _ in roles:
            best = self._select_model_for_capability(capability, models)
            if best:
                role_models[role] = best
        if not role_models:
            return await self._single_best_strategy(prompt, task_type, models, 0.7)
        
        # Round 1: independent role drafts
        tasks = []
        role_order: List[str] = []
        for role, _cap, instruction in roles:
            model = role_models.get(role)
            if not model:
                continue
            role_order.append(role)
            role_prompt = f"""{instruction}

Task: {prompt}
Respond in a concise, role-appropriate way."""
            tasks.append(self._call_model(model, role_prompt))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        role_responses: Dict[str, ModelResponse] = {}
        for i, resp in enumerate(responses):
            if isinstance(resp, ModelResponse) and resp.content:
                role_responses[role_order[i]] = resp
        
        if not role_responses:
            raise RuntimeError("All expert panel models failed")
        
        # Blackboard-style summary of first round
        board_summary_parts = []
        for role, resp in role_responses.items():
            board_summary_parts.append(f"{role}: {resp.content[:500]}")
        board_summary = "\n".join(board_summary_parts)
        
        # Round 2: refinement with shared context
        refined_responses: Dict[str, ModelResponse] = dict(role_responses)
        
        # Allow domain expert to refine using others' notes
        if "domain_expert" in role_models:
            model = role_models["domain_expert"]
            prior = role_responses.get("domain_expert")
            refine_prompt = f"""You are the Domain Expert refining your answer.

Original task: {prompt}
Your previous answer: {prior.content if prior else ''}
Other agents' findings:
{board_summary}

Improve accuracy and clarity. Keep it concise."""
            try:
                refined_responses["domain_expert"] = await self._call_model(model, refine_prompt)
            except Exception:
                pass
        
        # Devil's advocate adds critique with context
        if "devils_advocate" in role_models:
            model = role_models["devils_advocate"]
            critique_prompt = f"""You are the Devil's Advocate reviewing the group work.

Task: {prompt}
Peer findings:
{board_summary}

Provide the top issues, risks, or missing pieces. If none, state 'APPROVED'."""
            try:
                refined_responses["devils_advocate"] = await self._call_model(model, critique_prompt)
            except Exception:
                pass
        
        # Synthesizer creates final consensus
        synth_prompt = f"""You are the Synthesizer. Create a final, balanced answer.

CRITICAL: Answer the question directly. Do NOT ask clarifying questions. Do NOT suggest alternative criteria. Just provide the answer.

Task: {prompt}
Domain Expert contribution:
{refined_responses.get('domain_expert', role_responses.get('domain_expert')).content if refined_responses.get('domain_expert') or role_responses.get('domain_expert') else ''}

Devil's Advocate critique:
{refined_responses.get('devils_advocate', role_responses.get('devils_advocate')).content if refined_responses.get('devils_advocate') or role_responses.get('devils_advocate') else ''}

Rules:
- Integrate strengths from all inputs.
- Address or acknowledge critiques.
- Be concise and actionable.
- Do not invent facts.
- Do NOT ask questions - provide the answer."""
        synth_model = role_models.get("synthesizer") or list(role_models.values())[0]
        try:
            synth_response = await self._call_model(synth_model, synth_prompt)
        except Exception:
            synth_response = role_responses.get("domain_expert") or next(iter(role_responses.values()))
        
        final_answer = synth_response.content if isinstance(synth_response, ModelResponse) else str(synth_response)
        
        # Consensus score based on role outputs
        consensus_inputs = [
            final_answer,
            refined_responses.get("domain_expert", role_responses.get("domain_expert")).content if refined_responses.get("domain_expert") or role_responses.get("domain_expert") else "",
            refined_responses.get("devils_advocate", role_responses.get("devils_advocate")).content if refined_responses.get("devils_advocate") or role_responses.get("devils_advocate") else "",
        ]
        consensus_score = self._consensus_score(consensus_inputs)
        
        token_list = [r.tokens_used for r in refined_responses.values() if r]
        latency_list = [r.latency_ms for r in refined_responses.values() if r]
        total_tokens = sum(token_list) if token_list else 0
        total_latency = max(latency_list) if latency_list else 0.0
        
        return EliteResult(
            final_answer=final_answer,
            models_used=list(role_models.values()),
            primary_model=synth_model,
            strategy_used="expert_panel",
            total_latency_ms=total_latency,
            total_tokens=total_tokens,
            quality_score=min(1.0, (synth_response.quality_score if isinstance(synth_response, ModelResponse) else 0.9) + 0.05),
            confidence=0.90,
            responses_generated=len(refined_responses),
            synthesis_method="expert_synthesis_v2",
            performance_notes=[
                f"Roles: {list(role_models.keys())}",
                f"Consensus score: {consensus_score:.2f}",
            ],
            consensus_score=consensus_score,
        )
    
    async def _challenge_and_refine_strategy(
        self,
        prompt: str,
        task_type: str,
        models: List[str],
        quality_threshold: float,
    ) -> EliteResult:
        """Generate, challenge, and refine iteratively."""
        # Initial generation
        best_model = self._select_best_model(task_type, models)
        initial = await self._call_model(best_model, prompt)
        
        if not initial or not initial.content:
            raise RuntimeError("Initial generation failed")
        
        current_answer = initial.content
        iterations = 0
        max_iterations = 2
        
        # Select challenger model (different from generator)
        challenger_models = [m for m in models if m != best_model]
        challenger = self._select_best_model("reasoning", challenger_models) if challenger_models else best_model
        
        total_tokens = initial.tokens_used
        
        while iterations < max_iterations:
            # Challenge the answer
            challenge_prompt = f"""Review this answer critically:

Question: {prompt}

Answer: {current_answer}

Identify any errors, weaknesses, or areas for improvement. Be specific.
If the answer is perfect, say "APPROVED".
Otherwise, list specific issues that need fixing."""

            challenge = await self._call_model(challenger, challenge_prompt)
            total_tokens += challenge.tokens_used
            
            if not challenge or "APPROVED" in challenge.content.upper():
                break
            
            # Refine based on challenge
            refine_prompt = f"""Improve this answer based on the feedback below.

IMPORTANT: Your response should be the IMPROVED ANSWER ONLY - do NOT include:
- The feedback itself
- Meta-commentary about the improvements
- Self-critique or analysis of the answer
- Phrases like "Here is the improved answer" or "I have addressed..."

Just provide the clean, improved final answer that a user would read.

Original question: {prompt}

Current answer: {current_answer}

Feedback to address (incorporate silently, do not repeat): {challenge.content}

Provide the improved answer:"""

            refined = await self._call_model(best_model, refine_prompt)
            total_tokens += refined.tokens_used
            
            if refined and refined.content:
                current_answer = refined.content
            
            iterations += 1
        
        return EliteResult(
            final_answer=current_answer,
            models_used=[best_model, challenger],
            primary_model=best_model,
            strategy_used="challenge_and_refine",
            total_latency_ms=0,  # Will be set by caller
            total_tokens=total_tokens,
            quality_score=0.90,  # Refinement bonus
            confidence=0.88,
            responses_generated=iterations * 2 + 1,
            synthesis_method=f"iterative_refinement_{iterations}",
            performance_notes=[f"Refinement iterations: {iterations}"],
        )
    
    def _select_best_model(
        self,
        task_type: str,
        models: List[str],
    ) -> str:
        """Select the best model for a task type."""
        required_caps = TASK_CAPABILITIES.get(task_type, [ModelCapability.QUALITY])
        
        best_model = None
        best_score = -1
        
        for model in models:
            caps = MODEL_CAPABILITIES.get(model, {})
            
            # Calculate weighted score for required capabilities
            score = sum(caps.get(cap, 0.5) for cap in required_caps) / len(required_caps)
            
            # Adjust by historical performance if available
            if self.enable_learning and self.performance_tracker:
                snapshot = self.performance_tracker.snapshot()
                perf = snapshot.get(model)
                if perf and perf.calls > 10:
                    # Blend static capabilities with learned performance
                    historical = perf.success_rate * 0.3 + perf.avg_quality * 0.7
                    score = score * 0.6 + historical * 0.4
            
            if score > best_score:
                best_score = score
                best_model = model
        
        return best_model or models[0]
    
    def _select_top_models(
        self,
        task_type: str,
        models: List[str],
        n: int,
    ) -> List[str]:
        """Select top N models for a task type."""
        required_caps = TASK_CAPABILITIES.get(task_type, [ModelCapability.QUALITY])
        
        scored = []
        for model in models:
            caps = MODEL_CAPABILITIES.get(model, {})
            score = sum(caps.get(cap, 0.5) for cap in required_caps) / len(required_caps)
            scored.append((model, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [model for model, _ in scored[:n]]
    
    def _select_model_for_capability(
        self,
        capability: ModelCapability,
        models: List[str],
    ) -> Optional[str]:
        """Select best model for a specific capability."""
        best = None
        best_score = -1
        
        for model in models:
            caps = MODEL_CAPABILITIES.get(model, {})
            score = caps.get(capability, 0.0)
            if score > best_score:
                best_score = score
                best = model
        
        return best
    
    async def _call_model(
        self,
        model: str,
        prompt: str,
    ) -> ModelResponse:
        """Call a model and return structured response."""
        provider_name = self.model_providers.get(model)
        if not provider_name or provider_name not in self.providers:
            raise ValueError(f"No provider for model: {model}")
        
        provider = self.providers[provider_name]
        
        # Convert full OpenRouter ID to short model name for API call
        # e.g., "openai/gpt-4o" -> "gpt-4o"
        api_model = model.split("/")[-1] if "/" in model else model
        
        start = time.time()
        try:
            result = await provider.complete(prompt, model=api_model)
            latency = (time.time() - start) * 1000
            
            content = getattr(result, 'content', '') or getattr(result, 'text', '')
            tokens = getattr(result, 'tokens_used', 0)
            
            # Quick quality estimation
            quality = self._estimate_quality(content)
            
            return ModelResponse(
                model=model,
                content=content,
                latency_ms=latency,
                tokens_used=tokens,
                quality_score=quality,
                confidence=0.8,
            )
        except Exception as e:
            logger.error("Model %s failed: %s", model, e)
            raise
    
    async def _call_model_with_timeout(
        self,
        model: str,
        prompt: str,
        timeout: float,
    ) -> Optional[ModelResponse]:
        """Call model with timeout."""
        try:
            return await asyncio.wait_for(
                self._call_model(model, prompt),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Model %s timed out", model)
            return None
        except Exception as e:
            logger.warning("Model %s failed: %s", model, e)
            return None
    
    def _estimate_quality(self, content: str) -> float:
        """Quick quality estimation heuristic."""
        if not content:
            return 0.0
        
        score = 0.5
        
        # Length factor
        if len(content) > 100:
            score += 0.1
        if len(content) > 500:
            score += 0.1
        
        # Structure indicators
        if any(marker in content for marker in ['\n\n', '1.', '- ', '* ']):
            score += 0.1
        
        # Reasoning indicators
        reasoning_words = ['because', 'therefore', 'however', 'although', 'specifically']
        reasoning_count = sum(1 for w in reasoning_words if w in content.lower())
        score += min(0.15, reasoning_count * 0.05)
        
        return min(1.0, score)

    def _consensus_score(self, texts: List[str]) -> float:
        """Rough consensus score via pairwise Jaccard overlap."""
        cleaned = [self._normalize_text(t) for t in texts if t]
        if len(cleaned) < 2:
            return 1.0 if cleaned else 0.0
        pairs = 0
        overlaps = 0.0
        for i in range(len(cleaned)):
            for j in range(i + 1, len(cleaned)):
                pairs += 1
                overlaps += self._jaccard(cleaned[i], cleaned[j])
        return overlaps / pairs if pairs else 0.0

    def _normalize_text(self, text: str) -> List[str]:
        return [w for w in text.lower().split() if w.isalpha()]

    def _jaccard(self, a: List[str], b: List[str]) -> float:
        if not a or not b:
            return 0.0
        sa, sb = set(a), set(b)
        inter = len(sa & sb)
        union = len(sa | sb) or 1
        return inter / union
    
    async def _judge_best_response(
        self,
        prompt: str,
        responses: List[ModelResponse],
    ) -> ModelResponse:
        """Use a judge to select the best response."""
        if len(responses) == 1:
            return responses[0]
        
        # Build comparison prompt
        judge_prompt = f"""Compare these responses to the question:
Question: {prompt}

"""
        for i, resp in enumerate(responses, 1):
            judge_prompt += f"Response {i}:\n{resp.content[:1000]}\n\n"
        
        judge_prompt += """Which response is best? Consider:
- Accuracy and correctness
- Completeness
- Clarity
- Relevance

Reply with ONLY the number of the best response (e.g., "1" or "2")."""

        # Use best available model as judge
        judge_model = self._select_best_model("reasoning", list(self.model_providers.keys()))
        
        try:
            result = await self._call_model(judge_model, judge_prompt)
            # Parse selection
            for i, resp in enumerate(responses, 1):
                if str(i) in result.content[:10]:
                    resp.quality_score = min(1.0, resp.quality_score + 0.1)
                    return resp
        except Exception:
            pass
        
        # Fallback: return highest quality
        return max(responses, key=lambda r: r.quality_score)
    
    async def _synthesize_responses(
        self,
        prompt: str,
        responses: List[ModelResponse],
        task_type: str,
    ) -> Tuple[str, str]:
        """Synthesize multiple responses with quality weighting."""
        if len(responses) == 1:
            return responses[0].content, responses[0].model
        
        # Sort by quality
        sorted_responses = sorted(responses, key=lambda r: r.quality_score, reverse=True)
        
        # Use best model's response as base
        primary = sorted_responses[0]
        
        # If second response is close in quality, synthesize
        if len(sorted_responses) > 1:
            secondary = sorted_responses[1]
            
            if secondary.quality_score >= primary.quality_score * 0.9:
                # Synthesize
                synth_prompt = f"""Combine the best elements of these two responses:

CRITICAL: Provide the combined answer directly. Do NOT ask clarifying questions.

Question: {prompt}

Response A (primary):
{primary.content[:1500]}

Response B (secondary):
{secondary.content[:1500]}

Create a combined response that takes the best from both. Output only the final response. Do NOT ask questions."""

                synth_model = self._select_best_model("synthesis", list(self.model_providers.keys()))
                
                try:
                    result = await self._call_model(synth_model, synth_prompt)
                    return result.content, synth_model
                except Exception:
                    pass
        
        return primary.content, primary.model
    
    async def _synthesize_expert_panel(
        self,
        prompt: str,
        role_responses: Dict[str, ModelResponse],
    ) -> str:
        """Synthesize expert panel responses."""
        synth_prompt = f"""Synthesize these expert perspectives into one comprehensive answer:

CRITICAL: Provide the answer directly. Do NOT ask clarifying questions.

Question: {prompt}

"""
        for role, resp in role_responses.items():
            synth_prompt += f"{role.upper()} perspective:\n{resp.content[:1000]}\n\n"
        
        synth_prompt += """Create a unified, comprehensive answer that integrates all perspectives. 
Output only the final synthesized answer. Do NOT ask questions."""

        synth_model = self._select_best_model("synthesis", list(self.model_providers.keys()))
        
        try:
            result = await self._call_model(synth_model, synth_prompt)
            return result.content
        except Exception:
            # Fallback: use analyst response
            return role_responses.get("analyst", list(role_responses.values())[0]).content
    
    def _log_performance(self, result: EliteResult, task_type: str) -> None:
        """Log performance for learning.
        
        Strategy Memory (PR2): Now logs extended strategy information for
        learning which strategies work best for different query types.
        """
        if not self.performance_tracker:
            return
        
        try:
            # Determine model roles if available
            model_roles = {}
            if result.primary_model:
                model_roles[result.primary_model] = "primary"
            for i, model in enumerate(result.models_used):
                if model != result.primary_model:
                    model_roles[model] = f"secondary_{i}"
            
            # Determine query complexity from performance notes
            query_complexity = "medium"
            for note in result.performance_notes:
                if "complex" in note.lower():
                    query_complexity = "complex"
                    break
                elif "simple" in note.lower():
                    query_complexity = "simple"
                    break
            
            # Strategy Memory (PR2): Log extended strategy information
            self.performance_tracker.log_run(
                models_used=result.models_used,
                success_flag=result.quality_score >= 0.7,
                latency_ms=result.total_latency_ms,
                domain=task_type,
                # Strategy Memory (PR2) extended fields
                strategy=result.strategy_used,
                task_type=task_type,
                primary_model=result.primary_model,
                model_roles=model_roles,
                quality_score=result.quality_score,
                confidence=result.confidence,
                total_tokens=result.total_tokens,
                query_complexity=query_complexity,
                ensemble_size=result.responses_generated,
                performance_notes=result.performance_notes,
            )
        except Exception as e:
            logger.debug("Failed to log performance: %s", e)


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def elite_orchestrate(
    prompt: str,
    providers: Dict[str, Any],
    task_type: str = "general",
    strategy: str = "auto",
) -> EliteResult:
    """Convenience function for elite orchestration."""
    orchestrator = EliteOrchestrator(providers)
    return await orchestrator.orchestrate(prompt, task_type, strategy=strategy)


def get_best_model_for_task(task_type: str, available_models: List[str]) -> str:
    """Get the best model for a specific task type."""
    required_caps = TASK_CAPABILITIES.get(task_type, [ModelCapability.QUALITY])
    
    best = None
    best_score = -1
    
    for model in available_models:
        caps = MODEL_CAPABILITIES.get(model, {})
        score = sum(caps.get(cap, 0.5) for cap in required_caps) / len(required_caps)
        if score > best_score:
            best_score = score
            best = model
    
    return best or available_models[0] if available_models else "gpt-4o"

