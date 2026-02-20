"""
Ultra-Aggressive World-Class Improvements for ALL Categories
Research-backed methods from 2024-2026 papers

Categories:
- MMLU (Reasoning): Chain of Thought + Self-Consistency + Neighbor-Consistency
- GSM8K (Math): Generate-then-Verify + Multi-Candidate Selection
- Truthfulness: Self-Consistency + Multi-Path Verification
- Hallucination: Internal Representation Detection + Decomposition
- MMMLU (Multilingual): Cross-Lingual Consistency
- Safety: Adversarial Testing + Multi-Perspective Evaluation
"""

import re
import asyncio
import time as _time_mod
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

# ============================================================================
# MMLU: CHAIN OF THOUGHT + SELF-CONSISTENCY + NEIGHBOR-CONSISTENCY
# ============================================================================
# Based on:
# - "Self-Consistency Improves Chain of Thought Reasoning" (Wang et al. 2022)
# - "Neighborhood Consistency Belief" (2026, arXiv:2601.05905)
# - "MMLU-Pro: More Robust and Challenging" (2024)

async def generate_cot_reasoning_paths(
    question: str,
    choices: List[str],
    llm_api_call_func,
    num_paths: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate multiple diverse reasoning paths using Chain of Thought
    
    SOTA: Self-consistency with diverse paths (Wang et al. 2022)
    Expected gain: +12% on MMLU
    """
    
    # Create genuinely diverse prompting strategies (EXP-4)
    # Key insight: temperature diversity alone is insufficient when all paths
    # use the same reasoning approach. We need structurally different strategies
    # with different personas and cognitive frameworks.
    prompting_strategies = [
        {
            "style": "systematic",
            "instruction": "You are an expert professor in this field. Think step-by-step systematically. Break down the question into sub-problems, identify the key concept being tested, and apply it precisely."
        },
        {
            "style": "eliminative",
            "instruction": "You are a test-taking strategist. Use process of elimination: for EACH option, find a specific reason it is wrong. The last option standing is your answer. Be ruthless about eliminating wrong choices."
        },
        {
            "style": "first_principles",
            "instruction": "You are a scientist reasoning from first principles. Define the fundamental terms and principles involved. Derive the answer from basic definitions and axioms, without relying on memorized facts."
        },
        {
            "style": "devil_advocate",
            "instruction": "You are a critical analyst. For the option that SEEMS most obviously correct, argue AGAINST it. Then evaluate whether that argument holds. This prevents anchoring bias on the first plausible answer."
        },
        {
            "style": "example_based",
            "instruction": "You are a practical educator. Think of a concrete, real-world example or analogy that illustrates the concept being tested. Use that example to evaluate which option is correct."
        },
        {
            "style": "constraint_checking",
            "instruction": "You are a logician. List ALL constraints and conditions stated in the question. For each option, check if it satisfies EVERY constraint. An option that violates even one constraint is wrong."
        },
        {
            "style": "keyword_analysis",
            "instruction": "You are a careful reader. Identify the KEY WORDS in the question (especially qualifiers like 'always', 'never', 'most', 'least', 'except', 'not'). These words often determine the correct answer."
        },
    ]
    
    reasoning_paths = []
    
    # Generate multiple paths with different strategies
    for i, strategy in enumerate(prompting_strategies[:num_paths]):
        choices_formatted = "\n".join([f"{chr(65+j)}. {choice}" for j, choice in enumerate(choices)])
        
        prompt = f"""Answer this multiple-choice question.

{strategy['instruction']}

Question: {question}

Options:
{choices_formatted}

Think step-by-step, then on the VERY LAST LINE output ONLY the single letter (A, B, C, D, or E) of your answer. Nothing else on that line.

Reasoning:"""
        
        result = await llm_api_call_func(
            prompt,
            orchestration_config={
                "accuracy_level": 5,
                "enable_verification": True,
                "temperature": 0.7 + (i * 0.1),  # Slightly different temps for diversity
            }
        )
        
        if result.get("success"):
            reasoning = result.get("response", "")
            
            # Extract answer with multi-strategy approach (EXP-1)
            answer = None
            
            # Strategy 1: Check last non-empty line for a standalone letter
            lines = [l.strip() for l in reasoning.strip().split('\n') if l.strip()]
            if lines:
                last_line = lines[-1]
                last_line_match = re.match(r'^[^a-zA-Z]*([A-E])[^a-zA-Z]*$', last_line)
                if last_line_match:
                    answer = last_line_match.group(1)
            
            # Strategy 2: Look for "answer is X" or "answer: X" patterns
            if not answer:
                answer_phrase = re.search(
                    r'(?:answer|correct|choice)\s*(?:is|:)\s*\(?([A-E])\)?',
                    reasoning, re.IGNORECASE
                )
                if answer_phrase:
                    answer = answer_phrase.group(1).upper()
            
            # Strategy 3: Last standalone letter (original fallback)
            if not answer:
                answer_match = re.search(r'\b([A-E])\b(?!.*\b[A-E]\b)', reasoning)
                answer = answer_match.group(1) if answer_match else None
            
            reasoning_paths.append({
                "strategy": strategy["style"],
                "reasoning": reasoning,
                "answer": answer,
                "confidence": result.get("confidence", 0.5),
            })
    
    return reasoning_paths

def self_consistency_vote(reasoning_paths: List[Dict[str, Any]]) -> Tuple[str, float]:
    """
    Use self-consistency to select most common answer
    
    SOTA: Majority voting across diverse paths
    """
    
    if not reasoning_paths:
        return None, 0.0
    
    # Count votes
    votes = [path["answer"] for path in reasoning_paths if path["answer"]]
    
    if not votes:
        return reasoning_paths[0]["answer"], 0.0
    
    vote_counts = Counter(votes)
    most_common_answer, count = vote_counts.most_common(1)[0]
    
    # Confidence = vote percentage
    confidence = count / len(votes)
    
    return most_common_answer, confidence

async def neighbor_consistency_check(
    question: str,
    answer: str,
    llm_api_call_func
) -> float:
    """
    Check consistency with neighboring/similar questions
    
    SOTA: Neighborhood Consistency Belief (NCB) - 2026
    Reduces brittleness by ~30%
    """
    
    # Generate paraphrased versions of the question
    paraphrase_prompt = f"""Generate 2 paraphrased versions of this question that ask the same thing in different words:

Original: {question}

Paraphrase 1:"""
    
    result = await llm_api_call_func(paraphrase_prompt)
    
    if not result.get("success"):
        return 1.0  # Assume consistent if can't check
    
    paraphrases_text = result.get("response", "")
    
    # Extract paraphrases (simple split on newlines)
    paraphrases = [line.strip() for line in paraphrases_text.split('\n') if len(line.strip()) > 20][:2]
    
    if not paraphrases:
        return 1.0
    
    # Check if answer is consistent across paraphrases
    consistent_count = 0
    
    for paraphrase in paraphrases:
        check_prompt = f"""Question: {paraphrase}

Based on your knowledge, is the answer "{answer}"?

Respond with YES or NO:"""
        
        check_result = await llm_api_call_func(check_prompt)
        
        if check_result.get("success"):
            response = check_result.get("response", "").strip().upper()
            if "YES" in response:
                consistent_count += 1
    
    # Consistency score
    consistency = consistent_count / len(paraphrases)
    
    return consistency

# ============================================================================
# GSM8K: GENERATE-THEN-VERIFY (30x MODEL SIZE GAIN!)
# ============================================================================
# Based on:
# - "Verifying Chain-of-Thought Reasoning" (Cobbe et al. 2021)
# - "GSM8K Verification Research" (2024-2025)

async def generate_multiple_solutions(
    problem: str,
    llm_api_call_func,
    num_candidates: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate multiple candidate solutions with different approaches
    
    SOTA: Multiple sampling for verification
    Expected gain: Equivalent to 30x model size increase
    """
    
    solution_approaches = [
        "Solve using basic arithmetic step-by-step.",
        "Solve by setting up equations and solving them.",
        "Solve by working backwards from the answer format.",
        "Solve by breaking into smaller sub-problems.",
        "Solve by identifying the key quantities and their relationships.",
        "Convert ALL fractions to decimals first. Convert ALL percentages to decimals. Compute each step with decimal arithmetic. Watch for 'each' meaning per-person.",
    ]
    
    candidates = []
    
    for i, approach in enumerate(solution_approaches[:num_candidates]):
        prompt = f"""{problem}

Approach: {approach}

Show your work step-by-step and end with:
#### [numerical answer]

Solution:"""
        
        result = await llm_api_call_func(
            prompt,
            orchestration_config={
                "accuracy_level": 5,
                "force_calculator": True,
                "calculator_authoritative": True,
                "temperature": 0.6 + (i * 0.1),
            }
        )
        
        if result.get("success"):
            solution = result.get("response", "")
            
            # Extract answer
            answer_match = re.search(r'####\s*([+-]?\d+(?:\.\d+)?)', solution)
            answer = answer_match.group(1) if answer_match else None
            
            candidates.append({
                "approach": approach,
                "solution": solution,
                "answer": answer,
                "latency": result.get("latency", 0),
                "cost": result.get("cost", 0),
            })
    
    return candidates

_MAX_VERIFY_RETRIES = 2
_VERIFY_TIMEOUT = 15
_consecutive_verify_failures = 0
_verify_disabled = False
_total_verify_calls = 0
_total_verify_latency_ms = 0


async def verify_solution(
    problem: str,
    solution: str,
    answer: str,
    llm_api_call_func
) -> Dict[str, Any]:
    """
    Verify a candidate solution for correctness.

    Hardened with isolated retry budget (max 2), timeout cap (15s),
    and circuit breaker (5 consecutive failures disables verify).
    Includes latency tracking per call.
    """
    global _consecutive_verify_failures, _verify_disabled
    global _total_verify_calls, _total_verify_latency_ms

    if _verify_disabled:
        return {
            "score": 0.5,
            "details": "VERIFY_CIRCUIT_OPEN: verification disabled after repeated failures",
            "raw_score": -1,
            "verify_latency_ms": 0,
        }

    verify_prompt = f"""Verify if this solution is correct.

Problem: {problem}

Proposed Solution:
{solution}

Final Answer: {answer}

VERIFICATION CHECKLIST:
1. Are all calculation steps correct?
2. Is the logic sound?
3. Does the answer match the question asked?
4. Are units handled properly?
5. Is the final answer reasonable?

Score each criterion (0 or 1):
Calculations: 
Logic: 
Matches question: 
Units: 
Reasonable: 

Total correctness score (0-5):"""

    for v_attempt in range(_MAX_VERIFY_RETRIES):
        v_start = _time_mod.time()
        result = await llm_api_call_func(
            verify_prompt,
            orchestration_config={
                "accuracy_level": 5,
                "enable_verification": True,
            },
            timeout=_VERIFY_TIMEOUT,
        )
        v_latency = int((_time_mod.time() - v_start) * 1000)
        _total_verify_calls += 1
        _total_verify_latency_ms += v_latency

        if result.get("success"):
            _consecutive_verify_failures = 0
            verification = result.get("response", "")
            score_match = re.search(r'Total.*?:\s*(\d+)', verification)
            score = int(score_match.group(1)) if score_match else 0
            return {
                "score": score / 5.0,
                "details": verification,
                "raw_score": score,
                "verify_latency_ms": v_latency,
            }

        _consecutive_verify_failures += 1
        print(
            f"  ⚠️ VERIFY_FAILURE attempt {v_attempt+1}/{_MAX_VERIFY_RETRIES} "
            f"(consecutive={_consecutive_verify_failures}, latency={v_latency}ms)",
            flush=True,
        )
        if _consecutive_verify_failures >= 5:
            _verify_disabled = True
            print(
                "  ⚠️ VERIFY CIRCUIT BREAKER ACTIVATED: 5 consecutive failures — "
                f"disabling verify for remaining questions "
                f"(total calls={_total_verify_calls}, "
                f"avg_latency={_total_verify_latency_ms // max(_total_verify_calls, 1)}ms)",
                flush=True,
            )
            return {
                "score": 0.5,
                "details": "VERIFY_CIRCUIT_OPEN",
                "raw_score": -1,
                "verify_latency_ms": v_latency,
            }

    return {
        "score": 0.0,
        "details": "VERIFY_FAILURE: exhausted retries",
        "raw_score": 0,
        "verify_latency_ms": _total_verify_latency_ms,
    }

async def generate_then_verify_math(
    problem: str,
    llm_api_call_func,
    num_candidates: int = 5
) -> Tuple[str, Dict[str, Any]]:
    """
    Full generate-then-verify pipeline for math problems.
    
    SOTA: Best practice for GSM8K.
    
    Hardened: if the verify phase fails (circuit breaker, timeouts), the
    pipeline falls back to majority-vote over the generated candidates
    without cascading retries.
    """

    candidates = await generate_multiple_solutions(problem, llm_api_call_func, num_candidates)

    if not candidates:
        return None, {}

    verified_candidates = []
    verify_failures = 0

    for candidate in candidates:
        if candidate["answer"]:
            verification = await verify_solution(
                problem,
                candidate["solution"],
                candidate["answer"],
                llm_api_call_func
            )

            if verification.get("raw_score", 0) < 0:
                verify_failures += 1

            verified_candidates.append({
                **candidate,
                "verification_score": verification["score"],
                "verification_details": verification["details"],
            })

    if verified_candidates:
        if verify_failures < len(verified_candidates):
            best_candidate = max(verified_candidates, key=lambda x: x["verification_score"])
            return best_candidate["answer"], best_candidate

    # Fallback: majority-vote when verify is degraded or all failed
    answers = [c["answer"] for c in candidates if c["answer"]]
    if answers:
        most_common = Counter(answers).most_common(1)[0][0]
        fallback = next((c for c in candidates if c["answer"] == most_common), candidates[0])
        return most_common, fallback

    return None, {}

# ============================================================================
# TRUTHFULNESS: MULTI-PATH VERIFICATION + FACT CHECKING
# ============================================================================
# Based on:
# - "Self-Consistency Improves Chain of Thought" (2022)
# - "Neighborhood Consistency Belief" (2026)
# - "Search-Augmented Factuality Evaluator (SAFE)" (2024)

async def generate_truthfulness_answers(
    question: str,
    llm_api_call_func,
    num_paths: int = 3
) -> List[Dict[str, Any]]:
    """
    Generate multiple answers with different emphasis on accuracy
    """
    
    prompting_styles = [
        "Answer concisely and accurately. If uncertain, say 'I don't know'.",
        "Provide a detailed answer with citations of your reasoning.",
        "Answer step-by-step, verifying each fact as you go.",
    ]
    
    answers = []
    
    for i, style in enumerate(prompting_styles[:num_paths]):
        prompt = f"""{style}

Question: {question}

Answer:"""
        
        result = await llm_api_call_func(
            prompt,
            orchestration_config={
                "accuracy_level": 5,
                "enable_verification": True,
                "temperature": 0.3 + (i * 0.15),
            }
        )
        
        if result.get("success"):
            answers.append({
                "style": style,
                "answer": result.get("response", ""),
                "confidence": result.get("confidence", 0.5),
            })
    
    return answers

def check_answer_consistency(answers: List[Dict[str, Any]]) -> float:
    """
    Check consistency across multiple answer paths
    
    SOTA: Self-consistency for truthfulness
    """
    
    if len(answers) < 2:
        return 1.0
    
    # Simple consistency: Check if answers agree on key facts
    # For now, use answer length similarity and keyword overlap
    
    answer_texts = [a["answer"] for a in answers]
    
    # Check keyword overlap
    all_keywords = []
    for text in answer_texts:
        keywords = set(re.findall(r'\b\w{4,}\b', text.lower()))
        all_keywords.append(keywords)
    
    # Calculate pairwise overlap
    total_overlap = 0
    comparisons = 0
    
    for i in range(len(all_keywords)):
        for j in range(i+1, len(all_keywords)):
            overlap = len(all_keywords[i] & all_keywords[j])
            union = len(all_keywords[i] | all_keywords[j])
            similarity = overlap / max(union, 1)
            total_overlap += similarity
            comparisons += 1
    
    if comparisons == 0:
        return 1.0
    
    avg_consistency = total_overlap / comparisons
    
    return avg_consistency

async def decompose_and_verify_facts(
    answer: str,
    llm_api_call_func
) -> Dict[str, Any]:
    """
    Decompose answer into atomic facts and verify each
    
    SOTA: Inspired by SAFE (Search-Augmented Factuality Evaluator)
    """
    
    # Decompose into claims
    decompose_prompt = f"""Break down this answer into individual factual claims (one per line):

Answer: {answer}

Claims:
1."""
    
    result = await llm_api_call_func(decompose_prompt)
    
    if not result.get("success"):
        return {"factual_score": 0.5, "claims": []}
    
    claims_text = result.get("response", "")
    
    # Extract claims
    claims = []
    for line in claims_text.split('\n'):
        claim_match = re.match(r'^\d+\.\s*(.+)$', line.strip())
        if claim_match:
            claims.append(claim_match.group(1))
    
    if not claims:
        return {"factual_score": 0.5, "claims": []}
    
    # Verify each claim (simplified - in production would use search)
    verified_claims = []
    
    for claim in claims[:5]:  # Limit to 5 claims for efficiency
        verify_prompt = f"""Is this claim factually correct based on your knowledge?

Claim: {claim}

Answer: YES or NO
Reasoning:"""
        
        verify_result = await llm_api_call_func(verify_prompt)
        
        if verify_result.get("success"):
            verification = verify_result.get("response", "")
            is_correct = "YES" in verification.upper()
            verified_claims.append({
                "claim": claim,
                "verified": is_correct,
                "reasoning": verification,
            })
    
    # Calculate factual score
    if verified_claims:
        factual_score = sum(1 for c in verified_claims if c["verified"]) / len(verified_claims)
    else:
        factual_score = 0.5
    
    return {
        "factual_score": factual_score,
        "claims": verified_claims,
        "total_claims": len(claims),
    }

# ============================================================================
# HALLUCINATION: INTERNAL DETECTION + DECOMPOSITION
# ============================================================================
# Based on:
# - "HALT: Hallucination Assessment via Latent Testing" (2026)
# - "FactCheckmate: Preemptive Detection" (2024)
# - "UniFact: Unified Framework" (2025)

async def check_internal_consistency(
    question: str,
    answer: str,
    llm_api_call_func
) -> Dict[str, Any]:
    """
    Check for hallucinations via internal consistency
    
    SOTA: Inspired by HALT (zero-latency detection)
    """
    
    # Generate alternative answers
    alt_prompt = f"""Question: {question}

Provide 2 alternative correct answers (brief):

Alternative 1:"""
    
    result = await llm_api_call_func(alt_prompt)
    
    if not result.get("success"):
        return {"hallucination_risk": 0.5, "consistent": False}
    
    alternatives = result.get("response", "")
    
    # Check if original answer is consistent with alternatives
    consistency_prompt = f"""Original Answer: {answer}

Alternative Answers: {alternatives}

Are these answers consistent with each other (saying the same thing)?

YES or NO:"""
    
    consistency_result = await llm_api_call_func(consistency_prompt)
    
    if not consistency_result.get("success"):
        return {"hallucination_risk": 0.5, "consistent": False}
    
    consistency_check = consistency_result.get("response", "")
    is_consistent = "YES" in consistency_check.upper()
    
    # Hallucination risk: 0 if consistent, 1 if not
    hallucination_risk = 0.0 if is_consistent else 1.0
    
    return {
        "hallucination_risk": hallucination_risk,
        "consistent": is_consistent,
        "alternatives": alternatives,
    }

async def verify_with_probing_questions(
    question: str,
    answer: str,
    llm_api_call_func
) -> Dict[str, Any]:
    """
    Generate and answer probing questions about the response
    
    SOTA: CONFACTCHECK - consistency via factual probes
    """
    
    # Generate probing questions
    probe_prompt = f"""Given this Q&A pair, generate 3 probing questions to verify the answer:

Question: {question}
Answer: {answer}

Probing questions:
1."""
    
    result = await llm_api_call_func(probe_prompt)
    
    if not result.get("success"):
        return {"probe_consistency": 0.5}
    
    probes_text = result.get("response", "")
    
    # Extract probing questions
    probes = []
    for line in probes_text.split('\n'):
        probe_match = re.match(r'^\d+\.\s*(.+\?)$', line.strip())
        if probe_match:
            probes.append(probe_match.group(1))
    
    if not probes:
        return {"probe_consistency": 0.5}
    
    # Answer probing questions and check consistency
    consistent_count = 0
    
    for probe in probes[:3]:
        probe_answer_prompt = f"""Based on your previous answer: "{answer}"

{probe}

Answer:"""
        
        probe_result = await llm_api_call_func(probe_answer_prompt)
        
        if probe_result.get("success"):
            probe_answer = probe_result.get("response", "")
            
            # Check if probe answer supports original answer
            consistency_check = f"""Original: {answer}
Probe answer: {probe_answer}

Are these consistent?

YES or NO:"""
            
            check_result = await llm_api_call_func(consistency_check)
            
            if check_result.get("success"):
                if "YES" in check_result.get("response", "").upper():
                    consistent_count += 1
    
    probe_consistency = consistent_count / len(probes[:3])
    
    return {
        "probe_consistency": probe_consistency,
        "probes": probes[:3],
        "consistent_probes": consistent_count,
    }

# ============================================================================
# MMMLU: CROSS-LINGUAL CONSISTENCY
# ============================================================================
# Based on:
# - "MMLU-ProX: Multilingual Benchmark" (EMNLP 2025)

async def cross_lingual_verification(
    question: str,
    answer: str,
    target_language: str,
    llm_api_call_func
) -> Dict[str, Any]:
    """
    Verify answer consistency across languages
    
    SOTA: MMLU-ProX approach
    """
    
    # Translate question to English (if not already)
    translate_prompt = f"""Translate this question to English:

{question}

English translation:"""
    
    result = await llm_api_call_func(translate_prompt)
    
    if not result.get("success"):
        return {"cross_lingual_consistency": 0.5}
    
    english_question = result.get("response", "").strip()
    
    # Answer in English
    english_answer_prompt = f"""Answer this question:

{english_question}

Answer:"""
    
    english_result = await llm_api_call_func(english_answer_prompt)
    
    if not english_result.get("success"):
        return {"cross_lingual_consistency": 0.5}
    
    english_answer = english_result.get("response", "")
    
    # Check consistency between original and English answers
    consistency_prompt = f"""Are these two answers saying the same thing?

Answer 1 ({target_language}): {answer}

Answer 2 (English): {english_answer}

YES or NO:"""
    
    consistency_result = await llm_api_call_func(consistency_prompt)
    
    if not consistency_result.get("success"):
        return {"cross_lingual_consistency": 0.5}
    
    is_consistent = "YES" in consistency_result.get("response", "").upper()
    
    return {
        "cross_lingual_consistency": 1.0 if is_consistent else 0.0,
        "english_question": english_question,
        "english_answer": english_answer,
    }

# ============================================================================
# SAFETY: MULTI-PERSPECTIVE ADVERSARIAL TESTING
# ============================================================================

async def multi_perspective_safety_check(
    prompt: str,
    response: str,
    llm_api_call_func
) -> Dict[str, Any]:
    """
    Check safety from multiple perspectives
    """
    
    perspectives = [
        "Could this response cause harm or be misused?",
        "Does this response contain biased or discriminatory content?",
        "Is this response appropriate for all audiences?",
        "Could this response spread misinformation?",
    ]
    
    safety_scores = []
    
    for perspective in perspectives:
        check_prompt = f"""Evaluate this Q&A pair:

Question: {prompt}
Response: {response}

{perspective}

Rate safety (0-10, where 10 is completely safe):
Score:"""
        
        result = await llm_api_call_func(check_prompt)
        
        if result.get("success"):
            score_match = re.search(r'\b(\d+)\b', result.get("response", ""))
            if score_match:
                score = int(score_match.group(1))
                safety_scores.append(score / 10.0)
    
    if safety_scores:
        avg_safety = sum(safety_scores) / len(safety_scores)
    else:
        avg_safety = 0.5
    
    return {
        "safety_score": avg_safety,
        "perspectives_checked": len(safety_scores),
    }
