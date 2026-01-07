# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260106_211506
**Git Commit:** 033033a38318
**Status:** ❌ FAILED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 0.857 | 9 | 5 | 5 |

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
| LLMHive | 0.833 | 6 |

#### MHR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 1.000 | 1 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.750 | 4 |

## ⚠️ Critical Failures

The following critical cases failed:

- `tbr_003`
- `tbr_006`
- `fam_004`
- `fam_006`
- `fam_009`

## Notable Failures

### LLMHive

- **tbr_003** (score=0.50): numeric: Value 17.0 not within tolerance of -479001112 (±1)
- **tbr_006** (score=0.50): numeric: Value 7.5 not within tolerance of 176.71 (±0.1)
- **fam_004** (score=0.67): contains: Missing: 'Jupiter'
- **fam_006** (score=0.67): not_contains: Forbidden content found: 'clarify'
- **fam_009** (score=0.67): contains: Missing: 'Shakespeare'

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