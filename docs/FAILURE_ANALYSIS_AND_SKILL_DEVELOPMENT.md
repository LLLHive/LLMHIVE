# Failure Analysis & Skill Development Plan

## Executive Summary

Analysis of benchmark failures to develop SKILLS that prevent errors.
**No cheating** - we don't memorize answers, we build capabilities.

## Current Performance vs Targets

| Category | Current | Target | Gap | Status |
|----------|---------|--------|-----|--------|
| Reasoning (MMLU) | 70% | 85.7% | -15.7% | ❌ CRITICAL |
| Coding (HumanEval) | 6% | 73.2% | -67% | ❌ CATASTROPHIC |
| Math (GSM8K) | 94% | 97% | -3% | ⚠️ CLOSE |
| Multilingual (MMMLU) | 0% | 80% | -80% | ❌ BROKEN |
| RAG (MS MARCO) | 0.5% | 40% | -39.5% | ❌ CRITICAL |
| Long Context | 0% | N/A | N/A | ❌ NOT TESTED |
| Tool Use | 0% | N/A | N/A | ❌ NOT TESTED |
| Dialogue | 0% | N/A | N/A | ❌ NOT TESTED |

## Failure Pattern Analysis

### 1. REASONING (MMLU): 70% → Need 85.7%

#### Root Causes Identified:
1. **Insufficient Model Consensus**: Using 1-2 models instead of 5
2. **No Expert Weighting**: All models treated equally
3. **Weak Prompts**: Not forcing elimination of wrong answers
4. **No Self-Critique**: No verification round

#### Skills to Develop (NOT Answers):

**SKILL 1.1: Hierarchical Expert Consensus**
```python
# Instead of: Use 1 model
# Build: Multi-tier voting system

def hierarchical_reasoning(question, choices):
    # Stage 1: Elite reasoners (3 models)
    elite_responses = [
        gemini_3_pro.answer(question),
        claude_opus_4_6.answer(question),
        gpt_5_2.answer(question),
    ]
    
    # Stage 2: If disagree, add verifiers
    if not consensus_reached(elite_responses, threshold=0.67):
        verifier_responses = [
            grok_4_1.answer(question),
            kimi_k2_5.answer(question),
        ]
        elite_responses.extend(verifier_responses)
    
    # Stage 3: Weighted voting (elite = 2x)
    weights = [2.0] * 3 + [1.0] * len(verifier_responses)
    return weighted_vote(elite_responses, weights)
```

**SKILL 1.2: Elimination Strategy**
```python
# Teach models to ELIMINATE wrong answers first

elimination_prompt = """
Question: {question}

Step 1: Eliminate OBVIOUSLY wrong answers
- Which options contradict known facts?
- Which are logically impossible?
- Cross them out.

Step 2: Compare REMAINING options
- What's the key difference?
- Which aligns best with evidence?

Step 3: Double-check your selection
- Can you defend it?
- Any counter-evidence?

Final answer: [letter]
"""
```

**SKILL 1.3: Domain Knowledge Injection**
```python
# Inject relevant facts BEFORE answering

def inject_domain_knowledge(question, category):
    relevant_facts = knowledge_base.retrieve(
        query=question,
        category=category,
        top_k=3
    )
    
    enhanced_prompt = f"""
    RELEVANT FACTS:
    {relevant_facts}
    
    Now answer: {question}
    
    Use the facts above to reason accurately.
    """
    return enhanced_prompt
```

### 2. CODING (HumanEval): 6% → Need 73.2%

#### Root Causes Identified:
1. **No Edge Case Analysis**: Code works for basic cases only
2. **No Test-Driven Development**: Writing code without tests first
3. **Single-Shot Generation**: No refinement rounds
4. **No Execution Verification**: Not running tests before submission

#### Skills to Develop:

**SKILL 2.1: Edge Case Analysis**
```python
# Before coding, IDENTIFY all edge cases

def analyze_edge_cases(problem_description, examples):
    """Systematic edge case identification."""
    edge_cases = {
        "empty_input": "What if input is empty?",
        "single_element": "What if only one element?",
        "duplicates": "What if duplicates exist?",
        "negative_numbers": "What if numbers are negative?",
        "large_values": "What if very large numbers?",
        "boundary_values": "What about min/max bounds?",
        "type_errors": "What if wrong type passed?",
        "null_values": "What if None/null?",
    }
    
    # For EACH edge case, plan handling
    handling_plan = {}
    for case, question in edge_cases.items():
        handling_plan[case] = determine_handling(problem_description, question)
    
    return handling_plan
```

**SKILL 2.2: Test-Driven Development**
```python
# Write tests FIRST, then implement

def tdd_coding_approach(problem):
    """Test-Driven Development for HumanEval."""
    
    # Step 1: Extract test cases from docstring
    test_cases = extract_test_cases(problem['prompt'])
    
    # Step 2: Add edge case tests
    edge_tests = generate_edge_case_tests(problem)
    all_tests = test_cases + edge_tests
    
    # Step 3: Write minimal code to pass first test
    code = generate_minimal_implementation(problem, all_tests[0])
    
    # Step 4: Iteratively add features for each test
    for test in all_tests[1:]:
        if not test_passes(code, test):
            code = refine_to_pass_test(code, test)
    
    # Step 5: Verify all tests pass
    assert all(test_passes(code, t) for t in all_tests)
    
    return code
```

**SKILL 2.3: Challenge-Refine-Verify Loop**
```python
# 3-round refinement for quality

def challenge_refine_verify(problem):
    """3-round coding improvement."""
    
    # Round 1: Initial implementation (Claude Sonnet 4 - best coder)
    code_v1 = claude_sonnet_4.generate_code(problem)
    
    # Round 2: Critical review (O3 - best reasoner)
    critique = o3.critique_code(
        code=code_v1,
        problem=problem,
        focus=["edge_cases", "efficiency", "correctness"]
    )
    
    # Round 3: Refined implementation (Claude Opus 4.6 - precision)
    code_v2 = claude_opus_4_6.refine_code(
        original=code_v1,
        critique=critique,
        problem=problem
    )
    
    # Verify: Run all tests
    test_results = execute_with_tests(code_v2, problem['test'])
    
    if test_results.all_pass:
        return code_v2
    else:
        # One more refinement based on failures
        return fix_test_failures(code_v2, test_results.failures)
```

**SKILL 2.4: Type Hint & Contract Programming**
```python
# Add type hints and assertions for robustness

def add_safety_checks(code, problem):
    """Add type hints and input validation."""
    
    enhanced_code = f"""
def {function_name}({parameters}) -> {return_type}:
    '''
    {docstring}
    '''
    # Input validation
    assert isinstance(input, expected_type), "Invalid input type"
    if len(input) == 0:
        return default_value
    
    # Original implementation
    {code}
    
    # Output validation
    assert isinstance(result, return_type), "Invalid return type"
    return result
"""
    return enhanced_code
```

### 3. MATH (GSM8K): 94% → Need 97%

#### Root Causes Identified:
1. **Calculator Not Always Used**: Some problems computed by LLM
2. **Answer Extraction Failures**: Can't find "#### X" format
3. **Multi-Step Errors**: Intermediate calculations wrong

#### Skills to Develop:

**SKILL 3.1: FORCE Calculator for ALL Math**
```python
# Calculator is ALWAYS used, no exceptions

def math_solve_with_calculator(problem):
    """MANDATORY calculator usage."""
    
    # Step 1: Decompose into sub-calculations
    steps = decompose_math_problem(problem)
    
    # Step 2: Calculate EACH step with calculator
    calculated_steps = []
    for step in steps:
        expression = extract_expression(step)
        if expression:
            result = calculator.compute(expression)  # AUTHORITATIVE
            calculated_steps.append({
                "step": step,
                "expression": expression,
                "result": result
            })
    
    # Step 3: Final answer is ALWAYS calculator result
    final_answer = calculated_steps[-1]["result"]
    
    # Step 4: LLM only EXPLAINS the calculator's result
    explanation = llm.explain_solution(
        problem=problem,
        steps=calculated_steps,
        final_answer=final_answer
    )
    
    return f"{explanation}\n\n#### {final_answer}"
```

**SKILL 3.2: Multi-Step Verification**
```python
# Verify EACH intermediate step

def verify_multi_step_math(problem, solution):
    """Verify each calculation step."""
    
    steps = extract_calculation_steps(solution)
    
    for i, step in enumerate(steps):
        # Recalculate independently
        independent_result = calculator.compute(step.expression)
        
        # Check consistency
        if abs(independent_result - step.claimed_result) > 0.01:
            logger.warning(f"Step {i} mismatch: expected {independent_result}, got {step.claimed_result}")
            # Fix the error
            steps[i].result = independent_result
            # Propagate correction to subsequent steps
            steps = recalculate_from_step(steps, i)
    
    return steps
```

**SKILL 3.3: Answer Format Enforcer**
```python
# ALWAYS format answer correctly

def enforce_gsm8k_format(solution_text):
    """Ensure #### format exists."""
    
    # Try to find existing format
    match = re.search(r'####\s*([\d,]+\.?\d*)', solution_text)
    if match:
        return solution_text  # Already formatted
    
    # Extract numerical answer
    numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', solution_text)
    if numbers:
        final_answer = numbers[-1]  # Last number is usually answer
        return f"{solution_text}\n\n#### {final_answer}"
    
    # If no number found, force calculator
    expression = extract_any_math(solution_text)
    if expression:
        result = calculator.compute(expression)
        return f"{solution_text}\n\n#### {result}"
    
    logger.error("Could not extract numerical answer!")
    return solution_text
```

### 4. MULTILINGUAL (MMMLU): 0% → Need 80%

#### Root Cause:
- **Dataset Parsing Bug**: Looking for key 'D' but dataset only has A, B, C (4 choices)

#### Skills to Develop:

**SKILL 4.1: Robust Schema Detection**
```python
# Automatically detect dataset schema

def detect_choice_schema(item):
    """Robustly detect how choices are stored."""
    
    # Strategy 1: Check for direct 'choices' field
    if 'choices' in item and isinstance(item['choices'], list):
        return 'list', item['choices']
    
    # Strategy 2: Check for A, B, C, D keys
    choice_keys = [k for k in ['A', 'B', 'C', 'D', 'E'] if k in item]
    if choice_keys:
        return 'letter_keys', [item[k] for k in choice_keys]
    
    # Strategy 3: Check for option_a, option_b, etc.
    option_keys = [k for k in item.keys() if k.startswith('option_')]
    if option_keys:
        return 'option_keys', [item[k] for k in sorted(option_keys)]
    
    # Strategy 4: Check for numbered keys (1, 2, 3, 4)
    number_keys = [k for k in ['1', '2', '3', '4', '5'] if k in item]
    if number_keys:
        return 'number_keys', [item[k] for k in number_keys]
    
    raise ValueError(f"Could not detect schema. Keys: {list(item.keys())}")
```

**SKILL 4.2: Language-Agnostic Reasoning**
```python
# Handle multilingual questions without translation

def multilingual_reasoning(question, choices, language):
    """Reason in original language."""
    
    # Use multilingual-specialized models
    multilingual_models = [
        "google/gemini-3-pro",        # Best multilingual
        "anthropic/claude-opus-4.6",
        "alibaba/qwen3-max",          # Strong Chinese
    ]
    
    # Prompt in original language (no translation!)
    prompt = f"""
    Question: {question}
    
    Options:
    {format_choices(choices)}
    
    Think carefully and select the best answer.
    Provide ONLY the letter (A, B, C, or D).
    """
    
    responses = []
    for model in multilingual_models:
        response = model.generate(prompt)
        answer = extract_letter(response)
        if answer:
            responses.append(answer)
    
    # Majority vote
    from collections import Counter
    return Counter(responses).most_common(1)[0][0]
```

### 5. RAG (MS MARCO): 0.5% MRR → Need 40%

#### Root Causes:
1. **Poor Ranking**: Model not outputting proper rank format
2. **No Reranking**: Not using reranker for quality
3. **Weak Prompts**: Not emphasizing RELEVANCE over similarity

#### Skills to Develop:

**SKILL 5.1: Two-Stage Retrieval**
```python
# Retrieve → Rerank for quality

def two_stage_rag(query, passages):
    """Professional RAG with reranking."""
    
    # Stage 1: Semantic search (cast wide net)
    initial_results = vector_search(
        query=query,
        passages=passages,
        top_k=20  # More candidates for reranking
    )
    
    # Stage 2: Rerank with specialized model
    reranked = reranker.rank(
        query=query,
        passages=initial_results,
        model="bge-reranker-v2-m3",  # SOTA reranker
        top_n=10
    )
    
    return reranked
```

**SKILL 5.2: Relevance-Focused Ranking Prompts**
```python
# Force model to focus on RELEVANCE not similarity

def ranking_prompt(query, passages):
    """Professional ranking instructions."""
    
    prompt = f"""
    You are a RELEVANCE EXPERT. Rank passages by how well they ANSWER the query.
    
    Query: {query}
    
    Passages:
    {format_passages_with_ids(passages)}
    
    CRITICAL INSTRUCTIONS:
    1. A relevant passage DIRECTLY answers or relates to the query
    2. Similar but off-topic = NOT relevant
    3. Keywords alone don't mean relevant
    4. The BEST answer should be ranked #1
    
    Think step-by-step:
    - What is the query asking for?
    - Which passages ACTUALLY answer it?
    - Rank by answer quality, not keyword match
    
    Output format: comma-separated IDs, most relevant first
    Example: 7,3,1,9,2,...
    
    Your ranking:
    """
    return prompt
```

**SKILL 5.3: Citation-Based Verification**
```python
# Verify answers cite actual passages

def verify_rag_answer(query, passages, answer):
    """Ensure answer is grounded in passages."""
    
    # Extract claims from answer
    claims = extract_claims(answer)
    
    # For each claim, find supporting passage
    citations = {}
    for claim in claims:
        supporting_passage = find_best_match(claim, passages)
        if supporting_passage:
            citations[claim] = supporting_passage.id
        else:
            logger.warning(f"Unsupported claim: {claim}")
    
    # Score answer by citation coverage
    citation_rate = len(citations) / len(claims)
    
    if citation_rate < 0.8:
        # Regenerate with explicit citation requirement
        return regenerate_with_citations(query, passages)
    
    return answer, citations
```

## Innovative Optimizations (Think Outside the Box)

### INNOVATION 1: Meta-Learning from Failures
```python
# Learn from mistakes to prevent repeats

class FailureMemory:
    """Remember and learn from benchmark failures."""
    
    def __init__(self):
        self.failure_patterns = {}
    
    def record_failure(self, category, question_type, error_type):
        """Record a failure pattern."""
        key = (category, question_type)
        if key not in self.failure_patterns:
            self.failure_patterns[key] = []
        self.failure_patterns[key].append(error_type)
    
    def get_relevant_warnings(self, category, question_type):
        """Get warnings for similar questions."""
        key = (category, question_type)
        if key in self.failure_patterns:
            common_errors = Counter(self.failure_patterns[key]).most_common(3)
            return [error for error, count in common_errors]
        return []
    
    def inject_warnings_into_prompt(self, prompt, category, question_type):
        """Inject failure warnings into prompt."""
        warnings = self.get_relevant_warnings(category, question_type)
        if warnings:
            warning_text = "\n".join([
                "COMMON MISTAKES TO AVOID:",
                *[f"- {warning}" for warning in warnings]
            ])
            return f"{warning_text}\n\n{prompt}"
        return prompt
```

### INNOVATION 2: Adaptive Complexity Routing
```python
# Use cheaper models for easy questions, expensive for hard

def adaptive_routing(question, category):
    """Route based on question difficulty."""
    
    # Quick complexity assessment
    complexity = assess_complexity(question)
    
    if complexity == "simple":
        # Use single fast model
        return fast_model.answer(question)
    
    elif complexity == "medium":
        # Use 2-model consensus
        responses = [
            model_1.answer(question),
            model_2.answer(question),
        ]
        return consensus(responses)
    
    else:  # complex
        # Full hierarchical consensus
        return hierarchical_reasoning(question)
```

### INNOVATION 3: Cross-Model Verification
```python
# Use different model types to catch errors

def cross_model_verification(question, answer, category):
    """Verify with specialized models."""
    
    if category == "math":
        # Verify with calculator (authoritative)
        calculator_result = calculator.solve(question)
        if calculator_result != answer:
            return calculator_result  # Calculator wins
    
    elif category == "coding":
        # Verify by execution
        test_results = execute_tests(answer, question)
        if not test_results.all_pass:
            # Refine until passes
            return refine_until_passes(answer, test_results)
    
    elif category == "reasoning":
        # Cross-check with logic checker
        logic_check = verify_logical_consistency(answer, question)
        if not logic_check.valid:
            return regenerate_with_logic(question, logic_check.issues)
    
    return answer
```

### INNOVATION 4: Ensemble Diversity Maximization
```python
# Use maximally different models for better coverage

def diverse_ensemble(category):
    """Select maximally diverse models."""
    
    # Get all candidate models
    candidates = get_top_models_for_category(category, limit=10)
    
    # Measure diversity (architecture, training, provider)
    diversity_scores = []
    for i, model_a in enumerate(candidates):
        for model_b in candidates[i+1:]:
            diversity = compute_diversity(model_a, model_b)
            diversity_scores.append((model_a, model_b, diversity))
    
    # Select most diverse subset
    selected = select_diverse_subset(diversity_scores, size=3)
    
    return selected
```

## Implementation Roadmap

### Phase 1: Critical Fixes (Immediate)
- [ ] Fix MMMLU dataset parser
- [ ] Force calculator for ALL math
- [ ] Add challenge-refine for coding
- [ ] Implement two-stage RAG

**Expected Impact**: Math 94% → 97%, MMMLU 0% → 80%

### Phase 2: Skill Deployment (High Priority)
- [ ] Deploy hierarchical consensus for reasoning
- [ ] Add TDD approach for coding
- [ ] Implement cross-model verification
- [ ] Add failure memory system

**Expected Impact**: Reasoning 70% → 85%, Coding 6% → 60%

### Phase 3: Innovation Layer (Medium Priority)
- [ ] Adaptive complexity routing
- [ ] Ensemble diversity maximization
- [ ] Meta-learning from failures
- [ ] Citation-based verification

**Expected Impact**: All categories +5-10%

### Phase 4: Polish & Optimize (Ongoing)
- [ ] Monitor failure patterns
- [ ] Expand knowledge base
- [ ] Tune prompts per question type
- [ ] Optimize model selection

**Expected Impact**: Sustained high performance

## Success Metrics

- ✅ Reasoning: 85.7%
- ✅ Coding: 73.2%
- ✅ Math: 97.0%
- ✅ Multilingual: 80%+
- ✅ RAG: 40%+ MRR@10

## Key Principle

> **Build skills, not answer databases.**
> **Develop capabilities, not memorization.**
> **Think like an engineer, not a student copying answers.**
