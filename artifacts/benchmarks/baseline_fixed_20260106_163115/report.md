# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260106_213116
**Git Commit:** 033033a38318
**Status:** ❌ FAILED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 0.917 | 11 | 3 | 3 |

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
| LLMHive | 0.944 | 6 |

#### MHR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.667 | 1 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.875 | 4 |

## ⚠️ Critical Failures

The following critical cases failed:

- `mhr_006`
- `tbr_003`
- `fam_004`

## Notable Failures

### LLMHive

- **tbr_003** (score=0.50): numeric: Could not extract numeric value (expected: -479001112)
- **mhr_006** (score=0.67): numeric: Value 10.0 not within tolerance of 50 (±1)
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