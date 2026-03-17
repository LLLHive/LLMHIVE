# Benchmark Regression Analysis — Paired Benchmark (run_paired_bench_10pct.sh)

## Executive Summary

The **severe MMLU regression** in the paired benchmark you stopped (4/19 correct ≈ **21%** vs expected 66–77%) is driven by:

1. **Confidence parsing defaulting to 50%** — When the model output lacks `CONFIDENCE: X.XX`, the benchmark defaults to 0.5, which triggers verification on every question.
2. **Verification not improving accuracy** — With 2 calls (agent1 + verification), the verifier often disagrees or stays at 50%, so wrong answers are kept.
3. **Prediction bias toward A** — 10/18 predictions were A; when wrong, often pred=A vs correct=B/C/D.
4. **Transient API failure** — One `server_502` error caused retry and possible provider switch.

---

## Observed Regression (Paired Benchmark Run)

**Run:** `scripts/run_paired_bench_10pct.sh` — stopped during MMLU (reasoning) category  
**Log:** `artifacts/paired_bench/paired_bench_20260309T010215Z.log`  
**Answers:** `benchmark_reports/answers_elite_20260308_210221.jsonl`

| Metric | Observed | Expected (baseline) | Delta |
|--------|----------|---------------------|-------|
| **MMLU accuracy** | 4/19 ≈ **21%** | 66–77% (best_scores / prior runs) | **-45 to -56 pp** |
| **Correct** | 4 | — | — |
| **Attempted** | 19 (20th sample had server_502 error) | 20 | — |

### Sample Output Pattern

```
[1/20] MMLU: ❌ pred=A correct=C conf=50% calls=2 subj=business_ethics
[2/20] MMLU: ✅ pred=C correct=C conf=50% calls=2 subj=miscellaneous
...
[10/20] MMLU: ❌ pred=A correct=B conf=90% calls=1 subj=college_medicine   ← confident but wrong
[11/20] MMLU: ✅ pred=B correct=B conf=100% calls=1 subj=elementary_mathematics
[RETRY] Attempt 1 failed (server_502), backoff 2s then provider switch
[FAIL] API call aborted after 2 attempts (category=reasoning, err=exception:)
[12/20] MMLU: ❌ pred=D correct=A (RERUN RECOVERED) calls=2 subj=business_ethics
...
[19/20] MMLU: ✅ pred=A correct=A conf=50% calls=2 subj=sociology
```

---

## Root Cause Analysis

### 1. **conf=50% and calls=2 (Primary)**

From `answers_elite_20260308_210221.jsonl`:

- **14 of 18 samples** have `confidence: 0.5` and `num_paths: 2`.
- **4 samples** have different confidence (0.85, 1.0, 0.9) and `num_paths: 1`.

**Mechanism** (from `run_category_benchmarks.py`):

- The benchmark expects `CONFIDENCE: X.XX` in the model response.
- If the regex `r'CONFIDENCE:\s*([\d.]+)'` does not match, confidence defaults to **0.5**.
- When `confidence < 0.90`, a verification call is made → `calls=2`.
- When `confidence < 0.50` (_MMLU_SELF_CHECK_THRESHOLD), an escalation call is made → `calls=3`.

So **conf=50%** means either:

- The model does not output `CONFIDENCE:` in the expected format, or
- The confidence is parsed as 0.5.

That triggers verification on almost every question. The verifier often disagrees or stays at 50%, so wrong answers are retained.

### 2. **Verification Not Helping**

When verification runs:

- If verifier agrees: confidence can increase.
- If verifier disagrees and has higher confidence: predicted answer changes to verifier’s.
- If verifier disagrees and confidence stays low: both are ~50%, so the wrong answer is kept.

In this run, many wrong answers show `conf=50% calls=2`, so the verifier is not correcting them.

### 3. **Prediction Bias Toward A**

From the answers log:

- **10 of 18** predictions were `pred=A`.
- When wrong, correct answers were often B or C.

Possible causes:

- Position bias (first option when uncertain).
- Model tendency to prefer A.
- The verification step, when uncertain, may favor A.

### 4. **API/Infra: server_502**

Log shows:

```
[RETRY] Attempt 1 failed (server_502), backoff 2s then provider switch
[FAIL] API call aborted after 2 attempts (category=reasoning, err=exception:)
```

Sample 11 (or 12) failed with `server_502`; after retry and provider switch, the run continued with RERUN RECOVERED for sample 12. Transient 502s can cause provider switches and affect behavior.

### 5. **Response Format**

The benchmark prompt asks for:

```
FINAL_ANSWER: <letter>
CONFIDENCE: <0.00-1.00>
```

The API returns the raw model output. If the Elite+ orchestration or the model returns something like:

- `Final Answer: A.` (no CONFIDENCE line)
- `The answer is A.`
- Or a different structure

then the benchmark does not parse confidence and defaults to 0.5.

---

## Hypotheses to Investigate

| Hypothesis | Evidence | Next Step |
|------------|----------|-----------|
| **Model not outputting CONFIDENCE** | 14/18 samples have conf=0.5 | Inspect raw API responses for MMLU |
| **Regex mismatch** | Regex works for 0.85, 1.0, 0.9 cases | Check if model uses different casing/format |
| **Elite+ wrapping response** | Orchestration returns `content` | Confirm raw model output is passed through |
| **Verifier quality** | Wrong answers kept with 2 calls | Review verifier logic and prompts |
| **Position bias** | 10/18 pred=A | Analyze question/option distribution |

---

## Recommendations

1. **Inspect raw API responses** — Log one or two full MMLU responses for a sample with `conf=0.5` to confirm whether `CONFIDENCE:` is present.
2. **Relax confidence parsing** — Support common variants (e.g. `Confidence:`, `confidence:`, `CONFIDENCE: 0.7` or `70`).
3. **Review verifier effectiveness** — When verification runs and disagrees, measure how often it corrects vs. worsens the answer.
4. **Monitor position bias** — Track per-option prediction distribution and compare to correct-answer distribution.
5. **Re-run paired benchmark** — After fixes, re-run to confirm MMLU returns to baseline.

---

## Data Sources Reviewed

- `artifacts/paired_bench/paired_bench_20260309T010215Z.log` — run output
- `benchmark_reports/answers_elite_20260308_210221.jsonl` — per-sample answers and confidence
- `scripts/run_category_benchmarks.py` (lines 2420–2498) — MMLU confidence parsing and verification
- `benchmark_reports/best_scores.json` — reasoning baseline 77.8%
- `scripts/run_paired_bench_10pct.sh` — paired benchmark config

---

*Analysis completed: review only, no code changes.*
