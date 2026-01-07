# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260106_204210
**Git Commit:** 033033a38318
**Status:** ❌ FAILED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 0.595 | 1 | 13 | 13 |

### Category Breakdown

#### ADV

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.833 | 2 |

#### CDR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.500 | 1 |

#### FAM

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.667 | 6 |

#### MHR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.333 | 1 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.458 | 4 |

## ⚠️ Critical Failures

The following critical cases failed:

- `mhr_006`
- `tbr_001`
- `tbr_002`
- `tbr_003`
- `tbr_006`
- `fam_001`
- `fam_002`
- `fam_004`
- `fam_005`
- `fam_006`
- `fam_009`
- `cdr_002`
- `adv_010`

## Notable Failures

### LLMHive

- **mhr_006** (score=0.33): regex: Pattern not found: '50\s*years?|five\s*decades', numeric: Could not extract numeric value (expected: 50)
- **tbr_002** (score=0.33): regex: Pattern not found: '62\s*minutes|about\s*62|approximately\s*62', numeric: Could not extract numeric value (expected: 62.14)
- **tbr_001** (score=0.50): numeric: Could not extract numeric value (expected: 28.89)
- **tbr_003** (score=0.50): numeric: Could not extract numeric value (expected: -479001112)
- **tbr_006** (score=0.50): numeric: Could not extract numeric value (expected: 176.71)

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