"""
Benchmark Answer Quality Enhancer

This module provides aggressive prompt optimization and orchestration
enhancements specifically for achieving top-tier benchmark scores.

Target: Restore historical performance levels:
- Reasoning: 85.7% (from 70-74%)
- Coding: 73.2% (from 10%)
- Math: 97.0% (from 92-94%)
- RAG: Strong retrieval + synthesis (from 0-0.5%)

Approach: MAXIMIZE ANSWER QUALITY through:
1. Category-specific prompt engineering
2. Multi-round refinement
3. Best-of-N generation with selection
4. Verification and self-critique
5. Chain-of-thought forcing
6. Increased model budget (3-5 models per query if needed)
"""

import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# =============================================================================
# BENCHMARK-OPTIMIZED PROMPTS
# =============================================================================

def enhance_reasoning_prompt(query: str) -> str:
    """Enhance reasoning prompts for MMLU-style questions.
    
    Target: 85.7% (historical) from 70-74% (current)
    
    Strategy:
    - Force step-by-step analysis
    - Require elimination of wrong answers
    - Request confidence assessment
    - Emphasize precision
    """
    return f"""Analyze this question with rigorous step-by-step reasoning.

Question: {query}

Approach:
1. Read the question carefully and identify what's being asked
2. For each answer option, evaluate its correctness
3. Eliminate clearly wrong answers
4. Compare remaining options
5. Select the most accurate answer
6. Double-check your reasoning

Provide your final answer as a single letter (A, B, C, or D) at the end.

Step-by-step analysis:"""


def enhance_coding_prompt(problem_prompt: str) -> str:
    """Enhance coding prompts for HumanEval.
    
    Target: 73.2% (historical) from 10% (current)
    
    Strategy:
    - Request complete, tested implementation
    - Emphasize edge cases
    - Request type hints and error handling
    - Force verification thinking
    """
    return f"""Write production-quality Python code for this function.

{problem_prompt}

Requirements:
1. Complete implementation (not just stub)
2. Handle all edge cases mentioned in docstring
3. Include proper error handling
4. Use type hints where appropriate
5. Test your logic mentally before writing
6. Ensure the function works for ALL test cases

Think through the logic step-by-step, then provide the complete function implementation.

Implementation:"""


def enhance_math_prompt(problem: str) -> str:
    """Enhance math prompts for GSM8K.
    
    Target: 97.0% (historical) from 92-94% (current)
    
    Strategy:
    - Force step-by-step calculation
    - Request verification
    - Emphasize final answer format
    - Catch calculation errors
    """
    return f"""Solve this math problem with careful step-by-step work.

Problem: {problem}

Instructions:
1. Break down the problem into steps
2. Show ALL calculations explicitly
3. Verify each step for arithmetic errors
4. Double-check your final answer
5. Format answer as: #### [number]

Work through this carefully:"""


def enhance_rag_ranking_prompt(query: str, passages: str) -> str:
    """Enhance RAG ranking prompts for MS MARCO.
    
    Target: Correct MRR@10 calculation and strong ranking
    
    Strategy:
    - Clear ranking instructions
    - Force consideration of all passages
    - Request explicit ranking
    - Emphasize relevance over similarity
    """
    return f"""Rank these passages by relevance to the query.

Query: {query}

Passages:
{passages}

Instructions:
1. Read each passage carefully
2. Assess which passages directly answer or relate to the query
3. Rank ALL passages from most to least relevant
4. Return ONLY the passage IDs in ranked order (comma-separated)

Example format: 7,3,1,9,2,4,8,6,5

Your ranked list (most relevant first):"""


def enhance_multilingual_prompt(query: str, choices: List[str]) -> str:
    """Enhance multilingual prompts for MMMLU.
    
    Strategy:
    - Handle multiple languages
    - Clear answer format
    - Careful reading emphasis
    """
    return f"""Answer this question carefully.

{query}

A) {choices[0]}
B) {choices[1]}
C) {choices[2]}
D) {choices[3]}

Instructions:
1. Read the question in its original language
2. Understand what is being asked
3. Evaluate each option
4. Select the best answer
5. Provide ONLY the letter (A, B, C, or D)

Your answer:"""


# =============================================================================
# ORCHESTRATION ENHANCEMENT
# =============================================================================

def get_enhanced_orchestration_config(category: str, tier: str = "elite") -> Dict[str, Any]:
    """Get enhanced orchestration configuration for benchmarks.
    
    Args:
        category: Task category (reasoning, coding, math, rag, multilingual)
        tier: Model tier (elite, premium, standard)
    
    Returns:
        Orchestration configuration optimized for quality
    """
    base_config = {
        "use_hrm": True,
        "use_adaptive_routing": True,
        "use_deep_consensus": True,
        "use_prompt_diffusion": False,
        "accuracy_level": 5,  # Maximum quality
        "enable_verification": True,
        "enable_self_critique": True,
    }
    
    # Category-specific enhancements
    category_configs = {
        "reasoning": {
            **base_config,
            "num_models": 3,  # Use 3 top models
            "require_consensus": True,
            "consensus_threshold": 0.67,  # 2 of 3 must agree
            "enable_chain_of_thought": True,
        },
        "coding": {
            **base_config,
            "num_models": 2,  # Primary + reviewer
            "enable_self_critique": True,
            "enable_test_verification": True,
            "num_refinement_rounds": 2,  # Generate → Critique → Refine
        },
        "math": {
            **base_config,
            "num_models": 3,
            "enable_calculator": True,
            "calculator_authoritative": True,  # Calculator result is final
            "require_consensus": True,
            "enable_verification": True,
        },
        "rag": {
            **base_config,
            "num_models": 2,  # Retrieval + synthesis
            "enable_reranking": True,
            "enable_citation_verification": True,
            "top_k_retrieval": 10,  # More context
        },
        "multilingual": {
            **base_config,
            "num_models": 2,
            "enable_language_detection": True,
            "enable_translation_verification": False,  # Keep original language
        },
    }
    
    config = category_configs.get(category, base_config)
    
    # For elite tier, enable ALL quality features
    if tier == "elite":
        config["accuracy_level"] = 5
        config["enable_verification"] = True
        config["enable_self_critique"] = True
        config["use_deep_consensus"] = True
    
    return config


# =============================================================================
# ANSWER POST-PROCESSING
# =============================================================================

def extract_code_from_response(response: str, problem_prompt: str) -> str:
    """Extract clean code from LLM response for HumanEval.
    
    Handles:
    - Markdown code blocks
    - Explanatory text
    - Multiple code blocks (take the most complete one)
    - Partial implementations
    """
    # Remove markdown fences
    cleaned = re.sub(r'```python\n?|```\n?', '', response)
    
    # If response contains the full function definition, use it
    if 'def ' in cleaned:
        # Extract from 'def' to end of function
        lines = cleaned.split('\n')
        in_function = False
        function_lines = []
        indent_level = None
        
        for line in lines:
            if line.strip().startswith('def '):
                in_function = True
                function_lines = [line]
                # Detect base indentation
                indent_level = len(line) - len(line.lstrip())
                continue
            
            if in_function:
                # Check if we've left the function (dedented to same or less)
                if line.strip() and not line.startswith(' ' * (indent_level + 1)):
                    # Check if it's not just a blank line
                    if line.strip():
                        break
                function_lines.append(line)
        
        if function_lines:
            return '\n'.join(function_lines) + '\n'
    
    # Fallback: combine problem_prompt with implementation
    if problem_prompt in cleaned:
        cleaned = problem_prompt + cleaned.split(problem_prompt, 1)[ 1]
    else:
        # Extract just the implementation part
        cleaned = problem_prompt.rstrip() + '\n' + cleaned.lstrip()
    
    return cleaned + '\n'


def extract_ranked_ids(response: str, valid_ids: List[int]) -> List[int]:
    """Extract ranked passage IDs from LLM response for MS MARCO.
    
    Target: Robust extraction to fix 0% MRR@10
    
    Handles:
    - Comma-separated lists: "7,3,1,9"
    - Space-separated: "7 3 1 9"
    - Numbered lists: "1. 7\n2. 3"
    - Text with IDs: "Most relevant: 7, then 3, then 1"
    """
    ranked = []
    
    # Strategy 1: Look for comma or space-separated numbers
    numbers = re.findall(r'\b\d+\b', response)
    for num_str in numbers:
        try:
            num = int(num_str)
            if num in valid_ids and num not in ranked:
                ranked.append(num)
        except ValueError:
            continue
    
    # Strategy 2: If no valid IDs found, try to find them in order of mention
    if not ranked:
        for vid in valid_ids:
            if str(vid) in response and vid not in ranked:
                ranked.append(vid)
    
    # If still nothing, return IDs in original order as fallback
    if not ranked:
        ranked = valid_ids[:10]
    
    return ranked[:10]  # Return top 10


def extract_multiple_choice_answer(response: str) -> Optional[str]:
    """Extract A/B/C/D answer from LLM response.
    
    Target: Robust extraction for MMLU/MMMLU
    
    Handles:
    - "Answer: A"
    - "The answer is B"
    - "A is correct"
    - "(D)" at end
    - Just "A" alone
    """
    response = response.strip()
    
    # Strategy 1: Look for explicit answer patterns
    patterns = [
        r'(?:answer|choice|select|option)[\s:]*([ABCD])\b',
        r'\b([ABCD])\s+is\s+(?:correct|right|accurate)',
        r'\(([ABCD])\)',
        r'\b([ABCD])\s*$',  # Single letter at end
        r'^([ABCD])\b',  # Single letter at start
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 2: Last letter A-D in response
    letters = re.findall(r'\b[ABCD]\b', response)
    if letters:
        return letters[-1]
    
    return None


def extract_math_answer(response: str) -> Optional[float]:
    """Extract numerical answer from math problem response.
    
    Target: 97% (historical) from 92-94% (current)
    
    Handles:
    - "#### 42" format
    - "Final Answer: 42"
    - "The answer is 42"
    - Just "42" at end
    """
    # Strategy 1: Look for #### format (GSM8K standard)
    match = re.search(r'####\s*(-?[\d,]+\.?\d*)', response)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            pass
    
    # Strategy 2: Look for explicit answer statements
    patterns = [
        r'(?:final answer|answer|result)[\s:]*(-?[\d,]+\.?\d*)',
        r'\$?(-?[\d,]+\.?\d*)\s*$',  # Number at end
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                continue
    
    return None


# =============================================================================
# BENCHMARK MODE DETECTION
# =============================================================================

def is_benchmark_mode() -> bool:
    """Check if running in benchmark mode."""
    import os
    return os.getenv("LLMHIVE_BENCHMARK_MODE") == "1"


def should_use_enhanced_prompts() -> bool:
    """Check if enhanced prompts should be used."""
    import os
    # Enable for benchmarks or if explicitly requested
    return (
        os.getenv("LLMHIVE_BENCHMARK_MODE") == "1" or
        os.getenv("LLMHIVE_ENHANCED_PROMPTS") == "1"
    )
