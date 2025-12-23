"""Advanced reasoning method model routing system (Late 2025).

This module implements intelligent model routing based on reasoning methods,
following the latest model capabilities and rankings as of November 2025.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class ReasoningMethod(str, Enum):
    """Advanced reasoning methods for LLM orchestration.
    
    Based on research: "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
    """
    # Original methods
    chain_of_thought = "chain-of-thought"
    tree_of_thought = "tree-of-thought"
    react = "react"
    plan_and_solve = "plan-and-solve"
    self_consistency = "self-consistency"
    reflexion = "reflexion"
    
    # Research methods from "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
    hierarchical_decomposition = "hierarchical-decomposition"  # HRM-style
    iterative_refinement = "iterative-refinement"  # Diffusion-inspired
    confidence_filtering = "confidence-filtering"  # DeepConf
    dynamic_planning = "dynamic-planning"  # Test-time decision-making


# Model identifiers (as they appear in the orchestrator)
# Updated for Dec 2025 availability
MODEL_GPT_5_1 = "gpt-5.1"  # if/when available
MODEL_GPT_5_1_INSTANT = "gpt-5.1-instant"
MODEL_GPT_4_1 = "gpt-4.1"
MODEL_GPT_4O = "gpt-4o"
MODEL_CLAUDE_4_5 = "claude-opus-4.5"
MODEL_CLAUDE_SONNET_4 = "claude-sonnet-4"
MODEL_GEMINI_3_PRO = "gemini-3-pro"
MODEL_GEMINI_2_5 = "gemini-2.5-pro"
MODEL_GROK_4_HEAVY = "grok-4-heavy"
MODEL_GROK_4 = "grok-4"
MODEL_GROK_4_1 = "grok-4.1"
MODEL_LLAMA_3_70B = "llama-3-70b"
MODEL_DEEPSEEK_V3_1 = "deepseek-v3.1"
MODEL_QWEN3 = "qwen3"
MODEL_MISTRAL_LARGE_2 = "mistral-large-2"
MODEL_MIXTRAL_8X22B = "mixtral-8x22b"

# Fallback models (CURRENT OpenRouter rankings - December 2025)
# These MUST match actual OpenRouter model IDs

# OpenAI - Top tier
FALLBACK_GPT_5 = "openai/gpt-5"  # #1 in Health rankings
FALLBACK_O1 = "openai/o1"  # #5 in Health rankings - reasoning specialist
FALLBACK_GPT_4O = "openai/gpt-4o"  # Still available as fallback
FALLBACK_GPT_4O_MINI = "openai/gpt-4o-mini"

# Anthropic - Top tier
FALLBACK_CLAUDE_OPUS_4 = "anthropic/claude-opus-4-20250514"  # #2 in Health rankings
FALLBACK_CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4-20250514"  # #4 in Health rankings
FALLBACK_CLAUDE_3_5 = "anthropic/claude-3-5-sonnet-20241022"
FALLBACK_CLAUDE_3_HAIKU = "anthropic/claude-3-5-haiku-20241022"

# Google - Top tier
FALLBACK_GEMINI_2_PRO = "google/gemini-2.0-pro"  # #3 in Health rankings
FALLBACK_MED_PALM_3 = "google/med-palm-3"  # #6 in Health rankings - medical specialist
FALLBACK_GEMINI_2_5 = "google/gemini-2.5-pro"
FALLBACK_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"

# Meta - Llama 4
FALLBACK_LLAMA_4_70B = "meta-llama/llama-4-70b"  # #7 in Health rankings

# Mistral AI
FALLBACK_MISTRAL_LARGE_2 = "mistralai/mistral-large-2"  # #8 in Health rankings
FALLBACK_MISTRAL = "mistralai/mistral-large"
FALLBACK_MIXTRAL = "mistralai/mixtral-8x7b"

# xAI: Grok
FALLBACK_GROK_2 = "x-ai/grok-2"
FALLBACK_GROK_BETA = "x-ai/grok-beta"  # Legacy

# Other providers
FALLBACK_DEEPSEEK = "deepseek/deepseek-chat"
FALLBACK_QWEN = "qwen/qwen2.5"


# Model routing configuration for each reasoning method
# Format: (preferred_model, [fallback1, fallback2, ...])
# Based on research: "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
REASONING_METHOD_ROUTING = {
    # Original methods
    ReasoningMethod.chain_of_thought: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,
        [MODEL_GPT_4_1, MODEL_GPT_4O, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.tree_of_thought: (
        MODEL_CLAUDE_4_5,
        [MODEL_CLAUDE_SONNET_4, MODEL_GPT_5_1, MODEL_GPT_4O, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4_HEAVY, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.react: (
        MODEL_CLAUDE_4_5,
        [MODEL_CLAUDE_SONNET_4, MODEL_GPT_5_1, MODEL_GPT_4O, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.plan_and_solve: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,
        [MODEL_GPT_4_1, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.self_consistency: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,
        [MODEL_GPT_4_1, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4_HEAVY, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.reflexion: (
        MODEL_CLAUDE_4_5,
        [MODEL_CLAUDE_SONNET_4, MODEL_GPT_5_1, MODEL_GPT_4O, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # Research methods from "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
    # 1. Hierarchical Task Decomposition (HRM-style)
    # Best: GPT-4.1 (GPT-5.1), Claude 2/3, Gemini Pro/Ultra, PaLM 2, LLaMA-2 70B
    ReasoningMethod.hierarchical_decomposition: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,  # complex planning
        [MODEL_GPT_4_1, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # 2. Diffusion-Inspired Iterative Reasoning
    # Best: GPT-4.1, Gemini 2.5 Pro/Ultra, Claude 2, GPT-3.5 Turbo, Open-source
    ReasoningMethod.iterative_refinement: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,
        [MODEL_GPT_4_1, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # 3. Confidence-Based Filtering (DeepConf)
    # Best: GPT-4, Gemini, Claude 2, GPT-3.5, Open-source with logits
    ReasoningMethod.confidence_filtering: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,
        [MODEL_GPT_4_1, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # 4. Dynamic Planning (Test-Time Decision-Making)
    # Best: GPT-4, Gemini, Claude 2, GPT-3.5, Rule-based
    ReasoningMethod.dynamic_planning: (
        MODEL_GPT_5_1 if MODEL_GPT_5_1 else MODEL_GPT_4O,
        [MODEL_GPT_4_1, MODEL_GEMINI_3_PRO, MODEL_GEMINI_2_5, MODEL_CLAUDE_4_5, MODEL_CLAUDE_SONNET_4, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
}


def get_models_for_reasoning_method(
    method: ReasoningMethod,
    available_models: Optional[List[str]] = None,
) -> List[str]:
    """
    Get the best model(s) for a given reasoning method.
    
    Args:
        method: The reasoning method to use
        available_models: List of models actually available in the orchestrator
        
    Returns:
        List of model identifiers to use (preferred first, then fallbacks)
    """
    preferred, fallbacks = REASONING_METHOD_ROUTING.get(method, (None, []))
    
    # Build candidate list
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.extend(fallbacks)
    
    # If available_models is provided, filter to only include available ones
    if available_models:
        candidates = [m for m in candidates if m in available_models]
    
    # If no candidates match, use fallback models
    if not candidates:
        logger.warning(
            "No preferred models available for method %s, using fallback models",
            method.value,
        )
        candidates = [
            FALLBACK_GPT_4O,
            FALLBACK_CLAUDE_3_5,
            FALLBACK_GEMINI_2_5,
        ]
    
    # Map future models to current fallbacks
    mapped_candidates = []
    for model_id in candidates:
        if model_id == MODEL_DEEPSEEK_V3_1:
            mapped_candidates.append(FALLBACK_DEEPSEEK)
        elif model_id == MODEL_QWEN3:
            mapped_candidates.append(FALLBACK_QWEN)
        elif model_id == MODEL_MISTRAL_LARGE_2:
            mapped_candidates.append(FALLBACK_MISTRAL)
        elif model_id == MODEL_MIXTRAL_8X22B:
            mapped_candidates.append(FALLBACK_MIXTRAL)
        elif model_id == MODEL_GROK_4_1:
            mapped_candidates.append(FALLBACK_GROK_BETA)
        else:
            # Keep original model ID (will be mapped in orchestrator_adapter)
            mapped_candidates.append(model_id)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for m in mapped_candidates:
        if m not in seen:
            seen.add(m)
            unique_candidates.append(m)
    
    # Return at least one model
    return unique_candidates[:3] if unique_candidates else [FALLBACK_GPT_4O_MINI]


def map_reasoning_mode_to_method(reasoning_mode: str) -> ReasoningMethod:
    """
    Map the simple reasoning_mode (fast/standard/deep) to an advanced reasoning method.
    
    This provides backward compatibility while enabling advanced methods.
    """
    mode_lower = reasoning_mode.lower()
    
    if mode_lower == "fast":
        return ReasoningMethod.chain_of_thought  # Fast CoT
    elif mode_lower == "standard":
        return ReasoningMethod.chain_of_thought  # Standard CoT
    elif mode_lower == "deep":
        return ReasoningMethod.tree_of_thought  # Deep = tree search
    else:
        # Default to chain-of-thought
        return ReasoningMethod.chain_of_thought


# ==============================================================================
# Task-Type Based Model Selection (Automatic Routing)
# ==============================================================================

# Model capabilities for intelligent task routing
# Each model is rated 0-100 on various capabilities
MODEL_CAPABILITIES = {
    FALLBACK_GPT_4O: {
        "coding": 95,
        "math": 90,
        "reasoning": 95,
        "creative": 85,
        "factual": 90,
        "analysis": 95,
        "speed": 75,
        "overall": 92,
    },
    FALLBACK_GPT_4O_MINI: {
        "coding": 80,
        "math": 75,
        "reasoning": 80,
        "creative": 75,
        "factual": 80,
        "analysis": 80,
        "speed": 95,
        "overall": 80,
    },
    FALLBACK_CLAUDE_SONNET_4: {
        "coding": 95,
        "math": 85,
        "reasoning": 95,
        "creative": 95,
        "factual": 90,
        "analysis": 95,
        "speed": 70,
        "overall": 93,
    },
    FALLBACK_CLAUDE_3_5: {
        "coding": 90,
        "math": 85,
        "reasoning": 90,
        "creative": 90,
        "factual": 88,
        "analysis": 90,
        "speed": 80,
        "overall": 89,
    },
    FALLBACK_CLAUDE_3_HAIKU: {
        "coding": 75,
        "math": 70,
        "reasoning": 75,
        "creative": 80,
        "factual": 75,
        "analysis": 75,
        "speed": 98,
        "overall": 78,
    },
    FALLBACK_GEMINI_2_5: {
        "coding": 90,
        "math": 90,
        "reasoning": 92,
        "creative": 80,
        "factual": 92,
        "analysis": 90,
        "speed": 80,
        "overall": 90,
    },
    FALLBACK_GEMINI_2_5_FLASH: {
        "coding": 80,
        "math": 80,
        "reasoning": 82,
        "creative": 75,
        "factual": 85,
        "analysis": 80,
        "speed": 95,
        "overall": 82,
    },
    FALLBACK_GROK_2: {
        "coding": 85,
        "math": 80,
        "reasoning": 85,
        "creative": 85,
        "factual": 92,  # Excellent for real-time
        "analysis": 85,
        "speed": 85,
        "overall": 86,
    },
    FALLBACK_DEEPSEEK: {
        "coding": 95,  # Exceptional at coding
        "math": 90,
        "reasoning": 88,
        "creative": 70,
        "factual": 80,
        "analysis": 85,
        "speed": 90,
        "overall": 86,
    },
}

# Task type to capability mapping (aligns with domain categories)
TASK_CAPABILITY_MAP = {
    # Code/Programming
    "code_generation": "coding",
    "debugging": "coding",
    # Math/Quantitative
    "math_problem": "math",
    # Health/Medical (needs accuracy + factual + reasoning)
    "health_medical": "reasoning",  # Medical needs careful reasoning
    # Science/Academic
    "science_research": "analysis",
    # Legal (needs accuracy + reasoning)
    "legal_analysis": "reasoning",
    # Finance (needs analysis + factual)
    "financial_analysis": "analysis",
    # Other
    "factual_question": "factual",
    "research_analysis": "analysis",
    "creative_writing": "creative",
    "explanation": "reasoning",
    "comparison": "analysis",
    "planning": "reasoning",
    "summarization": "analysis",
    "fast_response": "speed",
    "high_quality": "overall",
    "general": "overall",
}


def get_best_models_for_task(
    task_type: str,
    available_models: Optional[List[str]] = None,
    num_models: int = 3,
    criteria: Optional[dict] = None,
) -> List[str]:
    """
    Get the best models for a specific task type (Automatic Model Selection).
    
    Args:
        task_type: Type of task (from PromptOps analysis)
        available_models: Models actually available in the orchestrator
        num_models: Maximum number of models to return
        criteria: User criteria (accuracy, speed, creativity weights)
        
    Returns:
        List of best models for the task, ordered by fit
    """
    # Map task type to capability
    capability = TASK_CAPABILITY_MAP.get(task_type.lower(), "overall")
    
    # Default criteria if not provided
    if not criteria:
        criteria = {"accuracy": 70, "speed": 50, "creativity": 50}
    
    # Determine all candidate models
    all_models = list(MODEL_CAPABILITIES.keys())
    
    if available_models:
        # Filter to only available models
        candidate_models = [m for m in all_models if m in available_models]
    else:
        candidate_models = all_models
    
    if not candidate_models:
        # Fallback to defaults
        return [FALLBACK_GPT_4O, FALLBACK_CLAUDE_3_5, FALLBACK_DEEPSEEK][:num_models]
    
    # Score each model based on task type and user criteria
    model_scores = []
    for model in candidate_models:
        caps = MODEL_CAPABILITIES.get(model, {})
        
        # Base score from task capability
        task_score = caps.get(capability, 50)
        
        # Adjust by criteria
        # Accuracy: weight task-specific capability
        accuracy_weight = criteria.get("accuracy", 70) / 100
        accuracy_score = task_score * accuracy_weight
        
        # Speed: weight speed capability
        speed_weight = criteria.get("speed", 50) / 100
        speed_score = caps.get("speed", 50) * speed_weight
        
        # Creativity: weight creative capability
        creativity_weight = criteria.get("creativity", 50) / 100
        creativity_score = caps.get("creative", 50) * creativity_weight
        
        # Combined score
        total_score = accuracy_score + speed_score * 0.3 + creativity_score * 0.2
        model_scores.append((model, total_score))
    
    # Sort by score descending
    model_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top N models
    selected = [m for m, _ in model_scores[:num_models]]
    
    logger.info(
        "Task-type model selection: task=%s, capability=%s, selected=%s",
        task_type,
        capability,
        selected,
    )
    
    return selected


def get_diverse_ensemble(
    task_type: str,
    available_models: Optional[List[str]] = None,
    num_models: int = 3,
) -> List[str]:
    """
    Get a diverse ensemble of models for multi-model orchestration.
    
    Ensures diversity by selecting from different providers.
    
    Args:
        task_type: Type of task
        available_models: Available models
        num_models: Target ensemble size
        
    Returns:
        Diverse list of models
    """
    # Define provider groups
    provider_groups = {
        "openai": [FALLBACK_GPT_4O, FALLBACK_GPT_4O_MINI],
        "anthropic": [FALLBACK_CLAUDE_SONNET_4, FALLBACK_CLAUDE_3_5, FALLBACK_CLAUDE_3_HAIKU],
        "google": [FALLBACK_GEMINI_2_5, FALLBACK_GEMINI_2_5_FLASH],
        "xai": [FALLBACK_GROK_2],
        "deepseek": [FALLBACK_DEEPSEEK],
    }
    
    # Get best models for task
    best_models = get_best_models_for_task(task_type, available_models, num_models=10)
    
    # Select one from each provider for diversity
    ensemble = []
    providers_used = set()
    
    for model in best_models:
        if len(ensemble) >= num_models:
            break
        
        # Find provider
        provider = None
        for p, models in provider_groups.items():
            if model in models:
                provider = p
                break
        
        # Add if new provider
        if provider and provider not in providers_used:
            ensemble.append(model)
            providers_used.add(provider)
    
    # Fill remaining slots with best remaining
    for model in best_models:
        if len(ensemble) >= num_models:
            break
        if model not in ensemble:
            ensemble.append(model)
    
    logger.info(
        "Diverse ensemble: task=%s, ensemble=%s, providers=%s",
        task_type,
        ensemble,
        list(providers_used),
    )
    
    return ensemble

