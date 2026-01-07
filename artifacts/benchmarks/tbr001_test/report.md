# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260106_235442
**Git Commit:** 033033a38318
**Status:** ❌ FAILED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 0.500 | 0 | 1 | 1 |

### Category Breakdown

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.500 | 1 |

## ⚠️ Critical Failures

The following critical cases failed:

- `tbr_001`

## Notable Failures

### LLMHive

- **tbr_001** (score=0.50): numeric: Value 4.5 not within tolerance of 28.89 (±0.5)

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