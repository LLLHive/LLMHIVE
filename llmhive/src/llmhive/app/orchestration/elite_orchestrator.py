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
    from .reasoning_strategies_controller import ReasoningStrategiesController

logger = logging.getLogger(__name__)

# KB Pipeline Integration (lazy loaded to avoid circular imports)
_kb_bridge_loaded = False
_process_with_kb_pipeline = None
_kb_available = False


def _load_kb_bridge():
    """Lazy load KB pipeline bridge."""
    global _kb_bridge_loaded, _process_with_kb_pipeline, _kb_available
    
    if _kb_bridge_loaded:
        return _kb_available
    
    try:
        from llmhive.pipelines.kb_orchestrator_bridge import (
            process_with_kb_pipeline,
            create_kb_orchestrator_handler,
        )
        _process_with_kb_pipeline = process_with_kb_pipeline
        _kb_available = True
        logger.info("KB pipeline bridge loaded successfully")
    except ImportError as e:
        logger.debug("KB pipeline bridge not available: %s", e)
        _kb_available = False
    
    _kb_bridge_loaded = True
    return _kb_available

# Try to import reasoning strategies controller for enhanced selection
try:
    from .reasoning_strategies_controller import (
        get_strategy_controller,
        TraceLogTags,
        REASONING_METHODS_DB,
    )
    REASONING_STRATEGIES_AVAILABLE = True
except ImportError:
    REASONING_STRATEGIES_AVAILABLE = False
    get_strategy_controller = None  # type: ignore
    TraceLogTags = None  # type: ignore
    REASONING_METHODS_DB = None  # type: ignore


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
    # ==========================================================================
    # GPT-5.x Series (Q1 2026) - Next-gen flagship models
    # ==========================================================================
    # GPT-5: Flagship model - best overall quality
    "gpt-5": {
        ModelCapability.CODING: 0.97,
        ModelCapability.REASONING: 0.98,
        ModelCapability.MATH: 0.96,
        ModelCapability.CREATIVE: 0.92,
        ModelCapability.FACTUAL: 0.96,
        ModelCapability.ANALYSIS: 0.97,
        ModelCapability.SUMMARIZATION: 0.94,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.98,
        ModelCapability.SPEED: 0.65,
        ModelCapability.QUALITY: 0.98,
    },
    # GPT-5 Pro: Enhanced reasoning and accuracy
    "gpt-5-pro": {
        ModelCapability.CODING: 0.98,
        ModelCapability.REASONING: 0.99,
        ModelCapability.MATH: 0.98,
        ModelCapability.CREATIVE: 0.90,
        ModelCapability.FACTUAL: 0.98,
        ModelCapability.ANALYSIS: 0.98,
        ModelCapability.SUMMARIZATION: 0.95,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.98,
        ModelCapability.SPEED: 0.55,
        ModelCapability.QUALITY: 0.99,
    },
    # GPT-5 Mini: Fast and efficient
    "gpt-5-mini": {
        ModelCapability.CODING: 0.88,
        ModelCapability.REASONING: 0.86,
        ModelCapability.MATH: 0.85,
        ModelCapability.CREATIVE: 0.82,
        ModelCapability.FACTUAL: 0.86,
        ModelCapability.ANALYSIS: 0.85,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.95,
        ModelCapability.QUALITY: 0.86,
    },
    # GPT-5 Nano: Ultra-fast, cost-effective
    "gpt-5-nano": {
        ModelCapability.CODING: 0.78,
        ModelCapability.REASONING: 0.75,
        ModelCapability.MATH: 0.72,
        ModelCapability.CREATIVE: 0.70,
        ModelCapability.FACTUAL: 0.76,
        ModelCapability.ANALYSIS: 0.74,
        ModelCapability.SUMMARIZATION: 0.80,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.82,
        ModelCapability.SPEED: 0.98,
        ModelCapability.QUALITY: 0.75,
    },
    # GPT-5.1: Iterative improvement
    "gpt-5.1": {
        ModelCapability.CODING: 0.97,
        ModelCapability.REASONING: 0.98,
        ModelCapability.MATH: 0.97,
        ModelCapability.CREATIVE: 0.93,
        ModelCapability.FACTUAL: 0.97,
        ModelCapability.ANALYSIS: 0.97,
        ModelCapability.SUMMARIZATION: 0.95,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.98,
        ModelCapability.SPEED: 0.68,
        ModelCapability.QUALITY: 0.98,
    },
    # GPT-5.2: Latest iteration
    "gpt-5.2": {
        ModelCapability.CODING: 0.98,
        ModelCapability.REASONING: 0.98,
        ModelCapability.MATH: 0.97,
        ModelCapability.CREATIVE: 0.94,
        ModelCapability.FACTUAL: 0.97,
        ModelCapability.ANALYSIS: 0.98,
        ModelCapability.SUMMARIZATION: 0.95,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.98,
        ModelCapability.SPEED: 0.70,
        ModelCapability.QUALITY: 0.98,
    },
    # GPT-5.2 Pro: Best-in-class
    "gpt-5.2-pro": {
        ModelCapability.CODING: 0.99,
        ModelCapability.REASONING: 0.99,
        ModelCapability.MATH: 0.99,
        ModelCapability.CREATIVE: 0.92,
        ModelCapability.FACTUAL: 0.99,
        ModelCapability.ANALYSIS: 0.99,
        ModelCapability.SUMMARIZATION: 0.96,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.99,
        ModelCapability.SPEED: 0.52,
        ModelCapability.QUALITY: 0.99,
    },
    # ==========================================================================
    # OpenAI o-Series: Reasoning Specialists
    # ==========================================================================
    # o1: Dedicated reasoning model
    "o1": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.99,  # Specialist!
        ModelCapability.MATH: 0.98,       # Specialist!
        ModelCapability.CREATIVE: 0.70,   # Lower for creative
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.96,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.40,      # Slower due to reasoning
        ModelCapability.QUALITY: 0.96,
    },
    # o1-pro: Enhanced reasoning
    "o1-pro": {
        ModelCapability.CODING: 0.96,
        ModelCapability.REASONING: 0.995, # Best reasoning!
        ModelCapability.MATH: 0.99,       # Near-perfect math
        ModelCapability.CREATIVE: 0.68,
        ModelCapability.FACTUAL: 0.94,
        ModelCapability.ANALYSIS: 0.97,
        ModelCapability.SUMMARIZATION: 0.80,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.86,
        ModelCapability.SPEED: 0.30,      # Very slow
        ModelCapability.QUALITY: 0.97,
    },
    # o3: Latest reasoning model
    "o3": {
        ModelCapability.CODING: 0.97,
        ModelCapability.REASONING: 0.995, # Top-tier reasoning
        ModelCapability.MATH: 0.99,
        ModelCapability.CREATIVE: 0.72,
        ModelCapability.FACTUAL: 0.95,
        ModelCapability.ANALYSIS: 0.98,
        ModelCapability.SUMMARIZATION: 0.83,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.35,
        ModelCapability.QUALITY: 0.98,
    },
    # o4-mini: Fast reasoning
    "o4-mini": {
        ModelCapability.CODING: 0.90,
        ModelCapability.REASONING: 0.94,
        ModelCapability.MATH: 0.95,
        ModelCapability.CREATIVE: 0.68,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.90,
        ModelCapability.SUMMARIZATION: 0.78,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.85,
        ModelCapability.SPEED: 0.75,
        ModelCapability.QUALITY: 0.92,
    },
    # ==========================================================================
    # Gemini 2.0 Series
    # ==========================================================================
    # Gemini 2.0 Pro: Long context, multimodal
    "gemini-2.0-pro": {
        ModelCapability.CODING: 0.90,
        ModelCapability.REASONING: 0.92,
        ModelCapability.MATH: 0.94,
        ModelCapability.CREATIVE: 0.85,
        ModelCapability.FACTUAL: 0.94,
        ModelCapability.ANALYSIS: 0.93,
        ModelCapability.SUMMARIZATION: 0.90,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.78,
        ModelCapability.QUALITY: 0.92,
    },
    # Gemini 2.0 Flash: Speed optimized
    "gemini-2.0-flash": {
        ModelCapability.CODING: 0.82,
        ModelCapability.REASONING: 0.80,
        ModelCapability.MATH: 0.82,
        ModelCapability.CREATIVE: 0.78,
        ModelCapability.FACTUAL: 0.84,
        ModelCapability.ANALYSIS: 0.80,
        ModelCapability.SUMMARIZATION: 0.84,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.82,
        ModelCapability.SPEED: 0.96,
        ModelCapability.QUALITY: 0.80,
    },
    # ==========================================================================
    # Llama 4 Series (Meta)
    # ==========================================================================
    "llama-4-70b": {
        ModelCapability.CODING: 0.90,
        ModelCapability.REASONING: 0.88,
        ModelCapability.MATH: 0.86,
        ModelCapability.CREATIVE: 0.82,
        ModelCapability.FACTUAL: 0.86,
        ModelCapability.ANALYSIS: 0.87,
        ModelCapability.SUMMARIZATION: 0.85,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.75,
        ModelCapability.QUALITY: 0.88,
    },
    "llama-4-405b": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.93,
        ModelCapability.MATH: 0.91,
        ModelCapability.CREATIVE: 0.86,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.92,
        ModelCapability.SUMMARIZATION: 0.90,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.92,
        ModelCapability.SPEED: 0.60,
        ModelCapability.QUALITY: 0.93,
    },
    # ==========================================================================
    # Qwen 3 Series (Alibaba)
    # ==========================================================================
    "qwen-3-72b": {
        ModelCapability.CODING: 0.92,
        ModelCapability.REASONING: 0.90,
        ModelCapability.MATH: 0.92,
        ModelCapability.CREATIVE: 0.80,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.89,
        ModelCapability.SUMMARIZATION: 0.86,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.72,
        ModelCapability.QUALITY: 0.90,
    },
    # ==========================================================================
    # Mistral Large 2
    # ==========================================================================
    "mistral-large-2": {
        ModelCapability.CODING: 0.91,
        ModelCapability.REASONING: 0.89,
        ModelCapability.MATH: 0.88,
        ModelCapability.CREATIVE: 0.84,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.88,
        ModelCapability.SUMMARIZATION: 0.86,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.78,
        ModelCapability.QUALITY: 0.89,
    },
    # ==========================================================================
    # LATEST MODELS (January 2026 Update)
    # ==========================================================================
    
    # --------------------------------------------------------------------------
    # Claude 4.5 Series (Anthropic's Latest - January 2026)
    # --------------------------------------------------------------------------
    # Claude 4.5 Opus: BEST Anthropic model - surpasses Claude 4
    "claude-opus-4.5": {
        ModelCapability.CODING: 0.98,
        ModelCapability.REASONING: 0.99,
        ModelCapability.MATH: 0.96,
        ModelCapability.CREATIVE: 0.98,
        ModelCapability.FACTUAL: 0.97,
        ModelCapability.ANALYSIS: 0.98,
        ModelCapability.SUMMARIZATION: 0.95,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.98,
        ModelCapability.SPEED: 0.50,
        ModelCapability.QUALITY: 0.99,
    },
    # Claude 4.5 Sonnet: Excellent balance of quality and speed
    "claude-sonnet-4.5": {
        ModelCapability.CODING: 0.97,
        ModelCapability.REASONING: 0.96,
        ModelCapability.MATH: 0.92,
        ModelCapability.CREATIVE: 0.94,
        ModelCapability.FACTUAL: 0.94,
        ModelCapability.ANALYSIS: 0.95,
        ModelCapability.SUMMARIZATION: 0.93,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.96,
        ModelCapability.SPEED: 0.70,
        ModelCapability.QUALITY: 0.96,
    },
    # Claude 4.5 Haiku: Fast and efficient
    "claude-haiku-4.5": {
        ModelCapability.CODING: 0.85,
        ModelCapability.REASONING: 0.82,
        ModelCapability.MATH: 0.80,
        ModelCapability.CREATIVE: 0.80,
        ModelCapability.FACTUAL: 0.82,
        ModelCapability.ANALYSIS: 0.80,
        ModelCapability.SUMMARIZATION: 0.85,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.95,
        ModelCapability.QUALITY: 0.82,
    },
    # Claude 4.1 Opus: Intermediate upgrade
    "claude-opus-4.1": {
        ModelCapability.CODING: 0.96,
        ModelCapability.REASONING: 0.98,
        ModelCapability.MATH: 0.94,
        ModelCapability.CREATIVE: 0.96,
        ModelCapability.FACTUAL: 0.95,
        ModelCapability.ANALYSIS: 0.97,
        ModelCapability.SUMMARIZATION: 0.94,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.97,
        ModelCapability.SPEED: 0.52,
        ModelCapability.QUALITY: 0.98,
    },
    # Claude 3.7 Sonnet with thinking: Enhanced reasoning
    "claude-3.7-sonnet": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.95,
        ModelCapability.MATH: 0.90,
        ModelCapability.CREATIVE: 0.92,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.94,
        ModelCapability.SUMMARIZATION: 0.91,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.94,
        ModelCapability.SPEED: 0.68,
        ModelCapability.QUALITY: 0.94,
    },
    
    # --------------------------------------------------------------------------
    # Gemini 3 Series (Google's Latest - January 2026)
    # --------------------------------------------------------------------------
    # Gemini 3 Pro Preview: Next-gen Google flagship
    "gemini-3-pro-preview": {
        ModelCapability.CODING: 0.96,
        ModelCapability.REASONING: 0.97,
        ModelCapability.MATH: 0.98,
        ModelCapability.CREATIVE: 0.90,
        ModelCapability.FACTUAL: 0.97,
        ModelCapability.ANALYSIS: 0.96,
        ModelCapability.SUMMARIZATION: 0.94,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.95,
        ModelCapability.SPEED: 0.72,
        ModelCapability.QUALITY: 0.97,
    },
    # Gemini 3 Flash Preview: Fast next-gen
    "gemini-3-flash-preview": {
        ModelCapability.CODING: 0.88,
        ModelCapability.REASONING: 0.86,
        ModelCapability.MATH: 0.90,
        ModelCapability.CREATIVE: 0.82,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.85,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.96,
        ModelCapability.QUALITY: 0.86,
    },
    # Gemini 2.5 Flash Lite: Ultra-fast, cost-effective
    "gemini-2.5-flash-lite": {
        ModelCapability.CODING: 0.78,
        ModelCapability.REASONING: 0.75,
        ModelCapability.MATH: 0.78,
        ModelCapability.CREATIVE: 0.72,
        ModelCapability.FACTUAL: 0.78,
        ModelCapability.ANALYSIS: 0.74,
        ModelCapability.SUMMARIZATION: 0.80,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.80,
        ModelCapability.SPEED: 0.98,
        ModelCapability.QUALITY: 0.75,
    },
    
    # --------------------------------------------------------------------------
    # OpenAI Deep Research Models (January 2026)
    # --------------------------------------------------------------------------
    # o3 Deep Research: Extended reasoning for research
    "o3-deep-research": {
        ModelCapability.CODING: 0.95,
        ModelCapability.REASONING: 0.998,  # Best reasoning
        ModelCapability.MATH: 0.99,
        ModelCapability.CREATIVE: 0.70,
        ModelCapability.FACTUAL: 0.97,
        ModelCapability.ANALYSIS: 0.98,
        ModelCapability.SUMMARIZATION: 0.85,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.20,  # Very slow, deep thinking
        ModelCapability.QUALITY: 0.98,
    },
    # o4-mini Deep Research: Faster research variant
    "o4-mini-deep-research": {
        ModelCapability.CODING: 0.92,
        ModelCapability.REASONING: 0.96,
        ModelCapability.MATH: 0.97,
        ModelCapability.CREATIVE: 0.68,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.94,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.86,
        ModelCapability.SPEED: 0.55,
        ModelCapability.QUALITY: 0.95,
    },
    # GPT-5.2 Codex: Specialized for code
    "gpt-5.2-codex": {
        ModelCapability.CODING: 0.995,  # Best coding model
        ModelCapability.REASONING: 0.94,
        ModelCapability.MATH: 0.95,
        ModelCapability.CREATIVE: 0.75,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.90,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.95,
        ModelCapability.SPEED: 0.65,
        ModelCapability.QUALITY: 0.96,
    },
    
    # --------------------------------------------------------------------------
    # DeepSeek Latest (January 2026)
    # --------------------------------------------------------------------------
    # DeepSeek V3.2 Speciale: Enhanced version
    "deepseek-v3.2-speciale": {
        ModelCapability.CODING: 0.97,
        ModelCapability.REASONING: 0.95,
        ModelCapability.MATH: 0.96,
        ModelCapability.CREATIVE: 0.80,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.93,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.92,
        ModelCapability.SPEED: 0.80,
        ModelCapability.QUALITY: 0.95,
    },
    # DeepSeek V3.1 Terminus: Specialized variant
    "deepseek-v3.1-terminus": {
        ModelCapability.CODING: 0.95,
        ModelCapability.REASONING: 0.94,
        ModelCapability.MATH: 0.95,
        ModelCapability.CREATIVE: 0.78,
        ModelCapability.FACTUAL: 0.90,
        ModelCapability.ANALYSIS: 0.92,
        ModelCapability.SUMMARIZATION: 0.86,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.82,
        ModelCapability.QUALITY: 0.93,
    },
    # DeepSeek Chat V3.1
    "deepseek-chat-v3.1": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.93,
        ModelCapability.MATH: 0.94,
        ModelCapability.CREATIVE: 0.80,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.90,
        ModelCapability.SUMMARIZATION: 0.86,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.82,
        ModelCapability.QUALITY: 0.92,
    },
    
    # --------------------------------------------------------------------------
    # Grok Latest (X.AI - January 2026)
    # --------------------------------------------------------------------------
    # Grok 4.1 Fast: Speed-optimized
    "grok-4.1-fast": {
        ModelCapability.CODING: 0.88,
        ModelCapability.REASONING: 0.90,
        ModelCapability.MATH: 0.87,
        ModelCapability.CREATIVE: 0.85,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.86,
        ModelCapability.SUMMARIZATION: 0.84,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.92,
        ModelCapability.QUALITY: 0.88,
    },
    # Grok 4 Fast
    "grok-4-fast": {
        ModelCapability.CODING: 0.86,
        ModelCapability.REASONING: 0.88,
        ModelCapability.MATH: 0.85,
        ModelCapability.CREATIVE: 0.83,
        ModelCapability.FACTUAL: 0.86,
        ModelCapability.ANALYSIS: 0.85,
        ModelCapability.SUMMARIZATION: 0.82,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.86,
        ModelCapability.SPEED: 0.94,
        ModelCapability.QUALITY: 0.86,
    },
    # Grok Code Fast: Specialized for coding
    "grok-code-fast-1": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.85,
        ModelCapability.MATH: 0.88,
        ModelCapability.CREATIVE: 0.70,
        ModelCapability.FACTUAL: 0.80,
        ModelCapability.ANALYSIS: 0.82,
        ModelCapability.SUMMARIZATION: 0.78,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.88,
        ModelCapability.SPEED: 0.92,
        ModelCapability.QUALITY: 0.88,
    },
    
    # --------------------------------------------------------------------------
    # Mistral Latest (January 2026)
    # --------------------------------------------------------------------------
    # Mistral Large 2512: Latest flagship
    "mistral-large-2512": {
        ModelCapability.CODING: 0.93,
        ModelCapability.REASONING: 0.92,
        ModelCapability.MATH: 0.90,
        ModelCapability.CREATIVE: 0.86,
        ModelCapability.FACTUAL: 0.90,
        ModelCapability.ANALYSIS: 0.91,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.92,
        ModelCapability.SPEED: 0.76,
        ModelCapability.QUALITY: 0.92,
    },
    # Devstral 2512: Developer-focused
    "devstral-2512": {
        ModelCapability.CODING: 0.95,
        ModelCapability.REASONING: 0.88,
        ModelCapability.MATH: 0.90,
        ModelCapability.CREATIVE: 0.72,
        ModelCapability.FACTUAL: 0.85,
        ModelCapability.ANALYSIS: 0.86,
        ModelCapability.SUMMARIZATION: 0.80,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.85,
        ModelCapability.QUALITY: 0.90,
    },
    
    # --------------------------------------------------------------------------
    # Qwen Latest (Alibaba - January 2026)
    # --------------------------------------------------------------------------
    # Qwen3 Max: Flagship Qwen
    "qwen3-max": {
        ModelCapability.CODING: 0.94,
        ModelCapability.REASONING: 0.93,
        ModelCapability.MATH: 0.95,
        ModelCapability.CREATIVE: 0.85,
        ModelCapability.FACTUAL: 0.92,
        ModelCapability.ANALYSIS: 0.92,
        ModelCapability.SUMMARIZATION: 0.90,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.92,
        ModelCapability.SPEED: 0.70,
        ModelCapability.QUALITY: 0.93,
    },
    # Qwen3 VL 235B: Vision-language multimodal
    "qwen3-vl-235b": {
        ModelCapability.CODING: 0.90,
        ModelCapability.REASONING: 0.92,
        ModelCapability.MATH: 0.93,
        ModelCapability.CREATIVE: 0.88,
        ModelCapability.FACTUAL: 0.90,
        ModelCapability.ANALYSIS: 0.91,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.55,
        ModelCapability.QUALITY: 0.92,
    },
    
    # --------------------------------------------------------------------------
    # Llama Latest (Meta - January 2026)
    # --------------------------------------------------------------------------
    # Llama 4 Maverick: Experimental flagship
    "llama-4-maverick": {
        ModelCapability.CODING: 0.92,
        ModelCapability.REASONING: 0.91,
        ModelCapability.MATH: 0.89,
        ModelCapability.CREATIVE: 0.88,
        ModelCapability.FACTUAL: 0.90,
        ModelCapability.ANALYSIS: 0.90,
        ModelCapability.SUMMARIZATION: 0.88,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.91,
        ModelCapability.SPEED: 0.72,
        ModelCapability.QUALITY: 0.91,
    },
    # Llama 3.3 Nemotron Super: NVIDIA optimized
    "llama-3.3-nemotron-super-49b": {
        ModelCapability.CODING: 0.90,
        ModelCapability.REASONING: 0.89,
        ModelCapability.MATH: 0.88,
        ModelCapability.CREATIVE: 0.82,
        ModelCapability.FACTUAL: 0.88,
        ModelCapability.ANALYSIS: 0.88,
        ModelCapability.SUMMARIZATION: 0.86,
        ModelCapability.INSTRUCTION_FOLLOWING: 0.90,
        ModelCapability.SPEED: 0.82,
        ModelCapability.QUALITY: 0.89,
    },
}

# Create aliases for full OpenRouter IDs (maps to same capabilities)
_MODEL_ALIASES = {
    # ==========================================================================
    # OpenAI Models
    # ==========================================================================
    # GPT-4 series
    "openai/gpt-4o": "gpt-4o",
    "openai/gpt-4o-mini": "gpt-4o-mini",
    # GPT-5 series (Q1 2026)
    "openai/gpt-5": "gpt-5",
    "openai/gpt-5-pro": "gpt-5-pro",
    "openai/gpt-5-mini": "gpt-5-mini",
    "openai/gpt-5-nano": "gpt-5-nano",
    "openai/gpt-5-chat": "gpt-5",
    "openai/gpt-5.1": "gpt-5.1",
    "openai/gpt-5.1-chat": "gpt-5.1",
    "openai/gpt-5.1-codex": "gpt-5.1",
    "openai/gpt-5.1-codex-max": "gpt-5.1",
    "openai/gpt-5.1-codex-mini": "gpt-5.1",
    "openai/gpt-5.2": "gpt-5.2",
    "openai/gpt-5.2-pro": "gpt-5.2-pro",
    "openai/gpt-5.2-chat": "gpt-5.2",
    "openai/gpt-5.2-codex": "gpt-5.2-codex",  # NEW: Codex variant
    "openai/gpt-5-image": "gpt-5",
    "openai/gpt-5-image-mini": "gpt-5-mini",
    "openai/gpt-5-codex": "gpt-5",
    # o-series (reasoning specialists)
    "openai/o1": "o1",
    "openai/o1-pro": "o1-pro",
    "openai/o3": "o3",
    "openai/o4-mini": "o4-mini",
    "openai/o1-mini": "o4-mini",
    "openai/o3-deep-research": "o3-deep-research",  # NEW: Deep research
    "openai/o4-mini-deep-research": "o4-mini-deep-research",  # NEW: Deep research
    
    # ==========================================================================
    # Anthropic Claude Models (January 2026 Latest)
    # ==========================================================================
    # Claude 4.5 series (LATEST)
    "anthropic/claude-opus-4.5": "claude-opus-4.5",  # NEW: Best Anthropic
    "anthropic/claude-sonnet-4.5": "claude-sonnet-4.5",  # NEW
    "anthropic/claude-haiku-4.5": "claude-haiku-4.5",  # NEW
    # Claude 4.1 series
    "anthropic/claude-opus-4.1": "claude-opus-4.1",  # NEW
    # Claude 4.0 series
    "anthropic/claude-sonnet-4": "claude-sonnet-4",
    "anthropic/claude-opus-4": "claude-opus-4",
    # Claude 3.7 series
    "anthropic/claude-3.7-sonnet": "claude-3.7-sonnet",  # NEW
    "anthropic/claude-3.7-sonnet:thinking": "claude-3.7-sonnet",  # NEW with thinking
    # Claude 3.5 series (legacy)
    "anthropic/claude-3-5-sonnet-20241022": "claude-sonnet-4",
    "anthropic/claude-3.5-sonnet": "claude-sonnet-4",
    "anthropic/claude-3.5-sonnet:beta": "claude-sonnet-4",
    "anthropic/claude-3.5-haiku": "claude-haiku-4.5",
    
    # ==========================================================================
    # Google Gemini Models (January 2026 Latest)
    # ==========================================================================
    # Gemini 3 series (LATEST)
    "google/gemini-3-pro-preview": "gemini-3-pro-preview",  # NEW: Latest flagship
    "google/gemini-3-flash-preview": "gemini-3-flash-preview",  # NEW
    "google/gemini-3-pro-image-preview": "gemini-3-pro-preview",
    # Gemini 2.5 series
    "google/gemini-2.5-pro": "gemini-2.5-pro",
    "google/gemini-2.5-flash": "gemini-2.5-flash",
    "google/gemini-2.5-flash-lite": "gemini-2.5-flash-lite",  # NEW
    "google/gemini-2.5-flash-lite-preview-09-2025": "gemini-2.5-flash-lite",
    "google/gemini-2.5-flash-image": "gemini-2.5-flash",
    "google/gemini-2.5-flash-image-preview": "gemini-2.5-flash",
    # Gemini 2.0 series
    "google/gemini-2.0-pro": "gemini-2.0-pro",
    "google/gemini-2.0-flash": "gemini-2.0-flash",
    "google/gemini-2.0-pro-exp": "gemini-2.0-pro",
    "google/gemini-2.0-flash-exp": "gemini-2.0-flash",
    
    # ==========================================================================
    # DeepSeek Models (January 2026 Latest)
    # ==========================================================================
    "deepseek/deepseek-v3.2": "deepseek-v3.2",
    "deepseek/deepseek-v3.2-speciale": "deepseek-v3.2-speciale",  # NEW
    "deepseek/deepseek-v3.2-exp": "deepseek-v3.2-speciale",
    "deepseek/deepseek-v3.1-terminus": "deepseek-v3.1-terminus",  # NEW
    "deepseek/deepseek-v3.1-terminus:exacto": "deepseek-v3.1-terminus",
    "deepseek/deepseek-chat-v3.1": "deepseek-chat-v3.1",  # NEW
    "deepseek/deepseek-chat": "deepseek-chat",
    "deepseek/deepseek-r1-0528": "deepseek-r1-0528",
    "deepseek/deepseek-r1": "deepseek-r1-0528",
    "deepseek/deepseek-v3": "deepseek-v3.2",
    
    # ==========================================================================
    # X.AI Grok Models (January 2026 Latest)
    # ==========================================================================
    "x-ai/grok-4": "grok-4",
    "x-ai/grok-4.1-fast": "grok-4.1-fast",  # NEW
    "x-ai/grok-4-fast": "grok-4-fast",  # NEW
    "x-ai/grok-code-fast-1": "grok-code-fast-1",  # NEW: Code specialist
    "x-ai/grok-3": "grok-4",  # Map older to newer
    "x-ai/grok-3-mini": "grok-4-fast",
    "x-ai/grok-2": "grok-2",
    
    # ==========================================================================
    # Meta Llama Models (January 2026 Latest)
    # ==========================================================================
    "meta-llama/llama-4-maverick": "llama-4-maverick",  # NEW: Experimental flagship
    "meta-llama/llama-4-70b": "llama-4-70b",
    "meta-llama/llama-4-405b": "llama-4-405b",
    "meta-llama/llama-4-70b-instruct": "llama-4-70b",
    "meta-llama/llama-4-405b-instruct": "llama-4-405b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5": "llama-3.3-nemotron-super-49b",  # NEW: NVIDIA
    "nvidia/llama-3.1-nemotron-ultra-253b-v1": "llama-4-405b",
    
    # ==========================================================================
    # Qwen Models (Alibaba - January 2026 Latest)
    # ==========================================================================
    "qwen/qwen3-max": "qwen3-max",  # NEW: Flagship
    "qwen/qwen3-vl-235b-a22b-instruct": "qwen3-vl-235b",  # NEW: Multimodal
    "qwen/qwen3-vl-235b-a22b-thinking": "qwen3-vl-235b",
    "qwen/qwen3-vl-32b-instruct": "qwen3-vl-235b",
    "qwen/qwen3-vl-8b-instruct": "qwen-3-72b",
    "qwen/qwen-3-72b": "qwen-3-72b",
    "qwen/qwen3-72b": "qwen-3-72b",
    "qwen/qwen-3-72b-instruct": "qwen-3-72b",
    
    # ==========================================================================
    # Mistral Models (January 2026 Latest)
    # ==========================================================================
    "mistralai/mistral-large-2512": "mistral-large-2512",  # NEW: Latest flagship
    "mistralai/devstral-2512": "devstral-2512",  # NEW: Developer model
    "mistralai/devstral-2512:free": "devstral-2512",
    "mistralai/mistral-large-2": "mistral-large-2",
    "mistralai/mistral-large-2411": "mistral-large-2",
    "mistralai/ministral-14b-2512": "mistral-large-2",
    "mistralai/ministral-8b-2512": "mistral-large-2",
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
        use_reasoning_strategies: bool = True,
        use_kb_pipelines: bool = True,
    ) -> None:
        """Initialize elite orchestrator.
        
        Args:
            providers: LLM providers by name
            performance_tracker: Performance tracker for learning
            enable_learning: Whether to use historical performance data
            use_openrouter_rankings: Enable dynamic model selection from OpenRouter
            db_session: Database session for OpenRouter rankings
            use_reasoning_strategies: Enable Q4 2025 reasoning strategies controller
                for enhanced strategy selection, fallback handling, and trace logging
            use_kb_pipelines: Enable KB-aligned pipeline selection (Q4 2025)
                Uses Techniques Knowledge Base for optimal pipeline routing
        """
        self.providers = providers
        self.performance_tracker = performance_tracker
        self.enable_learning = enable_learning
        self.use_openrouter_rankings = use_openrouter_rankings
        self.db_session = db_session
        
        # Q4 2025: Reasoning strategies controller integration
        self.use_reasoning_strategies = use_reasoning_strategies and REASONING_STRATEGIES_AVAILABLE
        self._reasoning_controller: Optional["ReasoningStrategiesController"] = None
        if self.use_reasoning_strategies:
            self._reasoning_controller = get_strategy_controller()
            logger.info("Elite orchestrator initialized with reasoning strategies controller")
        
        # Q4 2025: KB Pipeline integration
        self.use_kb_pipelines = use_kb_pipelines
        if self.use_kb_pipelines:
            kb_available = _load_kb_bridge()
            if kb_available:
                logger.info("Elite orchestrator initialized with KB pipeline support")
            else:
                logger.debug("KB pipelines requested but not available, using built-in strategies")
                self.use_kb_pipelines = False
        
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
        
        PRIORITY: OpenRouter FIRST (400+ models), direct APIs as FALLBACK.
        """
        mapping = {}
        openrouter_available = "openrouter" in self.providers
        together_available = "together" in self.providers
        
        # All supported models
        all_models = [
            # OpenAI
            "gpt-4o", "gpt-4o-mini", "gpt-5", "o1", "o1-pro", "o3",
            "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-5", 
            "openai/o1-pro", "openai/o3",
            # Anthropic
            "claude-sonnet-4", "claude-opus-4", "claude-3-5-sonnet-20241022", 
            "claude-3-5-haiku-20241022", "claude-sonnet-4-20250514",
            "anthropic/claude-sonnet-4", "anthropic/claude-opus-4",
            "anthropic/claude-3-5-sonnet-20241022",
            # Google
            "gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-pro-preview",
            "google/gemini-2.5-pro", "google/gemini-2.5-flash",
            "google/gemini-3-pro-preview",
            # DeepSeek
            "deepseek-chat", "deepseek-v3.2", "deepseek-r1-0528",
            "deepseek/deepseek-chat", "deepseek/deepseek-v3.2",
            "deepseek/deepseek-r1-0528",
            # Grok
            "grok-2", "grok-4", "x-ai/grok-2", "x-ai/grok-4",
            # OpenRouter-only models
            "meta-llama/llama-4-maverick", "mistralai/mistral-large-2512",
            # =============================================================
            # FREE tier models - From OpenRouter free-models collection
            # Source: https://openrouter.ai/collections/free-models
            # Updated: January 30, 2026
            # =============================================================
            # TOP TIER FREE MODELS
            "deepseek/deepseek-r1-0528:free",           # 164K - BEST reasoning (o1-level!)
            "tngtech/deepseek-r1t2-chimera:free",       # 164K - DeepSeek-based, 20% faster
            "tngtech/deepseek-r1t-chimera:free",        # 164K - DeepSeek-based
            "meta-llama/llama-3.3-70b-instruct:free",   # 131K - GPT-4 level
            "google/gemma-3-27b-it:free",               # 131K - Multimodal, 140+ languages
            "qwen/qwen3-coder:free",                    # 262K - BEST for coding
            "qwen/qwen3-next-80b-a3b-instruct:free",    # 262K - Strong reasoning
            "openai/gpt-oss-120b:free",                 # 131K - Tool use
            "openai/gpt-oss-20b:free",                  # 131K - Fast
            "z-ai/glm-4.5-air:free",                    # 131K - Multilingual
            "nvidia/nemotron-3-nano-30b-a3b:free",      # 256K - Agentic
            "nvidia/nemotron-nano-12b-v2-vl:free",      # 128K - Vision
            "arcee-ai/trinity-large-preview:free",      # 131K - Creative/agentic
            "arcee-ai/trinity-mini:free",               # 131K - Fast
            "upstage/solar-pro-3:free",                 # 128K - Korean/multilingual
            "tngtech/tng-r1t-chimera:free",             # 164K - Creative
            "liquid/lfm-2.5-1.2b-thinking:free",        # 32K - Thinking
            "liquid/lfm-2.5-1.2b-instruct:free",        # 32K - Fast
            "allenai/molmo-2-8b:free",                  # 36K - Vision
        ]
        
        together_models = [
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "Qwen/Qwen2.5-72B-Instruct-Turbo",
        ]
        
        if openrouter_available:
            # Route ALL models through OpenRouter (PRIMARY)
            for model in all_models:
                mapping[model] = "openrouter"
            logger.info("OpenRouter is PRIMARY - routing all models through it")
            
            # Route Together.ai models directly when available
            if together_available:
                for model in together_models:
                    mapping[model] = "together"
        else:
            # FALLBACK to direct providers
            provider_models = {
                "openai": ["gpt-4o", "gpt-4o-mini", "gpt-5", "o1", "o1-pro", "o3",
                          "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-5", 
                          "openai/o1-pro", "openai/o3"],
                "anthropic": ["claude-sonnet-4", "claude-opus-4", "claude-3-5-sonnet-20241022", 
                             "claude-3-5-haiku-20241022", "claude-sonnet-4-20250514",
                             "anthropic/claude-sonnet-4", "anthropic/claude-opus-4",
                             "anthropic/claude-3-5-sonnet-20241022"],
                "gemini": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-pro-preview",
                          "google/gemini-2.5-pro", "google/gemini-2.5-flash",
                          "google/gemini-3-pro-preview"],
                "deepseek": ["deepseek-chat", "deepseek-v3.2", "deepseek-r1-0528",
                            "deepseek/deepseek-chat", "deepseek/deepseek-v3.2",
                            "deepseek/deepseek-r1-0528"],
                "grok": ["grok-2", "grok-4", "x-ai/grok-2", "x-ai/grok-4"],
                "together": together_models,
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
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools_available: Optional[List[str]] = None,
        cost_budget: str = "medium",
        force_kb_pipeline: Optional[str] = None,
    ) -> EliteResult:
        """
        Orchestrate models to produce the best possible response.
        
        Args:
            prompt: User prompt
            task_type: Type of task for capability matching
            available_models: Models to use (default: all available or dynamic from OpenRouter)
            strategy: Orchestration strategy (auto|dynamic|kb|single_best|parallel_race|best_of_n|expert_panel)
                - "kb": Use KB-aligned pipelines (recommended)
                - "auto": Auto-select between KB and built-in strategies
            quality_threshold: Minimum acceptable quality
            max_parallel: Maximum parallel model calls
            timeout_seconds: Total timeout
            domain_filter: Optional domain filter for OpenRouter ranking selection
            user_id: Optional user ID for KB pipeline context
            session_id: Optional session ID for KB pipeline context  
            tools_available: Optional list of available tools for KB pipelines
            cost_budget: Cost budget for KB pipelines ("low", "medium", "high")
            force_kb_pipeline: Force a specific KB pipeline (for testing)
            
        Returns:
            EliteResult with optimized response
        """
        start_time = time.time()
        performance_notes: List[str] = []
        
        # Q4 2025: KB Pipeline routing
        # Route to KB pipelines when explicitly requested or when auto mode with KB available
        use_kb = (
            self.use_kb_pipelines 
            and _kb_available 
            and (strategy == "kb" or force_kb_pipeline is not None)
        )
        
        # Auto mode: prefer KB pipelines for complex reasoning tasks
        if (
            strategy in ("auto", "automatic") 
            and self.use_kb_pipelines 
            and _kb_available
        ):
            # Use KB for tasks that benefit from technique-aligned pipelines
            kb_preferred_tasks = {
                "math_problem", "reasoning", "code_generation", "debugging",
                "research_analysis", "factual_question", "health_medical",
                "legal_analysis", "planning",
            }
            if task_type in kb_preferred_tasks:
                use_kb = True
                performance_notes.append("Auto-selected KB pipeline for task type")
        
        if use_kb:
            return await self._orchestrate_with_kb_pipeline(
                prompt=prompt,
                task_type=task_type,
                start_time=start_time,
                performance_notes=performance_notes,
                available_models=available_models,
                user_id=user_id,
                session_id=session_id,
                tools_available=tools_available,
                cost_budget=cost_budget,
                force_pipeline=force_kb_pipeline,
            )
        
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
            strategy = self._select_strategy(task_type, len(models), prompt, models)
        
        performance_notes.append(f"Strategy: {strategy}")
        
        # Q4 2025: Add trace logging tags if reasoning strategies controller is active
        if self.use_reasoning_strategies and self._reasoning_controller and TraceLogTags:
            trace_tags = TraceLogTags.format_tags(
                reasoning_method=strategy,
                strategy_source="elite_orchestrator",
                models_used=models[:3],  # Log first 3 models
            )
            performance_notes.append(f"Trace: {trace_tags.get('reasoning_method')}")
        
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
    
    async def _orchestrate_with_kb_pipeline(
        self,
        prompt: str,
        task_type: str,
        start_time: float,
        performance_notes: List[str],
        *,
        available_models: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools_available: Optional[List[str]] = None,
        cost_budget: str = "medium",
        force_pipeline: Optional[str] = None,
    ) -> EliteResult:
        """
        Route orchestration through KB-aligned pipelines.
        
        This method uses the Techniques Knowledge Base to select and execute
        the optimal pipeline for the given query.
        """
        performance_notes.append("Using KB pipeline integration")
        
        try:
            # Call KB bridge
            result = await _process_with_kb_pipeline(
                query=prompt,
                user_id=user_id,
                session_id=session_id,
                tools_available=tools_available,
                models_available=available_models,
                cost_budget=cost_budget,
                force_pipeline=force_pipeline,
                enable_tracing=True,
            )
            
            total_latency = (time.time() - start_time) * 1000
            
            # Map KB result to EliteResult
            return EliteResult(
                final_answer=result.final_answer,
                models_used=list(available_models or self.model_providers.keys())[:3],
                primary_model=available_models[0] if available_models else "kb_pipeline",
                strategy_used=f"kb:{result.pipeline_name}",
                total_latency_ms=total_latency,
                total_tokens=result.metrics.get("total_tokens", 0),
                quality_score=0.9 if result.confidence == "high" else (
                    0.75 if result.confidence == "medium" else 0.6
                ),
                confidence=0.9 if result.confidence == "high" else (
                    0.75 if result.confidence == "medium" else 0.6
                ),
                responses_generated=1,
                synthesis_method=f"kb_pipeline_{result.pipeline_name}",
                performance_notes=performance_notes + [
                    f"KB pipeline: {result.pipeline_name}",
                    f"Techniques: {result.technique_ids}",
                    f"Confidence: {result.confidence}",
                    f"Fallback used: {result.fallback_used}",
                ],
                consensus_score=1.0 if not result.fallback_used else 0.7,
            )
            
        except Exception as e:
            logger.warning("KB pipeline failed, falling back to built-in: %s", e)
            performance_notes.append(f"KB pipeline error: {str(e)[:50]}")
            
            # Fallback to built-in single_best strategy
            models = available_models or list(self.model_providers.keys())
            models = [m for m in models if m in self.model_providers]
            
            if not models:
                raise ValueError("No available models for fallback orchestration")
            
            result = await self._single_best_strategy(
                prompt, task_type, models, 0.7
            )
            
            total_latency = (time.time() - start_time) * 1000
            result.total_latency_ms = total_latency
            result.strategy_used = "kb_fallback:single_best"
            result.performance_notes = performance_notes
            
            return result
    
    def _select_strategy(
        self,
        task_type: str,
        num_models: int,
        prompt: str,
        available_models: Optional[List[str]] = None,
    ) -> str:
        """Auto-select the best strategy for the task.
        
        Uses the Q4 2025 Meta-Learning Strategy Optimizer when available,
        falling back to reasoning strategies controller, then heuristic selection.
        
        Strategy Selection Priority (Q4 2025):
        1. Meta-Learning Strategy Optimizer (if trained with enough data)
        2. Reasoning Strategies Controller (pattern-based)
        3. Legacy heuristic rules
        """
        # Determine complexity early (used by all selectors)
        prompt_lower = prompt.lower()
        complexity = "simple"
        if len(prompt) > 500 or prompt.count("?") > 1:
            complexity = "complex"
        elif any(word in prompt_lower for word in ["explain", "analyze", "compare"]):
            complexity = "medium"
        
        # Q4 2025: Try Meta-Learning Strategy Optimizer first
        try:
            from .strategy_optimizer import get_strategy_optimizer, optimize_strategy_selection
            
            query_analysis = {
                "task_type": task_type,
                "domain": self._infer_domain(prompt_lower),
                "complexity": complexity,
                "tokens_estimate": len(prompt.split()),
                "prefer_speed": any(w in prompt_lower for w in ["quick", "fast", "brief"]),
                "prefer_quality": any(w in prompt_lower for w in ["thorough", "detailed", "comprehensive"]),
                "available_models": available_models or [],
            }
            
            strategy, metadata = optimize_strategy_selection(
                query_analysis=query_analysis,
                current_strategy="automatic",
            )
            
            # Only use ML recommendation if confident (method=="ml" and enough data)
            if metadata.get("method") == "ml":
                logger.debug(
                    "Strategy optimizer (ML) selected %s (confidence: %.0f%%)",
                    strategy,
                    metadata.get("confidence", 0) * 100,
                )
                return strategy
                
        except ImportError:
            pass  # Optimizer not available
        except Exception as e:
            logger.debug("Strategy optimizer failed, trying fallback: %s", e)
        
        # Q4 2025: Use reasoning strategies controller for enhanced selection
        if self.use_reasoning_strategies and self._reasoning_controller:
            try:
                # Determine complexity
                prompt_lower = prompt.lower()
                complexity = "simple"
                if len(prompt) > 500 or prompt.count("?") > 1:
                    complexity = "complex"
                elif any(word in prompt_lower for word in ["explain", "analyze", "compare"]):
                    complexity = "medium"
                
                # Get strategy recommendation
                recommendation = self._reasoning_controller.select_strategy(
                    query=prompt,
                    task_type=task_type,
                    complexity=complexity,
                    available_models=available_models,
                    prefer_speed=any(w in prompt_lower for w in ["quick", "fast", "brief"]),
                    prefer_quality=any(w in prompt_lower for w in ["thorough", "detailed", "comprehensive"]),
                )
                
                # Map reasoning method to orchestration strategy
                method = recommendation.get("strategy", "chain_of_thought")
                orchestration_strategy = self._map_reasoning_to_orchestration(method, num_models)
                
                logger.debug(
                    "Reasoning controller selected %s -> %s (source: %s)",
                    method,
                    orchestration_strategy,
                    recommendation.get("source"),
                )
                
                return orchestration_strategy
                
            except Exception as e:
                logger.warning("Reasoning controller failed, using fallback: %s", e)
                # Fall through to heuristic selection
        
        # Legacy heuristic selection
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
    
    def _map_reasoning_to_orchestration(
        self,
        reasoning_method: str,
        num_models: int,
    ) -> str:
        """Map a reasoning method to an orchestration strategy.
        
        The reasoning strategies controller suggests methods like 'self_consistency',
        'tree_of_thoughts', etc. This maps them to the orchestration strategies
        that the EliteOrchestrator can execute.
        """
        # Direct mappings for orchestration strategies
        orchestration_mappings = {
            # Self-consistency → best_of_n (generate multiple, vote)
            "self_consistency": "best_of_n",
            # Debate → expert_panel (multiple models, synthesis)
            "debate": "expert_panel" if num_models >= 2 else "challenge_and_refine",
            # Mixture → expert_panel (combine strategies)
            "mixture": "expert_panel" if num_models >= 3 else "quality_weighted_fusion",
            # Tree of thoughts → challenge_and_refine (explore, evaluate)
            "tree_of_thoughts": "challenge_and_refine",
            # Reflection → challenge_and_refine (generate, critique)
            "reflection": "challenge_and_refine",
            # Step verification → challenge_and_refine (verify each step)
            "step_verification": "challenge_and_refine",
            # Best of N → best_of_n
            "best_of_n": "best_of_n",
            # Progressive → quality_weighted_fusion (adaptive)
            "progressive_deepening": "quality_weighted_fusion",
            # Simple methods → single_best
            "chain_of_thought": "single_best",
            "rag": "single_best",  # RAG is handled at a different layer
            "react": "single_best",  # ReAct is handled at tool layer
            "pal": "single_best",  # PAL is handled at code layer
            "deepconf": "expert_panel" if num_models >= 2 else "challenge_and_refine",
            "self_refine": "challenge_and_refine",
        }
        
        return orchestration_mappings.get(reasoning_method, "quality_weighted_fusion")
    
    def _infer_domain(self, prompt_lower: str) -> str:
        """Infer the domain from prompt content.
        
        Used by the Strategy Optimizer to get domain-specific recommendations.
        
        Args:
            prompt_lower: Lowercase prompt text
            
        Returns:
            Domain classification string
        """
        # Coding/technical
        if any(word in prompt_lower for word in [
            "code", "python", "javascript", "function", "class", "debug", "error",
            "api", "database", "sql", "algorithm", "programming"
        ]):
            return "coding"
        
        # Technical but not coding
        if any(word in prompt_lower for word in [
            "technical", "architecture", "system", "deploy", "cloud", "docker",
            "kubernetes", "infrastructure"
        ]):
            return "technical"
        
        # Creative
        if any(word in prompt_lower for word in [
            "creative", "story", "poem", "write", "fiction", "narrative",
            "imagine", "fantasy"
        ]):
            return "creative"
        
        # Business
        if any(word in prompt_lower for word in [
            "business", "market", "strategy", "revenue", "customer", "sales",
            "finance", "investment", "startup"
        ]):
            return "business"
        
        # General/default
        return "general"
    
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
        
        # OpenRouter needs FULL model ID (e.g., "openai/gpt-4o")
        # Direct providers need SHORT model name (e.g., "gpt-4o")
        if provider_name == "openrouter":
            api_model = model  # Keep full ID for OpenRouter
        else:
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
        """Synthesize multiple responses with quality weighting.
        
        Enhanced synthesis (Q1 2026):
        - Longer context windows (4000 chars) for better synthesis
        - Conflict detection between responses
        - Task-type-specific synthesis strategies
        - Structured merge instructions
        """
        if len(responses) == 1:
            return responses[0].content, responses[0].model
        
        # Sort by quality
        sorted_responses = sorted(responses, key=lambda r: r.quality_score, reverse=True)
        
        # Use best model's response as base
        primary = sorted_responses[0]
        
        # If second response is close in quality, synthesize
        if len(sorted_responses) > 1:
            secondary = sorted_responses[1]
            
            if secondary.quality_score >= primary.quality_score * 0.85:  # Lowered threshold
                # Detect potential conflicts
                conflict_indicators = self._detect_response_conflicts(
                    primary.content, secondary.content
                )
                
                # Task-specific synthesis instructions
                task_instructions = self._get_synthesis_instructions(task_type)
                
                # Enhanced synthesis prompt with longer context
                synth_prompt = f"""You are an expert synthesizer. Your task is to create the best possible answer by intelligently combining multiple AI responses.

## User's Question
{prompt}

## Response A (Quality Score: {primary.quality_score:.2f}, Model: {primary.model})
{primary.content[:4000]}

## Response B (Quality Score: {secondary.quality_score:.2f}, Model: {secondary.model})
{secondary.content[:4000]}

## Synthesis Instructions
{task_instructions}

{conflict_indicators}

## Output Requirements
1. Create ONE unified, comprehensive answer
2. Take the BEST information from each response
3. Resolve any conflicts using logic and evidence
4. Maintain accuracy - do not add unsupported claims
5. Keep the appropriate tone and depth for the topic
6. Do NOT ask clarifying questions - provide a complete answer
7. Do NOT mention that you are synthesizing responses

Provide your synthesized answer now:"""

                synth_model = self._select_best_model("synthesis", list(self.model_providers.keys()))
                
                try:
                    result = await self._call_model(synth_model, synth_prompt)
                    return result.content, synth_model
                except Exception:
                    pass
        
        return primary.content, primary.model
    
    def _detect_response_conflicts(self, response_a: str, response_b: str) -> str:
        """Detect potential conflicts between responses for synthesis guidance."""
        # Simple heuristic: look for contradictory patterns
        conflict_words = ['however', 'but', 'contrary', 'disagree', 'incorrect', 'wrong']
        
        a_lower = response_a.lower()
        b_lower = response_b.lower()
        
        # Check for numerical disagreements (very rough heuristic)
        import re
        nums_a = set(re.findall(r'\b\d+\.?\d*\b', response_a))
        nums_b = set(re.findall(r'\b\d+\.?\d*\b', response_b))
        numerical_diff = nums_a.symmetric_difference(nums_b)
        
        if len(numerical_diff) > 5:
            return """## Conflict Alert
The responses contain different numerical values. Please verify calculations and use the most accurate figures."""
        
        # Check for hedging language differences
        hedging_a = sum(1 for w in ['might', 'may', 'could', 'possibly', 'perhaps'] if w in a_lower)
        hedging_b = sum(1 for w in ['might', 'may', 'could', 'possibly', 'perhaps'] if w in b_lower)
        
        if abs(hedging_a - hedging_b) > 3:
            return """## Confidence Note
The responses have different levels of certainty. Prefer definitive statements when well-supported."""
        
        return ""
    
    def _get_synthesis_instructions(self, task_type: str) -> str:
        """Get task-specific synthesis instructions."""
        instructions = {
            "health_medical": """For medical/health topics:
- Prioritize accuracy and safety above all
- Include appropriate disclaimers
- Cite mechanisms of action when relevant
- Be conservative with recommendations""",
            
            "code_generation": """For code/programming:
- Ensure the code is syntactically correct
- Prefer the more efficient solution
- Include error handling if either response has it
- Keep helpful comments""",
            
            "math_problem": """For math problems:
- Verify calculations step by step
- Use the solution with clearer reasoning
- Show work where appropriate
- Double-check final numerical answers""",
            
            "creative_writing": """For creative content:
- Blend the most engaging elements
- Maintain consistent tone and style
- Preserve unique creative choices
- Ensure narrative coherence""",
            
            "research_analysis": """For research/analysis:
- Integrate complementary insights
- Maintain logical flow
- Cite sources if provided
- Present balanced perspectives""",
            
            "factual_question": """For factual questions:
- Use the most well-supported facts
- Verify claims against both responses
- Be precise with terminology
- Acknowledge uncertainty where appropriate""",
        }
        return instructions.get(task_type, """General synthesis:
- Combine the strongest elements from each response
- Ensure logical coherence
- Maintain appropriate depth and detail""")
    
    async def _synthesize_expert_panel(
        self,
        prompt: str,
        role_responses: Dict[str, ModelResponse],
    ) -> str:
        """Synthesize expert panel responses with enhanced multi-perspective integration.
        
        Enhanced (Q1 2026):
        - Structured role-based synthesis
        - Longer context per expert (2000 chars)
        - Explicit conflict resolution
        - Quality-weighted integration
        """
        # Sort roles by quality for prioritization
        sorted_roles = sorted(
            role_responses.items(),
            key=lambda x: x[1].quality_score,
            reverse=True
        )
        
        synth_prompt = f"""You are a master synthesizer tasked with combining expert perspectives into one world-class answer.

## User's Question
{prompt}

## Expert Panel Responses
"""
        for role, resp in sorted_roles:
            role_description = {
                "researcher": "Deep research and fact-finding",
                "analyst": "Critical analysis and evaluation",
                "synthesizer": "Integration and summary",
                "critic": "Quality assessment and error detection",
                "creative": "Novel approaches and ideas",
                "validator": "Verification and fact-checking",
            }.get(role, role.title())
            
            synth_prompt += f"""### {role.upper()} ({role_description})
Quality Score: {resp.quality_score:.2f}
{resp.content[:2000]}

"""
        
        synth_prompt += """## Synthesis Guidelines
1. **Weight by Quality**: Give more weight to higher-quality expert responses
2. **Resolve Conflicts**: If experts disagree, use evidence and logic to determine the best answer
3. **Integrate Strengths**: Each expert may have unique insights - capture them all
4. **Maintain Coherence**: The final answer should read as one unified response
5. **Be Comprehensive**: Cover all relevant aspects raised by the experts
6. **Be Accurate**: Do not introduce information not supported by the expert responses

## Output
Provide a single, comprehensive, well-structured answer that a user would receive.
Do NOT mention that you are synthesizing or that this comes from multiple experts.
Do NOT ask clarifying questions.

Your synthesized answer:"""

        synth_model = self._select_best_model("synthesis", list(self.model_providers.keys()))
        
        try:
            result = await self._call_model(synth_model, synth_prompt)
            return result.content
        except Exception:
            # Fallback: use highest quality response
            best_role = sorted_roles[0] if sorted_roles else list(role_responses.items())[0]
            return best_role[1].content
    
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
            
            # Q4 2025 Meta-Learning: Also record to Strategy Optimizer for ML training
            try:
                from .strategy_optimizer import record_orchestration_outcome
                record_orchestration_outcome(
                    query_analysis={
                        "task_type": task_type,
                        "domain": task_type,  # Use task_type as domain approximation
                        "complexity": query_complexity,
                        "available_models": result.models_used,
                    },
                    strategy=result.strategy_used,
                    success=result.quality_score >= 0.7,
                    quality_score=result.quality_score,
                    latency_ms=result.total_latency_ms,
                )
            except ImportError:
                pass  # Optimizer not available
            except Exception as opt_e:
                logger.debug("Strategy optimizer recording failed: %s", opt_e)
                
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


async def kb_orchestrate(
    prompt: str,
    providers: Dict[str, Any],
    *,
    task_type: str = "general",
    tools_available: Optional[List[str]] = None,
    cost_budget: str = "medium",
    force_pipeline: Optional[str] = None,
) -> EliteResult:
    """
    Convenience function for KB-aligned orchestration.
    
    Uses the Techniques Knowledge Base to select the optimal pipeline.
    
    Args:
        prompt: User prompt
        providers: LLM providers by name
        task_type: Type of task for capability matching
        tools_available: Available tools for the pipeline
        cost_budget: Cost budget ("low", "medium", "high")
        force_pipeline: Force a specific pipeline (for testing)
        
    Returns:
        EliteResult with optimized response
    """
    orchestrator = EliteOrchestrator(providers, use_kb_pipelines=True)
    return await orchestrator.orchestrate(
        prompt,
        task_type,
        strategy="kb",
        tools_available=tools_available,
        cost_budget=cost_budget,
        force_kb_pipeline=force_pipeline,
    )


def is_kb_available() -> bool:
    """Check if KB pipeline integration is available."""
    _load_kb_bridge()
    return _kb_available

