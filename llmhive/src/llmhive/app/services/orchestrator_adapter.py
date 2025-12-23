"""Adapter service to bridge ChatRequest to internal orchestrator.

Enhanced with Elite Orchestration for maximum performance:
- PromptOps preprocessing (ALWAYS ON)
- Intelligent model-task matching
- Quality-weighted fusion
- Parallel execution
- Challenge and refine strategies
- Verification gate with retry
- Answer refinement (ALWAYS ON)
"""
from __future__ import annotations

import json
import logging
import time
import os
from typing import Dict, Any, List, Optional, Tuple

from ..models.orchestration import (
    ChatRequest,
    ChatResponse,
    AgentTrace,
    ReasoningMode,
    ReasoningMethod,
    DomainPack,
    AgentMode,
)
from ..orchestrator import Orchestrator
# profiles_firestore requires google-cloud-firestore which may not be available
try:
    from ..profiles_firestore import get_profile
    PROFILES_AVAILABLE = True
except ImportError:
    get_profile = lambda x: None  # type: ignore
    PROFILES_AVAILABLE = False
from ..audit_log import log_audit_event
from .model_router import (
    get_models_for_reasoning_method,
    map_reasoning_mode_to_method,
    ReasoningMethod as RouterReasoningMethod,
    FALLBACK_GPT_4O,
    FALLBACK_GPT_4O_MINI,
    FALLBACK_CLAUDE_SONNET_4,
    FALLBACK_CLAUDE_3_5,
    FALLBACK_CLAUDE_3_HAIKU,
    FALLBACK_GEMINI_2_5,
    FALLBACK_GEMINI_2_5_FLASH,
    FALLBACK_GROK_2,
    FALLBACK_GROK_BETA,
    FALLBACK_DEEPSEEK,
    # Automatic model selection functions
    get_best_models_for_task,
    get_diverse_ensemble,
    MODEL_CAPABILITIES,
)
from .reasoning_prompts import get_reasoning_prompt_template

# Import Clarification Manager for ambiguity detection
try:
    from ..orchestration.clarification_manager import (
        ClarificationManager,
        ClarificationStatus,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError:
    CLARIFICATION_AVAILABLE = False
    ClarificationManager = None

# Import ModelKnowledgeStore for Pinecone-backed intelligent model selection
try:
    from ..knowledge.model_knowledge_store import (
        ModelKnowledgeStore,
        get_model_knowledge_store,
    )
    MODEL_KNOWLEDGE_AVAILABLE = True
except ImportError:
    MODEL_KNOWLEDGE_AVAILABLE = False
    ModelKnowledgeStore = None
    get_model_knowledge_store = None

# Import comprehensive model intelligence for deep orchestration decisions
try:
    from ..knowledge.model_intelligence import (
        MODEL_PROFILES,
        REASONING_METHODS,
        REASONING_HACKS,
        TEAM_STRATEGIES,
        get_model_profile,
        get_best_models_for_task as get_intelligent_best_models,
        get_team_for_task,
        get_reasoning_hack,
        ModelTier,
    )
    MODEL_INTELLIGENCE_AVAILABLE = True
except ImportError:
    MODEL_INTELLIGENCE_AVAILABLE = False
    MODEL_PROFILES = {}
    REASONING_METHODS = {}
    REASONING_HACKS = {}
    TEAM_STRATEGIES = {}
    get_model_profile = lambda x: None
    get_intelligent_best_models = lambda *a, **k: []
    get_team_for_task = lambda x: None
    get_reasoning_hack = lambda *a: None
    ModelTier = None

# Import Elite Orchestrator and Quality Booster
try:
    from ..orchestration.elite_orchestrator import (
        EliteOrchestrator,
        EliteResult,
        get_best_model_for_task,
    )
    ELITE_AVAILABLE = True
except ImportError:
    ELITE_AVAILABLE = False
    EliteOrchestrator = None

try:
    from ..orchestration.quality_booster import (
        QualityBooster,
        boost_response,
    )
    QUALITY_BOOSTER_AVAILABLE = True
except ImportError:
    QUALITY_BOOSTER_AVAILABLE = False
    QualityBooster = None

# Import PromptOps for always-on preprocessing
try:
    from ..orchestration.prompt_ops import PromptOps, PromptSpecification
    PROMPTOPS_AVAILABLE = True
except ImportError:
    PROMPTOPS_AVAILABLE = False
    PromptOps = None
    PromptSpecification = None

# Import Answer Refiner for polishing
try:
    from ..orchestration.answer_refiner import (
        AnswerRefiner,
        RefinementConfig,
        OutputFormat,
        ToneStyle,
    )
    REFINER_AVAILABLE = True
except ImportError:
    REFINER_AVAILABLE = False
    AnswerRefiner = None

# Import Prompt Templates for verification
try:
    from ..orchestration.prompt_templates import build_verifier_prompt
    VERIFIER_PROMPT_AVAILABLE = True
except ImportError:
    VERIFIER_PROMPT_AVAILABLE = False

# Import Tool Verification for math, code, and factual verification
try:
    from ..orchestration.tool_verification import (
        get_verification_pipeline,
        VerificationPipeline,
        VerificationType,
    )
    TOOL_VERIFICATION_AVAILABLE = True
except ImportError:
    TOOL_VERIFICATION_AVAILABLE = False
    get_verification_pipeline = None

# Import Tool Broker for automatic tool detection and execution
try:
    from ..orchestration.tool_broker import (
        get_tool_broker,
        ToolBroker,
        ToolType,
        ToolAnalysis,
        check_and_execute_tools,
    )
    TOOL_BROKER_AVAILABLE = True
except ImportError:
    TOOL_BROKER_AVAILABLE = False
    get_tool_broker = None

# PR5: Import budget-aware routing
try:
    from ..orchestration.adaptive_router import (
        BudgetConstraints,
        get_adaptive_router,
    )
    BUDGET_ROUTING_AVAILABLE = True
except ImportError:
    BUDGET_ROUTING_AVAILABLE = False
    BudgetConstraints = None

# Import Pinecone Knowledge Base for RAG and learning
try:
    from ..knowledge.pinecone_kb import (
        get_knowledge_base,
        PineconeKnowledgeBase,
        RecordType,
    )
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    get_knowledge_base = None

# Import cascade router and reasoning detector for intelligent routing
try:
    from ..orchestration.cascade_router import CascadeRouter, QueryComplexity
    from ..orchestration.reasoning_detector import ReasoningDetector, ReasoningType
    CASCADE_ROUTING_AVAILABLE = True
except ImportError:
    CASCADE_ROUTING_AVAILABLE = False
    CascadeRouter = None  # type: ignore
    ReasoningDetector = None  # type: ignore
    QueryComplexity = None  # type: ignore
    ReasoningType = None  # type: ignore

logger = logging.getLogger(__name__)

# Configuration
MAX_CHALLENGE_LOOPS = 2  # Max retry attempts on verification failure
VERIFICATION_ENABLED = True  # Enable verification gate
REFINER_ALWAYS_ON = True  # Always run answer refinement

# Global orchestrator instance
_orchestrator = Orchestrator()

# Elite orchestrator instance (initialized on first use)
_elite_orchestrator: Optional[EliteOrchestrator] = None
_quality_booster: Optional[QualityBooster] = None


def _get_elite_orchestrator() -> Optional[EliteOrchestrator]:
    """Get or create elite orchestrator instance."""
    global _elite_orchestrator
    if _elite_orchestrator is None and ELITE_AVAILABLE:
        _elite_orchestrator = EliteOrchestrator(
            providers=_orchestrator.providers,
            performance_tracker=getattr(_orchestrator, 'performance_tracker', None),
            enable_learning=True,
        )
        logger.info("Elite orchestrator initialized")
    return _elite_orchestrator


# ==============================================================================
# INTELLIGENT PINECONE-BACKED MODEL SELECTION
# ==============================================================================

# Actual OpenRouter model IDs (VERIFIED December 2025)
# These MUST match exactly what OpenRouter returns from /api/v1/models
OPENROUTER_GPT_5 = "openai/gpt-5"                        # ✓ Verified
OPENROUTER_CLAUDE_OPUS_4 = "anthropic/claude-opus-4"    # ✓ Verified (no date suffix)
OPENROUTER_GEMINI_2_PRO = "google/gemini-2.5-pro"       # ✓ Verified (2.5, not 2.0)
OPENROUTER_CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4"  # ✓ Verified (no date suffix)
OPENROUTER_O3 = "openai/o3"                              # ✓ Verified (o3 is latest reasoning)
OPENROUTER_O1 = "openai/o1-pro"                          # ✓ Verified (o1-pro available)
OPENROUTER_LLAMA_4 = "meta-llama/llama-4-maverick"       # ✓ Verified (maverick variant)
OPENROUTER_MISTRAL_LARGE = "mistralai/mistral-large-2512"  # ✓ Verified
OPENROUTER_GPT_4O = "openai/gpt-4o"                      # ✓ Verified (still available)
OPENROUTER_DEEPSEEK = "deepseek/deepseek-v3.2"           # ✓ Verified (v3.2 is latest)
OPENROUTER_DEEPSEEK_R1 = "deepseek/deepseek-r1-0528"     # ✓ Verified (reasoning model)
OPENROUTER_GROK_4 = "x-ai/grok-4"                        # ✓ Verified (grok-4 is latest)
OPENROUTER_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"  # ✓ Verified
OPENROUTER_GEMINI_3_PRO = "google/gemini-3-pro-preview"  # ✓ Verified (newest)

# Define model strengths for complementary selection (matching ACTUAL OpenRouter models)
MODEL_STRENGTHS = {
    # ===== TOP TIER (verified December 2025) =====
    OPENROUTER_GPT_5: {
        "strengths": ["reasoning", "coding", "analysis", "general", "factual"],
        "provider": "openai", "tier": "flagship", "rank": 1
    },
    OPENROUTER_CLAUDE_OPUS_4: {
        "strengths": ["reasoning", "creative", "analysis", "medical", "legal"],
        "provider": "anthropic", "tier": "flagship", "rank": 2
    },
    OPENROUTER_GEMINI_2_PRO: {
        "strengths": ["reasoning", "factual", "analysis", "multimodal", "research"],
        "provider": "google", "tier": "flagship", "rank": 3
    },
    OPENROUTER_GEMINI_3_PRO: {
        "strengths": ["reasoning", "factual", "analysis", "multimodal", "research", "medical"],
        "provider": "google", "tier": "flagship", "rank": 4
    },
    OPENROUTER_CLAUDE_SONNET_4: {
        "strengths": ["reasoning", "creative", "coding", "analysis"],
        "provider": "anthropic", "tier": "flagship", "rank": 5
    },
    
    # ===== REASONING SPECIALISTS =====
    OPENROUTER_O3: {
        "strengths": ["reasoning", "math", "coding", "logic", "analysis", "research"],
        "provider": "openai", "tier": "reasoning", "rank": 6
    },
    OPENROUTER_O1: {
        "strengths": ["reasoning", "math", "coding", "logic", "analysis"],
        "provider": "openai", "tier": "reasoning", "rank": 7
    },
    OPENROUTER_DEEPSEEK_R1: {
        "strengths": ["reasoning", "math", "coding", "logic"],
        "provider": "deepseek", "tier": "reasoning", "rank": 8
    },
    
    # ===== OTHER TOP MODELS =====
    OPENROUTER_LLAMA_4: {
        "strengths": ["reasoning", "coding", "general", "open-source"],
        "provider": "meta", "tier": "flagship", "rank": 9
    },
    OPENROUTER_MISTRAL_LARGE: {
        "strengths": ["reasoning", "coding", "multilingual", "analysis"],
        "provider": "mistral", "tier": "flagship", "rank": 10
    },
    
    # ===== STILL AVAILABLE (legacy/fallback) =====
    OPENROUTER_GPT_4O: {
        "strengths": ["reasoning", "coding", "analysis", "general"],
        "provider": "openai", "tier": "flagship", "rank": 11
    },
    OPENROUTER_DEEPSEEK: {
        "strengths": ["coding", "math", "reasoning"],
        "provider": "deepseek", "tier": "specialized", "rank": 12
    },
    OPENROUTER_GROK_4: {
        "strengths": ["factual", "realtime", "creative", "reasoning"],
        "provider": "xai", "tier": "flagship", "rank": 13
    },
    
    # ===== FAST MODELS =====
    OPENROUTER_GEMINI_2_5_FLASH: {
        "strengths": ["speed", "factual", "general"],
        "provider": "google", "tier": "fast", "rank": 20
    },
}

# Map domains to required strengths
DOMAIN_REQUIRED_STRENGTHS = {
    "health_medical": ["medical", "reasoning", "factual", "analysis"],
    "legal_analysis": ["reasoning", "analysis", "factual", "legal"],
    "financial_analysis": ["math", "analysis", "reasoning"],
    "science_research": ["analysis", "factual", "reasoning", "research"],
    "code_generation": ["coding", "reasoning"],
    "debugging": ["coding", "analysis"],
    "math_problem": ["math", "reasoning", "logic"],
    "creative_writing": ["creative", "reasoning"],
    "factual_question": ["factual", "reasoning"],
    "research_analysis": ["analysis", "reasoning", "factual", "research"],
    "general": ["reasoning", "general"],
}

# Domain-specific top models (VERIFIED against actual OpenRouter models)
DOMAIN_TOP_MODELS = {
    "health_medical": [
        OPENROUTER_GPT_5,           # #1 overall
        OPENROUTER_CLAUDE_OPUS_4,   # #2 - excellent for medical reasoning
        OPENROUTER_GEMINI_3_PRO,    # #3 - newest Google model
        OPENROUTER_GEMINI_2_PRO,    # #4 - strong for factual/research
    ],
    "legal_analysis": [
        OPENROUTER_CLAUDE_OPUS_4,   # Best for legal reasoning
        OPENROUTER_GPT_5,
        OPENROUTER_O3,              # Strong reasoning model
    ],
    "financial_analysis": [
        OPENROUTER_O3,              # Math + reasoning specialist
        OPENROUTER_GPT_5,
        OPENROUTER_CLAUDE_OPUS_4,
        OPENROUTER_DEEPSEEK_R1,     # Good at math
    ],
    "science_research": [
        OPENROUTER_GEMINI_3_PRO,    # Newest, strong for research
        OPENROUTER_GEMINI_2_PRO,    # Strong for research
        OPENROUTER_CLAUDE_OPUS_4,
        OPENROUTER_GPT_5,
    ],
    "code_generation": [
        OPENROUTER_CLAUDE_SONNET_4, # Best for coding
        OPENROUTER_GPT_5,
        OPENROUTER_DEEPSEEK,        # Specialized for coding
        OPENROUTER_DEEPSEEK_R1,     # Reasoning + coding
    ],
    "debugging": [
        OPENROUTER_CLAUDE_SONNET_4,
        OPENROUTER_DEEPSEEK,
        OPENROUTER_GPT_5,
    ],
    "math_problem": [
        OPENROUTER_O3,              # Best reasoning specialist
        OPENROUTER_DEEPSEEK_R1,     # Reasoning model
        OPENROUTER_GPT_5,
        OPENROUTER_GEMINI_2_PRO,
    ],
    "creative_writing": [
        OPENROUTER_CLAUDE_OPUS_4,   # Best for creative
        OPENROUTER_CLAUDE_SONNET_4,
        OPENROUTER_GPT_5,
    ],
    "factual_question": [
        OPENROUTER_GPT_5,
        OPENROUTER_GEMINI_3_PRO,
        OPENROUTER_GROK_4,          # Real-time knowledge
    ],
    "general": [
        OPENROUTER_GPT_5,
        OPENROUTER_CLAUDE_OPUS_4,
        OPENROUTER_GEMINI_2_PRO,
    ],
}

# Models with tool/function calling support (VERIFIED against OpenRouter)
TOOL_CAPABLE_MODELS = {
    OPENROUTER_GPT_5,
    OPENROUTER_GPT_4O,
    OPENROUTER_O3,
    OPENROUTER_O1,
    OPENROUTER_CLAUDE_OPUS_4,
    OPENROUTER_CLAUDE_SONNET_4,
    OPENROUTER_GEMINI_3_PRO,
    OPENROUTER_GEMINI_2_PRO,
    OPENROUTER_GEMINI_2_5_FLASH,
    OPENROUTER_LLAMA_4,
    OPENROUTER_MISTRAL_LARGE,
    OPENROUTER_GROK_4,
    OPENROUTER_DEEPSEEK,
}


async def get_intelligent_models(
    task_type: str,
    num_models: int = 3,
    require_tools: bool = False,
    available_models: Optional[List[str]] = None,
    accuracy_priority: bool = True,
) -> List[str]:
    """
    Intelligent model selection using COMPREHENSIVE MODEL INTELLIGENCE:
    1. Deep model profiles (strengths, weaknesses, costs, latency)
    2. Team composition strategies
    3. Domain-specific top models (from OpenRouter rankings)
    4. Pinecone category rankings
    5. Complementary model strengths (provider diversity)
    6. Tool support filtering
    
    Args:
        task_type: The detected task type (from PromptOps)
        num_models: Number of models to select
        require_tools: If True, only select models with tool support
        available_models: Limit selection to these models
        accuracy_priority: If True, prioritize accuracy over speed
        
    Returns:
        List of model IDs optimized for the task
    """
    selected = []
    used_providers = set()
    
    # ===========================================================================
    # STEP 0: Use comprehensive MODEL_INTELLIGENCE if available
    # ===========================================================================
    if MODEL_INTELLIGENCE_AVAILABLE and MODEL_PROFILES:
        # Try to get a team strategy first
        team_strategy = get_team_for_task(task_type)
        if team_strategy and accuracy_priority:
            logger.info(
                "Using team strategy '%s' for %s: %s",
                team_strategy.name, task_type, team_strategy.models
            )
            for model_id in team_strategy.models:
                if len(selected) >= num_models:
                    break
                if require_tools:
                    profile = get_model_profile(model_id)
                    if profile and not profile.supports_tools:
                        continue
                if available_models is not None and model_id not in available_models:
                    continue
                
                profile = get_model_profile(model_id)
                if profile:
                    provider = profile.provider.lower()
                    if provider not in used_providers or len(selected) < 2:
                        selected.append(model_id)
                        used_providers.add(provider)
            
            if selected:
                logger.info(
                    "Team strategy selected for %s: %s (roles: %s)",
                    task_type, selected, 
                    {m: team_strategy.roles.get(m, "member") for m in selected}
                )
                return selected[:num_models]
        
        # Fall back to intelligent best models from profiles
        if not selected:
            max_tier = ModelTier.FLAGSHIP if accuracy_priority else ModelTier.BALANCED
            profile_selected = get_intelligent_best_models(
                task_type,
                num_models=num_models,
                max_cost_tier=max_tier,
                require_tools=require_tools,
            )
            if profile_selected:
                for model_id in profile_selected:
                    if available_models is not None and model_id not in available_models:
                        continue
                    profile = get_model_profile(model_id)
                    if profile:
                        provider = profile.provider.lower()
                        if provider not in used_providers or len(selected) < 2:
                            selected.append(model_id)
                            used_providers.add(provider)
                
                if selected:
                    logger.info(
                        "MODEL_PROFILES selected for %s: %s",
                        task_type, selected
                    )
                    return selected[:num_models]
    
    # ===========================================================================
    # STEP 1: Use domain-specific top models (fallback from OpenRouter rankings)
    # ===========================================================================
    domain_top = DOMAIN_TOP_MODELS.get(task_type, DOMAIN_TOP_MODELS.get("general", []))
    for model_id in domain_top:
        if len(selected) >= num_models:
            break
        if require_tools and model_id not in TOOL_CAPABLE_MODELS:
            continue
        if available_models is not None and model_id not in available_models:
            continue
        
        model_info = MODEL_STRENGTHS.get(model_id, {})
        provider = model_info.get("provider", "unknown")
        
        # Ensure provider diversity
        if provider not in used_providers or len(selected) < 2:
            selected.append(model_id)
            used_providers.add(provider)
    
    if selected:
        logger.info(
            "Domain-specific models for %s: %s (from OpenRouter rankings)",
            task_type, selected
        )
    
    # Step 1: Supplement with Pinecone category rankings if needed
    if len(selected) < num_models and MODEL_KNOWLEDGE_AVAILABLE and get_model_knowledge_store is not None:
        try:
            store = get_model_knowledge_store()
            # Get category-specific rankings
            rankings = await store.get_best_models_for_task(
                task_description=task_type,
                category=task_type,
                top_k=num_models * 2,  # Get extra for filtering
                require_tools=require_tools,
            )
            
            if rankings:
                for record in rankings:
                    model_id = record.model_id
                    if model_id and model_id not in selected and len(selected) < num_models:
                        # Check if available
                        if available_models is None or model_id in available_models:
                            # Ensure provider diversity
                            model_info = MODEL_STRENGTHS.get(model_id, {})
                            provider = model_info.get("provider", "unknown")
                            
                            if provider not in used_providers or len(used_providers) >= 3:
                                selected.append(model_id)
                                used_providers.add(provider)
                
                if len(selected) > len(domain_top):
                    logger.info(
                        "Pinecone added %d more models for %s",
                        len(selected) - len(domain_top), task_type
                    )
        except Exception as e:
            logger.warning("Pinecone model selection failed, using fallback: %s", e)
    
    # Step 2: Add complementary models based on required strengths
    required_strengths = DOMAIN_REQUIRED_STRENGTHS.get(task_type, ["reasoning", "general"])
    
    # Score remaining models by strength match + diversity
    candidates = []
    for model_id, info in MODEL_STRENGTHS.items():
        if model_id in selected:
            continue
        if available_models is not None and model_id not in available_models:
            continue
        if require_tools and model_id not in TOOL_CAPABLE_MODELS:
            continue
            
        # Calculate strength match score
        model_strengths = set(info.get("strengths", []))
        match_score = len(model_strengths & set(required_strengths))
        
        # Bonus for provider diversity
        provider = info.get("provider", "unknown")
        diversity_bonus = 2 if provider not in used_providers else 0
        
        # Tier bonus (flagship > specialized > fast for accuracy)
        tier = info.get("tier", "fast")
        if accuracy_priority:
            tier_bonus = {"flagship": 3, "specialized": 2, "fast": 0}.get(tier, 0)
        else:
            tier_bonus = {"flagship": 1, "specialized": 1, "fast": 3}.get(tier, 0)
        
        total_score = match_score + diversity_bonus + tier_bonus
        candidates.append((model_id, total_score, provider))
    
    # Sort by score and add to selection
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    for model_id, score, provider in candidates:
        if len(selected) >= num_models:
            break
        selected.append(model_id)
        used_providers.add(provider)
    
    # Step 3: Fallback to OpenRouter top-ranked models (VERIFIED December 2025)
    if len(selected) < num_models:
        # Use actual OpenRouter ranking order (verified against /api/v1/models)
        fallback_order = [
            OPENROUTER_GPT_5,           # #1
            OPENROUTER_CLAUDE_OPUS_4,   # #2
            OPENROUTER_GEMINI_3_PRO,    # #3 newest
            OPENROUTER_GEMINI_2_PRO,    # #4
            OPENROUTER_CLAUDE_SONNET_4, # #5
            OPENROUTER_O3,              # #6 reasoning
            OPENROUTER_LLAMA_4,         # #7
            OPENROUTER_MISTRAL_LARGE,   # #8
            OPENROUTER_GROK_4,          # #9
            OPENROUTER_GPT_4O,          # fallback
        ]
        for model_id in fallback_order:
            if model_id not in selected and len(selected) < num_models:
                if available_models is None or model_id in available_models:
                    if not require_tools or model_id in TOOL_CAPABLE_MODELS:
                        selected.append(model_id)
    
    logger.info(
        "Intelligent model selection for '%s': %d models, require_tools=%s -> %s",
        task_type, num_models, require_tools, selected
    )
    
    return selected[:num_models]


def get_intelligent_models_sync(
    task_type: str,
    num_models: int = 3,
    require_tools: bool = False,
    available_models: Optional[List[str]] = None,
    accuracy_priority: bool = True,
) -> List[str]:
    """
    Synchronous wrapper for intelligent model selection.
    Uses local knowledge when Pinecone is not available.
    """
    import asyncio
    
    # Try async version first
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - use sync fallback
            return _get_intelligent_models_local(
                task_type, num_models, require_tools, available_models, accuracy_priority
            )
        else:
            return loop.run_until_complete(
                get_intelligent_models(
                    task_type, num_models, require_tools, available_models, accuracy_priority
                )
            )
    except RuntimeError:
        # No event loop - use sync fallback
        return _get_intelligent_models_local(
            task_type, num_models, require_tools, available_models, accuracy_priority
        )


def _get_intelligent_models_local(
    task_type: str,
    num_models: int = 3,
    require_tools: bool = False,
    available_models: Optional[List[str]] = None,
    accuracy_priority: bool = True,
) -> List[str]:
    """
    Local (non-Pinecone) intelligent model selection.
    Uses DOMAIN_TOP_MODELS first, then MODEL_STRENGTHS for supplementary selection.
    """
    selected = []
    used_providers = set()
    
    # Step 0: Use domain-specific top models FIRST (from OpenRouter rankings)
    domain_top = DOMAIN_TOP_MODELS.get(task_type, DOMAIN_TOP_MODELS.get("general", []))
    for model_id in domain_top:
        if len(selected) >= num_models:
            break
        if require_tools and model_id not in TOOL_CAPABLE_MODELS:
            continue
        if available_models is not None and model_id not in available_models:
            continue
        
        model_info = MODEL_STRENGTHS.get(model_id, {})
        provider = model_info.get("provider", "unknown")
        
        if provider not in used_providers or len(selected) < 2:
            selected.append(model_id)
            used_providers.add(provider)
    
    # If we need more, score remaining models by strength match
    if len(selected) < num_models:
        required_strengths = DOMAIN_REQUIRED_STRENGTHS.get(task_type, ["reasoning", "general"])
        
        candidates = []
        for model_id, info in MODEL_STRENGTHS.items():
            if model_id in selected:
                continue
            if available_models is not None and model_id not in available_models:
                continue
            if require_tools and model_id not in TOOL_CAPABLE_MODELS:
                continue
            
            model_strengths = set(info.get("strengths", []))
            match_score = len(model_strengths & set(required_strengths))
            
            provider = info.get("provider", "unknown")
            diversity_bonus = 2 if provider not in used_providers else 0
            
            # Use rank if available (lower is better)
            rank = info.get("rank", 99)
            rank_bonus = max(0, 10 - rank)  # Higher bonus for lower rank
            
            tier = info.get("tier", "fast")
            if accuracy_priority:
                tier_bonus = {"flagship": 3, "reasoning": 4, "specialized": 2, "fast": 0}.get(tier, 0)
            else:
                tier_bonus = {"flagship": 1, "reasoning": 1, "specialized": 1, "fast": 3}.get(tier, 0)
            
            total_score = match_score + diversity_bonus + tier_bonus + rank_bonus
            candidates.append((model_id, total_score, provider))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        for model_id, score, provider in candidates:
            if len(selected) >= num_models:
                break
            selected.append(model_id)
            used_providers.add(provider)
    
    # Fallback - use actual OpenRouter top-ranked models
    if len(selected) < num_models:
        fallback_order = [
            OPENROUTER_GPT_5,
            OPENROUTER_CLAUDE_OPUS_4,
            OPENROUTER_GEMINI_2_PRO,
            OPENROUTER_CLAUDE_SONNET_4,
            OPENROUTER_O1,
        ]
        for model_id in fallback_order:
            if model_id not in selected and len(selected) < num_models:
                if available_models is None or model_id in available_models:
                    selected.append(model_id)
    
    return selected[:num_models]


def _get_quality_booster() -> Optional[QualityBooster]:
    """Get or create quality booster instance."""
    global _quality_booster
    if _quality_booster is None and QUALITY_BOOSTER_AVAILABLE:
        _quality_booster = QualityBooster(
            providers=_orchestrator.providers,
            default_model="gpt-4o",
        )
        logger.info("Quality booster initialized")
    return _quality_booster


# Knowledge base instance
_knowledge_base: Optional[PineconeKnowledgeBase] = None

# Cascade router and reasoning detector instances
_cascade_router: Optional["CascadeRouter"] = None
_reasoning_detector: Optional["ReasoningDetector"] = None


def _get_cascade_router() -> Optional["CascadeRouter"]:
    """Get or create cascade router for cost-optimized model selection."""
    global _cascade_router
    if _cascade_router is None and CASCADE_ROUTING_AVAILABLE:
        _cascade_router = CascadeRouter()
        logger.info("Cascade router initialized for cost-optimized routing")
    return _cascade_router


def _get_reasoning_detector() -> Optional["ReasoningDetector"]:
    """Get or create reasoning detector for complex query detection."""
    global _reasoning_detector
    if _reasoning_detector is None and CASCADE_ROUTING_AVAILABLE:
        _reasoning_detector = ReasoningDetector()
        logger.info("Reasoning detector initialized")
    return _reasoning_detector


def _get_knowledge_base() -> Optional[PineconeKnowledgeBase]:
    """Get or create knowledge base instance for RAG and learning."""
    global _knowledge_base
    if _knowledge_base is None and KNOWLEDGE_BASE_AVAILABLE:
        _knowledge_base = get_knowledge_base()
        logger.info("Knowledge base initialized")
    return _knowledge_base


async def _augment_with_rag(
    prompt: str,
    domain: str = "default",
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> str:
    """Augment prompt with relevant context from knowledge base."""
    kb = _get_knowledge_base()
    if not kb:
        return prompt
    
    try:
        verification_result = None
        refined_text = None
        selected_strategy = "standard"
        augmented = await kb.augment_prompt(
            query=prompt,
            domain=domain,
            user_id=user_id,
            project_id=project_id,
            org_id=org_id,
            max_context_length=1500,
        )
        if augmented != prompt:
            logger.info("Prompt augmented with RAG context")
        return augmented
    except Exception as e:
        logger.warning(f"RAG augmentation failed: {e}")
        return prompt


async def _store_answer_for_learning(
    query: str,
    answer: str,
    models_used: List[str],
    quality_score: float,
    domain: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    org_id: Optional[str] = None,
    is_partial: bool = False,
    record_type: Optional[RecordType] = None,
) -> None:
    """Store answer in knowledge base for future learning."""
    kb = _get_knowledge_base()
    if not kb:
        return
    
    try:
        record_type = record_type or (RecordType.PARTIAL_ANSWER if is_partial else RecordType.FINAL_ANSWER)
        await kb.store_answer(
            query=query,
            answer=answer,
            models_used=models_used,
            record_type=record_type,
            quality_score=quality_score,
            domain=domain,
            user_id=user_id,
            project_id=project_id,
            org_id=org_id,
        )
        logger.debug(f"Stored {'partial' if is_partial else 'final'} answer for learning")
    except Exception as e:
        logger.warning(f"Failed to store answer: {e}")


async def _learn_orchestration_pattern(
    query_type: str,
    strategy_used: str,
    models_used: List[str],
    success: bool,
    latency_ms: int,
    quality_score: float,
    user_id: Optional[str] = None,
) -> None:
    """Learn from orchestration pattern for future optimization."""
    kb = _get_knowledge_base()
    if not kb:
        return
    
    try:
        await kb.store_orchestration_pattern(
            query_type=query_type,
            strategy_used=strategy_used,
            models_used=models_used,
            success=success,
            latency_ms=latency_ms,
            quality_score=quality_score,
            user_id=user_id,
        )
        logger.debug(f"Learned orchestration pattern: {strategy_used} for {query_type}")
    except Exception as e:
        logger.warning(f"Failed to learn pattern: {e}")


def _detect_task_type(prompt: str) -> str:
    """Detect task type from prompt for optimal routing.
    
    Categories map to model capabilities and rankings for intelligent selection.
    """
    prompt_lower = prompt.lower()
    
    # Code/Programming - DeepSeek, Claude Sonnet 4, GPT-4o excel
    if any(kw in prompt_lower for kw in ["code", "function", "implement", "debug", "program", "script", "api", "backend", "frontend"]):
        return "code_generation"
    
    # Math/Quantitative - o1, GPT-4o, Gemini Pro excel
    elif any(kw in prompt_lower for kw in ["calculate", "solve", "math", "equation", "integral", "derivative", "proof"]):
        return "math_problem"
    
    # Health/Medical - Claude Opus 4, GPT-5, Med-PaLM 3 excel (requires accuracy)
    elif any(kw in prompt_lower for kw in [
        "treatment", "symptom", "diagnosis", "medical", "health", "disease", "medication",
        "drug", "therapy", "clinical", "patient", "headache", "pain", "condition",
        "doctor", "hospital", "illness", "chronic", "acute", "prognosis"
    ]):
        return "health_medical"
    
    # Science/Academic - Claude Opus 4, o1, Gemini Pro excel
    elif any(kw in prompt_lower for kw in [
        "scientific", "research", "study", "hypothesis", "experiment", "theory",
        "peer-reviewed", "journal", "academic", "physics", "chemistry", "biology"
    ]):
        return "science_research"
    
    # Legal - Claude models, GPT-4o excel (requires precision)
    elif any(kw in prompt_lower for kw in [
        "legal", "law", "contract", "liability", "court", "attorney", "lawsuit",
        "regulation", "compliance", "statute", "precedent", "jurisdiction"
    ]):
        return "legal_analysis"
    
    # Finance/Business - o1, Gemini Pro, GPT-4o excel
    elif any(kw in prompt_lower for kw in [
        "financial", "investment", "stock", "market", "portfolio", "valuation",
        "revenue", "profit", "budget", "accounting", "tax", "fiscal"
    ]):
        return "financial_analysis"
    
    # Creative Writing - Claude models excel
    elif any(kw in prompt_lower for kw in [
        "write", "story", "creative", "poem", "narrative", "fiction", "character"
    ]):
        return "creative_writing"
    
    # Research/Analysis - needs multi-model consensus
    elif any(kw in prompt_lower for kw in ["research", "analyze", "comprehensive", "in-depth", "latest", "developments"]):
        return "research_analysis"
    
    # Explanation - needs clarity
    elif any(kw in prompt_lower for kw in ["explain", "what is", "how does", "why"]):
        return "explanation"
    
    # Comparison - needs multi-perspective
    elif any(kw in prompt_lower for kw in ["compare", "versus", "difference", "pros and cons"]):
        return "comparison"
    
    elif any(kw in prompt_lower for kw in ["summarize", "summary", "tldr"]):
        return "summarization"
    elif any(kw in prompt_lower for kw in ["quick", "fast", "brief"]):
        return "fast_response"
    elif any(kw in prompt_lower for kw in ["detailed", "thorough", "complete"]):
        return "high_quality"
    else:
        return "general"


def _select_elite_strategy(
    accuracy_level: int,
    task_type: str,
    num_models: int,
    complexity: str = "moderate",
    criteria: Optional[dict] = None,
    prompt_spec: Optional[Any] = None,
) -> str:
    """Select the best elite orchestration strategy intelligently.
    
    Strategies (in order of quality vs. speed tradeoff):
    - single_best: Fastest - simple queries, single model (~100ms)
    - parallel_race: Fast - speed-critical, first-win (~150ms)
    - best_of_n: Medium - select best from multiple (~300ms)
    - quality_weighted_fusion: Balanced - combine perspectives (~400ms)
    - expert_panel: Thorough - multiple expert views (~600ms)
    - challenge_and_refine: Most thorough - verification loop (~800ms)
    
    Selection considers:
    - Task type (code/math need verification, research needs perspectives)
    - Complexity (simple → fast, complex → thorough)
    - Accuracy level (1-5, user preference)
    - User criteria (speed, accuracy, creativity weights)
    - PromptOps analysis (if available)
    """
    # Default criteria
    if not criteria:
        criteria = {"accuracy": 70, "speed": 50, "creativity": 50}
    
    speed_priority = criteria.get("speed", 50)
    accuracy_priority = criteria.get("accuracy", 70)
    creativity_priority = criteria.get("creativity", 50)
    
    # ========================================================================
    # PHASE 1: HARD RULES - ALL ACCURACY-CRITICAL DOMAINS GET EXPERT TREATMENT
    # ========================================================================
    
    # Code and math ALWAYS need verification (non-negotiable)
    if task_type in ["code_generation", "debugging", "math_problem"]:
        # But speed-optimize if user explicitly wants fast
        if speed_priority >= 80 and accuracy_level <= 2:
            logger.info("Strategy: Code/math with high speed priority -> best_of_n")
            return "best_of_n"  # Skip challenge loop but still compare
        logger.info("Strategy: Code/math task -> challenge_and_refine")
        return "challenge_and_refine"
    
    # ALL ACCURACY-CRITICAL DOMAINS: Health, Legal, Finance, Science
    # These require expert_panel (3+ models) or challenge_and_refine (fewer models)
    accuracy_critical_domains = [
        "health_medical",      # Lives at stake
        "legal_analysis",      # Legal liability
        "financial_analysis",  # Money at stake
        "science_research",    # Factual accuracy
    ]
    
    if task_type in accuracy_critical_domains:
        if num_models >= 3:
            logger.info("Strategy: %s task, 3+ models -> expert_panel (accuracy-critical)", task_type)
            return "expert_panel"  # Multiple perspectives for critical domains
        elif num_models >= 2:
            logger.info("Strategy: %s task, 2 models -> quality_weighted_fusion (accuracy-critical)", task_type)
            return "quality_weighted_fusion"
        logger.info("Strategy: %s task -> challenge_and_refine (accuracy-critical)", task_type)
        return "challenge_and_refine"
    
    # Factual questions with high accuracy need verification
    if task_type == "factual_question" and accuracy_priority >= 80:
        if num_models >= 3:
            logger.info("Strategy: Factual question, 3+ models, high accuracy -> expert_panel")
            return "expert_panel"
        logger.info("Strategy: Factual question with high accuracy -> challenge_and_refine")
        return "challenge_and_refine"
    
    # ========================================================================
    # PHASE 2: FAST PATH (Speed-optimized)
    # ========================================================================
    
    # Simple complexity OR explicit fast preference OR low accuracy setting
    if complexity == "simple" or speed_priority >= 85 or accuracy_level <= 1:
        if num_models == 1:
            logger.info("Strategy: Fast mode, 1 model -> single_best")
            return "single_best"
        else:
            logger.info("Strategy: Fast mode, multiple models -> parallel_race")
            return "parallel_race"
    
    # ========================================================================
    # PHASE 3: BALANCED SELECTION (Based on task characteristics)
    # ========================================================================
    
    # Research and analysis tasks need multiple perspectives
    if task_type in ["research_analysis", "comparison", "explanation"]:
        if num_models >= 3 and accuracy_level >= 3:
            logger.info("Strategy: Research task, 3+ models -> expert_panel")
            return "expert_panel"
        elif num_models >= 2:
            logger.info("Strategy: Research task, 2+ models -> quality_weighted_fusion")
            return "quality_weighted_fusion"
    
    # Creative writing benefits from multiple perspectives and synthesis
    if task_type == "creative_writing":
        if creativity_priority >= 70 and num_models >= 2:
            logger.info("Strategy: Creative task, high creativity -> expert_panel")
            return "expert_panel"  # More diverse outputs
        logger.info("Strategy: Creative task -> quality_weighted_fusion")
        return "quality_weighted_fusion"
    
    # Planning tasks need structured approach
    if task_type == "planning":
        if accuracy_level >= 4:
            logger.info("Strategy: Planning task, high accuracy -> challenge_and_refine")
            return "challenge_and_refine"
        logger.info("Strategy: Planning task -> best_of_n")
        return "best_of_n"
    
    # ========================================================================
    # PHASE 4: ACCURACY-DRIVEN SELECTION
    # ========================================================================
    
    # Maximum accuracy requested
    if accuracy_level >= 5 or accuracy_priority >= 90:
        if num_models >= 2:
            logger.info("Strategy: Maximum accuracy -> challenge_and_refine")
            return "challenge_and_refine"
        logger.info("Strategy: Maximum accuracy, 1 model -> single_best (with verification)")
        return "single_best"  # Will use internal verification
    
    # High accuracy
    if accuracy_level >= 4 or accuracy_priority >= 75:
        if num_models >= 3:
            logger.info("Strategy: High accuracy, 3+ models -> expert_panel")
            return "expert_panel"
        elif num_models >= 2:
            logger.info("Strategy: High accuracy, 2+ models -> best_of_n")
            return "best_of_n"
    
    # Medium accuracy
    if accuracy_level >= 3:
        if num_models >= 2:
            logger.info("Strategy: Medium accuracy, 2+ models -> quality_weighted_fusion")
            return "quality_weighted_fusion"
    
    # ========================================================================
    # PHASE 5: COMPLEXITY-DRIVEN FALLBACK
    # ========================================================================
    
    # Complex or research complexity
    if complexity in ["complex", "research"]:
        if num_models >= 2:
            logger.info("Strategy: Complex task -> quality_weighted_fusion")
            return "quality_weighted_fusion"
    
    # Moderate complexity
    if complexity == "moderate" and num_models >= 2:
        logger.info("Strategy: Moderate complexity -> parallel_race")
        return "parallel_race"
    
    # ========================================================================
    # PHASE 6: DEFAULT
    # ========================================================================
    if num_models >= 2:
        logger.info("Strategy: Default multi-model -> quality_weighted_fusion")
        return "quality_weighted_fusion"
    
    logger.info("Strategy: Default single model -> single_best")
    return "single_best"


def _map_reasoning_mode(mode: ReasoningMode) -> int:
    """Map ReasoningMode enum to reasoning depth integer."""
    mapping = {
        ReasoningMode.fast: 1,
        ReasoningMode.standard: 2,
        ReasoningMode.deep: 3,
    }
    return mapping.get(mode, 2)


def _map_model_to_provider(model_id: str, available_providers: list) -> str:
    """Map a user-selected model ID to an actual provider/model name.
    
    Latest models (December 2025):
    - OpenAI: GPT-4o, GPT-4o-mini, o1, o1-mini
    - Anthropic: Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3.5 Haiku
    - Google: Gemini 2.5 Pro, Gemini 2.5 Flash
    - xAI: Grok-2, Grok-2-mini
    """
    model_lower = model_id.lower()
    
    # OpenAI models
    if "gpt-5" in model_lower or "gpt-4" in model_lower or "o1" in model_lower:
        if "mini" in model_lower:
            return FALLBACK_GPT_4O_MINI
        return FALLBACK_GPT_4O
    
    # Anthropic Claude models
    elif "claude" in model_lower:
        if "haiku" in model_lower:
            return FALLBACK_CLAUDE_3_HAIKU  # claude-3-5-haiku-20241022
        elif "sonnet-4" in model_lower or "4.5" in model_lower or "opus" in model_lower:
            return FALLBACK_CLAUDE_SONNET_4  # claude-sonnet-4-20250514
        return FALLBACK_CLAUDE_3_5  # claude-3-5-sonnet-20241022
    
    # Google Gemini models
    elif "gemini" in model_lower:
        if "flash" in model_lower:
            return FALLBACK_GEMINI_2_5_FLASH  # gemini-2.5-flash
        return FALLBACK_GEMINI_2_5  # gemini-2.5-pro
    
    # xAI Grok models - Use Grok-2 (latest)
    elif "grok" in model_lower:
        return FALLBACK_GROK_2  # grok-2
    
    # DeepSeek models
    elif "deepseek" in model_lower:
        return FALLBACK_DEEPSEEK  # deepseek-chat
    
    # Llama (local)
    elif "llama" in model_lower:
        if "local" in available_providers:
            return "local"
        return "stub"
    
    # Direct model name match
    elif model_id in available_providers:
        return model_id
    
    else:
        # Default to first available
        return available_providers[0] if available_providers else "stub"


def _get_display_name(model_id: str) -> str:
    """Get a user-friendly display name for a model."""
    display_names = {
        FALLBACK_GPT_4O: "GPT-4o",
        FALLBACK_GPT_4O_MINI: "GPT-4o Mini",
        FALLBACK_CLAUDE_SONNET_4: "Claude Sonnet 4",
        FALLBACK_CLAUDE_3_5: "Claude 3.5 Sonnet",
        FALLBACK_CLAUDE_3_HAIKU: "Claude 3.5 Haiku",
        FALLBACK_GEMINI_2_5: "Gemini 2.5 Pro",
        FALLBACK_GEMINI_2_5_FLASH: "Gemini 2.5 Flash",
        FALLBACK_GROK_2: "Grok-2",
        FALLBACK_DEEPSEEK: "DeepSeek V3",
    }
    return display_names.get(model_id, model_id)


def _auto_select_reasoning_method(prompt: str, domain_pack: str) -> RouterReasoningMethod | None:
    """Heuristic selection of reasoning strategy when none provided."""
    plower = prompt.lower()
    math_signals = any(tok in plower for tok in ["solve", "equation", "integral", "derivative", "sum", "product"]) or any(ch in plower for ch in ["=", "+", "-", "*", "/"])
    code_signals = any(tok in plower for tok in ["code", "function", "class", "bug", "error", "stack trace", "compile", "python", "javascript", "typescript", "java", "c++"])
    factual_signals = any(plower.startswith(w) for w in ["who", "what", "when", "where", "which", "name", "list", "give me", "provide", "cite"])
    planning_signals = any(tok in plower for tok in ["plan", "roadmap", "strategy", "architecture", "design", "options", "tradeoff", "trade-off", "pros and cons", "compare"])
    ambiguous = len(prompt.split()) < 6
    try:
        if code_signals or math_signals:
            return RouterReasoningMethod.plan_and_solve
        if planning_signals:
            return RouterReasoningMethod.hierarchical_decomposition
        if factual_signals:
            return RouterReasoningMethod.self_consistency
        if ambiguous:
            return RouterReasoningMethod.tree_of_thought
        if domain_pack == "coding":
            return RouterReasoningMethod.plan_and_solve
        return RouterReasoningMethod.chain_of_thought
    except Exception:
        return None


async def run_orchestration(request: ChatRequest) -> ChatResponse:
    """
    Run orchestration with ChatRequest and return ChatResponse.
    
    This adapter builds an orchestration_config from the ChatRequest,
    uses user-selected models if provided, and calls the orchestrator.
    """
    start_time = time.perf_counter()
    
    try:
        # Profile defaults (format/tone/show_confidence)
        user_profile = None
        try:
            user_profile = get_profile(request.metadata.user_id if request.metadata else None)
        except Exception:
            user_profile = None

        # Determine reasoning method (explicit > auto > legacy mode)
        if request.reasoning_method:
            reasoning_method = RouterReasoningMethod(request.reasoning_method.value)
        else:
            # Heuristic auto-selection based on query/task
            reasoning_method = _auto_select_reasoning_method(
                request.prompt,
                domain_pack=request.domain_pack.value,
            )
            # Fallback to legacy mode mapping
            if reasoning_method is None:
                reasoning_method = map_reasoning_mode_to_method(request.reasoning_mode.value)
        
        logger.info(
            "Using reasoning method: %s (from mode: %s)",
            reasoning_method.value,
            request.reasoning_mode.value,
        )
        
        # Get available providers from orchestrator
        available_providers = list(_orchestrator.providers.keys())
        
        # Use user-selected models if provided, otherwise auto-select
        if request.models and len(request.models) > 0:
            logger.info("User selected models: %s", request.models)
            
            # Map user-selected model names to actual provider models
            actual_models = []
            user_model_names = []  # Track what the user selected for response
            
            for model_id in request.models:
                mapped_model = _map_model_to_provider(model_id, available_providers)
                if mapped_model not in actual_models:  # Avoid duplicates
                    actual_models.append(mapped_model)
                    user_model_names.append(model_id)
            
            logger.info(
                "Mapped user models to providers: %s -> %s",
                request.models,
                actual_models,
            )
        else:
            # Auto-select models with intelligent routing
            # Step 1: Check if query requires advanced reasoning
            needs_reasoning_model = False
            reasoning_type = None
            reasoning_detector = _get_reasoning_detector()
            if reasoning_detector:
                try:
                    reasoning_signals = reasoning_detector.detect_reasoning_signals(request.prompt)
                    needs_reasoning_model = reasoning_detector.needs_reasoning_model(reasoning_signals)
                    if needs_reasoning_model:
                        reasoning_type = reasoning_signals.primary_type
                        logger.info(
                            "Reasoning detection: needs_reasoning=%s, type=%s, confidence=%.2f",
                            needs_reasoning_model,
                            reasoning_type.value if reasoning_type else "none",
                            reasoning_signals.confidence,
                        )
                except Exception as e:
                    logger.debug("Reasoning detection failed: %s", e)
            
            # Step 2: Use cascade routing for cost optimization
            cascade_router = _get_cascade_router()
            if cascade_router:
                try:
                    cascade_result = cascade_router.route_query_cascade(request.prompt)
                    logger.info(
                        "Cascade routing: complexity=%s, tier=%s, recommended_models=%s",
                        cascade_result.complexity.value,
                        cascade_result.tier.value,
                        cascade_result.models[:3],
                    )
                except Exception as e:
                    logger.debug("Cascade routing failed: %s", e)
            
            # Step 3: Select models based on reasoning method (fallback)
            selected_models = get_models_for_reasoning_method(
                reasoning_method,
                available_models=available_providers,
            )
            
            # Step 4: If reasoning model needed, prioritize reasoning-capable models
            if needs_reasoning_model:
                # Prioritize o1, o3-mini, or other reasoning models
                reasoning_models = ["gpt-4o", "claude-sonnet-4-20250514"]  # Best reasoning
                for rm in reasoning_models:
                    if rm in available_providers and rm not in selected_models:
                        selected_models.insert(0, rm)
                logger.info("Prioritized reasoning models: %s", selected_models[:3])
            
            # Map to actual model names
            actual_models = []
            user_model_names = []
            for model_id in selected_models:
                mapped = _map_model_to_provider(model_id, available_providers)
                if mapped not in actual_models:
                    actual_models.append(mapped)
                    user_model_names.append(model_id)
        
        if not actual_models:
            actual_models = ["gpt-4o-mini"]
            user_model_names = ["GPT-4o Mini"]
        
        logger.info(
            "Final models for orchestration: %s (display: %s)",
            actual_models,
            user_model_names,
        )
        
        # Extract criteria settings from metadata if provided
        criteria_settings = None
        metadata_dict: Dict[str, Any] = {}  # Initialize metadata_dict
        
        if request.metadata:
            # Get dict representation of metadata
            if hasattr(request.metadata, 'model_dump'):
                metadata_dict = request.metadata.model_dump(exclude_none=True)
            elif hasattr(request.metadata, 'dict'):
                metadata_dict = request.metadata.dict(exclude_none=True)
            
            # Check for criteria object directly on metadata (new format)
            if hasattr(request.metadata, 'criteria') and request.metadata.criteria:
                criteria_obj = request.metadata.criteria
                if hasattr(criteria_obj, 'model_dump'):
                    criteria_settings = criteria_obj.model_dump()
                elif hasattr(criteria_obj, 'dict'):
                    criteria_settings = criteria_obj.dict()
                elif isinstance(criteria_obj, dict):
                    criteria_settings = criteria_obj
            # Fallback: check dict representation
            elif 'criteria' in metadata_dict:
                criteria_settings = metadata_dict['criteria']
        
        # =====================================================================
        # PR5: Extract budget constraints from request
        # =====================================================================
        max_cost_usd = getattr(request.orchestration, 'max_cost_usd', None)
        prefer_cheaper = getattr(request.orchestration, 'prefer_cheaper_models', False)
        budget_constraints = None
        
        if BUDGET_ROUTING_AVAILABLE and (max_cost_usd is not None or prefer_cheaper):
            budget_constraints = BudgetConstraints(
                max_cost_usd=max_cost_usd or 1.0,
                prefer_cheaper=prefer_cheaper,
                estimated_tokens=getattr(request.orchestration, 'max_tokens', 2000) or 2000,
            )
            logger.info(
                "PR5: Budget constraints active: max_cost=$%.2f, prefer_cheaper=%s",
                budget_constraints.max_cost_usd,
                budget_constraints.prefer_cheaper,
            )
        
        # Build orchestration_config dict
        orchestration_config: Dict[str, Any] = {
            "reasoning_depth": _map_reasoning_mode(request.reasoning_mode),
            "reasoning_method": reasoning_method.value,
            "domain_pack": request.domain_pack.value,
            "agent_mode": request.agent_mode.value,
            "use_prompt_optimization": request.tuning.prompt_optimization,
            "use_output_validation": request.tuning.output_validation,
            "use_answer_structure": request.tuning.answer_structure,
            "learn_from_chat": request.tuning.learn_from_chat,
            "metadata": metadata_dict,
            "history": request.history or [],
            # Orchestration Studio settings
            "accuracy_level": request.orchestration.accuracy_level,
            "use_hrm": request.orchestration.enable_hrm,
            "use_prompt_diffusion": request.orchestration.enable_prompt_diffusion,
            "use_deep_consensus": request.orchestration.enable_deep_consensus,
            "use_adaptive_routing": request.orchestration.enable_adaptive_ensemble,
            # PR5: Budget constraints
            "max_cost_usd": max_cost_usd,
            "budget_constraints": budget_constraints,
        }
        
        # Add criteria settings if provided (for dynamic criteria equaliser)
        if criteria_settings:
            orchestration_config["criteria"] = criteria_settings
            logger.info(
                "Using criteria settings: accuracy=%d%%, speed=%d%%, creativity=%d%%",
                criteria_settings.get("accuracy", 70),
                criteria_settings.get("speed", 70),
                criteria_settings.get("creativity", 50),
            )
        
        # ========================================================================
        # STEP 0: RAG AUGMENTATION (If enabled)
        # ========================================================================
        enable_rag = getattr(request.orchestration, 'enable_vector_rag', False)
        user_id = metadata_dict.get('user_id')
        project_id = metadata_dict.get('project_id')
        org_id = metadata_dict.get('org_id')
        
        # Fast reuse: return cached high-confidence answer if nearly identical
        if KNOWLEDGE_BASE_AVAILABLE and os.getenv("ENABLE_FAST_REUSE", "0").lower() in {"1", "true", "yes"}:
            kb = _get_knowledge_base()
            if kb:
                try:
                    cached = await kb.retrieve_context(
                        query=request.prompt,
                        top_k=1,
                        record_types=[RecordType.FINAL_ANSWER, RecordType.DOMAIN_KNOWLEDGE],
                        domain=request.domain_pack.value,
                        user_id=user_id,
                        project_id=project_id,
                        org_id=org_id,
                        min_quality_score=0.9,
                        rerank=True,
                    )
                    if cached and cached[0].score >= 0.92:
                        meta_models = cached[0].metadata.get("models_used", "")
                        cached_models = meta_models.split(",") if isinstance(meta_models, str) else []
                        logger.info(
                            "Fast reuse hit: returning cached answer (score=%.2f, record=%s)",
                            cached[0].score,
                            cached[0].id,
                        )
                        return ChatResponse(
                            message=cached[0].content,
                            models_used=cached_models or ["knowledge_base_cache"],
                            reasoning_mode=request.reasoning_mode,
                            reasoning_method=request.reasoning_method,
                            domain_pack=request.domain_pack,
                            agent_mode=request.agent_mode,
                            used_tuning=request.tuning,
                            metadata=request.metadata,
                            tokens_used="cached",
                            latency_ms=int((time.perf_counter() - start_time) * 1000),
                            agent_traces=[],
                            extra={"source": "knowledge_base_cache", "record_id": cached[0].id},
                        )
                except Exception as e:
                    logger.debug("Fast reuse check failed: %s", e)
        
        if enable_rag and KNOWLEDGE_BASE_AVAILABLE:
            try:
                augmented_prompt = await _augment_with_rag(
                    prompt=request.prompt,
                    domain=request.domain_pack.value,
                    user_id=user_id,
                    project_id=project_id,
                    org_id=org_id,
                )
                original_prompt = request.prompt
                # Note: We don't modify request.prompt directly, use augmented_prompt in the pipeline
            except Exception as e:
                logger.warning(f"RAG augmentation failed: {e}")
                augmented_prompt = request.prompt
                original_prompt = request.prompt
        else:
            augmented_prompt = request.prompt
            original_prompt = request.prompt
        
        # ========================================================================
        # STEP 1: PROMPTOPS PREPROCESSING (Always On)
        # ========================================================================
        base_prompt = augmented_prompt  # Use RAG-augmented prompt if available
        prompt_spec: Optional[PromptSpecification] = None
        detected_task_type = "general"
        detected_complexity = "moderate"
        is_strict_format = False
        requested_output_format: Optional[str] = None
        
        if PROMPTOPS_AVAILABLE:
            try:
                prompt_ops = PromptOps(providers=_orchestrator.providers)
                prompt_spec = await prompt_ops.process(
                    request.prompt,
                    domain_hint=request.domain_pack.value,
                )
                
                # Use PromptOps analysis
                base_prompt = prompt_spec.refined_query
                detected_task_type = prompt_spec.analysis.task_type.value
                detected_complexity = prompt_spec.analysis.complexity.value
                requested_output_format = prompt_spec.analysis.output_format
                
                logger.info(
                    "PromptOps: task=%s, complexity=%s, tools=%s, confidence=%.2f",
                    detected_task_type,
                    detected_complexity,
                    prompt_spec.analysis.tool_hints,
                    prompt_spec.confidence,
                )
                
                # Log any ambiguities or safety flags
                if prompt_spec.analysis.ambiguities:
                    logger.info("PromptOps detected ambiguities: %s", prompt_spec.analysis.ambiguities[:3])
                if prompt_spec.safety_flags:
                    logger.warning("PromptOps safety flags: %s", prompt_spec.safety_flags)
                    
            except Exception as e:
                logger.warning("PromptOps failed, using raw prompt: %s", e)
        
        # ========================================================================
        # STEP 1.25: CLARIFICATION CHECK (Optional - adds questions to extra)
        # ========================================================================
        clarification_questions = []
        if CLARIFICATION_AVAILABLE and prompt_spec and prompt_spec.analysis.ambiguities:
            try:
                clarification_mgr = ClarificationManager()
                # Check if prompt is ambiguous enough to warrant clarification
                needs_clarification = await clarification_mgr.analyze_query(request.prompt)
                
                if needs_clarification.status != ClarificationStatus.NOT_NEEDED:
                    # Generate clarifying questions
                    questions = await clarification_mgr.generate_questions(
                        request.prompt,
                        max_query_questions=3,
                        max_preference_questions=3,
                    )
                    
                    if questions:
                        clarification_questions = [
                            {
                                "id": q.id,
                                "question": q.question,
                                "category": q.category,
                                "options": q.options,
                                "required": q.required,
                            }
                            for q in questions
                        ]
                        logger.info(
                            "Clarification: Generated %d questions for ambiguous query",
                            len(clarification_questions)
                        )
            except Exception as e:
                logger.warning("Clarification check failed: %s", e)
        
        # ========================================================================
        # STEP 1.4: EXPLICIT HISTORY CONTEXT INJECTION (Multi-turn reliability)
        # ========================================================================
        if request.history:
            try:
                history_snippets = []
                for msg in request.history[-6:]:  # last 6 turns for context
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    content = content[:400]  # cap length per turn
                    prefix = "User" if role == "user" else "Assistant"
                    history_snippets.append(f"- {prefix}: {content}")
                
                if history_snippets:
                    history_block = "\n".join(history_snippets)
                    base_prompt = (
                        f"{base_prompt}\n\n"
                        "[CONTEXT FROM PREVIOUS MESSAGES]\n"
                        f"{history_block}\n"
                        "You MUST use this context and not contradict it. "
                        "Do not claim the preferences are missing; they are provided above. "
                        "Do not invent new preferences; rely ONLY on the context above."
                    )
            except Exception as e:
                logger.warning("Failed to inject history context: %s", e)
        
        # ========================================================================
        # STEP 1.45: OUTPUT FORMAT ENFORCEMENT (JSON-only)
        # ========================================================================
        if requested_output_format and requested_output_format.startswith("json"):
            if requested_output_format.endswith("_strict"):
                is_strict_format = True
            base_prompt = (
                f"{base_prompt}\n\n"
                "[OUTPUT FORMAT]\n"
                "Return ONLY a single JSON object with the required keys. "
                "Do not include any prose, explanations, or markdown fences. "
                "Output must be valid JSON."
            )
        
        # ========================================================================
        # STEP 1.5: TOOL BROKER - Automatic Tool Detection and Execution
        # ========================================================================
        tool_context = ""
        tool_results_info: Dict[str, Any] = {"used": False}
        
        # Check if live research is explicitly enabled (from frontend temporal detection)
        force_web_search = getattr(request.orchestration, 'enable_live_research', False)
        
        if TOOL_BROKER_AVAILABLE and (prompt_spec is None or prompt_spec.analysis.requires_tools or force_web_search):
            try:
                broker = get_tool_broker()
                tool_analysis = broker.analyze_tool_needs(base_prompt)
                
                # Force web search if enable_live_research is set
                if force_web_search and not tool_analysis.requires_tools:
                    logger.info("Forcing web search due to enable_live_research=True")
                    from ..orchestration.tool_broker import ToolRequest, ToolType as TT, ToolPriority
                    # Enhance query for recency and add recency params
                    import datetime
                    current_date = datetime.datetime.now().strftime("%B %Y")  # e.g., "December 2024"
                    enhanced_query = f"{base_prompt} {current_date} latest"
                    tool_analysis.tool_requests.append(ToolRequest(
                        tool_type=TT.WEB_SEARCH,
                        query=enhanced_query,
                        purpose="Real-time web search for current information",
                        priority=ToolPriority.HIGH,
                        metadata={"days": 30, "topic": "news"},  # Last 30 days, news topic
                    ))
                    tool_analysis.requires_tools = True
                
                # For any temporal query, ensure recency params are set
                if force_web_search:
                    for req in tool_analysis.tool_requests:
                        if req.tool_type.value == "web_search" and not req.metadata.get("days"):
                            req.metadata["days"] = 30
                            req.metadata["topic"] = "news"
                
                if tool_analysis.requires_tools:
                    logger.info(
                        "Tool Broker: Detected need for tools: %s",
                        [r.tool_type.value for r in tool_analysis.tool_requests],
                    )
                    
                    # Execute tools in parallel
                    tool_results = await broker.execute_tools(
                        tool_analysis.tool_requests,
                        parallel=True,
                    )
                    
                    # Format results for model context
                    tool_context = broker.format_tool_results(tool_results)
                    
                    # Track tool usage for response metadata
                    tool_results_info = {
                        "used": True,
                        "tools": [t.value for t in tool_results.keys()],
                        "success_count": sum(1 for r in tool_results.values() if r.success),
                        "reasoning": tool_analysis.reasoning,
                    }
                    
                    # Append tool context to the prompt with explicit instructions
                    if tool_context:
                        tool_instruction = (
                            "\n\n=== IMPORTANT: REAL-TIME DATA BELOW ===\n"
                            "The following information was retrieved from current web searches. "
                            "You MUST use this data to answer the question. Do NOT claim you cannot "
                            "access current information - the data below is current as of today.\n\n"
                            f"{tool_context}\n"
                            "=== END OF REAL-TIME DATA ===\n\n"
                            "CRITICAL INSTRUCTIONS:\n"
                            "1. Use ONLY the information from the real-time data above - do NOT hallucinate or make up information\n"
                            "2. If asked for a numbered list (e.g., 'top 10'), provide ALL items requested using the search data\n"
                            "3. If the search data doesn't have enough items, clearly state how many you found and list them all\n"
                            "4. Include specific details from the sources (names, versions, capabilities)\n"
                            "5. Do NOT say 'I cannot access' or 'I don't have real-time data' - you DO have current data above\n"
                            "Now provide a complete, accurate answer based on the real-time data:"
                        )
                        base_prompt = f"{base_prompt}{tool_instruction}"
                        logger.info("Tool context added to prompt with instructions (%d chars)", len(tool_context))
            except Exception as e:
                logger.warning("Tool Broker failed: %s", e)
        
        # ========================================================================
        # STEP 2: INTELLIGENT MODEL SELECTION (Based on agent_mode and task)
        # ========================================================================
        # Check agent_mode: "team" = multi-model ensemble, "single" = best single model
        agent_mode = orchestration_config.get("agent_mode", "team")
        is_team_mode = agent_mode == "team"
        
        # Check if we should use automatic model selection
        is_automatic_mode = (
            not request.models or  # No models provided
            len(request.models) == 0 or  # Empty list
            (len(request.models) == 1 and request.models[0].lower() in ["automatic", "auto"])
        )
        
        if is_automatic_mode:
            logger.info(
                "Intelligent model selection: agent_mode=%s, task_type='%s'",
                agent_mode, detected_task_type
            )
            
            # Determine if tools are needed (web search was used or could be needed)
            tools_needed = bool(tool_context)  # Web search was executed
            
            if is_team_mode:
                # TEAM MODE: Select multiple diverse models for ensemble orchestration
                # Uses Pinecone rankings + complementary strengths + tool support
                accuracy_lvl = orchestration_config.get("accuracy_level", 3)
                accuracy_priority = accuracy_lvl >= 3
                
                # Determine number of models based on accuracy level
                if accuracy_lvl >= 4:
                    num_team_models = min(4, len(available_providers))  # High accuracy: 4 models
                elif accuracy_lvl >= 3:
                    num_team_models = min(3, len(available_providers))  # Standard: 3 models
                else:
                    num_team_models = min(2, len(available_providers))  # Fast: 2 models
                
                # Use intelligent Pinecone-backed selection
                # This gets: top-ranked models for category + complementary models + tool-capable models
                auto_selected = get_intelligent_models_sync(
                    task_type=detected_task_type,
                    num_models=num_team_models,
                    require_tools=tools_needed,
                    available_models=available_providers,
                    accuracy_priority=accuracy_priority,
                )
                
                # Fallback to basic diverse ensemble if intelligent selection failed
                if len(auto_selected) < num_team_models:
                    auto_selected = get_diverse_ensemble(
                        detected_task_type,
                        available_models=available_providers,
                        num_models=num_team_models,
                    )
                
                logger.info(
                    "TEAM mode: Selected %d models for ensemble (tools=%s): %s",
                    len(auto_selected), tools_needed, auto_selected
                )
            else:
                # SINGLE MODE: Select just the ONE best model for the task
                # Still uses intelligent selection for optimal single-model choice
                auto_selected = get_intelligent_models_sync(
                    task_type=detected_task_type,
                    num_models=1,
                    require_tools=tools_needed,
                    available_models=available_providers,
                    accuracy_priority=True,
                )
                
                # Fallback
                if not auto_selected:
                    auto_selected = get_best_models_for_task(
                        detected_task_type,
                        available_models=available_providers,
                        num_models=1,
                        criteria=criteria_settings,
                    )
                
                logger.info(
                    "SINGLE mode: Selected best model (tools=%s): %s",
                    tools_needed, auto_selected[0] if auto_selected else "default"
                )
            
            # Map selected models to actual provider names
            actual_models = []
            user_model_names = []
            for model_id in auto_selected:
                mapped = _map_model_to_provider(model_id, available_providers)
                if mapped not in actual_models:
                    actual_models.append(mapped)
                    user_model_names.append(_get_display_name(model_id))
            
            logger.info(
                "Intelligent model selection: agent_mode=%s, task=%s -> models=%s",
                agent_mode, detected_task_type, actual_models,
            )
        
        # Enhance prompt with reasoning method template
        enhanced_prompt = get_reasoning_prompt_template(
            reasoning_method,
            base_prompt,
            domain_pack=request.domain_pack.value,
        )
        
        # ===========================================================================
        # Apply reasoning hacks for non-reasoning models to unlock deeper thinking
        # ===========================================================================
        reasoning_hack_applied = False
        reasoning_hack_level = None
        
        # Import reasoning hacker for advanced prompt transformation
        try:
            from ..orchestration.reasoning_hacker import (
                get_hack_prompt,
                get_recommended_hack_level,
                ReasoningHackLevel,
                REASONING_HACK_PROMPTS,
            )
            REASONING_HACKER_AVAILABLE = True
        except ImportError:
            REASONING_HACKER_AVAILABLE = False
        
        if MODEL_INTELLIGENCE_AVAILABLE and actual_models:
            primary_model = actual_models[0]
            profile = get_model_profile(primary_model)
            
            if profile:
                # Check if model needs reasoning hacks (not native reasoning like o1)
                from ..knowledge.model_intelligence import ReasoningCapability
                
                if ReasoningCapability.NATIVE_COT not in profile.reasoning_capabilities:
                    # Model can benefit from reasoning hacks
                    accuracy_lvl = orchestration_config.get("accuracy_level", 3)
                    
                    # Use reasoning hacker module if available
                    if REASONING_HACKER_AVAILABLE:
                        # Determine hack level based on task and accuracy
                        if accuracy_lvl >= 4:
                            reasoning_hack_level = ReasoningHackLevel.HEAVY
                        elif accuracy_lvl >= 3:
                            reasoning_hack_level = ReasoningHackLevel.MEDIUM
                        else:
                            reasoning_hack_level = ReasoningHackLevel.LIGHT
                        
                        # High-stakes domains get maximum hacking
                        high_stakes = ["health_medical", "legal_analysis", "financial_analysis"]
                        if detected_task_type in high_stakes and accuracy_lvl >= 3:
                            reasoning_hack_level = ReasoningHackLevel.MAXIMUM
                        
                        # Apply the hack prompt
                        enhanced_prompt = get_hack_prompt(
                            level=reasoning_hack_level,
                            question=enhanced_prompt,
                            task_type=detected_task_type,
                        )
                        reasoning_hack_applied = True
                        
                        logger.info(
                            "Applied reasoning hack level=%s for %s (reasoning_score=%d, task=%s)",
                            reasoning_hack_level.value,
                            profile.display_name,
                            profile.reasoning_score,
                            detected_task_type,
                        )
                    else:
                        # Fallback to basic hack
                        if accuracy_lvl >= 4:
                            reasoning_hack = get_reasoning_hack(primary_model, detected_task_type)
                            if reasoning_hack and "{question}" in reasoning_hack:
                                enhanced_prompt = reasoning_hack.replace("{question}", enhanced_prompt)
                                reasoning_hack_applied = True
                                logger.info(
                                    "Applied fallback reasoning hack for %s",
                                    profile.display_name,
                                )
                    
                    # Log model's native hack capability
                    if profile.reasoning_hack_method and not reasoning_hack_applied:
                        logger.debug(
                            "Model %s supports reasoning via: %s",
                            profile.display_name,
                            profile.reasoning_hack_method[:100],
                        )
        
        logger.info(
            "Running orchestration: method=%s, domain=%s, agent_mode=%s, models=%s, "
            "hrm=%s, adaptive=%s, accuracy=%d",
            reasoning_method.value,
            orchestration_config["domain_pack"],
            orchestration_config["agent_mode"],
            actual_models,
            orchestration_config.get("use_hrm", False),
            orchestration_config.get("use_adaptive_routing", False),
            orchestration_config.get("accuracy_level", 3),
        )
        
        # Use PromptOps task type if available, otherwise detect from prompt
        task_type = detected_task_type if detected_task_type != "general" else _detect_task_type(base_prompt)
        accuracy_level = orchestration_config.get("accuracy_level", 3)
        
        # Determine if we should use elite orchestration
        # Elite orchestration requires TEAM mode with multiple models
        use_elite = (
            ELITE_AVAILABLE and 
            is_team_mode and  # Only use elite in TEAM mode
            accuracy_level >= 3 and 
            len(actual_models) >= 2
        )
        
        elite_result = None
        
        if use_elite:
            logger.info(
                "Using ELITE orchestration: task=%s, accuracy=%d, strategy=auto",
                task_type, accuracy_level
            )
            
            elite = _get_elite_orchestrator()
            if elite:
                try:
                    # Reuse prior successful orchestration pattern if available
                    kb_strategy = None
                    if KNOWLEDGE_BASE_AVAILABLE:
                        kb = _get_knowledge_base()
                        if kb:
                            kb_strategy = await kb.get_best_strategy(
                                query_type=task_type,
                                user_id=user_id,
                            )
                            if kb_strategy:
                                logger.info(
                                    "Using learned strategy from KB: %s (models=%s)",
                                    kb_strategy[0],
                                    kb_strategy[1],
                                )
                                selected_strategy = kb_strategy[0]
                                if kb_strategy[1]:
                                    actual_models = kb_strategy[1]
                    
                    # Select strategy based on accuracy, task, complexity, and user criteria
                    strategy = selected_strategy or _select_elite_strategy(
                        accuracy_level=accuracy_level,
                        task_type=task_type,
                        num_models=len(actual_models),
                        complexity=detected_complexity,
                        criteria=criteria_settings,
                        prompt_spec=prompt_spec,
                    )
                    selected_strategy = strategy
                    
                    elite_result = await elite.orchestrate(
                        enhanced_prompt,
                        task_type=task_type,
                        available_models=actual_models,
                        strategy=strategy,
                        quality_threshold=0.7,
                        max_parallel=min(3, len(actual_models)),
                    )
                    
                    final_text = elite_result.final_answer
                    
                    logger.info(
                        "Elite orchestration complete: strategy=%s, quality=%.2f, models=%s",
                        elite_result.strategy_used,
                        elite_result.quality_score,
                        elite_result.models_used,
                    )
                except Exception as e:
                    logger.warning("Elite orchestration failed, falling back: %s", e)
                    use_elite = False
        
        if not use_elite or elite_result is None:
            # Standard orchestration path
            artifacts = await _orchestrator.orchestrate(
                enhanced_prompt,
                actual_models,
                use_hrm=orchestration_config.get("use_hrm", False),
                use_adaptive_routing=orchestration_config.get("use_adaptive_routing", False),
                use_deep_consensus=orchestration_config.get("use_deep_consensus", False),
                use_prompt_diffusion=orchestration_config.get("use_prompt_diffusion", False),
                accuracy_level=accuracy_level,
            )
            final_text = artifacts.final_response.content
        
        # Apply quality boosting for high accuracy requests
        if QUALITY_BOOSTER_AVAILABLE and accuracy_level >= 4:
            booster = _get_quality_booster()
            if booster:
                try:
                    logger.info("Applying quality boost for high-accuracy request")
                    boost_result = await booster.boost(
                        base_prompt,
                        final_text,
                        techniques=["reflection", "verification"],
                        max_iterations=1,
                    )
                    if boost_result.quality_improvement > 0:
                        final_text = boost_result.boosted_response
                        logger.info(
                            "Quality boost applied: improvement=%.2f, techniques=%s",
                            boost_result.quality_improvement,
                            boost_result.techniques_applied,
                        )
                except Exception as e:
                    logger.warning("Quality boost failed: %s", e)
        
        # Distill multi-model/agent outputs into reusable knowledge
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                kb = _get_knowledge_base()
                if kb:
                    used_models = []
                    if elite_result and getattr(elite_result, "models_used", None):
                        used_models = elite_result.models_used
                    elif artifacts and getattr(artifacts, "models_used", None):
                        used_models = artifacts.models_used
                    if used_models and len(used_models) > 1:
                        distilled_content = f"Distilled consensus for: {original_prompt[:200]}\nModels: {', '.join(used_models)}\nAnswer:\n{final_text[:1800]}"
                await kb.store_answer(
                            query=original_prompt[:500],
                            answer=distilled_content,
                            models_used=used_models,
                            record_type=RecordType.DOMAIN_KNOWLEDGE,
                            quality_score=0.6,
                            domain=request.domain_pack.value,
                            user_id=user_id,
                            project_id=project_id,
                    org_id=org_id,
                            metadata={"multi_agent_distilled": True},
                        )
            except Exception as e:
                logger.debug("Failed to distill multi-agent output: %s", e)
        
        # ========================================================================
        # STEP 4: TOOL-BASED VERIFICATION (For code/math/factual tasks)
        # ========================================================================
        verification_confidence = 1.0
        verification_issues: List[str] = []
        
        # Only verify for tasks that benefit from deterministic verification
        should_verify = (
            TOOL_VERIFICATION_AVAILABLE and
            VERIFICATION_ENABLED and
            task_type in ["code_generation", "debugging", "math_problem", "factual_question"]
        )
        
        if should_verify:
            try:
                verification_pipeline = get_verification_pipeline()
                
                verified_text, verification_confidence, verification_issues = (
                    await verification_pipeline.verify_answer(
                        final_text,
                        base_prompt,
                        fix_errors=True,  # Auto-correct math/code errors
                    )
                )
                
                if verification_issues:
                    logger.warning(
                        "Verification found %d issues (confidence=%.2f): %s",
                        len(verification_issues),
                        verification_confidence,
                        verification_issues[:3],
                    )
                    final_text = verified_text  # Use corrected version
                else:
                    logger.info(
                        "Verification passed: task=%s, confidence=%.2f",
                        task_type,
                        verification_confidence,
                    )
                verification_result = {
                    "passed": len(verification_issues) == 0,
                    "confidence": verification_confidence,
                }
            except Exception as e:
                logger.warning("Tool verification failed: %s", e)
        
        # ========================================================================
        # FINAL STEP: ALWAYS-ON ANSWER REFINEMENT
        # ========================================================================
        if REFINER_AVAILABLE and REFINER_ALWAYS_ON:
            try:
                # Detect output format from PromptOps analysis, allow user override, then profile default
                output_format = OutputFormat.PARAGRAPH
                requested_format = request.format_style or (user_profile.default_format_style if user_profile else None)
                if prompt_spec and prompt_spec.analysis.output_format:
                    requested_format = requested_format or prompt_spec.analysis.output_format
                
                if requested_format:
                    fmt = requested_format
                    # Check for strict format (e.g., "json_strict" means output ONLY JSON)
                    if fmt.endswith("_strict"):
                        is_strict_format = True
                        fmt = fmt.replace("_strict", "")
                    
                    format_map = {
                        "json": OutputFormat.JSON,
                        "markdown": OutputFormat.MARKDOWN,
                        "code": OutputFormat.CODE,
                        "list": OutputFormat.BULLET,
                        "bullet": OutputFormat.BULLET,
                        "bullet_points": OutputFormat.BULLET,
                        "table": OutputFormat.TABLE,
                        "executive_summary": OutputFormat.EXEC_SUMMARY,
                        "exec_summary": OutputFormat.EXEC_SUMMARY,
                        "qa": OutputFormat.QA,
                        "paragraph": OutputFormat.PARAGRAPH,
                    }
                    output_format = format_map.get(fmt, OutputFormat.PARAGRAPH)
                    
                    # For strict JSON, extract only the JSON from the response
                    if is_strict_format and fmt == "json":
                        import re
                        # Find JSON object or array in the response
                        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])', final_text, re.DOTALL)
                        if json_match:
                            final_text = json_match.group(1)
                            logger.info("Strict JSON format: extracted JSON from response")
                
                # Extract word limit from constraints if specified
                max_words = None
                if prompt_spec and prompt_spec.analysis.constraints:
                    for constraint in prompt_spec.analysis.constraints:
                        if "Maximum" in constraint and "words" in constraint:
                            import re
                            match = re.search(r'Maximum\s+(\d+)\s+words', constraint)
                            if match:
                                max_words = int(match.group(1))
                                logger.info(f"Word limit detected: {max_words} words")
                
                # Tone override from request or profile
                tone_style = ToneStyle.PROFESSIONAL
                tone_requested = request.tone_style or (user_profile.default_tone_style if user_profile else None)
                if tone_requested:
                    try:
                        tone_style = ToneStyle(tone_requested)
                    except Exception:
                        logger.warning("Unknown tone_style '%s', using professional", tone_requested)
                
                include_conf = accuracy_level >= 4
                if request.show_confidence is not None:
                    include_conf = bool(request.show_confidence)
                elif user_profile and user_profile.show_confidence is not None:
                    include_conf = bool(user_profile.show_confidence)

                refiner_config = RefinementConfig(
                    output_format=output_format,
                    tone=tone_style,
                    include_confidence=include_conf,
                    include_citations=accuracy_level >= 3,
                    preserve_structure=True,
                    max_words=max_words,
                )
                
                refiner = AnswerRefiner(providers=_orchestrator.providers)
                refined_answer = await refiner.refine(
                    final_text,
                    query=base_prompt,
                    config=refiner_config,
                )
                
                if refined_answer and refined_answer.refined_content:
                    refined_text = refined_answer.refined_content
                    final_text = refined_text
                    logger.info(
                        "Answer refined: %d improvements, format=%s",
                        len(refined_answer.improvements_made),
                        refined_answer.format_applied.value,
                    )
                
                # Final safeguard for strict JSON output
                if is_strict_format and (prompt_spec and prompt_spec.analysis.output_format and prompt_spec.analysis.output_format.startswith("json")):
                    import re, json as _json
                    json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])', final_text, re.DOTALL)
                    if json_match:
                        candidate = json_match.group(1)
                        try:
                            _json.loads(candidate)
                            final_text = candidate
                            logger.info("Strict JSON: validated JSON extraction after refinement")
                        except Exception:
                            final_text = candidate
                            logger.warning("Strict JSON: extracted JSON but parsing failed; returning best-effort JSON text")
                    else:
                        logger.warning("Strict JSON requested but no JSON found after refinement; returning original text")
            except Exception as e:
                logger.warning("Answer refinement failed (using unrefined): %s", e)
        
        # Build agent traces from artifacts (if available)
        traces: list[AgentTrace] = []
        
        # Extract token usage and other metrics
        token_usage = None
        quality_score = None
        
        if elite_result:
            # Use elite orchestrator metrics
            token_usage = elite_result.total_tokens
            quality_score = elite_result.quality_score
            actual_models_used = elite_result.models_used
        elif 'artifacts' in dir() and artifacts:
            if hasattr(artifacts.final_response, 'tokens_used'):
                token_usage = artifacts.final_response.tokens_used
            actual_models_used = actual_models
        else:
            actual_models_used = actual_models
        
        # Calculate latency
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Build extra data
        extra: Dict[str, Any] = {
            "orchestration_settings": {
                "accuracy_level": orchestration_config.get("accuracy_level", 3),
                "hrm_enabled": orchestration_config.get("use_hrm", False),
                "adaptive_routing_enabled": orchestration_config.get("use_adaptive_routing", False),
                "deep_consensus_enabled": orchestration_config.get("use_deep_consensus", False),
                "prompt_diffusion_enabled": orchestration_config.get("use_prompt_diffusion", False),
            },
        }
        
        # Add elite orchestrator info if used
        if elite_result:
            extra["elite_orchestration"] = {
                "enabled": True,
                "strategy": elite_result.strategy_used,
                "synthesis_method": elite_result.synthesis_method,
                "quality_score": elite_result.quality_score,
                "confidence": elite_result.confidence,
                "responses_generated": elite_result.responses_generated,
                "primary_model": elite_result.primary_model,
                "consensus_score": getattr(elite_result, "consensus_score", None),
            }
            extra["performance_notes"] = elite_result.performance_notes
        else:
            if 'artifacts' in dir() and artifacts:
                extra["initial_responses_count"] = len(artifacts.initial_responses)
                extra["critiques_count"] = len(artifacts.critiques)
                extra["improvements_count"] = len(artifacts.improvements)
                # Add consensus notes if available
                if hasattr(artifacts, 'consensus_notes') and artifacts.consensus_notes:
                    extra["consensus_notes"] = artifacts.consensus_notes
        
        # Add task type detected
        extra["task_type"] = task_type
        
        # Add clarification questions if generated (frontend can optionally display)
        if clarification_questions:
            extra["clarification"] = {
                "suggested_questions": clarification_questions,
                "note": "These questions could help refine the answer. Consider asking them as follow-up.",
            }
        
        # Add verification results to extra
        if should_verify:
            extra["verification"] = {
                "performed": True,
                "confidence": verification_confidence,
                "issues_found": len(verification_issues),
                "issues": verification_issues[:5] if verification_issues else [],
                "corrected": bool(verification_issues),
            }
        else:
            extra["verification"] = {"performed": False}
        
        # Add tool broker results to extra
        extra["tool_broker"] = tool_results_info
        
        # Add models used info to extra
        extra["models_requested"] = request.models or []
        extra["models_mapped"] = actual_models
        
        # PR5: Add budget info to extra
        if budget_constraints:
            extra["budget"] = {
                "max_cost_usd": budget_constraints.max_cost_usd,
                "prefer_cheaper": budget_constraints.prefer_cheaper,
                "estimated_tokens": budget_constraints.estimated_tokens,
            }
        
        # Build response with models_used
        response = ChatResponse(
            message=final_text,
            models_used=user_model_names,
            reasoning_mode=request.reasoning_mode,
            reasoning_method=request.reasoning_method,
            domain_pack=request.domain_pack,
            agent_mode=request.agent_mode,
            used_tuning=request.tuning,
            metadata=request.metadata,
            tokens_used=token_usage,
            latency_ms=latency_ms,
            agent_traces=traces,
            extra=extra,
        )
        
        logger.info(
            "Orchestration completed: latency=%dms, tokens=%s",
            latency_ms,
            token_usage or "unknown",
        )
        
        # ========================================================================
        # STEP FINAL: STORE ANSWER FOR LEARNING (If Vector RAG is enabled)
        # ========================================================================
        if enable_rag and KNOWLEDGE_BASE_AVAILABLE:
            try:
                # Calculate quality score based on verification and refinement
                quality_score = 0.7  # Base score
                if verification_result and verification_result.get("passed"):
                    quality_score += 0.2
                if refined_text and refined_text != final_text:
                    quality_score += 0.1
                
                # Store the final answer for future RAG retrieval
                await _store_answer_for_learning(
                    query=original_prompt,
                    answer=final_text,
                    models_used=actual_models,
                    quality_score=min(quality_score, 1.0),
                    domain=request.domain_pack.value,
                    user_id=user_id,
                    project_id=project_id,
                    org_id=org_id,
                    is_partial=False,
                )
                
                # Learn the orchestration pattern
                await _learn_orchestration_pattern(
                    query_type=detected_task_type,
                    strategy_used=selected_strategy,
                    models_used=actual_models,
                    success=True,
                    latency_ms=latency_ms,
                    quality_score=min(quality_score, 1.0),
                    user_id=user_id,
                )
                
            except Exception as e:
                logger.warning(f"Failed to store answer for learning: {e}")
        
        return response
        
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("Orchestration failed: %s", exc)
        
        # Return error response
        return ChatResponse(
            message=f"I apologize, but I encountered an error processing your request: {str(exc)}",
            models_used=request.models or [],
            reasoning_mode=request.reasoning_mode,
            reasoning_method=request.reasoning_method,
            domain_pack=request.domain_pack,
            agent_mode=request.agent_mode,
            used_tuning=request.tuning,
            metadata=request.metadata,
            latency_ms=latency_ms,
            agent_traces=[],
            extra={"error": str(exc)},
        )
    finally:
        # Audit logging (best-effort)
        try:
            log_audit_event(
                org_id=org_id,
                user_id=user_id,
                action="query",
                details={
                    "prompt": request.prompt[:200],
                    "models": actual_models if 'actual_models' in locals() else [],
                    "latency_ms": int((time.perf_counter() - start_time) * 1000),
                },
            )
        except Exception:
            pass

