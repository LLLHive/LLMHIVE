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
MODEL_GPT_5_1 = "gpt-5.1"
MODEL_GPT_5_1_INSTANT = "gpt-5.1-instant"
MODEL_CLAUDE_4_5 = "claude-opus-4.5"
MODEL_GEMINI_3_PRO = "gemini-3-pro"
MODEL_GROK_4_HEAVY = "grok-4-heavy"
MODEL_GROK_4 = "grok-4"
MODEL_GROK_4_1 = "grok-4.1"
MODEL_LLAMA_3_70B = "llama-3-70b"
MODEL_DEEPSEEK_V3_1 = "deepseek-v3.1"
MODEL_QWEN3 = "qwen3"
MODEL_MISTRAL_LARGE_2 = "mistral-large-2"
MODEL_MIXTRAL_8X22B = "mixtral-8x22b"

# Fallback models (current available models)
FALLBACK_GPT_4O = "gpt-4o"
FALLBACK_GPT_4O_MINI = "gpt-4o-mini"
FALLBACK_CLAUDE_3_5 = "claude-3-5-sonnet-20241022"
FALLBACK_CLAUDE_3_HAIKU = "claude-3-5-haiku-20241022"
FALLBACK_GEMINI_2_5 = "gemini-2.5-pro"
FALLBACK_GROK_BETA = "grok-beta"
FALLBACK_DEEPSEEK = "deepseek-chat"  # Current DeepSeek model
FALLBACK_QWEN = "qwen2.5"  # Current Qwen model
FALLBACK_MISTRAL = "mistral-large"  # Current Mistral model
FALLBACK_MIXTRAL = "mixtral-8x7b"  # Current Mixtral model


# Model routing configuration for each reasoning method
# Format: (preferred_model, [fallback1, fallback2, ...])
# Based on research: "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
REASONING_METHOD_ROUTING = {
    # Original methods
    ReasoningMethod.chain_of_thought: (
        MODEL_GPT_5_1,
        [MODEL_CLAUDE_4_5, MODEL_GEMINI_3_PRO, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.tree_of_thought: (
        MODEL_CLAUDE_4_5,
        [MODEL_GPT_5_1, MODEL_GEMINI_3_PRO, MODEL_GROK_4_HEAVY, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.react: (
        MODEL_CLAUDE_4_5,
        [MODEL_GPT_5_1, MODEL_GEMINI_3_PRO, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.plan_and_solve: (
        MODEL_GPT_5_1,
        [MODEL_CLAUDE_4_5, MODEL_GEMINI_3_PRO, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.self_consistency: (
        MODEL_GPT_5_1,
        [MODEL_CLAUDE_4_5, MODEL_GEMINI_3_PRO, MODEL_GROK_4_HEAVY, MODEL_LLAMA_3_70B],
    ),
    ReasoningMethod.reflexion: (
        MODEL_CLAUDE_4_5,
        [MODEL_GPT_5_1, MODEL_GEMINI_3_PRO, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # Research methods from "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
    # 1. Hierarchical Task Decomposition (HRM-style)
    # Best: GPT-4.1 (GPT-5.1), Claude 2/3, Gemini Pro/Ultra, PaLM 2, LLaMA-2 70B
    ReasoningMethod.hierarchical_decomposition: (
        MODEL_GPT_5_1,  # GPT-4.1 equivalent - best for complex planning
        [MODEL_CLAUDE_4_5, MODEL_GEMINI_3_PRO, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # 2. Diffusion-Inspired Iterative Reasoning
    # Best: GPT-4.1, Gemini 2.5 Pro/Ultra, Claude 2, GPT-3.5 Turbo, Open-source
    ReasoningMethod.iterative_refinement: (
        MODEL_GPT_5_1,  # GPT-4.1 - best for draft & refine
        [MODEL_GEMINI_3_PRO, MODEL_CLAUDE_4_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # 3. Confidence-Based Filtering (DeepConf)
    # Best: GPT-4, Gemini, Claude 2, GPT-3.5, Open-source with logits
    ReasoningMethod.confidence_filtering: (
        MODEL_GPT_5_1,  # GPT-4 - best calibration and confidence signals
        [MODEL_GEMINI_3_PRO, MODEL_CLAUDE_4_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
    ),
    
    # 4. Dynamic Planning (Test-Time Decision-Making)
    # Best: GPT-4, Gemini, Claude 2, GPT-3.5, Rule-based
    ReasoningMethod.dynamic_planning: (
        MODEL_GPT_5_1,  # GPT-4 - best for adaptive orchestration
        [MODEL_GEMINI_3_PRO, MODEL_CLAUDE_4_5, MODEL_GROK_4, MODEL_LLAMA_3_70B],
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

