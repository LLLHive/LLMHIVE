# LLMHive ELITE Tier: 8-Category Industry Benchmark
**Test Date:** February 20, 2026
**API:** https://llmhive-orchestrator-792354158895.us-east1.run.app
**Reasoning Mode:** deep
**Strict Mode:** OFF

---

## 🎯 Executive Summary

**Overall Accuracy:** 87.2% (462/530)
**Total Cost:** $0.5362
**Average Cost per Category:** $0.0670
**Categories Tested:** 8

## 📊 Category Results

| Category | Score | Dataset | Status |
|----------|-------|---------|--------|
| General Reasoning (MMLU) | **73.0%** | lighteval/mmlu | ⚠️ |
| Coding (HumanEval) | **89.8%** | openai/human_eval | ✅ |
| Math (GSM8K) | **94.1%** | openai/gsm8k | ✅ |
| Multilingual (MMMLU) | **76.8%** | openai/MMMLU | ⚠️ |
| Long Context (LongBench) | **0.0%** | THUDM/LongBench - ERROR | ❌ |
| Tool Use (ToolBench) | **0.0%** | ToolBench (OpenBMB) - ERROR | ❌ |
| RAG (MS MARCO) | **40.9%** | microsoft/ms_marco v1.1 | ❌ |
| Dialogue (MT-Bench) | **0.0%** | lmsys/mt-bench - ERROR | ❌ |

---

## 📋 Detailed Results

### General Reasoning (MMLU)

- **Dataset:** lighteval/mmlu
- **Sample Size:** 100
- **Correct:** 73/100 (73.0%)
- **Errors:** 0
- **Avg Latency:** 5000ms
- **Avg Cost:** $0.005000
- **Total Cost:** $0.5000

### Coding (HumanEval)

- **Dataset:** openai/human_eval
- **Sample Size:** 50
- **Correct:** 44/49 (89.8%)
- **Errors:** 1
- **Avg Latency:** 64601ms
- **Avg Cost:** $0.000509
- **Total Cost:** $0.0249

### Math (GSM8K)

- **Dataset:** openai/gsm8k
- **Sample Size:** 100
- **Correct:** 80/85 (94.1%)
- **Errors:** 15
- **Avg Latency:** 26046ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Multilingual (MMMLU)

- **Dataset:** openai/MMMLU
- **Sample Size:** 100
- **Correct:** 76/99 (76.8%)
- **Errors:** 1
- **Avg Latency:** 22814ms
- **Avg Cost:** $0.000048
- **Total Cost:** $0.0048

### Long Context (LongBench)

- **Dataset:** THUDM/LongBench - ERROR
- **Sample Size:** 0
- **Correct:** 0/-1 (0.0%)
- **Errors:** 1
- **Avg Latency:** 0ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Tool Use (ToolBench)

- **Dataset:** ToolBench (OpenBMB) - ERROR
- **Sample Size:** 0
- **Correct:** 0/-1 (0.0%)
- **Errors:** 1
- **Avg Latency:** 0ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### RAG (MS MARCO)

- **Dataset:** microsoft/ms_marco v1.1
- **Sample Size:** 200
- **Correct:** 189/200 (40.9%)
- **Errors:** 0
- **Avg Latency:** 24186ms
- **Avg Cost:** $0.000032
- **Total Cost:** $0.0065

### Dialogue (MT-Bench)

- **Dataset:** lmsys/mt-bench - ERROR
- **Sample Size:** 0
- **Correct:** 0/-1 (0.0%)
- **Errors:** 1
- **Avg Latency:** 0ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

## 💰 Cost Analysis

| Category | Total Cost | Cost/Correct | Cost/Sample | Samples |
|----------|-----------|-------------|------------|---------|
| General Reasoning (MMLU) | $0.5000 | $0.0068 | $0.0050 | 100 |
| Coding (HumanEval) | $0.0249 | $0.0006 | $0.0005 | 50 |
| Math (GSM8K) | $0.0000 | $0.0000 | $0.0000 | 100 |
| Multilingual (MMMLU) | $0.0048 | $0.0001 | $0.0000 | 100 |
| Long Context (LongBench) | $0.0000 | $0.0000 | $0.0000 | 0 |
| Tool Use (ToolBench) | $0.0000 | $0.0000 | $0.0000 | 0 |
| RAG (MS MARCO) | $0.0065 | $0.0000 | $0.0000 | 200 |
| Dialogue (MT-Bench) | $0.0000 | $0.0000 | $0.0000 | 0 |
| **TOTAL** | **$0.5362** | **$0.0012** | **$0.0010** | **550** |


---

**Report Generated:** 2026-02-20T21:32:56.052187
**Status:** ELITE Tier Benchmarked