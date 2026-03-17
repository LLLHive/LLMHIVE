# LLMHive FREE Tier: 8-Category Industry Benchmark
**Test Date:** March 01, 2026
**API:** https://llmhive-orchestrator-792354158895.us-east1.run.app
**Reasoning Mode:** deep
**Strict Mode:** OFF

---

## 🎯 Executive Summary

**Overall Accuracy:** 93.2% (109/117)
**Total Cost:** $0.0360
**Average Cost per Category:** $0.0045
**Categories Tested:** 8

## 📊 Category Results

| Category | Score | Dataset | Status |
|----------|-------|---------|--------|
| General Reasoning (MMLU) | **60.0%** | lighteval/mmlu | ⚠️ |
| Coding (HumanEval) | **95.9%** | openai/human_eval | ✅ |
| Math (GSM8K) | **100.0%** | openai/gsm8k | ✅ |
| Multilingual (MMMLU) | **90.0%** | openai/MMMLU | ✅ |
| Long Context (LongBench) | **100.0%** | THUDM/LongBench | ✅ |
| Tool Use (ToolBench) | **100.0%** | ToolBench (OpenBMB) | ✅ |
| RAG (MS MARCO) | **49.8%** | microsoft/ms_marco v1.1 | ❌ |
| Dialogue (MT-Bench) | **7.8 / 10** | lmsys/mt-bench | ⚠️ |

---

## 📋 Detailed Results

### General Reasoning (MMLU)

- **Dataset:** lighteval/mmlu
- **Sample Size:** 10
- **Correct:** 6/10 (60.0%)
- **Errors:** 0
- **Avg Latency:** 9000ms
- **Avg Cost:** $0.003600
- **Total Cost:** $0.0360

### Coding (HumanEval)

- **Dataset:** openai/human_eval
- **Sample Size:** 50
- **Correct:** 47/49 (95.9%)
- **Errors:** 1
- **Avg Latency:** 99304ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Math (GSM8K)

- **Dataset:** openai/gsm8k
- **Sample Size:** 10
- **Correct:** 10/10 (100.0%)
- **Errors:** 0
- **Avg Latency:** 28766ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Multilingual (MMMLU)

- **Dataset:** openai/MMMLU
- **Sample Size:** 10
- **Correct:** 9/10 (90.0%)
- **Errors:** 0
- **Avg Latency:** 59587ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Long Context (LongBench)

- **Dataset:** THUDM/LongBench
- **Sample Size:** 10
- **Correct:** 10/10 (100.0%)
- **Errors:** 0
- **Avg Latency:** 25341ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Tool Use (ToolBench)

- **Dataset:** ToolBench (OpenBMB)
- **Sample Size:** 5
- **Correct:** 5/5 (100.0%)
- **Errors:** 0
- **Avg Latency:** 11968ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### RAG (MS MARCO)

- **Dataset:** microsoft/ms_marco v1.1
- **Sample Size:** 20
- **Correct:** 20/20 (49.8%)
- **Errors:** 0
- **Avg Latency:** 37696ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Dialogue (MT-Bench)

- **Dataset:** lmsys/mt-bench
- **Sample Size:** 3
- **Score:** 7.8 / 10 (≥7/10 = pass: 2/3)
- **Errors:** 0
- **Avg Latency:** 100323ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

## 💰 Cost Analysis

| Category | Total Cost | Cost/Correct | Cost/Sample | Samples |
|----------|-----------|-------------|------------|---------|
| General Reasoning (MMLU) | $0.0360 | $0.0060 | $0.0036 | 10 |
| Coding (HumanEval) | $0.0000 | $0.0000 | $0.0000 | 50 |
| Math (GSM8K) | $0.0000 | $0.0000 | $0.0000 | 10 |
| Multilingual (MMMLU) | $0.0000 | $0.0000 | $0.0000 | 10 |
| Long Context (LongBench) | $0.0000 | $0.0000 | $0.0000 | 10 |
| Tool Use (ToolBench) | $0.0000 | $0.0000 | $0.0000 | 5 |
| RAG (MS MARCO) | $0.0000 | $0.0000 | $0.0000 | 20 |
| Dialogue (MT-Bench) | $0.0000 | $0.0000 | $0.0000 | 3 |
| **TOTAL** | **$0.0360** | **$0.0003** | **$0.0003** | **118** |


## 🛡️ Execution Integrity Summary

| Category | API Calls | Errors | Infra Failures | Retries | Fallback Used |
|----------|-----------|--------|----------------|---------|---------------|
| General Reasoning (MMLU) | 18 | 0 | 0 | 1 | 1 |
| Coding (HumanEval) | 102 | 3 | 0 | 0 | 0 |
| Math (GSM8K) | 60 | 3 | 0 | 3 | 3 |
| Multilingual (MMMLU) | 34 | 0 | 0 | 0 | 0 |
| Long Context (LongBench) | 10 | 0 | 0 | 0 | 0 |
| Tool Use (ToolBench) | 5 | 0 | 0 | 0 | 0 |
| RAG (MS MARCO) | 60 | 0 | 0 | 0 | 0 |
| Dialogue (MT-Bench) | 3 | 0 | 0 | 0 | 0 |


---

**Report Generated:** 2026-03-01T01:52:02.359914
**Status:** FREE Tier Benchmarked