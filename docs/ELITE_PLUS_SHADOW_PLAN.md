# Elite+ Shadow Orchestrator & Progressive Free — Implementation Plan

**Status:** Implemented (shadow mode, all flags OFF by default)
**Date:** March 2026
**Risk:** Zero — all new behavior is flag-gated, defaults preserve existing behavior.

---

## Architecture Overview

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier Detection  (tier=free/elite/auto, ORCH_TIER_LOCK)     │
└──────────┬──────────────────────────────────┬────────────────┘
           │                                  │
     ┌─────▼─────┐                     ┌──────▼──────┐
     │ FREE Tier  │                     │ ELITE Tier  │
     └─────┬─────┘                     └──────┬──────┘
           │                                  │
    FREE_PROGRESSIVE=1?               Base Elite Answer
           │                                  │
    ┌──────▼──────┐                 ELITE_PLUS_ENABLED=1?
    │ Progressive │                           │
    │ Escalation  │                  ┌────────▼────────┐
    │ Stage 1→2→3 │                  │  Elite+ Shadow  │
    └──────┬──────┘                  │  Blackboard +   │
           │                         │  Multi-Propose  │
           ▼                         │  + Verify +     │
     Free Answer                     │  Synthesize     │
                                     └────────┬────────┘
                                              │
                                     Mode = shadow?
                                       ├── yes → log only, return base
                                       ├── tiebreak → override if criteria met
                                       └── active → return shadow answer
```

---

## Environment Flags

### Elite+ Shadow Orchestrator

| Flag                              | Default    | Description                                                    |
|-----------------------------------|------------|----------------------------------------------------------------|
| `ELITE_PLUS_ENABLED`              | `0`        | Master switch. `0` = entirely off.                             |
| `ELITE_PLUS_MODE`                 | `shadow`   | `shadow` / `tiebreak` / `active`                               |
| `ELITE_PLUS_CANDIDATES`           | `openai/gpt-5.2,anthropic/claude-sonnet-4` | Comma-separated candidate model IDs |
| `ELITE_PLUS_INCLUDE_FREE_ADVISORS`| `0`        | Allow free models as advisory candidates in elite+             |
| `ELITE_PLUS_FREE_ADVISORS`        | `deepseek/deepseek-chat,qwen/qwen3-next-80b-a3b-instruct:free` | Free advisor models |
| `ELITE_PLUS_MAX_EXTRA_MODELS`     | `2`        | Max additional model calls per request                         |
| `ELITE_PLUS_BUDGET_MS`            | `2500`     | Time budget (ms) for each extra model call                     |
| `ELITE_PLUS_TRIGGER_CONFIDENCE`   | `0.55`     | Base confidence threshold below which to consider override      |
| `ELITE_PLUS_TRIGGER_DISAGREE`     | `1`        | Escalate if verifier disagrees with base                       |
| `ELITE_PLUS_LOG_SHADOW`           | `1`        | Log shadow results (always ON by default for analysis)         |

### Progressive Free Orchestration

| Flag                              | Default    | Description                                                    |
|-----------------------------------|------------|----------------------------------------------------------------|
| `FREE_PROGRESSIVE`                | `0`        | Master switch. `0` = use existing 3-model ensemble.            |
| `FREE_STAGE1_MODELS`              | `1`        | Models to call in Stage 1                                      |
| `FREE_STAGE2_ENSEMBLE_SIZE`       | `2`        | Total models after Stage 2 escalation                          |
| `FREE_STAGE3_ENSEMBLE_SIZE`       | `3`        | Total models after Stage 3 escalation                          |
| `FREE_ESCALATE_CONFIDENCE`        | `0.55`     | Confidence threshold — above this, early-stop                  |
| `FREE_EARLY_STOP_ON_AGREEMENT`    | `1`        | Stop at Stage 2 if both models agree                           |
| `FREE_MAX_TOTAL_CALLS_PER_QUERY`  | `3`        | Hard cap on total model calls per request                      |

### Tier Isolation (existing, unchanged)

| Flag                              | Default    | Description                                                    |
|-----------------------------------|------------|----------------------------------------------------------------|
| `ORCH_TIER_LOCK`                  | `none`     | Lock to `elite` / `free` / `none`                              |
| `ELITE_TIER_STRICT`               | `0`        | Assert no free models in elite responses                       |
| `FREE_TIER_STRICT`                | `0`        | Assert no paid models in free responses                        |
| `TRACE_PROVIDER_CALLS`            | `0`        | Include provider call details in telemetry                     |

### CI Benchmark Mode

| Flag                              | Default    | Description                                                    |
|-----------------------------------|------------|----------------------------------------------------------------|
| `CI_SCHEDULED_BENCH`              | `0`        | Enable CI mode: small slices, variance-aware pass/fail         |
| `CI_REGRESSION_THRESHOLD_PP`      | `8.0`      | Percentage-point drop threshold for CI regression failure       |

---

## Rollback (immediate, no deploy needed)

```bash
# Disable all new features — returns to pre-implementation behavior
export ELITE_PLUS_ENABLED=0
export FREE_PROGRESSIVE=0
export ELITE_PLUS_INCLUDE_FREE_ADVISORS=0
export ORCH_TIER_LOCK=none
export ELITE_TIER_STRICT=0
export FREE_TIER_STRICT=0
```

All flags default to OFF. Unsetting them has the same effect as setting to `0`.

---

## Graduation Criteria: Shadow → Tiebreak → Active

### Stage 1: Shadow (current)

**Duration:** 2-4 weeks of production traffic.

**What happens:** Elite+ runs alongside base elite, logs shadow results, never changes user-visible answers.

**Graduation to Tiebreak requires:**
- [ ] 10,000+ shadow comparisons logged
- [ ] Shadow answer matches or improves base in ≥70% of cases (measured by verifier agreement)
- [ ] No increase in p95 latency beyond `ELITE_PLUS_BUDGET_MS` (2.5s)
- [ ] Zero tier violations in shadow telemetry
- [ ] Shadow confidence distribution is well-calibrated (accuracy within 10pp of stated confidence)

### Stage 2: Tiebreak

**Duration:** 2-4 weeks.

**What happens:** Elite+ overrides base answer ONLY when base confidence < 0.55 AND shadow confidence is higher AND verifier confirms base is wrong.

**Graduation to Active requires:**
- [ ] Tiebreak overrides improve accuracy in ≥80% of override cases
- [ ] No regression on any category benchmark (full suite run)
- [ ] Override rate is reasonable (<15% of queries — too high suggests base model selection needs fixing)
- [ ] User satisfaction (if tracked) does not decrease

### Stage 3: Active

**What happens:** Elite+ answer is the primary answer for all elite-tier queries.

**Monitoring:**
- Track accuracy lift vs shadow-only baseline
- Monitor cost impact (extra model calls)
- Watch for latency degradation

---

## Telemetry Fields (API Response `extra` object)

### Elite+ Telemetry (`extra.elite_plus`)

```json
{
  "elite_plus_mode": "shadow",
  "elite_plus_enabled": true,
  "shadow_confidence": 0.82,
  "base_confidence": 0.70,
  "should_override": false,
  "candidates_count": 2,
  "models_called": ["openai/gpt-5.2", "anthropic/claude-sonnet-4"],
  "total_latency_ms": 1850,
  "blackboard_hash": "a1b2c3d4e5f6g7h8",
  "verdict_agrees": "openai/gpt-5.2"
}
```

### Progressive Free Telemetry (`extra.progressive_free`)

```json
{
  "progressive_free": true,
  "stages_executed": 1,
  "total_calls": 1,
  "total_latency_ms": 3200,
  "early_stopped": true,
  "final_confidence": 0.78,
  "models_used": ["deepseek/deepseek-chat"]
}
```

### Orchestration Features (`extra.orchestration_features`)

```json
{
  "hrm": false,
  "adaptive_routing": false,
  "deep_consensus": false,
  "elite_plus_enabled": false,
  "elite_plus_mode": null,
  "progressive_free": false,
  "effective_tier": "elite"
}
```

---

## Files Modified / Created

| File                                                              | Change                                      |
|-------------------------------------------------------------------|---------------------------------------------|
| `llmhive/src/llmhive/app/orchestration/elite_plus_orchestrator.py`| **NEW** — Elite+ shadow pipeline            |
| `llmhive/src/llmhive/app/orchestration/progressive_free.py`      | **NEW** — Progressive free escalation       |
| `llmhive/src/llmhive/app/orchestration/tier_allowlist.py`        | **NEW** — Tier-safe model filtering         |
| `llmhive/src/llmhive/app/services/orchestrator_adapter.py`       | Integration hooks, imports, env flags       |
| `scripts/run_category_benchmarks.py`                              | CI mode flag, variance-aware regression gate|
| `docs/ELITE_PLUS_SHADOW_PLAN.md`                                 | **NEW** — This document                     |

---

## Confirmation Layer Commands

```bash
# 1. Compile check (syntax validation)
python3 -m py_compile scripts/run_category_benchmarks.py
python3 -m py_compile scripts/micro_validation.py
python3 -m py_compile llmhive/src/llmhive/app/services/orchestrator_adapter.py
python3 -m py_compile llmhive/src/llmhive/app/orchestration/elite_plus_orchestrator.py
python3 -m py_compile llmhive/src/llmhive/app/orchestration/progressive_free.py
python3 -m py_compile llmhive/src/llmhive/app/orchestration/tier_allowlist.py

# 2. Dry-run
python3 scripts/micro_validation.py --dry-run

# 3. Strict elite smoke (5 queries)
CATEGORY_BENCH_TIER=elite ELITE_TIER_STRICT=1 \
  python3 scripts/micro_validation.py --elite-smoke

# 4. Strict free smoke (5 queries)
CATEGORY_BENCH_TIER=free ORCH_TIER_LOCK=free FREE_TIER_STRICT=1 \
  FREE_HARNESS_ASSERT=1 \
  python3 scripts/micro_validation.py --free-smoke

# 5. CI benchmark (small, fast, variance-aware)
CI_SCHEDULED_BENCH=1 ALLOW_SLICE_REGEN=0 \
  python3 scripts/run_category_benchmarks.py
```

---

## Risk Assessment

| Risk                         | Mitigation                                              |
|------------------------------|----------------------------------------------------------|
| Elite+ adds latency          | Budget-capped at 2.5s per extra call; shadow mode only   |
| Elite+ changes answers       | Shadow mode logs only; no override until graduated       |
| Progressive free drops acc.  | Default OFF; 3-model fallback preserved                  |
| CI false negatives           | Variance-aware threshold at 8pp + 2×SE                  |
| Tier leakage                 | Allowlist module + existing strict flags unchanged        |
| Import failures              | Every import wrapped in try/except with fallback          |
