# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260106_221237
**Git Commit:** 033033a38318
**Status:** ❌ FAILED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 0.952 | 13 | 1 | 1 |

### Category Breakdown

#### ADV

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 2 |

#### CDR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |

#### FAM

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 6 |

#### MHR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.833 | 4 |

## ⚠️ Critical Failures

The following critical cases failed:

- `tbr_006`

## Notable Failures

### LLMHive

- **tbr_006** (score=0.33): regex: Pattern not found: '176\.71\s*(?:sq(?:uare)?)?\s*m', numeric: Could not extract numeric value (expected: 176.71)

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