# Benchmark Report: Complex Reasoning Benchmark

**Version:** 1.0.0
**Date:** 20260107_014023
**Git Commit:** 39deabf50ce6
**Status:** ❌ FAILED

## Summary

### Leaderboard

| System | Mean Score | Passed | Failed | Critical Failures |
|--------|------------|--------|--------|-------------------|
| LLMHive | 0.839 | 38 | 17 | 2 |

### Category Breakdown

#### ADV

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.917 | 10 |

#### CDR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.683 | 10 |

#### CFQ

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.667 | 5 |

#### FAM

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.967 | 10 |

#### MHR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.933 | 10 |

#### TBR

| System | Mean Score | Cases |
|--------|------------|-------|
| LLMHive | 0.783 | 10 |

## ⚠️ Critical Failures

The following critical cases failed:

- `mhr_006`
- `fam_006`

## Notable Failures

### LLMHive

- **mhr_006** (score=0.33): regex: Pattern not found: '50\s*years?|five\s*decades', numeric: Could not extract numeric value (expected: 50)
- **tbr_008** (score=0.33): regex: Pattern not found: '37\s*(?:°?C|degrees?\s*C)', numeric: Could not extract numeric value (expected: 310.15)
- **cdr_001** (score=0.33): contains: Missing: '1, 1, 2, 3, 5, 8, 13, 21, 34, 55', regex: Pattern not found: '1,\s*1,\s*2,\s*3,\s*5,\s*8,\s*13,\s*21,\s*34,\s*55'
- **cfq_001** (score=0.33): regex: Pattern not found: 'what|which|clarify|refer|context|specific|previous', asked_clarification: Should have asked for clarification
- **tbr_005** (score=0.50): numeric: Could not extract numeric value (expected: 5.4)

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