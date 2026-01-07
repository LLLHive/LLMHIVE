# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260107_014455
**Git Commit:** 033033a38318
**Status:** ✅ PASSED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 1.000 | 2 | 0 | 0 |
| OpenRouter-gpt-4o | 0.583 | 0 | 2 | 2 |

### Category Breakdown

#### FAM

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |
| OpenRouter-gpt-4o | 0.667 | 1 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |
| OpenRouter-gpt-4o | 0.500 | 1 |

## Notable Failures

### LLMHive


### OpenRouter-gpt-4o

- **tbr_001** (score=0.50): numeric: Could not extract numeric value (expected: 28.89)
- **fam_004** (score=0.67): contains: Missing: 'Jupiter'

## Configuration

```json
{
  "temperature": 0.0,
  "max_tokens": 2048,
  "timeout_seconds": 120.0,
  "top_p": 1.0,
  "enable_tools": true,
  "enable_rag": true,
  "enable_mcp2": true,
  "deterministic": true,
  "reasoning_mode": "standard",
  "accuracy_level": 3,
  "enable_hrm": true,
  "enable_deep_consensus": false
}
```