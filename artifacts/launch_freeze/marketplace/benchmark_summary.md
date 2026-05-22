# Benchmark summary — marketplace use only

**Source of truth (do not use other dates or files):**

- Free: `benchmark_reports/category_benchmarks_free_20260331.json`
- Elite: `benchmark_reports/category_benchmarks_elite_20260401.json`
- Manifest: `artifacts/launch_freeze/benchmark_claim_basis.json`

**Claim rules:** No mixed benchmark bases. RAG in native retrieval framing (MS MARCO / MRR@10). Do not claim confirmed zero provider spend for Elite dialogue unless re-certified.

---

## Free tier certification (2026-03-31)

| Metric | Value |
|--------|--------|
| Overall accuracy | **93.3%** (544/583) |
| Total run cost (telemetry) | $0.0000 |
| Reasoning (MMLU) | 85.1% |
| Coding (HumanEval) | 96.0% |
| Math (GSM8K) | 100.0% |
| Multilingual (MMMLU) | 87.0% |
| Long context (LongBench) | 100.0% |
| Tool use (ToolBench) | 100.0% |
| RAG (MS MARCO) | 49.7% |
| Dialogue (MT-Bench) | 7.5 / 10 |

## Elite tier certification (2026-04-01)

| Metric | Value |
|--------|--------|
| Overall accuracy | **93.5%** (547/585) |
| Total run cost (telemetry) | $7.7690 |
| Reasoning (MMLU) | 88.8% |
| Coding (HumanEval) | 100.0% |
| Math (GSM8K) | 97.9% |
| Multilingual (MMMLU) | 88.4% |
| Long context (LongBench) | 100.0% |
| Tool use (ToolBench) | 100.0% |
| RAG (MS MARCO) | 55.4% |
| Dialogue (MT-Bench) | 7.2 / 10 |

---

## Approved one-liner for listings

> LLMHive multi-model orchestration achieved **93.3%** overall accuracy on our March 2026 free-tier certification and **93.5%** on April 2026 elite-tier certification across eight benchmark categories (reasoning, coding, math, multilingual, long context, tool use, RAG, dialogue).

## Do not claim in marketplace copy

- Results from other `benchmark_reports/*` dates
- “Always #1 vs GPT-5” without category context
- Unlimited elite at zero infrastructure cost
