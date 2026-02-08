# Benchmark Answer Quality Optimization

## User Request

> "fixing the test and lowering their standards is not whaat we aare looking for the test have to be industry benchmaarks, work on the answer side not maaking the question eaaasier."

## Problem Analysis

The benchmarks are CORRECT - they're industry-standard tests (MMLU, GSM8K, HumanEval, MS MARCO). The issue is that our ANSWERS aren't good enough.

### Current vs. Historical Performance

| Category | Historical | Current | Gap |
|----------|-----------|---------|-----|
| Reasoning (MMLU) | 85.7% | 70-74% | -12-15% |
| Coding (HumanEval) | 73.2% | 10% | -63% |
| Math (GSM8K) | 97.0% | 92-94% | -3-5% |
| RAG (MS MARCO) | Strong | 0-0.5% | -100% |

### Root Causes

1. **Coding**: Code executes (0 errors) but solutions are WRONG (10% pass rate)
   - Problem: Insufficient prompt guidance for edge cases
   - Problem: No verification or testing instructions

2. **RAG**: Answers have 24% F1 but 0% MRR@10
   - Problem: Ranking logic is broken/not being used
   - Problem: Weak synthesis instructions

3. **Reasoning**: 70-74% vs 85.7% historical
   - Problem: Prompts don't enforce step-by-step analysis
   - Problem: No elimination strategy for wrong answers

4. **Math**: 92-94% vs 97% historical
   - Problem: Calculator not being used consistently
   - Problem: No verification step

## Solution: ANSWER QUALITY ENHANCEMENT

### 1. Created `benchmark_enhancer.py`

A new module that provides:
- **Enhanced prompts** for each category with explicit quality instructions
- **Robust answer extraction** to fix parsing failures
- **Orchestration configuration** optimized for quality over cost

### 2. Enhanced Prompts

#### Reasoning (MMLU)
**Before:**
```
Answer this multiple-choice question. Provide ONLY the letter (A, B, C, or D).
```

**After:**
```
Analyze this question with rigorous step-by-step reasoning.

Approach:
1. Read the question carefully and identify what's being asked
2. For each answer option, evaluate its correctness
3. Eliminate clearly wrong answers
4. Compare remaining options
5. Select the most accurate answer

Provide your final answer as ONLY the letter (A, B, C, or D).
```

#### Coding (HumanEval)
**Before:**
```
Complete this Python function. Return ONLY the code implementation.
```

**After:**
```
Write production-quality Python code for this function.

Requirements:
1. Complete implementation (not just stub or pass)
2. Handle all edge cases mentioned in the docstring
3. Include proper error handling where appropriate
4. Ensure the function works correctly for ALL test cases
5. Think through the logic step-by-step before writing

Provide the complete function implementation:
```

#### Math (GSM8K)
**Before:**
```
Solve this math problem. Show your work and provide the final answer after ####.
```

**After:**
```
Solve this math problem with careful step-by-step work.

Instructions:
1. Break down the problem into clear steps
2. Show ALL calculations explicitly
3. Verify each step for arithmetic errors
4. Double-check your final answer
5. Format answer as: #### [number]

Work through this carefully:
```

### 3. Enhanced Orchestration Configuration

Now passing explicit orchestration config to the API:

```python
orchestration_config = {
    "accuracy_level": 5,  # Maximum quality (was 3)
    "use_deep_consensus": True,  # Multi-model voting
    "enable_verification": True,  # Verify answers
    "enable_calculator": True,  # For math
}
```

### 4. Model Selection (Already Excellent)

Confirmed that ELITE tier already uses top models:
- **Math**: O3, GPT-5, Claude Opus 4
- **Reasoning**: GPT-5, O3, Claude Opus 4
- **Coding**: Claude Sonnet 4, Claude Opus 4, GPT-5
- **RAG**: GPT-5, Claude Opus 4, Gemini 2.5 Pro

The models are NOT the problem - the prompts and orchestration were.

## Changes Made

### Files Modified

1. **`scripts/run_category_benchmarks.py`**
   - Enhanced prompts for reasoning, coding, and math
   - Added orchestration config parameter to API calls
   - Injected quality-focused config for each category

2. **`scripts/run_industry_benchmarks.py`**
   - Added orchestration config parameter to API calls
   - Default to maximum quality settings

3. **`llmhive/src/llmhive/app/orchestration/benchmark_enhancer.py`** (NEW)
   - Enhanced prompt templates for all categories
   - Robust answer extraction functions
   - Category-specific orchestration configurations
   - Best-of-N generation strategies

## Expected Impact

| Category | Current | Target | Strategy |
|----------|---------|--------|----------|
| Reasoning | 70-74% | 85.7% | Step-by-step analysis, elimination |
| Coding | 10% | 73.2% | Edge case handling, verification |
| Math | 92-94% | 97.0% | Calculator + consensus + verification |
| RAG | 0-0.5% | Strong | Better ranking instructions |

## Next Steps

1. **Run benchmarks** with enhanced prompts and configuration
2. **Analyze results** to measure improvement
3. **Iterate** on prompts that still underperform
4. **Document** final performance for marketing

## Key Principle

> "Test integrity is sacred. We improve ANSWERS, not tests."

The benchmarks are industry-standard. Our job is to make our orchestration produce answers that beat the frontier models, not to make the tests easier.

## Cost Impact

Expected cost increase: **2-3x per query** during benchmarks
- Worth it for marketing-grade results
- Elite tier already uses premium models
- Additional cost comes from:
  - Multi-model consensus (3 models instead of 1)
  - Verification rounds
  - Calculator integration
  - Deep consensus mechanisms

For $0.50-1.50 per benchmark question, we get results we can advertise.
