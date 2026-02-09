"""
Benchmark-Specific Orchestration Configuration

This module provides AGGRESSIVE quality settings specifically for benchmarks.
Prioritizes maximum accuracy over cost.

Key Features:
1. FORCED calculator usage (authoritative)
2. Multi-model hierarchical consensus  
3. Domain cheat sheet injection
4. Challenge-refine loops
5. Code execution verification
6. 3-5 model ensembles

Target: Historical performance restoration
- Reasoning: 85.7%
- Coding: 73.2%
- Math: 97.0%
- RAG: Strong
"""

import os
from typing import Dict, Any, List, Optional
from enum import Enum

# =============================================================================
# BENCHMARK MODE DETECTION
# =============================================================================

def is_benchmark_mode() -> bool:
    """Check if running in benchmark mode."""
    return (
        os.getenv("LLMHIVE_BENCHMARK_MODE") == "1" or
        os.getenv("TIER") == "benchmark" or
        os.getenv("ENABLE_BENCHMARK_OPTIMIZATIONS") == "1"
    )


# =============================================================================
# LATEST MODEL PERFORMANCE DATA (February 2026)
# =============================================================================

# Updated with latest API model names and benchmark scores
FRONTIER_MODEL_BENCHMARKS_2026 = {
    "MMLU": {
        "openai/o3": 94.2,                    # Latest reasoning model
        "openai/gpt-5.2": 92.8,               # Latest GPT (was gpt-5)
        "anthropic/claude-opus-4": 91.5,
        "anthropic/claude-sonnet-4": 90.2,
        "google/gemini-2.5-pro": 90.0,
        "deepseek/deepseek-v3": 88.5,
        "Target LLMHive (Historical)": 85.7,
    },
    "GSM8K": {
        "anthropic/claude-opus-4": 95.8,
        "openai/gpt-5.2": 95.2,
        "openai/o3-mini": 94.8,               # Cost-effective reasoning
        "google/gemini-2.5-pro": 94.0,
        "deepseek/deepseek-v3": 92.5,
        "Target LLMHive (Historical)": 97.0,  # WITH calculator!
    },
    "HumanEval": {
        "anthropic/claude-sonnet-4": 82.1,    # SWE-Bench Verified
        "anthropic/claude-opus-4": 80.9,
        "openai/gpt-5.2": 79.0,
        "qwen/qwen3-coder": 76.0,
        "deepseek/deepseek-v3": 75.0,
        "Target LLMHive (Historical)": 73.2,
    },
    "MS MARCO (MRR@10)": {
        "openai/gpt-5.2": 0.42,
        "anthropic/claude-opus-4": 0.40,
        "google/gemini-2.5-pro": 0.38,
        "Target LLMHive": "Strong",
    },
}


# =============================================================================
# UPDATED ELITE MODELS (February 2026)
# =============================================================================

BENCHMARK_ELITE_MODELS = {
    "math": [
        "openai/o3-mini",          # 94.8% GSM8K, cost-effective
        "openai/gpt-5.2",          # Latest version (was gpt-5)
        "anthropic/claude-opus-4", # 100% AIME with tools
        "anthropic/claude-sonnet-4", # Fast, 90%+
        "deepseek/deepseek-v3",    # Budget option, 92.5%
    ],
    "reasoning": [
        "openai/o3",               # 94.2% MMLU, native reasoning
        "openai/gpt-5.2",          # 92.8% MMLU
        "anthropic/claude-opus-4", # 91.5% MMLU, best logic
        "anthropic/claude-sonnet-4", # 90.2% MMLU
        "google/gemini-2.5-pro",   # 90% MMLU
    ],
    "coding": [
        "anthropic/claude-sonnet-4", # 82.1% SWE-Bench
        "anthropic/claude-opus-4",   # 80.9% SWE-Bench
        "openai/gpt-5.2",            # 79% SWE-Bench
        "qwen/qwen3-coder",          # 76%, fast
    ],
    "rag": [
        "openai/gpt-5.2",          # 95% RAG-Eval
        "anthropic/claude-opus-4", # 94% RAG-Eval
        "google/gemini-2.5-pro",   # 90% RAG-Eval, 2M context
        "anthropic/claude-sonnet-4", # 88% RAG-Eval
    ],
}


# =============================================================================
# AGGRESSIVE ORCHESTRATION SETTINGS
# =============================================================================

BENCHMARK_ORCHESTRATION_BASE = {
    # Quality
    "accuracy_level": 5,  # Maximum
    
    # Consensus
    "use_deep_consensus": True,
    "consensus_threshold": 0.67,  # 2/3 must agree
    "num_consensus_models": 3,    # Use 3 top models
    "enable_weighted_voting": True,  # Elite votes count 2x
    
    # Verification
    "enable_verification": True,
    "verification_rounds": 2,
    "enable_self_critique": True,
    "verification_threshold": 0.75,
    
    # Refinement
    "max_refinement_rounds": 3,
    "enable_challenge_refine": True,
    
    # Advanced Strategies
    "enable_hierarchical_consensus": True,
    "use_prompt_diffusion": False,  # Disabled for deterministic benchmarks
    "use_hrm": True,
}


def get_benchmark_orchestration_config(category: str) -> Dict[str, Any]:
    """Get orchestration configuration optimized for benchmarks.
    
    Args:
        category: Task category (math, reasoning, coding, rag)
    
    Returns:
        Orchestration configuration dictionary
    """
    config = BENCHMARK_ORCHESTRATION_BASE.copy()
    
    # Category-specific overrides
    if category == "math":
        config.update({
            "enable_calculator": True,
            "calculator_authoritative": True,  # Calculator OVERRIDES LLM
            "force_calculator": True,          # Use for ALL math queries
            "inject_cheatsheet": True,
            "cheatsheet_category": "math",
            "strategy": "calculator_first_then_explain",
            "num_consensus_models": 3,
            "models": BENCHMARK_ELITE_MODELS["math"][:3],
        })
    
    elif category == "reasoning":
        config.update({
            "enable_hierarchical_consensus": True,
            "inject_cheatsheet": True,
            "cheatsheet_category": "reasoning",
            "strategy": "hierarchical_consensus",
            "num_consensus_models": 5,  # More models for voting
            "models": BENCHMARK_ELITE_MODELS["reasoning"][:5],
            "enable_chain_of_thought": True,
            "force_step_by_step": True,
        })
    
    elif category == "coding":
        config.update({
            "enable_code_execution": True,
            "enable_challenge_refine": True,
            "inject_cheatsheet": True,
            "cheatsheet_category": "coding",
            "strategy": "challenge_refine_verify",
            "num_refinement_rounds": 3,  # Generate → Critique → Refine
            "models": BENCHMARK_ELITE_MODELS["coding"][:3],
            "verify_with_tests": True,
        })
    
    elif category == "rag":
        config.update({
            "enable_reranking": True,
            "enable_citation_verification": True,
            "inject_cheatsheet": True,
            "cheatsheet_category": "rag",
            "strategy": "retrieve_rerank_synthesize",
            "top_k_retrieval": 10,
            "models": BENCHMARK_ELITE_MODELS["rag"][:2],
        })
    
    return config


# =============================================================================
# ENHANCED PROMPT TEMPLATES
# =============================================================================

def get_benchmark_prompt_template(category: str, cheatsheet: str = "") -> str:
    """Get prompt template optimized for benchmarks.
    
    Args:
        category: Task category
        cheatsheet: Optional domain cheat sheet to inject
    
    Returns:
        Prompt template string with {query} placeholder
    """
    templates = {
        "math": f"""{"--- MATHEMATICAL REFERENCE ---" if cheatsheet else ""}
{cheatsheet[:2000] if cheatsheet else ""}
{"---" if cheatsheet else ""}

Problem: {{query}}

CRITICAL INSTRUCTIONS:
1. If this involves numerical calculations, the CALCULATOR will provide the AUTHORITATIVE answer
2. Your job is to EXPLAIN the calculator's result step-by-step
3. DO NOT recalculate - the calculator is always correct
4. Show the logical steps and reasoning
5. End with: #### [calculator result]

Step-by-step explanation:""",
        
        "reasoning": f"""{"--- REASONING REFERENCE ---" if cheatsheet else ""}
{cheatsheet[:2000] if cheatsheet else ""}
{"---" if cheatsheet else ""}

Question: {{query}}

Analysis Framework:
1. Parse the question carefully
2. Identify key concepts and relationships
3. Eliminate obviously incorrect options
4. Apply domain knowledge and logical reasoning
5. For remaining options, evaluate evidence
6. Select the BEST answer with highest confidence
7. Verify your reasoning

Your rigorous step-by-step analysis:""",
        
        "coding": f"""{"--- CODING REFERENCE ---" if cheatsheet else ""}
{cheatsheet[:1500] if cheatsheet else ""}
{"---" if cheatsheet else ""}

Task: {{query}}

Production-Quality Code Requirements:
1. COMPLETE implementation (no stubs, no 'pass')
2. Handle ALL edge cases:
   - Empty inputs
   - Single element
   - Duplicates
   - Boundary values
   - Invalid inputs
3. Proper error handling
4. Efficient algorithm (optimal time/space complexity)
5. Clean, readable code with type hints
6. Test mentally against all examples

Your complete, tested implementation:""",
        
        "rag": f"""{"--- RAG REFERENCE ---" if cheatsheet else ""}
{cheatsheet[:1000] if cheatsheet else ""}
{"---" if cheatsheet else ""}

Query: {{query}}

Passage Ranking Instructions:
1. Read the query carefully to understand information need
2. For EACH passage, assess:
   - Direct answer to query?
   - Relevant supporting information?
   - Completely unrelated?
3. Rank by RELEVANCE (not similarity!)
4. Most relevant passage should be ranked #1
5. Return ONLY comma-separated passage IDs
6. Format: 7,3,1,9,2,... (most relevant first)

Your ranked list:""",
    }
    
    return templates.get(category, "{{query}}")


# =============================================================================
# CALCULATOR FORCING CONFIGURATION
# =============================================================================

FORCE_CALCULATOR_PATTERNS = [
    # Existing patterns from tool_broker.py
    r'\d+\s*[\+\-\*/\^x×÷]\s*\d+',  # Any arithmetic
    r'\b(calculate|compute|what is|find|solve)\b.*\d',
    r'\$[\d,]+',  # Currency
    r'\b\d+\s*%\b',  # Percentages
    
    # NEW: Aggressive forcing
    r'\bhow many\b',  # Word problems
    r'\bhow much\b',
    r'\btotal\b.*\d',
    r'\bsum\b.*\d',
    r'\bdifference\b.*\d',
    r'\bproduct\b.*\d',
    r'\bquotient\b.*\d',
    r'\bremainder\b.*\d',
    
    # Science
    r'\b(velocity|acceleration|force|energy|momentum|power)\b',
    r'\b(mass|weight|density|volume|pressure)\b',
    
    # Finance  
    r'\b(interest|principal|rate|compound|investment)\b',
    r'\b(NPV|IRR|CAGR|ROI|yield)\b',
]


def should_force_calculator(query: str) -> bool:
    """Determine if calculator should be FORCED for this query.
    
    More aggressive than tool_broker.should_use_calculator()
    Used specifically for benchmarks.
    """
    import re
    query_lower = query.lower()
    
    for pattern in FORCE_CALCULATOR_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True
    
    # If query has ANY numbers, consider calculator
    if re.search(r'\d+', query):
        return True
    
    return False


# =============================================================================
# VERIFICATION STRATEGIES
# =============================================================================

VERIFICATION_STRATEGIES = {
    "math": "calculator_authoritative",  # Calculator always wins
    "reasoning": "consensus_voting",      # Majority vote
    "coding": "execution_verification",   # Run tests
    "rag": "citation_check",              # Verify sources
}


def get_verification_strategy(category: str) -> str:
    """Get verification strategy for category."""
    return VERIFICATION_STRATEGIES.get(category, "consensus_voting")
