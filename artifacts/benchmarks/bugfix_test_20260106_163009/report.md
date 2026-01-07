# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260106_213011
**Git Commit:** 033033a38318
**Status:** ✅ PASSED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 1.000 | 3 | 0 | 0 |

### Category Breakdown

#### FAM

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |

#### MHR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |

## Notable Failures

### LLMHive


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