"""OpenRouter Dynamic Model Selector.

Integrates real-time OpenRouter rankings into the orchestration system.
Replaces hardcoded model lists with dynamic selection based on:
- Real-time rankings from OpenRouter API
- Internal telemetry performance data
- Domain-specific requirements
- Cost/quality trade-offs

Usage:
    from .openrouter_selector import OpenRouterModelSelector
    
    selector = OpenRouterModelSelector(db_session)
    
    # Get best models for a task
    models = await selector.select_models_for_task(
        task_type="coding",
        domain="programming",
        count=3,
        strategy="quality",
    )
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from sqlalchemy.orm import Session

from ..openrouter.rankings import (
    RankingsAggregator,
    RankingDimension,
    TimeRange,
    RankedModel,
    RankingResult,
)
from ..openrouter.models import OpenRouterModel
from ..openrouter.client import OpenRouterClient, OpenRouterConfig

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Model selection strategies."""
    QUALITY = "quality"  # Prioritize highest quality models
    SPEED = "speed"  # Prioritize fastest models
    VALUE = "value"  # Best quality/cost ratio
    BALANCED = "balanced"  # Balance all factors
    AUTOMATIC = "automatic"  # Auto-detect best strategy


class TaskDomain(str, Enum):
    """Task domains for specialized model selection."""
    CODING = "coding"
    MATH = "math"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    GENERAL = "general"
    MULTIMODAL = "multimodal"
    TOOLS = "tools"


# Mapping from task types to ranking dimensions
# Enhanced Q1 2026: Added health_medical, science_research, legal, financial categories
TASK_TO_RANKING: Dict[str, List[RankingDimension]] = {
    # Code/Programming - needs reliable tool use
    "coding": [RankingDimension.TOOLS_AGENTS, RankingDimension.MOST_RELIABLE],
    "code_generation": [RankingDimension.TOOLS_AGENTS, RankingDimension.MOST_RELIABLE],
    "debugging": [RankingDimension.TOOLS_AGENTS, RankingDimension.MOST_RELIABLE],
    
    # Math/Quantitative - needs reliability and reasoning
    "math": [RankingDimension.MOST_RELIABLE, RankingDimension.BEST_VALUE],
    "math_problem": [RankingDimension.MOST_RELIABLE, RankingDimension.BEST_VALUE],
    
    # Health/Medical - CRITICAL: Prioritize reliability and quality over speed
    "health": [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
    "health_medical": [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
    "medical": [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
    
    # Science/Research - needs long context and reliability
    "research": [RankingDimension.LONG_CONTEXT, RankingDimension.MOST_RELIABLE],
    "science_research": [RankingDimension.LONG_CONTEXT, RankingDimension.MOST_RELIABLE],
    "science": [RankingDimension.LONG_CONTEXT, RankingDimension.MOST_RELIABLE],
    
    # Legal - needs reliability and long context for documents
    "legal": [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
    "legal_analysis": [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
    
    # Finance/Business - needs reliability and tools for calculations
    "financial": [RankingDimension.MOST_RELIABLE, RankingDimension.TOOLS_AGENTS],
    "financial_analysis": [RankingDimension.MOST_RELIABLE, RankingDimension.TOOLS_AGENTS],
    "business": [RankingDimension.MOST_RELIABLE, RankingDimension.BEST_VALUE],
    
    # Analysis - needs long context
    "analysis": [RankingDimension.LONG_CONTEXT, RankingDimension.BEST_VALUE],
    "research_analysis": [RankingDimension.LONG_CONTEXT, RankingDimension.MOST_RELIABLE],
    
    # Creative - trending models often have better creative outputs
    "creative": [RankingDimension.TRENDING, RankingDimension.BEST_VALUE],
    "creative_writing": [RankingDimension.TRENDING, RankingDimension.BEST_VALUE],
    
    # Multimodal/Vision
    "multimodal": [RankingDimension.MULTIMODAL, RankingDimension.MOST_RELIABLE],
    "vision": [RankingDimension.MULTIMODAL, RankingDimension.MOST_RELIABLE],
    
    # Tools/Agents
    "tools": [RankingDimension.TOOLS_AGENTS, RankingDimension.FASTEST],
    "agents": [RankingDimension.TOOLS_AGENTS, RankingDimension.MOST_RELIABLE],
    
    # General/Default
    "general": [RankingDimension.BEST_VALUE, RankingDimension.MOST_RELIABLE],
    "explanation": [RankingDimension.BEST_VALUE, RankingDimension.MOST_RELIABLE],
    "factual_question": [RankingDimension.MOST_RELIABLE, RankingDimension.BEST_VALUE],
    "summarization": [RankingDimension.LONG_CONTEXT, RankingDimension.FASTEST],
    "planning": [RankingDimension.MOST_RELIABLE, RankingDimension.TOOLS_AGENTS],
    "comparison": [RankingDimension.MOST_RELIABLE, RankingDimension.BEST_VALUE],
    
    # Speed-optimized
    "fast_response": [RankingDimension.FASTEST, RankingDimension.BEST_VALUE],
    "high_quality": [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
}

# Mapping from strategy to ranking dimensions
STRATEGY_TO_RANKING: Dict[SelectionStrategy, List[RankingDimension]] = {
    SelectionStrategy.QUALITY: [RankingDimension.MOST_RELIABLE, RankingDimension.LONG_CONTEXT],
    SelectionStrategy.SPEED: [RankingDimension.FASTEST, RankingDimension.BEST_VALUE],
    SelectionStrategy.VALUE: [RankingDimension.BEST_VALUE, RankingDimension.LOWEST_COST],
    SelectionStrategy.BALANCED: [RankingDimension.BEST_VALUE, RankingDimension.MOST_RELIABLE],
}

# =============================================================================
# QUALITY-BASED MODEL PREFERENCES (Q1 2026)
# =============================================================================
# These preferences override OpenRouter usage-based rankings for specific tasks
# where we need quality over popularity. Based on benchmark data and internal testing.

QUALITY_MODEL_PREFERENCES: Dict[str, List[str]] = {
    # ==========================================================================
    # UPDATED JANUARY 2026 - With Latest Flagship Models
    # ==========================================================================
    
    # Health/Medical: Prioritize models with proven accuracy on medical benchmarks
    # These models have shown best performance on MedQA, PubMedQA, clinical tasks
    "health_medical": [
        "anthropic/claude-opus-4.5",  # NEW: Best overall Anthropic
        "openai/gpt-5.2-pro",         # Latest OpenAI flagship
        "anthropic/claude-opus-4.1",  # Strong medical reasoning
        "google/gemini-3-pro-preview", # NEW: Latest Google
        "openai/o3-deep-research",    # NEW: Deep research for complex cases
        "anthropic/claude-sonnet-4.5", # Good balance speed/quality
        "openai/gpt-5.2",             # Strong baseline
        "google/gemini-2.5-pro",      # Proven track record
    ],
    
    # Math/Reasoning: Prioritize reasoning specialists
    "math_problem": [
        "openai/o3-deep-research",    # NEW: Best deep reasoning
        "openai/o3",                  # Excellent math reasoning
        "openai/o1-pro",              # Strong reasoning
        "anthropic/claude-opus-4.5",  # NEW: Top Anthropic
        "deepseek/deepseek-v3.2-speciale", # NEW: Enhanced DeepSeek
        "google/gemini-3-pro-preview", # NEW: Latest Google
        "openai/gpt-5.2-pro",         # Strong math
        "qwen/qwen3-max",             # NEW: Strong on math benchmarks
    ],
    
    # Code Generation: Prioritize coding specialists
    "code_generation": [
        "openai/gpt-5.2-codex",       # NEW: Best coding model
        "anthropic/claude-sonnet-4.5", # NEW: Excellent coding
        "mistralai/devstral-2512",    # NEW: Developer specialist
        "deepseek/deepseek-v3.2-speciale", # NEW: Top coder
        "x-ai/grok-code-fast-1",      # NEW: Fast code specialist
        "anthropic/claude-opus-4.5",  # Quality code
        "openai/gpt-5.2-pro",         # Strong overall
        "deepseek/deepseek-v3.2",     # Excellent coder
    ],
    
    # Research/Analysis: Prioritize long context and accuracy
    "research_analysis": [
        "openai/o3-deep-research",    # NEW: Purpose-built for research
        "google/gemini-3-pro-preview", # NEW: Best long context
        "anthropic/claude-opus-4.5",  # NEW: Excellent analysis
        "openai/gpt-5.2-pro",         # Strong research
        "anthropic/claude-sonnet-4.5", # Good balance
        "openai/o4-mini-deep-research", # NEW: Faster research option
        "google/gemini-2.5-pro",      # Proven
    ],
    
    # Legal: Prioritize accuracy and reasoning
    "legal_analysis": [
        "anthropic/claude-opus-4.5",  # NEW: Best legal reasoning
        "anthropic/claude-opus-4.1",  # Strong legal
        "openai/gpt-5.2-pro",         # Strong accuracy
        "google/gemini-3-pro-preview", # NEW: Good for documents
        "openai/o3-deep-research",    # Complex reasoning
        "mistralai/mistral-large-2512", # NEW: Latest Mistral
    ],
    
    # Financial: Prioritize accuracy and calculation
    "financial_analysis": [
        "openai/gpt-5.2-pro",         # Strong quantitative
        "openai/o3-deep-research",    # Complex calculations
        "anthropic/claude-opus-4.5",  # NEW: Best analysis
        "google/gemini-3-pro-preview", # NEW: Strong on numbers
        "deepseek/deepseek-v3.2-speciale", # Strong reasoning
        "qwen/qwen3-max",             # NEW: Strong math
    ],
    
    # Science: Prioritize accuracy and knowledge
    "science_research": [
        "google/gemini-3-pro-preview", # NEW: Latest scientific knowledge
        "openai/o3-deep-research",    # NEW: Deep scientific analysis
        "anthropic/claude-opus-4.5",  # NEW: Excellent reasoning
        "openai/gpt-5.2-pro",         # Excellent accuracy
        "anthropic/claude-opus-4.1",  # Strong scientific
        "google/gemini-2.5-pro",      # Proven
    ],
    
    # Creative: Prioritize creativity and quality
    "creative_writing": [
        "anthropic/claude-opus-4.5",  # NEW: Most creative
        "anthropic/claude-sonnet-4.5", # NEW: Good creative
        "openai/gpt-5.2",             # Strong creative
        "anthropic/claude-3.7-sonnet", # NEW: Good creative flow
        "google/gemini-3-pro-preview", # NEW: Good variety
        "meta-llama/llama-4-maverick", # NEW: Creative experiments
    ],
    
    # High Quality (explicit quality mode): Use best available
    "high_quality": [
        "anthropic/claude-opus-4.5",  # NEW: Best overall Anthropic
        "openai/gpt-5.2-pro",         # Best overall OpenAI
        "openai/o3-deep-research",    # NEW: Deep reasoning
        "google/gemini-3-pro-preview", # NEW: Latest Google
        "openai/gpt-5-pro",       # Quality focused
    ],
}


@dataclass
class SelectedModel:
    """A model selected for orchestration."""
    model_id: str
    model_name: str
    provider: str
    rank: int
    score: float
    
    # Capabilities
    supports_tools: bool = False
    supports_vision: bool = False
    context_length: int = 0
    
    # Pricing (USD per 1M tokens)
    price_prompt: float = 0.0
    price_completion: float = 0.0
    
    # Selection metadata
    selection_reason: str = ""
    ranking_dimension: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "provider": self.provider,
            "rank": self.rank,
            "score": self.score,
            "supports_tools": self.supports_tools,
            "supports_vision": self.supports_vision,
            "context_length": self.context_length,
            "price_prompt": self.price_prompt,
            "price_completion": self.price_completion,
            "selection_reason": self.selection_reason,
            "ranking_dimension": self.ranking_dimension,
        }


@dataclass
class SelectionResult:
    """Result of model selection."""
    primary_model: SelectedModel
    secondary_models: List[SelectedModel]
    all_candidates: List[SelectedModel]
    
    # Selection metadata
    strategy: SelectionStrategy
    task_type: str
    domain: str
    reasoning: str
    
    # Timestamps
    selected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def all_model_ids(self) -> List[str]:
        """Get all selected model IDs."""
        ids = [self.primary_model.model_id]
        ids.extend(m.model_id for m in self.secondary_models)
        return ids
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_model": self.primary_model.to_dict(),
            "secondary_models": [m.to_dict() for m in self.secondary_models],
            "strategy": self.strategy.value,
            "task_type": self.task_type,
            "domain": self.domain,
            "reasoning": self.reasoning,
            "selected_at": self.selected_at.isoformat(),
        }


class OpenRouterModelSelector:
    """Dynamic model selector using OpenRouter rankings.
    
    Provides real-time model selection based on:
    - Rankings from internal telemetry
    - Task/domain requirements
    - Cost constraints
    - Performance history
    
    Usage:
        selector = OpenRouterModelSelector(db_session)
        
        # Select models for coding task
        result = await selector.select_models(
            task_type="coding",
            count=3,
            strategy=SelectionStrategy.QUALITY,
        )
        
        # Get models for orchestration roles
        role_models = await selector.select_for_roles(
            roles=["primary", "validator", "fallback"],
            task_type="research",
        )
    """
    
    # Cache for rankings (TTL: 5 minutes)
    _rankings_cache: Dict[str, Tuple[RankingResult, datetime]] = {}
    _cache_ttl_seconds = 300
    
    def __init__(
        self,
        db_session: Optional[Session] = None,
        openrouter_client: Optional[OpenRouterClient] = None,
    ):
        """Initialize selector.
        
        Args:
            db_session: SQLAlchemy session for rankings aggregator
            openrouter_client: Optional OpenRouter client for direct API access
        """
        self.db = db_session
        self.client = openrouter_client
        self._aggregator: Optional[RankingsAggregator] = None
    
    def _get_aggregator(self) -> Optional[RankingsAggregator]:
        """Get or create rankings aggregator."""
        if self.db is None:
            return None
        if self._aggregator is None:
            self._aggregator = RankingsAggregator(self.db)
        return self._aggregator
    
    async def select_models(
        self,
        task_type: str = "general",
        *,
        count: int = 3,
        strategy: SelectionStrategy = SelectionStrategy.AUTOMATIC,
        domain: Optional[str] = None,
        max_price_per_1m: Optional[float] = None,
        min_context_length: Optional[int] = None,
        require_tools: bool = False,
        require_vision: bool = False,
        exclude_models: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        use_quality_preferences: bool = True,  # Q1 2026: Enable quality-based selection
    ) -> SelectionResult:
        """Select models based on task type and requirements.
        
        Args:
            task_type: Type of task (coding, research, creative, etc.)
            count: Number of models to select
            strategy: Selection strategy
            domain: Optional specific domain
            max_price_per_1m: Maximum price per 1M tokens
            min_context_length: Minimum context window
            require_tools: Require tool/function calling support
            require_vision: Require vision/image support
            exclude_models: Models to exclude
            tenant_id: Tenant ID for tenant-specific rankings
            use_quality_preferences: Use quality-based model preferences (default: True)
            
        Returns:
            SelectionResult with selected models
            
        Q1 2026 Enhancement:
            When use_quality_preferences=True, models from QUALITY_MODEL_PREFERENCES
            are prioritized for critical task types (health_medical, math_problem, etc.)
            This ensures quality over popularity for tasks where accuracy matters.
        """
        # Auto-detect strategy based on task
        if strategy == SelectionStrategy.AUTOMATIC:
            strategy = self._detect_strategy(task_type)
        
        # Determine domain
        effective_domain = domain or self._task_to_domain(task_type)
        
        # Q1 2026: Check if this task type has quality preferences
        quality_preferred_models = []
        if use_quality_preferences and task_type in QUALITY_MODEL_PREFERENCES:
            quality_preferred_models = QUALITY_MODEL_PREFERENCES[task_type]
            logger.info(
                "Using quality preferences for task=%s: %s",
                task_type, quality_preferred_models[:3]
            )
        
        # Get ranking dimensions for task and strategy
        task_dimensions = TASK_TO_RANKING.get(task_type, TASK_TO_RANKING["general"])
        strategy_dimensions = STRATEGY_TO_RANKING.get(strategy, [])
        
        # Combine and deduplicate
        dimensions = list(dict.fromkeys(task_dimensions + strategy_dimensions))
        
        # Build filters
        filters: Dict[str, Any] = {}
        if max_price_per_1m:
            filters["max_price_per_1m"] = max_price_per_1m
        if min_context_length:
            filters["min_context"] = min_context_length
        if require_tools:
            filters["supports_tools"] = True
        if require_vision:
            filters["multimodal_input"] = True
        
        # Fetch rankings from multiple dimensions
        all_candidates: Dict[str, SelectedModel] = {}
        reasoning_parts: List[str] = []
        
        aggregator = self._get_aggregator()
        
        for dimension in dimensions[:3]:  # Limit to top 3 dimensions
            try:
                if aggregator:
                    ranking = await self._get_ranking_cached(
                        dimension=dimension,
                        filters=filters,
                        tenant_id=tenant_id,
                    )
                else:
                    # Fallback to direct API if no DB
                    ranking = await self._fetch_ranking_from_api(dimension)
                
                if ranking and ranking.models:
                    for ranked_model in ranking.models[:count * 2]:
                        model_id = ranked_model.model.id
                        
                        # Skip excluded models
                        if exclude_models and model_id in exclude_models:
                            continue
                        
                        # Create or update candidate
                        if model_id not in all_candidates:
                            all_candidates[model_id] = self._ranked_to_selected(
                                ranked_model, dimension.value
                            )
                        else:
                            # Boost score for models appearing in multiple rankings
                            all_candidates[model_id].score += ranked_model.score * 0.5
                    
                    reasoning_parts.append(f"{dimension.value}: {len(ranking.models)} candidates")
                    
            except Exception as e:
                logger.warning("Failed to fetch %s ranking: %s", dimension.value, e)
        
        # Q1 2026: Apply quality preference boosts
        if quality_preferred_models:
            for idx, preferred_model in enumerate(quality_preferred_models):
                if preferred_model in all_candidates:
                    # Boost score based on position in preference list
                    # Higher position = bigger boost
                    boost = 100.0 - (idx * 10)  # 100, 90, 80, 70, ...
                    all_candidates[preferred_model].score += boost
                    all_candidates[preferred_model].selection_reason = f"quality_preferred_rank_{idx+1}"
                    logger.debug(
                        "Boosted %s by %.1f (quality preference #%d)",
                        preferred_model, boost, idx + 1
                    )
            reasoning_parts.append(f"quality_preferences: {len(quality_preferred_models)} preferred models")
        
        # If no candidates, use fallback
        if not all_candidates:
            return self._fallback_selection(task_type, count, strategy, effective_domain)
        
        # Sort by score
        sorted_candidates = sorted(
            all_candidates.values(),
            key=lambda m: m.score,
            reverse=True,
        )
        
        # Select top models
        primary = sorted_candidates[0]
        secondary = sorted_candidates[1:count] if len(sorted_candidates) > 1 else []
        
        # Build reasoning
        reasoning = f"Strategy: {strategy.value}; Task: {task_type}; " + "; ".join(reasoning_parts)
        
        return SelectionResult(
            primary_model=primary,
            secondary_models=secondary,
            all_candidates=sorted_candidates[:count * 2],
            strategy=strategy,
            task_type=task_type,
            domain=effective_domain,
            reasoning=reasoning,
        )
    
    async def select_for_roles(
        self,
        roles: List[str],
        task_type: str = "general",
        *,
        strategy: SelectionStrategy = SelectionStrategy.AUTOMATIC,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, SelectedModel]:
        """Select models for specific orchestration roles.
        
        Args:
            roles: List of role names (e.g., ["primary", "validator", "fallback"])
            task_type: Type of task
            strategy: Selection strategy
            tenant_id: Tenant ID
            
        Returns:
            Dictionary mapping role names to selected models
        """
        # Get more candidates than roles
        result = await self.select_models(
            task_type=task_type,
            count=len(roles) + 2,
            strategy=strategy,
            tenant_id=tenant_id,
        )
        
        role_models: Dict[str, SelectedModel] = {}
        available = [result.primary_model] + result.secondary_models
        
        # Role-specific selection logic
        role_priorities = {
            "primary": {"quality": 1.0, "speed": 0.5},
            "coordinator": {"quality": 1.0, "speed": 0.5},
            "validator": {"quality": 0.9, "speed": 0.7},
            "challenger": {"quality": 0.8, "speed": 0.8},
            "fallback": {"speed": 1.0, "cost": 1.0},
            "synthesizer": {"quality": 1.0, "context": 0.8},
        }
        
        used_models: set = set()
        
        for role in roles:
            priorities = role_priorities.get(role, {"quality": 0.8})
            
            # Score each available model for this role
            best_model = None
            best_score = -1
            
            for model in available:
                if model.model_id in used_models:
                    continue
                
                role_score = model.score
                
                # Adjust for role priorities
                if "speed" in priorities and model.price_prompt < 1.0:
                    role_score *= 1.0 + priorities["speed"] * 0.2
                if "cost" in priorities:
                    cost_factor = 1.0 / (1.0 + model.price_prompt)
                    role_score *= 1.0 + priorities["cost"] * cost_factor * 0.3
                if "context" in priorities and model.context_length > 100000:
                    role_score *= 1.0 + priorities["context"] * 0.2
                
                if role_score > best_score:
                    best_score = role_score
                    best_model = model
            
            if best_model:
                role_models[role] = best_model
                used_models.add(best_model.model_id)
                best_model.selection_reason = f"Selected for role: {role}"
            else:
                # Fallback: use primary model
                role_models[role] = result.primary_model
        
        return role_models
    
    async def get_model_capabilities(
        self,
        model_id: str,
    ) -> Dict[str, Any]:
        """Get capabilities for a specific model.
        
        Args:
            model_id: OpenRouter model ID
            
        Returns:
            Dictionary of model capabilities
        """
        if self.db:
            model = self.db.query(OpenRouterModel).filter(
                OpenRouterModel.id == model_id
            ).first()
            
            if model:
                return {
                    "id": model.id,
                    "name": model.name,
                    "context_length": model.context_length,
                    "supports_tools": model.supports_tools,
                    "supports_structured": model.supports_structured,
                    "multimodal_input": model.multimodal_input,
                    "multimodal_output": model.multimodal_output,
                    "price_prompt": float(model.price_per_1m_prompt or 0),
                    "price_completion": float(model.price_per_1m_completion or 0),
                }
        
        # Fallback: fetch from API
        if self.client:
            try:
                model_data = await self.client.get_model(model_id)
                return model_data or {}
            except Exception:
                pass
        
        return {}
    
    async def _get_ranking_cached(
        self,
        dimension: RankingDimension,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[RankingResult]:
        """Get ranking with caching."""
        cache_key = f"{dimension.value}:{hash(str(filters))}:{tenant_id}"
        
        # Check cache
        if cache_key in self._rankings_cache:
            result, cached_at = self._rankings_cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age < self._cache_ttl_seconds:
                return result
        
        # Fetch fresh ranking
        aggregator = self._get_aggregator()
        if not aggregator:
            return None
        
        result = aggregator.get_ranking(
            dimension=dimension,
            time_range=TimeRange.LAST_7D,
            limit=20,
            filters=filters,
            tenant_id=tenant_id,
        )
        
        # Cache result
        self._rankings_cache[cache_key] = (result, datetime.now(timezone.utc))
        
        return result
    
    async def _fetch_ranking_from_api(
        self,
        dimension: RankingDimension,
    ) -> Optional[RankingResult]:
        """Fetch ranking directly from OpenRouter API (fallback)."""
        if not self.client:
            return None
        
        try:
            # Map dimension to API endpoint
            # This is a simplified version; real implementation would
            # fetch from OpenRouter's endpoints
            models = await self.client.list_models()
            
            if not models:
                return None
            
            # Create mock ranking from model list
            ranked_models: List[RankedModel] = []
            for i, model_data in enumerate(models[:20]):
                model = OpenRouterModel.from_api_response(model_data)
                ranked_models.append(RankedModel(
                    model=model,
                    rank=i + 1,
                    score=1.0 - (i * 0.05),
                    metrics={},
                ))
            
            return RankingResult(
                dimension=dimension,
                time_range=TimeRange.LAST_7D,
                models=ranked_models,
            )
            
        except Exception as e:
            logger.error("Failed to fetch from API: %s", e)
            return None
    
    def _ranked_to_selected(
        self,
        ranked: RankedModel,
        dimension: str,
    ) -> SelectedModel:
        """Convert RankedModel to SelectedModel."""
        model = ranked.model
        
        # Extract provider from model ID
        provider = model.id.split("/")[0] if "/" in model.id else "unknown"
        
        return SelectedModel(
            model_id=model.id,
            model_name=model.name,
            provider=provider,
            rank=ranked.rank,
            score=ranked.score,
            supports_tools=model.supports_tools or False,
            supports_vision=model.multimodal_input or False,
            context_length=model.context_length or 0,
            price_prompt=float(model.price_per_1m_prompt or 0),
            price_completion=float(model.price_per_1m_completion or 0),
            ranking_dimension=dimension,
            selection_reason=f"Ranked #{ranked.rank} in {dimension}",
        )
    
    def _detect_strategy(self, task_type: str) -> SelectionStrategy:
        """Auto-detect best strategy for task type."""
        if task_type in ["fast_response", "quick-tasks"]:
            return SelectionStrategy.SPEED
        elif task_type in ["coding", "research", "analysis"]:
            return SelectionStrategy.QUALITY
        elif task_type in ["general", "summarization"]:
            return SelectionStrategy.VALUE
        else:
            return SelectionStrategy.BALANCED
    
    def _task_to_domain(self, task_type: str) -> str:
        """Map task type to domain."""
        mapping = {
            "code_generation": "coding",
            "debugging": "coding",
            "math_problem": "math",
            "research_analysis": "research",
            "creative_writing": "creative",
            "explanation": "general",
            "summarization": "general",
            "factual_question": "research",
            "planning": "analysis",
            "comparison": "analysis",
            "fast_response": "general",
            "high_quality": "research",
        }
        return mapping.get(task_type, task_type)
    
    def _fallback_selection(
        self,
        task_type: str,
        count: int,
        strategy: SelectionStrategy,
        domain: str,
    ) -> SelectionResult:
        """Fallback selection when rankings are unavailable.
        
        Uses dynamic catalog if available, otherwise minimal bootstrap.
        """
        fallback_models: List[SelectedModel] = []
        
        # Try dynamic catalog first
        try:
            from ..openrouter.dynamic_catalog import get_dynamic_catalog
            catalog = get_dynamic_catalog()
            
            # Get high-accuracy models from catalog
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop:
                # Already in async context
                pass
            else:
                # Sync fallback - use bootstrap
                raise RuntimeError("Not in async context")
            
        except Exception:
            pass
        
        # Bootstrap fallback models (updated with current model IDs)
        if not fallback_models:
            fallback_models = [
                SelectedModel(
                    model_id="openai/gpt-4o",
                    model_name="GPT-4o",
                    provider="openai",
                    rank=1,
                    score=0.95,
                    supports_tools=True,
                    supports_vision=True,
                    context_length=128000,
                    price_prompt=2.50,
                    price_completion=10.00,
                    selection_reason="Bootstrap fallback: Primary quality model",
                ),
                SelectedModel(
                    model_id="anthropic/claude-sonnet-4",
                    model_name="Claude Sonnet 4",
                    provider="anthropic",
                    rank=2,
                    score=0.93,
                    supports_tools=True,
                    supports_vision=True,
                    context_length=200000,
                    price_prompt=3.00,
                    price_completion=15.00,
                    selection_reason="Bootstrap fallback: Secondary quality model",
                ),
                SelectedModel(
                    model_id="openai/gpt-4o-mini",
                    model_name="GPT-4o Mini",
                    provider="openai",
                    rank=3,
                    score=0.85,
                    supports_tools=True,
                    supports_vision=True,
                    context_length=128000,
                    price_prompt=0.15,
                    price_completion=0.60,
                    selection_reason="Bootstrap fallback: Fast/cheap model",
                ),
                SelectedModel(
                    model_id="google/gemini-2.5-pro-preview",
                    model_name="Gemini 2.5 Pro",
                    provider="google",
                    rank=4,
                    score=0.88,
                    supports_tools=True,
                    supports_vision=True,
                    context_length=1000000,
                    price_prompt=1.25,
                    price_completion=5.00,
                    selection_reason="Bootstrap fallback: Long-context model",
                ),
            ]
        
        return SelectionResult(
            primary_model=fallback_models[0],
            secondary_models=fallback_models[1:count],
            all_candidates=fallback_models,
            strategy=strategy,
            task_type=task_type,
            domain=domain,
            reasoning="Bootstrap fallback: Rankings unavailable, using default models (updated)",
        )


# Global selector instance
_selector: Optional[OpenRouterModelSelector] = None


def get_openrouter_selector(
    db_session: Optional[Session] = None,
) -> OpenRouterModelSelector:
    """Get or create the global selector instance."""
    global _selector
    if _selector is None or db_session is not None:
        _selector = OpenRouterModelSelector(db_session)
    return _selector


async def select_models_dynamic(
    task_type: str,
    count: int = 3,
    strategy: str = "automatic",
    db_session: Optional[Session] = None,
) -> List[str]:
    """Convenience function for dynamic model selection.
    
    Args:
        task_type: Type of task
        count: Number of models to select
        strategy: Selection strategy name
        db_session: Optional database session
        
    Returns:
        List of model IDs
    """
    selector = get_openrouter_selector(db_session)
    
    strategy_enum = SelectionStrategy(strategy.lower())
    result = await selector.select_models(
        task_type=task_type,
        count=count,
        strategy=strategy_enum,
    )
    
    return result.all_model_ids

