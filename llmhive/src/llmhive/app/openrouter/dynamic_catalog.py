"""Dynamic Model Catalog for OpenRouter Integration.

This module provides a 100% dynamic model catalog that:
- Fetches all models from OpenRouter API
- Detects model families automatically
- Derives capabilities from API metadata
- Provides dynamic high-accuracy model selection
- Maintains only a minimal bootstrap fallback

Usage:
    from llmhive.app.openrouter.dynamic_catalog import get_dynamic_catalog
    
    catalog = get_dynamic_catalog()
    
    # Get best models for high accuracy tasks
    models = await catalog.get_high_accuracy_models(
        task_type="coding",
        max_count=5,
        max_cost_per_1m=10.0,
    )
    
    # Get models by family
    gpt5_models = await catalog.get_models_by_family("gpt-5.2")
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Bootstrap Fallback (Minimal - only used if API AND DB unavailable)
# =============================================================================

BOOTSTRAP_FALLBACK_MODELS = [
    {
        "id": "openai/gpt-4o",
        "name": "GPT-4o",
        "family": "gpt-4o",
        "author": "openai",
        "context_length": 128000,
        "supports_tools": True,
        "supports_reasoning": False,
        "supports_structured": True,
        "multimodal_input": True,
        "price_per_1m_prompt": 2.50,
        "price_per_1m_completion": 10.00,
        "tier": 1,
    },
    {
        "id": "anthropic/claude-sonnet-4",
        "name": "Claude Sonnet 4",
        "family": "claude-4",
        "author": "anthropic",
        "context_length": 200000,
        "supports_tools": True,
        "supports_reasoning": True,
        "supports_structured": True,
        "multimodal_input": True,
        "price_per_1m_prompt": 3.00,
        "price_per_1m_completion": 15.00,
        "tier": 1,
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "family": "gpt-4o-mini",
        "author": "openai",
        "context_length": 128000,
        "supports_tools": True,
        "supports_reasoning": False,
        "supports_structured": True,
        "multimodal_input": True,
        "price_per_1m_prompt": 0.15,
        "price_per_1m_completion": 0.60,
        "tier": 3,
    },
    {
        "id": "google/gemini-2.5-pro-preview",
        "name": "Gemini 2.5 Pro",
        "family": "gemini-2.5",
        "author": "google",
        "context_length": 1000000,
        "supports_tools": True,
        "supports_reasoning": True,
        "supports_structured": True,
        "multimodal_input": True,
        "price_per_1m_prompt": 1.25,
        "price_per_1m_completion": 10.00,
        "tier": 1,
    },
    {
        "id": "google/gemini-3.1-pro-preview",
        "name": "Gemini 3.1 Pro",
        "family": "gemini-3.1",
        "author": "google",
        "context_length": 1050000,
        "supports_tools": True,
        "supports_reasoning": True,
        "supports_structured": True,
        "multimodal_input": True,
        "price_per_1m_prompt": 2.00,
        "price_per_1m_completion": 12.00,
        "tier": 1,
    },
    {
        "id": "google/gemini-3-pro-preview",
        "name": "Gemini 3 Pro",
        "family": "gemini-3",
        "author": "google",
        "context_length": 1000000,
        "supports_tools": True,
        "supports_reasoning": True,
        "supports_structured": True,
        "multimodal_input": True,
        "price_per_1m_prompt": 1.25,
        "price_per_1m_completion": 5.00,
        "tier": 1,
    },
]


# =============================================================================
# Model Family Patterns
# =============================================================================

# Ordered by priority (more specific patterns first)
FAMILY_PATTERNS: List[Tuple[str, str]] = [
    # OpenAI newest
    ("gpt-5.2", r"openai/gpt-5\.2"),
    ("o3-pro", r"openai/o3-pro"),
    ("o3", r"openai/o3[^-]"),
    ("o1-pro", r"openai/o1-pro"),
    ("o1", r"openai/o1[^-]"),
    ("gpt-4o-mini", r"openai/gpt-4o-mini"),
    ("gpt-4o", r"openai/gpt-4o"),
    ("gpt-4-turbo", r"openai/gpt-4-turbo"),
    ("gpt-4", r"openai/gpt-4[^o]"),
    ("gpt-oss", r"openai/gpt-oss"),
    
    # Anthropic
    ("claude-4.5", r"anthropic/claude-.*-4\.5"),
    ("claude-4", r"anthropic/claude-.*-4(?!\.)"),
    ("claude-3.5", r"anthropic/claude-.*-3\.5"),
    ("claude-3", r"anthropic/claude-.*-3(?!\.)"),
    
    # Google
    ("gemini-3.1", r"google/gemini-3\.1"),
    ("gemini-3", r"google/gemini-3(?!\.)"),
    ("gemini-2.5", r"google/gemini-2\.5"),
    ("gemini-2", r"google/gemini-2(?!\.)"),
    ("gemini-1.5", r"google/gemini-1\.5"),
    
    # xAI
    ("grok-4", r"x-ai/grok-4"),
    ("grok-3", r"x-ai/grok-3"),
    ("grok-2", r"x-ai/grok-2"),
    ("grok-code", r"x-ai/grok-code"),
    
    # Meta
    ("llama-4", r"meta-llama/llama-4"),
    ("llama-3.3", r"meta-llama/llama-3\.3"),
    ("llama-3.2", r"meta-llama/llama-3\.2"),
    ("llama-3.1", r"meta-llama/llama-3\.1"),
    
    # DeepSeek
    ("deepseek-v3", r"deepseek/deepseek-v3"),
    ("deepseek-r1", r"deepseek/deepseek-r1"),
    ("deepseek-reasoner", r"deepseek/deepseek-reasoner"),
    ("deepseek-chat", r"deepseek/deepseek-chat"),
    
    # Minimax
    ("minimax-m2", r"minimax/minimax-m2"),
    
    # Mistral
    ("mistral-large", r"mistralai/mistral-large"),
    ("mixtral", r"mistralai/mixtral"),
    ("mistral-small", r"mistralai/mistral-small"),
]


# Author logo mapping
AUTHOR_LOGOS: Dict[str, str] = {
    "openai": "https://cdn.openrouter.ai/logos/openai.svg",
    "anthropic": "https://cdn.openrouter.ai/logos/anthropic.svg",
    "google": "https://cdn.openrouter.ai/logos/google.svg",
    "x-ai": "https://cdn.openrouter.ai/logos/xai.svg",
    "meta-llama": "https://cdn.openrouter.ai/logos/meta.svg",
    "deepseek": "https://cdn.openrouter.ai/logos/deepseek.svg",
    "mistralai": "https://cdn.openrouter.ai/logos/mistral.svg",
    "minimax": "https://cdn.openrouter.ai/logos/minimax.svg",
    "cohere": "https://cdn.openrouter.ai/logos/cohere.svg",
    "perplexity": "https://cdn.openrouter.ai/logos/perplexity.svg",
}


# Known high-accuracy model families (frontier models)
HIGH_ACCURACY_FAMILIES: Set[str] = {
    "gpt-5.2", "o3-pro", "o3", "o1-pro", "o1", "gpt-4o",
    "claude-4.5", "claude-4",
    "gemini-3.1", "gemini-3", "gemini-2.5",
    "grok-4", "grok-3",
    "llama-4",
    "deepseek-v3", "deepseek-r1",
    "minimax-m2",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DynamicModel:
    """Model with dynamically derived capabilities."""
    id: str
    name: str
    author: str
    family: str
    context_length: int
    
    # Pricing
    price_per_1m_prompt: float
    price_per_1m_completion: float
    price_per_request: float = 0.0
    price_reasoning: float = 0.0
    
    # Capabilities (derived from API)
    supports_tools: bool = False
    supports_reasoning: bool = False
    supports_structured: bool = False
    multimodal_input: bool = False
    multimodal_output: bool = False
    supports_streaming: bool = True
    
    # Classification
    tier: int = 2  # 1=frontier, 2=standard, 3=budget
    is_active: bool = True
    
    # Metadata
    logo_url: Optional[str] = None
    description: Optional[str] = None
    max_completion_tokens: Optional[int] = None
    supported_parameters: List[str] = field(default_factory=list)
    
    # Rankings (from internal telemetry)
    reliability_score: float = 0.5  # 0-1
    speed_score: float = 0.5  # 0-1
    
    @property
    def avg_cost_per_1m(self) -> float:
        """Average cost per 1M tokens (input+output / 2)."""
        return (self.price_per_1m_prompt + self.price_per_1m_completion) / 2
    
    @property
    def is_frontier(self) -> bool:
        """Whether this is a frontier model."""
        return self.family in HIGH_ACCURACY_FAMILIES or self.tier == 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "family": self.family,
            "context_length": self.context_length,
            "price_per_1m_prompt": self.price_per_1m_prompt,
            "price_per_1m_completion": self.price_per_1m_completion,
            "supports_tools": self.supports_tools,
            "supports_reasoning": self.supports_reasoning,
            "supports_structured": self.supports_structured,
            "multimodal_input": self.multimodal_input,
            "tier": self.tier,
            "is_frontier": self.is_frontier,
            "logo_url": self.logo_url,
        }


@dataclass
class CategoryRanking:
    """Ranking for a category."""
    category: str
    models: List[Tuple[str, int, float]]  # (model_id, rank, score)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Dynamic Model Catalog
# =============================================================================

class DynamicModelCatalog:
    """Dynamic model catalog with automatic family detection and capability derivation.
    
    This catalog:
    1. Fetches models from OpenRouter API
    2. Stores in DB for persistence
    3. Derives capabilities from API metadata
    4. Provides dynamic high-accuracy model selection
    5. Falls back to bootstrap only if all sources fail
    
    Usage:
        catalog = DynamicModelCatalog(db_session, openrouter_client)
        
        # Initialize from DB or API
        await catalog.initialize()
        
        # Get high-accuracy models for a task
        models = await catalog.get_high_accuracy_models(
            task_type="coding",
            require_tools=True,
        )
        
        # Get models by family
        gpt5_models = catalog.get_models_by_family("gpt-5.2")
    """
    
    def __init__(
        self,
        db_session: Optional[Any] = None,
        openrouter_client: Optional[Any] = None,
        cache_ttl_seconds: int = 300,
    ):
        """Initialize catalog.
        
        Args:
            db_session: SQLAlchemy session for persistence
            openrouter_client: OpenRouter API client
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.db = db_session
        self.client = openrouter_client
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # In-memory cache
        self._models: Dict[str, DynamicModel] = {}
        self._families: Dict[str, List[str]] = {}
        self._category_rankings: Dict[str, CategoryRanking] = {}
        self._last_refresh: Optional[datetime] = None
        self._initialized = False
    
    async def initialize(self, force_refresh: bool = False) -> None:
        """Initialize catalog from DB or API.
        
        Args:
            force_refresh: Force refresh from API even if cache is valid
        """
        if self._initialized and not force_refresh:
            return
        
        # Try to load from DB first
        if self.db:
            loaded = await self._load_from_db()
            if loaded:
                self._initialized = True
                logger.info("Loaded %d models from DB", len(self._models))
                return
        
        # Try to fetch from API
        if self.client:
            await self._refresh_from_api()
            self._initialized = True
            return
        
        # Fall back to bootstrap
        self._load_bootstrap_fallback()
        self._initialized = True
        logger.warning("Using bootstrap fallback - %d models", len(self._models))
    
    async def _load_from_db(self) -> bool:
        """Load models from database."""
        try:
            from ..openrouter.models import OpenRouterModel
            
            models = self.db.query(OpenRouterModel).filter(
                OpenRouterModel.is_active == True
            ).all()
            
            if not models:
                return False
            
            for model in models:
                dynamic_model = self._db_model_to_dynamic(model)
                self._models[dynamic_model.id] = dynamic_model
            
            self._rebuild_family_index()
            return True
            
        except Exception as e:
            logger.warning("Failed to load from DB: %s", e)
            return False
    
    async def _refresh_from_api(self) -> None:
        """Refresh catalog from OpenRouter API."""
        try:
            models_data = await self.client.list_models()
            
            if not models_data:
                logger.warning("No models returned from API")
                return
            
            for model_data in models_data:
                dynamic_model = self._api_model_to_dynamic(model_data)
                self._models[dynamic_model.id] = dynamic_model
            
            self._rebuild_family_index()
            self._last_refresh = datetime.now(timezone.utc)
            
            logger.info("Refreshed %d models from OpenRouter API", len(self._models))
            
        except Exception as e:
            logger.error("Failed to refresh from API: %s", e)
    
    def _load_bootstrap_fallback(self) -> None:
        """Load minimal bootstrap fallback."""
        for data in BOOTSTRAP_FALLBACK_MODELS:
            model = DynamicModel(**data)
            self._models[model.id] = model
        
        self._rebuild_family_index()
    
    def _db_model_to_dynamic(self, model: Any) -> DynamicModel:
        """Convert DB model to DynamicModel."""
        model_id = model.id
        
        return DynamicModel(
            id=model_id,
            name=model.name or model_id.split("/")[-1],
            author=self._extract_author(model_id),
            family=self._detect_family(model_id),
            context_length=model.context_length or 8192,
            price_per_1m_prompt=float(model.price_per_1m_prompt or 0),
            price_per_1m_completion=float(model.price_per_1m_completion or 0),
            supports_tools=model.supports_tools or False,
            supports_reasoning=self._has_reasoning_support(model),
            supports_structured=model.supports_structured or False,
            multimodal_input=model.multimodal_input or False,
            multimodal_output=model.multimodal_output or False,
            tier=self._determine_tier(model_id, float(model.price_per_1m_prompt or 0)),
            is_active=model.is_active,
            logo_url=self._resolve_logo(model_id),
            description=model.description,
            max_completion_tokens=model.max_completion_tokens,
        )
    
    def _api_model_to_dynamic(self, data: Dict[str, Any]) -> DynamicModel:
        """Convert API response to DynamicModel."""
        model_id = data.get("id", "")
        
        # Extract pricing
        pricing = data.get("pricing", {})
        price_prompt = float(pricing.get("prompt", 0)) * 1_000_000  # Convert to per 1M
        price_completion = float(pricing.get("completion", 0)) * 1_000_000
        price_reasoning = float(pricing.get("internal_reasoning", 0)) * 1_000_000
        
        # Extract supported parameters
        supported_params = data.get("supported_parameters", [])
        
        # Extract architecture
        architecture = data.get("architecture", {})
        input_modalities = architecture.get("input_modalities", [])
        output_modalities = architecture.get("output_modalities", [])
        
        # Derive capabilities
        supports_tools = "tools" in supported_params
        supports_reasoning = "reasoning" in supported_params or price_reasoning > 0
        supports_structured = "structured_outputs" in supported_params
        multimodal_input = "image" in input_modalities or "file" in input_modalities
        multimodal_output = "image" in output_modalities or "audio" in output_modalities
        
        # Top provider info
        top_provider = data.get("top_provider", {})
        context_length = top_provider.get("context_length") or data.get("context_length", 8192)
        max_completion = top_provider.get("max_completion_tokens")
        
        return DynamicModel(
            id=model_id,
            name=data.get("name", model_id.split("/")[-1]),
            author=self._extract_author(model_id),
            family=self._detect_family(model_id),
            context_length=context_length,
            price_per_1m_prompt=price_prompt,
            price_per_1m_completion=price_completion,
            price_reasoning=price_reasoning,
            supports_tools=supports_tools,
            supports_reasoning=supports_reasoning,
            supports_structured=supports_structured,
            multimodal_input=multimodal_input,
            multimodal_output=multimodal_output,
            tier=self._determine_tier(model_id, price_prompt),
            is_active=True,
            logo_url=self._resolve_logo(model_id),
            description=data.get("description"),
            max_completion_tokens=max_completion,
            supported_parameters=supported_params,
        )
    
    def _extract_author(self, model_id: str) -> str:
        """Extract author from model ID."""
        if "/" in model_id:
            return model_id.split("/")[0]
        return "unknown"
    
    def _detect_family(self, model_id: str) -> str:
        """Detect model family from ID."""
        model_id_lower = model_id.lower()
        
        for family_name, pattern in FAMILY_PATTERNS:
            if re.search(pattern, model_id_lower):
                return family_name
        
        # Default to author-slug
        author = self._extract_author(model_id)
        slug = model_id.split("/")[-1] if "/" in model_id else model_id
        
        # Try to extract base name
        parts = re.split(r"[-_]", slug)
        if len(parts) >= 2:
            return f"{author}-{parts[0]}"
        
        return author
    
    def _has_reasoning_support(self, model: Any) -> bool:
        """Check if model supports reasoning."""
        # Check supported_parameters if available
        params = getattr(model, "supported_parameters", None)
        if params:
            if isinstance(params, list):
                return "reasoning" in params
            if isinstance(params, str):
                return "reasoning" in params
        
        # Check by family
        family = self._detect_family(model.id)
        return family in {"o1", "o1-pro", "o3", "o3-pro", "deepseek-r1", "deepseek-reasoner"}
    
    def _determine_tier(self, model_id: str, price_per_1m: float) -> int:
        """Determine model tier (1=frontier, 2=standard, 3=budget)."""
        family = self._detect_family(model_id)
        
        # Frontier families
        if family in HIGH_ACCURACY_FAMILIES:
            return 1
        
        # Price-based tiers
        if price_per_1m >= 5.0:
            return 1
        elif price_per_1m >= 0.5:
            return 2
        else:
            return 3
    
    def _resolve_logo(self, model_id: str) -> str:
        """Resolve logo URL for model."""
        author = self._extract_author(model_id)
        return AUTHOR_LOGOS.get(author, "https://cdn.openrouter.ai/logos/default.svg")
    
    def _rebuild_family_index(self) -> None:
        """Rebuild family index from models."""
        self._families.clear()
        
        for model in self._models.values():
            if model.family not in self._families:
                self._families[model.family] = []
            self._families[model.family].append(model.id)
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_model(self, model_id: str) -> Optional[DynamicModel]:
        """Get a specific model by ID."""
        return self._models.get(model_id)
    
    def get_all_models(self) -> List[DynamicModel]:
        """Get all active models."""
        return [m for m in self._models.values() if m.is_active]
    
    def get_models_by_family(self, family: str) -> List[DynamicModel]:
        """Get all models in a family."""
        model_ids = self._families.get(family, [])
        return [self._models[mid] for mid in model_ids if mid in self._models]
    
    def get_models_by_author(self, author: str) -> List[DynamicModel]:
        """Get all models by author."""
        return [m for m in self._models.values() if m.author == author and m.is_active]
    
    def get_frontier_models(self) -> List[DynamicModel]:
        """Get all frontier (tier 1) models."""
        return [m for m in self._models.values() if m.is_frontier and m.is_active]
    
    async def get_high_accuracy_models(
        self,
        task_type: str = "general",
        *,
        max_count: int = 5,
        max_cost_per_1m: Optional[float] = None,
        require_tools: bool = False,
        require_reasoning: bool = False,
        require_structured: bool = False,
        min_context: int = 0,
        exclude_models: Optional[List[str]] = None,
    ) -> List[DynamicModel]:
        """Get high-accuracy models for a task.
        
        This replaces the hardcoded HIGH_ACCURACY_MODELS list with
        dynamic selection based on:
        - Frontier model families
        - Reliability scores from telemetry
        - Capability requirements
        - Budget constraints
        
        Args:
            task_type: Type of task
            max_count: Maximum models to return
            max_cost_per_1m: Maximum cost per 1M tokens
            require_tools: Require tool calling support
            require_reasoning: Require reasoning support
            require_structured: Require structured output support
            min_context: Minimum context length
            exclude_models: Models to exclude
            
        Returns:
            List of high-accuracy models sorted by quality score
        """
        await self.initialize()
        
        candidates: List[Tuple[DynamicModel, float]] = []
        exclude_set = set(exclude_models or [])
        
        for model in self._models.values():
            if not model.is_active:
                continue
            
            if model.id in exclude_set:
                continue
            
            # Check requirements
            if require_tools and not model.supports_tools:
                continue
            if require_reasoning and not model.supports_reasoning:
                continue
            if require_structured and not model.supports_structured:
                continue
            if model.context_length < min_context:
                continue
            if max_cost_per_1m and model.avg_cost_per_1m > max_cost_per_1m:
                continue
            
            # Calculate score
            score = 0.0
            
            # Frontier bonus
            if model.is_frontier:
                score += 0.3
            
            # Tier-based score
            if model.tier == 1:
                score += 0.25
            elif model.tier == 2:
                score += 0.15
            else:
                score += 0.05
            
            # Reliability score
            score += model.reliability_score * 0.2
            
            # Task-specific bonuses
            if task_type in ["coding", "debugging"] and model.supports_tools:
                score += 0.1
            if task_type in ["research", "analysis"] and model.context_length >= 100000:
                score += 0.1
            if task_type in ["math", "reasoning"] and model.supports_reasoning:
                score += 0.15
            
            # Capability bonuses
            if model.supports_tools:
                score += 0.05
            if model.supports_reasoning:
                score += 0.05
            if model.supports_structured:
                score += 0.03
            
            candidates.append((model, score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [c[0] for c in candidates[:max_count]]
    
    def get_role_models(
        self,
        role: str,
        available_models: Optional[List[str]] = None,
    ) -> List[DynamicModel]:
        """Get models suitable for an orchestration role.
        
        Roles and their requirements:
        - coordinator/planner: reasoning, high quality
        - executor/primary: tools, speed
        - validator/judge: reasoning, reliability
        - fallback: cheap, fast
        - specialist: domain-specific
        
        Args:
            role: Orchestration role
            available_models: Limit to these models if provided
            
        Returns:
            List of suitable models
        """
        role_requirements = {
            "coordinator": {"require_reasoning": True, "tier_max": 1},
            "planner": {"require_reasoning": True, "tier_max": 1},
            "executor": {"require_tools": True, "tier_max": 2},
            "primary": {"require_tools": True, "tier_max": 1},
            "validator": {"require_reasoning": True, "tier_max": 2},
            "judge": {"require_reasoning": True, "tier_max": 1},
            "fallback": {"tier_min": 3, "prefer_cheap": True},
            "synthesizer": {"require_reasoning": True, "tier_max": 1},
            "specialist": {"tier_max": 2},
        }
        
        reqs = role_requirements.get(role, {})
        tier_max = reqs.get("tier_max", 3)
        tier_min = reqs.get("tier_min", 1)
        require_tools = reqs.get("require_tools", False)
        require_reasoning = reqs.get("require_reasoning", False)
        prefer_cheap = reqs.get("prefer_cheap", False)
        
        candidates = []
        available_set = set(available_models) if available_models else None
        
        for model in self._models.values():
            if not model.is_active:
                continue
            
            if available_set and model.id not in available_set:
                continue
            
            if model.tier < tier_min or model.tier > tier_max:
                continue
            
            if require_tools and not model.supports_tools:
                continue
            if require_reasoning and not model.supports_reasoning:
                continue
            
            candidates.append(model)
        
        # Sort by cost (ascending if prefer_cheap, else by tier)
        if prefer_cheap:
            candidates.sort(key=lambda m: m.avg_cost_per_1m)
        else:
            candidates.sort(key=lambda m: (m.tier, -m.reliability_score))
        
        return candidates
    
    def get_escalation_target(self, current_model_id: str) -> Optional[str]:
        """Get escalation target for a model.
        
        Dynamic escalation based on family and tier.
        
        Args:
            current_model_id: Current model ID
            
        Returns:
            Model ID to escalate to, or None
        """
        current = self._models.get(current_model_id)
        if not current:
            return None
        
        # Find models in same family with better tier
        same_family = self.get_models_by_family(current.family)
        better_models = [
            m for m in same_family
            if m.tier < current.tier or 
            (m.tier == current.tier and m.avg_cost_per_1m > current.avg_cost_per_1m)
        ]
        
        if better_models:
            # Sort by tier, then by price (higher = better for same tier)
            better_models.sort(key=lambda m: (m.tier, -m.avg_cost_per_1m))
            return better_models[0].id
        
        # Cross-family escalation for tier 3
        if current.tier == 3:
            frontier = self.get_frontier_models()
            if frontier:
                # Pick a frontier model with similar capabilities
                for m in frontier:
                    if current.supports_tools and not m.supports_tools:
                        continue
                    return m.id
                return frontier[0].id
        
        return None
    
    def get_model_profiles_for_scoring(self) -> Dict[str, Dict[str, Any]]:
        """Get model profiles in the format expected by adaptive_router scoring.
        
        Returns:
            Dictionary of model_id -> profile dict
        """
        profiles = {}
        
        for model in self._models.values():
            if not model.is_active:
                continue
            
            # Map tier to size
            size = {1: "large", 2: "medium", 3: "small"}.get(model.tier, "medium")
            
            # Determine domains based on capabilities
            domains = ["general"]
            if model.supports_tools:
                domains.extend(["coding", "tools"])
            if model.supports_reasoning:
                domains.extend(["research", "analysis", "math"])
            if model.context_length >= 100000:
                domains.append("long-context")
            if model.multimodal_input:
                domains.append("multimodal")
            
            # Base quality from tier
            base_quality = {1: 0.9, 2: 0.75, 3: 0.6}.get(model.tier, 0.7)
            
            profiles[model.id] = {
                "size": size,
                "domains": list(set(domains)),
                "base_quality": base_quality,
                "supports_tools": model.supports_tools,
                "supports_reasoning": model.supports_reasoning,
                "context_length": model.context_length,
                "cost_per_1m_input": model.price_per_1m_prompt,
                "cost_per_1m_output": model.price_per_1m_completion,
                "family": model.family,
                "author": model.author,
            }
        
        return profiles


# =============================================================================
# Global Instance
# =============================================================================

_catalog: Optional[DynamicModelCatalog] = None


def get_dynamic_catalog(
    db_session: Optional[Any] = None,
    openrouter_client: Optional[Any] = None,
) -> DynamicModelCatalog:
    """Get or create the global dynamic catalog instance.
    
    Args:
        db_session: Optional DB session
        openrouter_client: Optional OpenRouter client
        
    Returns:
        DynamicModelCatalog instance
    """
    global _catalog
    
    if _catalog is None or db_session is not None or openrouter_client is not None:
        _catalog = DynamicModelCatalog(
            db_session=db_session,
            openrouter_client=openrouter_client,
        )
    
    return _catalog


async def get_high_accuracy_models(
    task_type: str = "general",
    max_count: int = 5,
    **kwargs,
) -> List[str]:
    """Convenience function to get high-accuracy model IDs.
    
    Args:
        task_type: Type of task
        max_count: Maximum models to return
        **kwargs: Additional filters
        
    Returns:
        List of model IDs
    """
    catalog = get_dynamic_catalog()
    await catalog.initialize()
    
    models = await catalog.get_high_accuracy_models(
        task_type=task_type,
        max_count=max_count,
        **kwargs,
    )
    
    return [m.id for m in models]

