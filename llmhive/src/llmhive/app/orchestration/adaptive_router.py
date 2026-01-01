"""Adaptive Model Router for intelligent model selection based on performance.

This module implements adaptive routing that selects models based on:
- Historical performance metrics
- Query domain matching
- Accuracy level requirements
- Available model capabilities
- Real-time OpenRouter rankings (when available)
- DYNAMIC MODEL CATALOG from OpenRouter API

The router can operate in two modes:
1. Static mode (default): Uses minimal bootstrap + dynamic catalog
2. Dynamic mode: Fetches real-time rankings from OpenRouter

To enable dynamic mode, initialize with use_openrouter_rankings=True

PR9: Updated to use DynamicModelCatalog instead of hardcoded MODEL_PROFILES.
The catalog is populated from OpenRouter API and stored in database.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..performance_tracker import performance_tracker, ModelPerformance

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from .openrouter_selector import OpenRouterModelSelector, SelectionResult

logger = logging.getLogger(__name__)


# =============================================================================
# DYNAMIC MODEL PROFILES (Lazy-loaded from catalog)
# =============================================================================

def get_dynamic_model_profiles() -> Dict[str, Dict[str, Any]]:
    """Get model profiles dynamically from catalog or fallback.
    
    This replaces the static MODEL_PROFILES dict with dynamic loading.
    Priority:
    1. Firestore model_catalog (353+ models with 262+ enriched columns)
    2. Dynamic catalog (from DB/API)
    3. Fallback to minimal bootstrap profiles
    """
    # Priority 1: Firestore model_catalog (the richest data source)
    try:
        from ..services.firestore_models import get_firestore_model_catalog
        fs_catalog = get_firestore_model_catalog()
        
        if fs_catalog.is_available():
            profiles = fs_catalog.get_model_profiles_for_orchestrator()
            if profiles and len(profiles) > 50:  # Expect at least 50 models
                logger.info("Loaded %d model profiles from Firestore", len(profiles))
                return profiles
    except ImportError:
        logger.debug("Firestore model catalog not available")
    except Exception as e:
        logger.warning("Failed to load Firestore model catalog: %s", e)
    
    # Priority 2: Dynamic catalog from OpenRouter API/SQLite
    try:
        from ..openrouter.dynamic_catalog import get_dynamic_catalog
        catalog = get_dynamic_catalog()
        
        # If catalog has models, use them
        if catalog._models:
            return catalog.get_model_profiles_for_scoring()
    except ImportError:
        logger.debug("Dynamic catalog not available, using bootstrap profiles")
    except Exception as e:
        logger.warning("Failed to load dynamic catalog: %s", e)
    
    # Priority 3: Bootstrap fallback profiles
    logger.warning("Using bootstrap fallback profiles (%d models)", len(BOOTSTRAP_MODEL_PROFILES))
    return BOOTSTRAP_MODEL_PROFILES


# Bootstrap profiles - minimal fallback when dynamic catalog unavailable
BOOTSTRAP_MODEL_PROFILES: Dict[str, Dict[str, Any]] = {
    "openai/gpt-4o": {
        "size": "large",
        "domains": ["general", "coding", "research"],
        "base_quality": 0.9,
        "speed_rating": 0.7,
        "cost_rating": 0.8,
        "cost_per_1m_input": 2.50,
        "cost_per_1m_output": 10.00,
        "family": "gpt-4o",
        "author": "openai",
    },
    "anthropic/claude-sonnet-4": {
        "size": "large",
        "domains": ["general", "coding", "research", "analysis"],
        "base_quality": 0.91,
        "speed_rating": 0.7,
        "cost_rating": 0.8,
        "cost_per_1m_input": 3.00,
        "cost_per_1m_output": 15.00,
        "family": "claude-4",
        "author": "anthropic",
    },
    "openai/gpt-4o-mini": {
        "size": "small",
        "domains": ["general", "coding", "quick-tasks"],
        "base_quality": 0.75,
        "speed_rating": 0.95,
        "cost_rating": 0.95,
        "cost_per_1m_input": 0.15,
        "cost_per_1m_output": 0.60,
        "family": "gpt-4o-mini",
        "author": "openai",
    },
    "google/gemini-2.5-pro-preview": {
        "size": "large",
        "domains": ["research", "coding", "multimodal", "analysis"],
        "base_quality": 0.88,
        "speed_rating": 0.75,
        "cost_rating": 0.75,
        "cost_per_1m_input": 1.25,
        "cost_per_1m_output": 5.00,
        "family": "gemini-2.5",
        "author": "google",
    },
    "deepseek/deepseek-chat": {
        "size": "medium",
        "domains": ["coding", "math", "reasoning"],
        "base_quality": 0.8,
        "speed_rating": 0.85,
        "cost_rating": 0.95,
        "cost_per_1m_input": 0.14,
        "cost_per_1m_output": 0.28,
        "family": "deepseek-chat",
        "author": "deepseek",
    },
}


# PR5: Default budget constraints
DEFAULT_MAX_COST_USD = 1.0  # Default max cost per request
DEFAULT_COST_WEIGHT = 0.15  # Weight of cost in scoring (0-1)


# MODEL_PROFILES is now dynamically loaded via get_dynamic_model_profiles()
# This allows automatic updates when new models are added to OpenRouter
# The function returns profiles from the dynamic catalog, or bootstrap fallback
MODEL_PROFILES: Dict[str, Dict[str, Any]] = {}  # Populated lazily


def _get_model_profiles() -> Dict[str, Dict[str, Any]]:
    """Get model profiles, loading dynamically if needed."""
    global MODEL_PROFILES
    
    if not MODEL_PROFILES:
        MODEL_PROFILES = get_dynamic_model_profiles()
    
    return MODEL_PROFILES


def refresh_model_profiles() -> Dict[str, Dict[str, Any]]:
    """Force refresh of model profiles from dynamic catalog."""
    global MODEL_PROFILES
    MODEL_PROFILES = get_dynamic_model_profiles()
    logger.info("Refreshed MODEL_PROFILES with %d models", len(MODEL_PROFILES))
    return MODEL_PROFILES


@dataclass
class BudgetConstraints:
    """PR5: Budget constraints for cost-aware routing."""
    max_cost_usd: float = DEFAULT_MAX_COST_USD  # Max cost per request
    cost_weight: float = DEFAULT_COST_WEIGHT  # Weight in scoring (0-1)
    prefer_cheaper: bool = False  # Strongly prefer cheaper models
    estimated_tokens: int = 2000  # Estimated tokens for cost calculation

# Domain inference keywords
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "medical": ["medical", "health", "disease", "symptom", "treatment", "diagnosis", "patient", "doctor"],
    "legal": ["legal", "law", "court", "attorney", "contract", "liability", "regulation", "statute"],
    "coding": ["code", "program", "function", "debug", "algorithm", "python", "javascript", "api"],
    "research": ["research", "study", "analyze", "investigate", "data", "findings", "methodology"],
    "math": ["calculate", "equation", "formula", "math", "solve", "theorem", "proof"],
    "finance": ["finance", "investment", "stock", "market", "portfolio", "trading", "revenue"],
    "writing": ["write", "essay", "article", "story", "content", "creative", "draft"],
    "general": [],  # Default fallback
}


@dataclass(slots=True)
class ModelScore:
    """Score breakdown for a model candidate."""
    model: str
    total_score: float
    domain_score: float
    performance_score: float
    accuracy_adjustment: float
    speed_adjustment: float
    cost_adjustment: float = 0.0  # PR5: Cost-based adjustment
    estimated_cost_usd: float = 0.0  # PR5: Estimated cost for this model
    reasoning: str = ""


@dataclass(slots=True)
class AdaptiveRoutingResult:
    """Result of adaptive model routing."""
    primary_model: str
    secondary_models: List[str]
    role_assignments: Dict[str, str]  # role -> model
    model_scores: List[ModelScore]
    reasoning: str
    recommended_ensemble_size: int


class AdaptiveModelRouter:
    """Routes queries to optimal models based on adaptive scoring.
    
    Supports two modes:
    1. Static mode (default): Uses hardcoded MODEL_PROFILES
    2. Dynamic mode: Fetches real-time rankings from OpenRouter
    
    Usage:
        # Static mode (default)
        router = AdaptiveModelRouter()
        
        # Dynamic mode with OpenRouter rankings
        router = AdaptiveModelRouter(
            use_openrouter_rankings=True,
            db_session=session,
        )
    """
    
    def __init__(
        self,
        available_providers: Optional[List[str]] = None,
        model_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        *,
        use_openrouter_rankings: bool = False,
        db_session: Optional["Session"] = None,
        budget_constraints: Optional[BudgetConstraints] = None,
    ) -> None:
        """
        Initialize adaptive router.
        
        Args:
            available_providers: List of available provider names
            model_profiles: Optional custom model profiles
            use_openrouter_rankings: Enable dynamic selection from OpenRouter
            db_session: Database session for OpenRouter rankings
            budget_constraints: PR5 - Budget constraints for cost-aware routing
        """
        self.available_providers = available_providers or []
        self.profiles = model_profiles or MODEL_PROFILES
        self.use_openrouter_rankings = use_openrouter_rankings
        self.db_session = db_session
        self._openrouter_selector: Optional["OpenRouterModelSelector"] = None
        
        # PR5: Budget constraints
        self.budget_constraints = budget_constraints or BudgetConstraints()
        
        # Cache for dynamic profiles
        self._dynamic_profiles_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Model Knowledge Store for intelligent routing
        self._knowledge_store = None
        self._knowledge_store_initialized = False
        
        # Ensure profiles are loaded (dynamic or bootstrap)
        if not self.profiles:
            self.profiles = _get_model_profiles()
    
    def _get_dynamic_role_preferences(self) -> Dict[str, List[str]]:
        """Get role preferences dynamically from catalog or use bootstrap.
        
        Returns role-to-models mapping based on dynamic catalog capabilities.
        """
        try:
            from ..openrouter.dynamic_catalog import get_dynamic_catalog
            catalog = get_dynamic_catalog()
            
            if catalog._models:
                # Build role preferences from catalog
                prefs: Dict[str, List[str]] = {}
                
                # Coordinator: needs reasoning capability, tier 1
                coordinator_models = catalog.get_role_models("coordinator")
                prefs["coordinator"] = [m.id for m in coordinator_models[:3]]
                
                # Executive: needs tools, tier 1
                executive_models = catalog.get_role_models("primary")
                prefs["executive"] = [m.id for m in executive_models[:3]]
                
                # Quality manager: validator role
                validator_models = catalog.get_role_models("validator")
                prefs["quality_manager"] = [m.id for m in validator_models[:2]]
                
                # Lead researcher: long context + reasoning
                prefs["lead_researcher"] = [m.id for m in coordinator_models[:2]]
                
                # Fact checker: reliable + cheap
                fallback_models = catalog.get_role_models("fallback")
                prefs["fact_checker"] = [m.id for m in fallback_models[:2]]
                
                # Synthesizer: reasoning + quality
                prefs["synthesizer"] = [m.id for m in coordinator_models[:2]]
                
                # Assistant: fast + cheap
                prefs["assistant"] = [m.id for m in fallback_models[:2]]
                
                return prefs
                
        except ImportError:
            pass
        except Exception as e:
            logger.debug("Failed to get dynamic role preferences: %s", e)
        
        # Bootstrap fallback
        return {
            "coordinator": ["anthropic/claude-sonnet-4", "openai/gpt-4o"],
            "executive": ["openai/gpt-4o", "anthropic/claude-sonnet-4"],
            "quality_manager": ["openai/gpt-4o", "openai/gpt-4o-mini"],
            "lead_researcher": ["google/gemini-2.5-pro-preview", "anthropic/claude-sonnet-4"],
            "fact_checker": ["openai/gpt-4o-mini", "deepseek/deepseek-chat"],
            "synthesizer": ["openai/gpt-4o", "anthropic/claude-sonnet-4"],
            "assistant": ["openai/gpt-4o-mini", "deepseek/deepseek-chat"],
        }
    
    def _get_dynamic_escalation_target(self, model_id: str) -> Optional[str]:
        """Get escalation target for a model dynamically.
        
        Args:
            model_id: Current model ID
            
        Returns:
            Model ID to escalate to, or None
        """
        try:
            from ..openrouter.dynamic_catalog import get_dynamic_catalog
            catalog = get_dynamic_catalog()
            
            if catalog._models:
                return catalog.get_escalation_target(model_id)
                
        except ImportError:
            pass
        except Exception as e:
            logger.debug("Failed to get dynamic escalation target: %s", e)
        
        # Bootstrap fallback escalation
        bootstrap_chain = {
            "openai/gpt-4o-mini": "openai/gpt-4o",
            "anthropic/claude-haiku-4": "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash-preview": "google/gemini-2.5-pro-preview",
            "deepseek/deepseek-chat": "deepseek/deepseek-reasoner",
        }
        
        return bootstrap_chain.get(model_id)
    
    def _get_knowledge_store(self):
        """Get or initialize the Model Knowledge Store for intelligent routing."""
        if self._knowledge_store_initialized:
            return self._knowledge_store
        
        try:
            from ..knowledge import MODEL_KNOWLEDGE_AVAILABLE, get_model_knowledge_store
            
            if MODEL_KNOWLEDGE_AVAILABLE:
                self._knowledge_store = get_model_knowledge_store()
                logger.info("Model Knowledge Store initialized for adaptive routing")
            else:
                logger.debug("Model Knowledge Store not available")
                
        except Exception as e:
            logger.warning("Failed to initialize Model Knowledge Store: %s", e)
        
        self._knowledge_store_initialized = True
        return self._knowledge_store
    
    async def get_best_models_from_knowledge(
        self,
        task_description: str,
        category: Optional[str] = None,
        require_reasoning: bool = False,
        require_tools: bool = False,
        top_k: int = 5,
    ) -> List[str]:
        """
        Get best models for a task from the Model Knowledge Store.
        
        This provides intelligence-based model selection using:
        - Model rankings from OpenRouter
        - Model capability profiles
        - Reasoning model analysis
        
        Args:
            task_description: Description of the task
            category: Optional category (programming, reasoning, etc.)
            require_reasoning: If True, prefer reasoning models
            require_tools: If True, require tool support
            top_k: Number of models to return
            
        Returns:
            List of model IDs ranked by suitability
        """
        store = self._get_knowledge_store()
        if not store:
            return []
        
        try:
            records = await store.get_best_models_for_task(
                task_description=task_description,
                category=category,
                require_reasoning=require_reasoning,
                require_tools=require_tools,
                top_k=top_k,
            )
            
            # Extract model IDs from records
            model_ids = []
            for record in records:
                if record.model_id and record.model_id not in model_ids:
                    model_ids.append(record.model_id)
            
            logger.debug(
                "Knowledge store suggested %d models for task: %s",
                len(model_ids), task_description[:50]
            )
            
            return model_ids
            
        except Exception as e:
            logger.warning("Failed to get models from knowledge store: %s", e)
            return []
    
    async def get_reasoning_models_from_knowledge(self, top_k: int = 5) -> List[str]:
        """
        Get the best reasoning models from the Knowledge Store.
        
        Returns:
            List of model IDs that are strong at reasoning
        """
        store = self._get_knowledge_store()
        if not store:
            return []
        
        try:
            records = await store.get_reasoning_models(top_k=top_k)
            return [r.model_id for r in records if r.model_id]
            
        except Exception as e:
            logger.warning("Failed to get reasoning models: %s", e)
            return []
    
    async def get_category_leaders_from_knowledge(
        self,
        category: str,
        top_k: int = 10,
    ) -> List[str]:
        """
        Get top models for a category from Knowledge Store rankings.
        
        Args:
            category: Category slug (programming, science, etc.)
            top_k: Number of models to return
            
        Returns:
            List of model IDs ranked by category performance
        """
        store = self._get_knowledge_store()
        if not store:
            return []
        
        try:
            records = await store.get_category_rankings(category=category, top_k=top_k)
            return [r.model_id for r in records if r.model_id]
            
        except Exception as e:
            logger.warning("Failed to get category rankings: %s", e)
            return []
    
    def _get_openrouter_selector(self) -> Optional["OpenRouterModelSelector"]:
        """Get or create OpenRouter selector."""
        if not self.use_openrouter_rankings:
            return None
        
        if self._openrouter_selector is None:
            from .openrouter_selector import OpenRouterModelSelector
            self._openrouter_selector = OpenRouterModelSelector(self.db_session)
        
        return self._openrouter_selector
    
    # =========================================================================
    # INTEL UPDATE DEC 2024: Smart Routing Integration
    # =========================================================================
    
    async def select_model_smart(
        self,
        query: str,
        task_type: str = "general",
        *,
        use_cascade: bool = True,
        detect_reasoning: bool = True,
        max_cost_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Smart model selection combining cascade routing and reasoning detection.
        
        This is the recommended entry point for intelligent model selection
        that balances cost, speed, and capability.
        
        Features (from Intel Update Dec 2024):
        1. Cascade routing - starts cheap, escalates only when needed (30-70% cost savings)
        2. Reasoning detection - routes complex reasoning to specialized models
        3. Knowledge-based selection - uses Pinecone model profiles
        
        Args:
            query: User query text
            task_type: Type of task (general, coding, reasoning)
            use_cascade: Enable cascade routing for cost optimization
            detect_reasoning: Enable reasoning model detection
            max_cost_usd: Maximum budget for this query
            
        Returns:
            Dict with:
            - model: Selected model ID
            - strategy: Routing strategy used
            - reasoning_analysis: ReasoningAnalysis if detect_reasoning=True
            - cascade_tier: Tier used if cascade routing applied
            - estimated_cost: Estimated cost tier
        """
        result: Dict[str, Any] = {
            "model": None,
            "strategy": "adaptive",
            "reasoning_analysis": None,
            "cascade_tier": None,
            "estimated_cost": "standard",
        }
        
        # Step 1: Check for reasoning requirements
        if detect_reasoning:
            try:
                from .reasoning_detector import get_reasoning_detector, ReasoningAnalysis
                
                detector = get_reasoning_detector()
                analysis: ReasoningAnalysis = detector.detect(query)
                result["reasoning_analysis"] = {
                    "needs_reasoning": analysis.needs_reasoning_model,
                    "reasoning_type": analysis.reasoning_type.value,
                    "confidence": analysis.confidence,
                    "detected_signals": analysis.detected_signals,
                    "recommended_effort": analysis.recommended_effort,
                }
                
                # If strong reasoning signals, route to reasoning model
                if analysis.needs_reasoning_model:
                    result["model"] = analysis.recommended_models[0] if analysis.recommended_models else "openai/o1"
                    result["strategy"] = "reasoning_specialized"
                    result["estimated_cost"] = "premium" if analysis.recommended_effort == "high" else "standard"
                    logger.info(
                        "Smart routing: Using reasoning model %s (confidence %.2f, type: %s)",
                        result["model"], analysis.confidence, analysis.reasoning_type.value
                    )
                    return result
                    
            except Exception as e:
                logger.warning("Failed to run reasoning detection: %s", e)
        
        # Step 2: Apply cascade routing for cost optimization
        if use_cascade:
            try:
                from .cascade_router import get_cascade_router
                
                cascade = get_cascade_router()
                complexity = cascade.classify_complexity(query)
                starting_tier = cascade.get_starting_tier(complexity)
                selected_model = cascade.get_model_for_tier(starting_tier, task_type)
                
                result["model"] = selected_model
                result["strategy"] = "cascade"
                result["cascade_tier"] = starting_tier
                result["estimated_cost"] = {1: "budget", 2: "standard", 3: "premium"}.get(starting_tier, "standard")
                
                logger.info(
                    "Smart routing: Cascade tier %d model %s (complexity: %s)",
                    starting_tier, selected_model, complexity.value
                )
                return result
                
            except Exception as e:
                logger.warning("Failed to apply cascade routing: %s", e)
        
        # Step 3: Fallback to standard adaptive routing
        domain = self.infer_domain(query)
        role_prefs = self._get_dynamic_role_preferences()
        
        # Get best model for domain/task
        if task_type == "coding" and "coding" in domain or domain == "coding":
            if "executive" in role_prefs:
                result["model"] = role_prefs["executive"][0]
        elif task_type == "reasoning" or domain in ["science", "math"]:
            if "coordinator" in role_prefs:
                result["model"] = role_prefs["coordinator"][0]
        else:
            if "assistant" in role_prefs:
                result["model"] = role_prefs["assistant"][0]
        
        if not result["model"]:
            result["model"] = "openai/gpt-4o-mini"  # Safe fallback
        
        result["strategy"] = "adaptive_fallback"
        logger.info("Smart routing: Fallback to %s for domain %s", result["model"], domain)
        
        return result
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get current routing statistics for monitoring."""
        stats = {
            "cascade_available": False,
            "reasoning_detector_available": False,
            "knowledge_store_available": False,
        }
        
        try:
            from .cascade_router import get_cascade_router
            cascade = get_cascade_router()
            stats["cascade_available"] = True
            stats["cascade_metrics"] = cascade.get_metrics()
        except Exception:
            pass
        
        try:
            from .reasoning_detector import get_reasoning_detector
            get_reasoning_detector()
            stats["reasoning_detector_available"] = True
        except Exception:
            pass
        
        if self._knowledge_store_initialized and self._knowledge_store:
            stats["knowledge_store_available"] = True
        
        return stats
    
    async def select_models_dynamic(
        self,
        query: str,
        roles: List[str],
        accuracy_level: int,
        *,
        available_models: Optional[List[str]] = None,
        max_models: Optional[int] = None,
        strategy: str = "automatic",
    ) -> AdaptiveRoutingResult:
        """
        Dynamic model selection using OpenRouter rankings.
        
        This is the async version that fetches real-time rankings.
        Falls back to static selection if OpenRouter is unavailable.
        
        Args:
            query: The refined query to process
            roles: List of role names that need model assignment
            accuracy_level: Slider value 1-5 (1=fastest, 5=most accurate)
            available_models: Optional list of available model names
            max_models: Maximum number of models to select
            strategy: Selection strategy ("automatic", "quality", "speed", "value")
            
        Returns:
            AdaptiveRoutingResult with model assignments and reasoning
        """
        selector = self._get_openrouter_selector()
        
        if selector is None:
            # Fall back to static selection
            return self.select_models_adaptive(
                query, roles, accuracy_level,
                available_models=available_models,
                max_models=max_models,
            )
        
        try:
            # Map accuracy level to strategy if automatic
            if strategy == "automatic":
                if accuracy_level <= 2:
                    strategy = "speed"
                elif accuracy_level >= 4:
                    strategy = "quality"
                else:
                    strategy = "balanced"
            
            # Infer task type from query
            domain = self.infer_domain(query)
            task_type = self._domain_to_task_type(domain)
            
            # Get dynamic selection
            from .openrouter_selector import SelectionStrategy
            
            result = await selector.select_models(
                task_type=task_type,
                count=len(roles) + 2,
                strategy=SelectionStrategy(strategy),
            )
            
            # Build role assignments from selection
            role_models = await selector.select_for_roles(
                roles=roles,
                task_type=task_type,
                strategy=SelectionStrategy(strategy),
            )
            
            role_assignments = {
                role: model.model_id
                for role, model in role_models.items()
            }
            
            # Build model scores for compatibility
            model_scores = [
                ModelScore(
                    model=m.model_id,
                    total_score=m.score,
                    domain_score=0.8,
                    performance_score=m.score,
                    accuracy_adjustment=0.0,
                    speed_adjustment=0.0,
                    reasoning=m.selection_reason,
                )
                for m in [result.primary_model] + result.secondary_models
            ]
            
            # Determine ensemble size based on accuracy level
            if accuracy_level <= 2:
                ensemble_size = 1
            elif accuracy_level <= 3:
                ensemble_size = 2
            elif accuracy_level <= 4:
                ensemble_size = 3
            else:
                ensemble_size = min(4, len(result.all_model_ids))
            
            return AdaptiveRoutingResult(
                primary_model=result.primary_model.model_id,
                secondary_models=[m.model_id for m in result.secondary_models],
                role_assignments=role_assignments,
                model_scores=model_scores,
                reasoning=f"Dynamic selection: {result.reasoning}",
                recommended_ensemble_size=ensemble_size,
            )
            
        except Exception as e:
            logger.warning(
                "OpenRouter dynamic selection failed, falling back to static: %s", e
            )
            return self.select_models_adaptive(
                query, roles, accuracy_level,
                available_models=available_models,
                max_models=max_models,
            )
    
    def _domain_to_task_type(self, domain: str) -> str:
        """Map domain to task type for OpenRouter selector."""
        mapping = {
            "medical": "research",
            "legal": "research",
            "coding": "coding",
            "research": "research",
            "math": "math",
            "finance": "analysis",
            "writing": "creative",
            "general": "general",
        }
        return mapping.get(domain, "general")
    
    def infer_domain(self, query: str) -> str:
        """Infer the domain of a query based on keywords."""
        query_lower = query.lower()
        
        domain_scores: Dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if not domain_scores:
            return "general"
        
        # Return domain with highest score
        return max(domain_scores.items(), key=lambda x: x[1])[0]
    
    def select_models_adaptive(
        self,
        query: str,
        roles: List[str],
        accuracy_level: int,
        *,
        available_models: Optional[List[str]] = None,
        max_models: Optional[int] = None,
        budget_constraints: Optional[BudgetConstraints] = None,
        max_cost_usd: Optional[float] = None,
    ) -> AdaptiveRoutingResult:
        """
        Adaptive model selection based on query, roles, and accuracy level.
        
        Args:
            query: The refined query to process
            roles: List of role names that need model assignment
            accuracy_level: Slider value 1-5 (1=fastest, 5=most accurate)
            available_models: Optional list of available model names
            max_models: Maximum number of models to select
            budget_constraints: PR5 - Budget constraints for cost-aware routing
            max_cost_usd: PR5 - Convenience param to set max cost (overrides budget_constraints)
            
        Returns:
            AdaptiveRoutingResult with model assignments and reasoning
        """
        # PR5: Build budget constraints
        budget = budget_constraints or self.budget_constraints
        if max_cost_usd is not None:
            budget = BudgetConstraints(
                max_cost_usd=max_cost_usd,
                cost_weight=budget.cost_weight,
                prefer_cheaper=budget.prefer_cheaper,
                estimated_tokens=budget.estimated_tokens,
            )
        
        # Infer domain
        domain = self.infer_domain(query)
        logger.info("Inferred domain: %s for query", domain)
        
        # Get performance snapshot
        perf_snapshot = performance_tracker.snapshot()
        
        # Get available models
        if available_models:
            candidates = [m for m in available_models if m in self.profiles]
        else:
            candidates = list(self.profiles.keys())
        
        if not candidates:
            candidates = ["stub"]
        
        # Score all models with budget awareness
        model_scores: List[ModelScore] = []
        for model in candidates:
            score = self._score_model(
                model,
                domain,
                accuracy_level,
                perf_snapshot.get(model),
                budget=budget,
            )
            model_scores.append(score)
        
        # Sort by total score (descending)
        model_scores.sort(key=lambda s: s.total_score, reverse=True)
        
        # PR5: Log budget-aware selection
        if max_cost_usd is not None or budget_constraints is not None:
            within_budget = [s for s in model_scores if s.estimated_cost_usd <= budget.max_cost_usd]
            logger.info(
                "PR5: Budget-aware selection: %d/%d models within budget ($%.2f)",
                len(within_budget), len(model_scores), budget.max_cost_usd
            )
        
        # Determine ensemble size based on accuracy level
        if accuracy_level <= 2:
            ensemble_size = 1
        elif accuracy_level <= 3:
            ensemble_size = 2
        elif accuracy_level <= 4:
            ensemble_size = 3
        else:
            ensemble_size = min(4, len(candidates))
        
        if max_models:
            ensemble_size = min(ensemble_size, max_models)
        
        # Select primary and secondary models
        primary_model = model_scores[0].model if model_scores else "stub"
        secondary_models = [s.model for s in model_scores[1:ensemble_size]]
        
        # Assign models to roles
        role_assignments = self._assign_models_to_roles(
            roles,
            model_scores,
            accuracy_level,
        )
        
        # Build reasoning
        reasoning_parts = [
            f"Domain: {domain}",
            f"Accuracy level: {accuracy_level}",
            f"Primary model: {primary_model} (score: {model_scores[0].total_score:.2f})" if model_scores else "No models available",
        ]
        if secondary_models:
            reasoning_parts.append(f"Secondary models: {', '.join(secondary_models)}")
        
        return AdaptiveRoutingResult(
            primary_model=primary_model,
            secondary_models=secondary_models,
            role_assignments=role_assignments,
            model_scores=model_scores,
            reasoning="; ".join(reasoning_parts),
            recommended_ensemble_size=ensemble_size,
        )
    
    def _score_model(
        self,
        model: str,
        domain: str,
        accuracy_level: int,
        perf: Optional[ModelPerformance],
        budget: Optional[BudgetConstraints] = None,
    ) -> ModelScore:
        """Score a model for the given domain and accuracy level.
        
        PR5: Now includes cost-aware scoring based on budget constraints.
        """
        profile = self.profiles.get(model, self.profiles.get("stub", {}))
        budget = budget or self.budget_constraints
        
        # Base domain score
        model_domains = profile.get("domains", ["general"])
        if domain in model_domains:
            domain_score = 1.0
        elif "general" in model_domains:
            domain_score = 0.5
        else:
            domain_score = 0.2
        
        # Performance score from historical data
        if perf:
            # Combine success rate, quality, and domain-specific performance
            success_component = perf.success_rate * 0.4
            quality_component = perf.avg_quality * 0.3
            domain_success = perf.get_domain_success_rate(domain) * 0.3
            performance_score = success_component + quality_component + domain_success
        else:
            # New model: use base quality from profile
            performance_score = profile.get("base_quality", 0.5)
        
        # Accuracy adjustment based on slider
        # High accuracy = prefer larger models, lower speed requirement
        # Low accuracy = prefer smaller models, higher speed
        size = profile.get("size", "medium")
        speed_rating = profile.get("speed_rating", 0.7)
        
        if accuracy_level >= 4:
            # High accuracy mode: prefer large models
            if size == "large":
                accuracy_adjustment = 0.3
            elif size == "medium":
                accuracy_adjustment = 0.1
            else:
                accuracy_adjustment = -0.1  # Penalize small models
            speed_adjustment = 0.0  # Don't care about speed
        elif accuracy_level <= 2:
            # Speed mode: prefer small/fast models
            if size == "small":
                accuracy_adjustment = 0.2
            elif size == "medium":
                accuracy_adjustment = 0.1
            else:
                accuracy_adjustment = -0.2  # Penalize large models for speed mode
            speed_adjustment = speed_rating * 0.3
        else:
            # Balanced mode
            accuracy_adjustment = 0.0
            speed_adjustment = speed_rating * 0.15
        
        # =====================================================================
        # PR5: Cost-aware scoring
        # =====================================================================
        cost_per_1m_input = profile.get("cost_per_1m_input", 1.0)
        cost_per_1m_output = profile.get("cost_per_1m_output", 1.0)
        
        # Estimate cost based on expected tokens (assuming 50% input, 50% output)
        estimated_input_tokens = budget.estimated_tokens // 2
        estimated_output_tokens = budget.estimated_tokens // 2
        estimated_cost_usd = (
            (estimated_input_tokens / 1_000_000) * cost_per_1m_input +
            (estimated_output_tokens / 1_000_000) * cost_per_1m_output
        )
        
        # Calculate cost adjustment
        cost_adjustment = 0.0
        if budget.max_cost_usd > 0:
            # Penalize models that exceed budget
            if estimated_cost_usd > budget.max_cost_usd:
                # Strong penalty for exceeding budget
                cost_adjustment = -0.5 * (estimated_cost_usd / budget.max_cost_usd)
                logger.debug(
                    "PR5: Model %s exceeds budget (%.4f > %.2f), penalty=%.2f",
                    model, estimated_cost_usd, budget.max_cost_usd, cost_adjustment
                )
            else:
                # Reward cheaper models (normalized 0-1 based on budget utilization)
                budget_utilization = estimated_cost_usd / budget.max_cost_usd
                cost_savings_bonus = (1.0 - budget_utilization) * budget.cost_weight
                cost_adjustment = cost_savings_bonus
        
        # Extra bonus for cheap models if prefer_cheaper is set
        if budget.prefer_cheaper:
            # Normalize cost relative to the most expensive model profile
            max_cost = max(
                p.get("cost_per_1m_input", 0) + p.get("cost_per_1m_output", 0)
                for p in self.profiles.values()
            ) or 1.0
            model_cost = cost_per_1m_input + cost_per_1m_output
            relative_cheapness = 1.0 - (model_cost / max_cost)
            cost_adjustment += relative_cheapness * 0.2  # Up to 20% bonus
        
        # Calculate total score with cost component
        total_score = (
            domain_score * 0.25
            + performance_score * 0.4
            + accuracy_adjustment
            + speed_adjustment
            + cost_adjustment
        )
        
        # Clamp to 0-1
        total_score = max(0.0, min(1.0, total_score))
        
        reasoning = (
            f"domain={domain_score:.2f}, perf={performance_score:.2f}, "
            f"acc_adj={accuracy_adjustment:.2f}, speed_adj={speed_adjustment:.2f}, "
            f"cost_adj={cost_adjustment:.2f}, est_cost=${estimated_cost_usd:.4f}"
        )
        
        return ModelScore(
            model=model,
            total_score=total_score,
            domain_score=domain_score,
            performance_score=performance_score,
            accuracy_adjustment=accuracy_adjustment,
            speed_adjustment=speed_adjustment,
            cost_adjustment=cost_adjustment,
            estimated_cost_usd=estimated_cost_usd,
            reasoning=reasoning,
        )
    
    def _assign_models_to_roles(
        self,
        roles: List[str],
        model_scores: List[ModelScore],
        accuracy_level: int,
    ) -> Dict[str, str]:
        """Assign models to roles based on role requirements and model capabilities."""
        assignments: Dict[str, str] = {}
        
        if not model_scores:
            return {role: "stub" for role in roles}
        
        # Role-to-capability mapping (DYNAMIC: uses catalog when available)
        role_preferences = self._get_dynamic_role_preferences()
        
        available_models = [s.model for s in model_scores]
        
        for role in roles:
            # Check role preferences
            prefs = role_preferences.get(role, [])
            assigned = None
            
            # Try preferred models first
            for pref in prefs:
                if pref in available_models:
                    assigned = pref
                    break
            
            # Fall back to role-level matching
            if not assigned:
                role_lower = role.lower()
                if "executive" in role_lower or "coordinator" in role_lower:
                    # Use top-scoring model for leadership roles
                    assigned = model_scores[0].model
                elif "assistant" in role_lower:
                    # Use smaller/faster model for assistant roles
                    small_models = [s.model for s in model_scores if self.profiles.get(s.model, {}).get("size") == "small"]
                    assigned = small_models[0] if small_models else model_scores[-1].model
                else:
                    # Use second-best model for specialist roles
                    assigned = model_scores[1].model if len(model_scores) > 1 else model_scores[0].model
            
            # Apply accuracy level adjustments
            if accuracy_level >= 5 and role in ["executive", "coordinator", "synthesizer"]:
                # For max accuracy, try to use the best model for key roles
                assigned = model_scores[0].model
            
            assignments[role] = assigned or "stub"
            
            # For high accuracy, assign secondary model for cross-checking
            if accuracy_level == 5:
                secondary_key = f"{role}_secondary"
                secondary_models = [s.model for s in model_scores if s.model != assigned]
                if secondary_models:
                    assignments[secondary_key] = secondary_models[0]
        
        return assignments
    
    def cascade_selection(
        self,
        query: str,
        initial_model: str,
        confidence_threshold: float = 0.7,
        available_models: Optional[List[str]] = None,
    ) -> Tuple[str, bool]:
        """
        Cascading model selection: start with lightweight, escalate if confidence is low.
        
        Args:
            query: The query to process
            initial_model: Initial lightweight model to try
            confidence_threshold: Minimum confidence to accept result
            available_models: Available model names
            
        Returns:
            Tuple of (selected_model, escalated)
        """
        # Get model size
        profile = self.profiles.get(initial_model, {})
        size = profile.get("size", "medium")
        
        # If already using large model, no escalation needed
        if size == "large":
            return (initial_model, False)
        
        # Check historical confidence for this model
        perf = performance_tracker.snapshot().get(initial_model)
        if perf:
            avg_quality = perf.avg_quality
            if avg_quality >= confidence_threshold:
                # Model historically performs well, use it
                return (initial_model, False)
        
        # Escalate to larger model (DYNAMIC: uses catalog when available)
        escalated_model = self._get_dynamic_escalation_target(initial_model)
        if escalated_model and (available_models is None or escalated_model in available_models):
            logger.info(
                "Cascading from %s to %s (confidence below %.2f)",
                initial_model,
                escalated_model,
                confidence_threshold,
            )
            return (escalated_model, True)
        
        # No escalation available
        return (initial_model, False)


# Global router instance
_adaptive_router: Optional[AdaptiveModelRouter] = None


def get_adaptive_router(
    *,
    use_openrouter_rankings: bool = False,
    db_session: Optional["Session"] = None,
) -> AdaptiveModelRouter:
    """Get the global adaptive router instance.
    
    Args:
        use_openrouter_rankings: Enable dynamic selection from OpenRouter
        db_session: Database session for OpenRouter rankings
        
    Returns:
        AdaptiveModelRouter instance
    """
    global _adaptive_router
    
    # Recreate if switching to dynamic mode
    if use_openrouter_rankings and _adaptive_router is not None:
        if not _adaptive_router.use_openrouter_rankings:
            _adaptive_router = None
    
    if _adaptive_router is None:
        _adaptive_router = AdaptiveModelRouter(
            use_openrouter_rankings=use_openrouter_rankings,
            db_session=db_session,
        )
    
    return _adaptive_router


def select_models_adaptive(
    refined_query: str,
    roles: List[str],
    accuracy_level: int,
    *,
    available_models: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Convenience function for adaptive model selection (static mode).
    
    Args:
        refined_query: The refined query to process
        roles: List of role names that need model assignment
        accuracy_level: Slider value 1-5 (1=fastest, 5=most accurate)
        available_models: Optional list of available model names
        
    Returns:
        Dictionary mapping role names to model names
    """
    router = get_adaptive_router()
    result = router.select_models_adaptive(
        refined_query,
        roles,
        accuracy_level,
        available_models=available_models,
    )
    return result.role_assignments


async def select_models_dynamic(
    refined_query: str,
    roles: List[str],
    accuracy_level: int,
    *,
    available_models: Optional[List[str]] = None,
    strategy: str = "automatic",
    db_session: Optional["Session"] = None,
) -> Dict[str, str]:
    """
    Convenience function for dynamic model selection with OpenRouter rankings.
    
    This is the async version that fetches real-time rankings from OpenRouter.
    Use this when you want to leverage the latest model performance data.
    
    Args:
        refined_query: The refined query to process
        roles: List of role names that need model assignment
        accuracy_level: Slider value 1-5 (1=fastest, 5=most accurate)
        available_models: Optional list of available model names
        strategy: Selection strategy ("automatic", "quality", "speed", "value")
        db_session: Database session for OpenRouter rankings
        
    Returns:
        Dictionary mapping role names to model names
    """
    router = get_adaptive_router(
        use_openrouter_rankings=True,
        db_session=db_session,
    )
    
    result = await router.select_models_dynamic(
        refined_query,
        roles,
        accuracy_level,
        available_models=available_models,
        strategy=strategy,
    )
    return result.role_assignments


def infer_domain(query: str) -> str:
    """Infer the domain of a query."""
    router = get_adaptive_router()
    return router.infer_domain(query)

