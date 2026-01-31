"""
LLMHive FREE Models Database
============================

Comprehensive database of FREE models available on OpenRouter with their
characteristics, strengths, limitations, and optimal use cases.

This enables intelligent model selection for the FREE tier orchestration,
allowing us to leverage the right models for each task type.

IMPORTANT: All model IDs here MUST match EXACTLY what OpenRouter expects.
Use the `:free` suffix for free-tier access.

Last Updated: January 30, 2026
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class ModelStrength(str, Enum):
    """Categories where a model excels."""
    REASONING = "reasoning"
    MATH = "math"
    CODING = "coding"
    MULTILINGUAL = "multilingual"
    LONG_CONTEXT = "long_context"
    SPEED = "speed"
    DIALOGUE = "dialogue"
    RAG = "rag"
    TOOL_USE = "tool_use"
    CREATIVE = "creative"


class SpeedTier(str, Enum):
    """Response speed classification."""
    FAST = "fast"         # < 5 seconds typical
    MEDIUM = "medium"     # 5-15 seconds typical
    SLOW = "slow"         # > 15 seconds typical


@dataclass
class FreeModelInfo:
    """Information about a free model."""
    model_id: str                    # OpenRouter model ID with :free suffix
    display_name: str                # Human-readable name
    provider: str                    # Model provider (Google, Meta, etc.)
    context_window: int              # Max context length in tokens
    speed_tier: SpeedTier            # Response speed classification
    strengths: List[ModelStrength]   # What this model is good at
    weaknesses: List[str] = field(default_factory=list)  # Known limitations
    best_for: List[str] = field(default_factory=list)    # Optimal use cases
    notes: str = ""                  # Additional notes
    verified_working: bool = True    # Has been tested and works
    # NEW (Jan 31, 2026): Multi-provider routing
    preferred_api: str = "openrouter"  # "google" | "deepseek" | "openrouter"
    native_model_id: Optional[str] = None  # ID for direct API (if different)
    # NEW (Jan 31, 2026): OpenRouter benchmark scores
    performance_score: float = 0.0   # OpenRouter performance score (0-100)
    capability_score: float = 0.0    # OpenRouter capability score (0-100)
    supports_tools: bool = False     # Function calling support
    
    @property
    def is_fast(self) -> bool:
        return self.speed_tier == SpeedTier.FAST
    
    @property
    def is_reasoning_model(self) -> bool:
        return ModelStrength.REASONING in self.strengths
    
    @property
    def supports_long_context(self) -> bool:
        return self.context_window >= 100000
    
    @property
    def uses_direct_api(self) -> bool:
        """Whether this model routes to a direct API (not OpenRouter)."""
        return self.preferred_api in ("google", "deepseek")


# =============================================================================
# FREE MODELS DATABASE
# =============================================================================

FREE_MODELS_DB: Dict[str, FreeModelInfo] = {
    # =========================================================================
    # GOOGLE MODELS
    # =========================================================================
    "google/gemma-3-27b-it:free": FreeModelInfo(
        model_id="google/gemma-3-27b-it:free",
        display_name="Gemma 3 27B Instruct",
        provider="Google",
        context_window=131072,
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.CODING,
            ModelStrength.SPEED,
            ModelStrength.MULTILINGUAL,
        ],
        best_for=["General tasks", "Fast responses", "Coding assistance"],
        notes="Excellent all-around model, very fast inference",
        verified_working=True,
    ),
    
    "google/gemini-2.0-flash-exp:free": FreeModelInfo(
        model_id="google/gemini-2.0-flash-exp:free",
        display_name="Gemini 2.0 Flash Experimental",
        provider="Google",
        context_window=1000000,  # 1M tokens!
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.LONG_CONTEXT,
            ModelStrength.RAG,
            ModelStrength.REASONING,
        ],
        best_for=["Long documents", "RAG", "Multi-document analysis"],
        notes="LONGEST context window, routes to Google AI direct API (15 RPM)",
        verified_working=True,
        preferred_api="google",  # Route to Google AI
        native_model_id="gemini-2.0-flash-exp",
    ),
    
    # =========================================================================
    # META/LLAMA MODELS
    # =========================================================================
    "meta-llama/llama-3.3-70b-instruct:free": FreeModelInfo(
        model_id="meta-llama/llama-3.3-70b-instruct:free",
        display_name="Llama 3.3 70B Instruct",
        provider="Meta",
        context_window=131072,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.CODING,
            ModelStrength.DIALOGUE,
            ModelStrength.MULTILINGUAL,
        ],
        best_for=["General reasoning", "Code generation", "Conversation"],
        notes="Strong general-purpose model via OpenRouter",
        verified_working=True,
        preferred_api="openrouter",
    ),
    
    "meta-llama/llama-3.1-405b-instruct:free": FreeModelInfo(
        model_id="meta-llama/llama-3.1-405b-instruct:free",
        display_name="Llama 3.1 405B Instruct",
        provider="Meta",
        context_window=131072,
        speed_tier=SpeedTier.SLOW,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.MATH,
            ModelStrength.CODING,
        ],
        best_for=["Complex reasoning", "Hard math", "Detailed analysis"],
        notes="🏆 RANK #8 - Largest Llama (62.0), powerful reasoning",
        verified_working=True,
        preferred_api="openrouter",
        performance_score=62.0,
        capability_score=0.0,
        supports_tools=False,
    ),
    
    "meta-llama/llama-3.2-3b-instruct:free": FreeModelInfo(
        model_id="meta-llama/llama-3.2-3b-instruct:free",
        display_name="Llama 3.2 3B Instruct",
        provider="Meta",
        context_window=131072,
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.SPEED,
        ],
        best_for=["Fast simple tasks", "Quick responses"],
        notes="Very fast but limited capability - use for speed-critical simple tasks",
        verified_working=True,
    ),
    
    # =========================================================================
    # DEEPSEEK MODELS
    # =========================================================================
    "deepseek/deepseek-r1-0528:free": FreeModelInfo(
        model_id="deepseek/deepseek-r1-0528:free",
        display_name="DeepSeek R1 (V3.2-Thinking)",
        provider="DeepSeek",
        context_window=163840,
        speed_tier=SpeedTier.MEDIUM,  # Faster via direct API
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.MATH,
            ModelStrength.CODING,
            ModelStrength.TOOL_USE,
        ],
        best_for=["Complex reasoning", "Math problems", "Step-by-step analysis"],
        notes="🏆 RANK #2 - Elite reasoning (81.3), 96% AIME 2025",
        verified_working=True,
        preferred_api="deepseek",  # Route to DeepSeek Direct
        native_model_id="deepseek-reasoner",
        performance_score=81.3,
        capability_score=57.9,
        supports_tools=False,
    ),
    
    "deepseek/deepseek-chat": FreeModelInfo(
        model_id="deepseek/deepseek-chat",
        display_name="DeepSeek Chat (V3.2-Speciale)",
        provider="DeepSeek",
        context_window=163840,
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.CODING,
            ModelStrength.SPEED,
        ],
        best_for=["Fast reasoning", "Code generation", "General tasks"],
        notes="Fast general-purpose model, 90% on HMMT 2025, routes to direct API",
        verified_working=True,
        preferred_api="deepseek",  # Route to DeepSeek Direct
        native_model_id="deepseek-chat",
    ),
    
    # =========================================================================
    # QWEN MODELS
    # =========================================================================
    "qwen/qwen3-next-80b-a3b-instruct:free": FreeModelInfo(
        model_id="qwen/qwen3-next-80b-a3b-instruct:free",
        display_name="Qwen3 Next 80B",
        provider="Alibaba",
        context_window=262144,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.MATH,
            ModelStrength.REASONING,
            ModelStrength.MULTILINGUAL,
            ModelStrength.LONG_CONTEXT,
        ],
        best_for=["Math", "Chinese language", "Long context tasks"],
        notes="Strong math and multilingual support, 262K context",
        verified_working=True,
    ),
    
    "qwen/qwen3-coder:free": FreeModelInfo(
        model_id="qwen/qwen3-coder:free",
        display_name="Qwen3 Coder",
        provider="Alibaba",
        context_window=262144,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.CODING,
            ModelStrength.TOOL_USE,
            ModelStrength.LONG_CONTEXT,
        ],
        best_for=["Code generation", "Code review", "Tool calling"],
        notes="🏆 RANK #3 - Best free coding model (74.2), specialized for programming",
        verified_working=True,
        performance_score=74.2,
        capability_score=67.9,
        supports_tools=True,
    ),
    
    # =========================================================================
    # ARCEE MODELS
    # =========================================================================
    "arcee-ai/trinity-large-preview:free": FreeModelInfo(
        model_id="arcee-ai/trinity-large-preview:free",
        display_name="Arcee Trinity Large",
        provider="Arcee AI",
        context_window=131072,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.DIALOGUE,
            ModelStrength.TOOL_USE,
            ModelStrength.CREATIVE,
        ],
        best_for=["Conversation", "Roleplay", "Tool use"],
        notes="🏆 RANK #9 - Excellent agentic model (61.9) with tool support",
        verified_working=True,
        performance_score=61.9,
        capability_score=71.0,
        supports_tools=True,
    ),
    
    "arcee-ai/trinity-mini:free": FreeModelInfo(
        model_id="arcee-ai/trinity-mini:free",
        display_name="Arcee Trinity Mini",
        provider="Arcee AI",
        context_window=131072,
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.SPEED,
            ModelStrength.CODING,
        ],
        best_for=["Fast responses", "Quick coding tasks"],
        notes="Fast and capable for quick tasks",
        verified_working=True,
    ),
    
    # =========================================================================
    # NVIDIA MODELS
    # =========================================================================
    "nvidia/nemotron-3-nano-30b-a3b:free": FreeModelInfo(
        model_id="nvidia/nemotron-3-nano-30b-a3b:free",
        display_name="NVIDIA Nemotron 3 Nano 30B",
        provider="NVIDIA",
        context_window=256000,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.LONG_CONTEXT,
            ModelStrength.RAG,
        ],
        best_for=["Long context", "Document analysis"],
        notes="256K context - good for RAG",
        verified_working=True,
    ),
    
    "nvidia/nemotron-nano-12b-v2-vl:free": FreeModelInfo(
        model_id="nvidia/nemotron-nano-12b-v2-vl:free",
        display_name="NVIDIA Nemotron Nano 12B VL",
        provider="NVIDIA",
        context_window=128000,
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.SPEED,
        ],
        best_for=["Fast inference", "Vision-language (limited)"],
        notes="Fast nano model with some vision capability",
        verified_working=True,
    ),
    
    # =========================================================================
    # OTHER MODELS
    # =========================================================================
    "nousresearch/hermes-3-llama-3.1-405b:free": FreeModelInfo(
        model_id="nousresearch/hermes-3-llama-3.1-405b:free",
        display_name="Hermes 3 Llama 3.1 405B",
        provider="NousResearch",
        context_window=131072,
        speed_tier=SpeedTier.SLOW,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.DIALOGUE,
        ],
        best_for=["Complex reasoning", "Extended dialogue"],
        notes="🏆 RANK #7 - Massive model (62.0), thorough reasoning",
        verified_working=True,
        performance_score=62.0,
        capability_score=0.0,
        supports_tools=False,
    ),
    
    "z-ai/glm-4.5-air:free": FreeModelInfo(
        model_id="z-ai/glm-4.5-air:free",
        display_name="GLM 4.5 Air",
        provider="Zhipu AI",
        context_window=131072,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.MULTILINGUAL,
            ModelStrength.DIALOGUE,
        ],
        best_for=["Multilingual tasks", "Chinese language"],
        notes="Strong multilingual support, especially Chinese",
        verified_working=True,
    ),
    
    "upstage/solar-pro-3:free": FreeModelInfo(
        model_id="upstage/solar-pro-3:free",
        display_name="Solar Pro 3",
        provider="Upstage",
        context_window=128000,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.MULTILINGUAL,
            ModelStrength.DIALOGUE,
        ],
        best_for=["Korean language", "Dialogue"],
        notes="🏆 RANK #6 - Strong multilingual model (66.0)",
        verified_working=True,
        performance_score=66.0,
        capability_score=77.0,
        supports_tools=True,
    ),
    
    "openai/gpt-oss-20b:free": FreeModelInfo(
        model_id="openai/gpt-oss-20b:free",
        display_name="GPT OSS 20B",
        provider="OpenAI (OSS)",
        context_window=131072,
        speed_tier=SpeedTier.FAST,
        strengths=[
            ModelStrength.SPEED,
        ],
        best_for=["Fast simple tasks"],
        notes="Fast OSS variant",
        verified_working=True,
    ),
    
    "openai/gpt-oss-120b:free": FreeModelInfo(
        model_id="openai/gpt-oss-120b:free",
        display_name="GPT OSS 120B",
        provider="OpenAI (OSS)",
        context_window=131072,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.TOOL_USE,
            ModelStrength.REASONING,
        ],
        best_for=["Tool calling", "General tasks"],
        notes="🏆 RANK #5 - Strong general model (67.3) with tool support",
        verified_working=True,
        performance_score=67.3,
        capability_score=72.5,
        supports_tools=True,
    ),
    
    "tngtech/deepseek-r1t-chimera:free": FreeModelInfo(
        model_id="tngtech/deepseek-r1t-chimera:free",
        display_name="DeepSeek R1T Chimera",
        provider="TNG Technology",
        context_window=163840,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.LONG_CONTEXT,
        ],
        best_for=["Reasoning", "Long context"],
        notes="DeepSeek variant with extended context",
        verified_working=True,
    ),
    
    "tngtech/deepseek-r1t2-chimera:free": FreeModelInfo(
        model_id="tngtech/deepseek-r1t2-chimera:free",
        display_name="DeepSeek R1T2 Chimera",
        provider="TNG Technology",
        context_window=163840,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.LONG_CONTEXT,
            ModelStrength.DIALOGUE,
        ],
        best_for=["Reasoning", "Long context analysis", "Roleplay"],
        notes="🏆 RANK #1 - Highest performance score (81.3) among free models",
        verified_working=True,
        performance_score=81.3,
        capability_score=57.9,
        supports_tools=False,
    ),
    
    "moonshotai/kimi-k2:free": FreeModelInfo(
        model_id="moonshotai/kimi-k2:free",
        display_name="Moonshot AI Kimi K2",
        provider="Moonshot AI",
        context_window=32768,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.REASONING,
            ModelStrength.MULTILINGUAL,
        ],
        best_for=["Reasoning", "Chinese language tasks"],
        notes="🏆 RANK #4 - Strong performance (67.5), good reasoning model",
        verified_working=True,
        performance_score=67.5,
        capability_score=0.0,  # Not in capability top 20
        supports_tools=False,
    ),
    
    "tngtech/tng-r1t-chimera:free": FreeModelInfo(
        model_id="tngtech/tng-r1t-chimera:free",
        display_name="TNG R1T Chimera",
        provider="TNG Technology",
        context_window=163840,
        speed_tier=SpeedTier.MEDIUM,
        strengths=[
            ModelStrength.CREATIVE,
            ModelStrength.DIALOGUE,
            ModelStrength.TOOL_USE,
        ],
        best_for=["Creative writing", "Storytelling", "Tool calling"],
        notes="Creative/storytelling focused, improved EQ",
        verified_working=True,
    ),
}


# =============================================================================
# MODEL SELECTION HELPERS
# =============================================================================

def get_models_by_strength(strength: ModelStrength) -> List[str]:
    """Get all free model IDs that excel at a particular strength."""
    return [
        model_id for model_id, info in FREE_MODELS_DB.items()
        if strength in info.strengths and info.verified_working
    ]


def get_fast_models() -> List[str]:
    """Get all fast free models."""
    return [
        model_id for model_id, info in FREE_MODELS_DB.items()
        if info.speed_tier == SpeedTier.FAST and info.verified_working
    ]


def get_models_for_category(category: str) -> List[str]:
    """
    Get optimal free models for a benchmark category.
    
    Returns models ordered by suitability (best first).
    """
    category_lower = category.lower()
    
    # Category to strength mapping
    CATEGORY_STRENGTHS = {
        "math": [ModelStrength.MATH, ModelStrength.REASONING],
        "mathematics": [ModelStrength.MATH, ModelStrength.REASONING],
        "calculus": [ModelStrength.MATH, ModelStrength.REASONING],
        "algebra": [ModelStrength.MATH, ModelStrength.REASONING],
        "geometry": [ModelStrength.MATH, ModelStrength.REASONING],
        "number_theory": [ModelStrength.MATH, ModelStrength.REASONING],
        "combinatorics": [ModelStrength.MATH, ModelStrength.REASONING],
        
        "coding": [ModelStrength.CODING],
        "code": [ModelStrength.CODING],
        "algorithm": [ModelStrength.CODING, ModelStrength.REASONING],
        "data_structures": [ModelStrength.CODING],
        "sql": [ModelStrength.CODING],
        "devops": [ModelStrength.CODING],
        
        "reasoning": [ModelStrength.REASONING],
        "general_reasoning": [ModelStrength.REASONING],
        "physics": [ModelStrength.REASONING, ModelStrength.MATH],
        "chemistry": [ModelStrength.REASONING],
        "biology": [ModelStrength.REASONING],
        "computer_science": [ModelStrength.REASONING, ModelStrength.CODING],
        
        "multilingual": [ModelStrength.MULTILINGUAL],
        "translation": [ModelStrength.MULTILINGUAL],
        "chinese": [ModelStrength.MULTILINGUAL],
        "japanese": [ModelStrength.MULTILINGUAL],
        "german": [ModelStrength.MULTILINGUAL],
        "french": [ModelStrength.MULTILINGUAL],
        
        "dialogue": [ModelStrength.DIALOGUE],
        "empathy": [ModelStrength.DIALOGUE],
        "conversation": [ModelStrength.DIALOGUE],
        
        "rag": [ModelStrength.RAG, ModelStrength.LONG_CONTEXT],
        "retrieval": [ModelStrength.RAG],
        "long_context": [ModelStrength.LONG_CONTEXT],
        "memory": [ModelStrength.LONG_CONTEXT],
        
        "tool_use": [ModelStrength.TOOL_USE],
        "tools": [ModelStrength.TOOL_USE],
        
        "speed": [ModelStrength.SPEED],
    }
    
    target_strengths = CATEGORY_STRENGTHS.get(category_lower, [ModelStrength.REASONING])
    
    # Score each model
    scored_models = []
    for model_id, info in FREE_MODELS_DB.items():
        if not info.verified_working:
            continue
        
        # Calculate strength match score
        strength_score = 0
        for strength in target_strengths:
            if strength in info.strengths:
                strength_score += 2
        
        # Bonus for fast models (useful in parallel strategies)
        if info.is_fast:
            strength_score += 1
        
        # Use performance score as primary ranking (if available)
        # Formula: Performance score is weighted 10x more than strength matching
        # This ensures elite models (80+) are prioritized over lower performers
        performance_score = info.performance_score if info.performance_score > 0 else 50.0
        combined_score = (performance_score * 10) + strength_score
        
        scored_models.append((
            model_id, 
            combined_score,
            performance_score,
            strength_score,
            info.speed_tier.value
        ))
    
    # Sort by combined score (descending), then by speed (fast first)
    speed_order = {"fast": 0, "medium": 1, "slow": 2}
    scored_models.sort(key=lambda x: (-x[1], speed_order.get(x[4], 2)))
    
    return [model_id for model_id, _, _, _, _ in scored_models]


def get_ensemble_for_task(task_type: str, ensemble_size: int = 5) -> List[str]:
    """
    Get an optimal ensemble of free models for a task.
    
    This returns a diverse set of models to maximize quality through consensus.
    
    Args:
        task_type: Type of task (e.g., "math", "coding", "reasoning")
        ensemble_size: Number of models to include
    
    Returns:
        List of model IDs optimized for the task
    """
    # Get models sorted by suitability
    suitable_models = get_models_for_category(task_type)
    
    # For consensus, we want diversity + quality
    # Include: 1-2 fast models, 2-3 strong models for the category
    
    fast_models = [m for m in suitable_models if FREE_MODELS_DB[m].is_fast]
    slow_strong_models = [
        m for m in suitable_models 
        if FREE_MODELS_DB[m].speed_tier in (SpeedTier.MEDIUM, SpeedTier.SLOW)
    ]
    
    # Build ensemble: start with fast models for quick initial response
    ensemble = []
    
    # Add fast models (1-2)
    for m in fast_models[:2]:
        if len(ensemble) < ensemble_size and m not in ensemble:
            ensemble.append(m)
    
    # Add strong models for quality
    for m in slow_strong_models:
        if len(ensemble) < ensemble_size and m not in ensemble:
            ensemble.append(m)
    
    # Fill remaining with any suitable models
    for m in suitable_models:
        if len(ensemble) < ensemble_size and m not in ensemble:
            ensemble.append(m)
    
    return ensemble[:ensemble_size]


# =============================================================================
# VERIFIED MODEL LIST FOR PROVIDER MAPPING
# =============================================================================

def get_all_verified_free_model_ids() -> List[str]:
    """Get all verified working free model IDs."""
    return [
        model_id for model_id, info in FREE_MODELS_DB.items()
        if info.verified_working
    ]


# =============================================================================
# ADVANCED ORCHESTRATION HELPERS (Jan 31, 2026)
# =============================================================================

def get_top_performers(
    category: str, 
    min_score: float = 0.0, 
    n: int = 5
) -> List[str]:
    """
    Get top N performing models for a category by performance score.
    
    Args:
        category: Task category (e.g., "math", "coding", "reasoning")
        min_score: Minimum performance score threshold (0-100)
        n: Number of models to return
    
    Returns:
        List of model IDs sorted by performance score (descending)
    """
    suitable_models = get_models_for_category(category)
    
    # Filter by minimum score
    high_performers = [
        model_id for model_id in suitable_models
        if FREE_MODELS_DB[model_id].performance_score >= min_score
    ]
    
    # Sort by performance score (descending)
    high_performers.sort(
        key=lambda m: FREE_MODELS_DB[m].performance_score, 
        reverse=True
    )
    
    return high_performers[:n]


def get_diverse_models(
    category: str,
    exclude_provider: Optional[str] = None,
    min_score: float = 0.0,
    n: int = 3
) -> List[str]:
    """
    Get diverse models from different providers for cross-validation.
    
    Args:
        category: Task category
        exclude_provider: Provider to exclude (e.g., "TNG Technology")
        min_score: Minimum performance score
        n: Number of models to return
    
    Returns:
        List of model IDs from different providers
    """
    suitable_models = get_models_for_category(category)
    
    # Filter by score
    qualified = [
        m for m in suitable_models
        if FREE_MODELS_DB[m].performance_score >= min_score
    ]
    
    # Group by provider
    by_provider: Dict[str, List[str]] = {}
    for model_id in qualified:
        provider = FREE_MODELS_DB[model_id].provider
        if exclude_provider and provider == exclude_provider:
            continue
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model_id)
    
    # Pick one from each provider (round-robin for diversity)
    diverse_selection = []
    providers = list(by_provider.keys())
    idx = 0
    
    while len(diverse_selection) < n and providers:
        provider = providers[idx % len(providers)]
        if by_provider[provider]:
            diverse_selection.append(by_provider[provider].pop(0))
            if not by_provider[provider]:
                providers.remove(provider)
        idx += 1
        
        # Safety: break if we've cycled through all
        if idx > len(providers) * 10:
            break
    
    return diverse_selection[:n]


def get_tool_capable_models(category: str = "reasoning") -> List[str]:
    """
    Get models that support function calling / tool use.
    
    Args:
        category: Task category for additional filtering
    
    Returns:
        List of tool-capable model IDs
    """
    tool_models = [
        model_id for model_id, info in FREE_MODELS_DB.items()
        if info.supports_tools and info.verified_working
    ]
    
    # Sort by performance score if available
    tool_models.sort(
        key=lambda m: FREE_MODELS_DB[m].performance_score,
        reverse=True
    )
    
    return tool_models


def get_fastest_model_for_category(category: str) -> str:
    """
    Get the single fastest model for a category.
    
    Prioritizes FAST speed tier, then performance score.
    
    Args:
        category: Task category
    
    Returns:
        Model ID of fastest suitable model
    """
    suitable_models = get_models_for_category(category)
    
    # Filter to FAST tier only
    fast_models = [
        m for m in suitable_models
        if FREE_MODELS_DB[m].speed_tier == SpeedTier.FAST
    ]
    
    if not fast_models:
        # Fallback to MEDIUM if no FAST available
        fast_models = [
            m for m in suitable_models
            if FREE_MODELS_DB[m].speed_tier == SpeedTier.MEDIUM
        ]
    
    if not fast_models:
        # Last resort: any model
        fast_models = suitable_models
    
    # Among fast models, pick highest performer
    if fast_models:
        fast_models.sort(
            key=lambda m: FREE_MODELS_DB[m].performance_score,
            reverse=True
        )
        return fast_models[0]
    
    # Ultimate fallback
    return list(FREE_MODELS_DB.keys())[0]


def get_elite_models(min_score: float = 80.0) -> List[str]:
    """
    Get all elite-tier models (80+ performance score).
    
    Args:
        min_score: Minimum score threshold for elite status
    
    Returns:
        List of elite model IDs sorted by score
    """
    elite = [
        model_id for model_id, info in FREE_MODELS_DB.items()
        if info.performance_score >= min_score and info.verified_working
    ]
    
    elite.sort(
        key=lambda m: FREE_MODELS_DB[m].performance_score,
        reverse=True
    )
    
    return elite


def get_model_provider(model_id: str) -> str:
    """Get the provider name for a model."""
    info = FREE_MODELS_DB.get(model_id)
    return info.provider if info else "Unknown"


def estimate_model_latency(model_id: str) -> float:
    """
    Estimate response latency in seconds for a model.
    
    Based on speed tier and provider routing.
    """
    info = FREE_MODELS_DB.get(model_id)
    if not info:
        return 30.0  # Default estimate
    
    # Base latency by speed tier
    if info.speed_tier == SpeedTier.FAST:
        base = 5.0
    elif info.speed_tier == SpeedTier.MEDIUM:
        base = 15.0
    else:  # SLOW
        base = 30.0
    
    # Direct API routing is faster
    if info.uses_direct_api:
        base *= 0.7  # 30% faster via direct API
    
    return base


# Print verification on import (for debugging)
if __name__ == "__main__":
    print("FREE MODELS DATABASE")
    print("=" * 60)
    for model_id, info in FREE_MODELS_DB.items():
        status = "✓" if info.verified_working else "✗"
        print(f"{status} {info.display_name}")
        print(f"  ID: {model_id}")
        print(f"  Context: {info.context_window:,} tokens")
        print(f"  Speed: {info.speed_tier.value}")
        print(f"  Strengths: {[s.value for s in info.strengths]}")
        print()
