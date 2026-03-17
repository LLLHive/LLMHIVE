# LLMHive FREE Tier: 8-Category Industry Benchmark
**Test Date:** March 03, 2026
**API:** https://llmhive-orchestrator-792354158895.us-east1.run.app
**Reasoning Mode:** deep
**Strict Mode:** OFF

---

## 🎯 Executive Summary

**Overall Accuracy:** 89.6% (528/589)
**Total Cost:** $0.3060
**Average Cost per Category:** $0.0382
**Categories Tested:** 8

## 📊 Category Results

| Category | Score | Dataset | Status |
|----------|-------|---------|--------|
| General Reasoning (MMLU) | **71.7%** | lighteval/mmlu | ⚠️ |
| Coding (HumanEval) | **93.9%** | openai/human_eval | ✅ |
| Math (GSM8K) | **99.0%** | openai/gsm8k | ✅ |
| Multilingual (MMMLU) | **81.8%** | openai/MMMLU | ✅ |
| Long Context (LongBench) | **100.0%** | THUDM/LongBench | ✅ |
| Tool Use (ToolBench) | **100.0%** | ToolBench (OpenBMB) | ✅ |
| RAG (MS MARCO) | **47.6%** | microsoft/ms_marco v1.1 | ❌ |
| Dialogue (MT-Bench) | **8.3 / 10** | lmsys/mt-bench | ✅ |

---

## 📋 Detailed Results

### General Reasoning (MMLU)

- **Dataset:** lighteval/mmlu
- **Sample Size:** 100
- **Correct:** 71/99 (71.7%)
- **Errors:** 1
- **Avg Latency:** 7727ms
- **Avg Cost:** $0.003091
- **Total Cost:** $0.3060

### Coding (HumanEval)

- **Dataset:** openai/human_eval
- **Sample Size:** 50
- **Correct:** 46/49 (93.9%)
- **Errors:** 1
- **Avg Latency:** 103170ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Math (GSM8K)

- **Dataset:** openai/gsm8k
- **Sample Size:** 100
- **Correct:** 99/100 (99.0%)
- **Errors:** 0
- **Avg Latency:** 37857ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Multilingual (MMMLU)

- **Dataset:** openai/MMMLU
- **Sample Size:** 100
- **Correct:** 81/99 (81.8%)
- **Errors:** 1
- **Avg Latency:** 73617ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Long Context (LongBench)

- **Dataset:** THUDM/LongBench
- **Sample Size:** 20
- **Correct:** 20/20 (100.0%)
- **Errors:** 0
- **Avg Latency:** 27468ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Tool Use (ToolBench)

- **Dataset:** ToolBench (OpenBMB)
- **Sample Size:** 10
- **Correct:** 10/10 (100.0%)
- **Errors:** 0
- **Avg Latency:** 15340ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### RAG (MS MARCO)

- **Dataset:** microsoft/ms_marco v1.1
- **Sample Size:** 200
- **Correct:** 190/199 (47.6%)
- **Errors:** 1
- **Avg Latency:** 49345ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Dialogue (MT-Bench)

- **Dataset:** lmsys/mt-bench
- **Sample Size:** 16
- **Score:** 8.3 / 10 (≥7/10 = pass: 11/13)
- **Errors:** 3
- **Avg Latency:** 116002ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

## 💰 Cost Analysis

| Category | Total Cost | Cost/Correct | Cost/Sample | Samples |
|----------|-----------|-------------|------------|---------|
| General Reasoning (MMLU) | $0.3060 | $0.0043 | $0.0031 | 100 |
| Coding (HumanEval) | $0.0000 | $0.0000 | $0.0000 | 50 |
| Math (GSM8K) | $0.0000 | $0.0000 | $0.0000 | 100 |
| Multilingual (MMMLU) | $0.0000 | $0.0000 | $0.0000 | 100 |
| Long Context (LongBench) | $0.0000 | $0.0000 | $0.0000 | 20 |
| Tool Use (ToolBench) | $0.0000 | $0.0000 | $0.0000 | 10 |
| RAG (MS MARCO) | $0.0000 | $0.0000 | $0.0000 | 200 |
| Dialogue (MT-Bench) | $0.0000 | $0.0000 | $0.0000 | 16 |
| **TOTAL** | **$0.3060** | **$0.0006** | **$0.0005** | **596** |


## 🛡️ Execution Integrity Summary

| Category | API Calls | Errors | Infra Failures | Retries | Fallback Used |
|----------|-----------|--------|----------------|---------|---------------|
| General Reasoning (MMLU) | 184 | 29 | 0 | 30 | 30 |
| Coding (HumanEval) | 103 | 4 | 0 | 3 | 3 |
| Math (GSM8K) | 464 | 37 | 0 | 56 | 56 |
| Multilingual (MMMLU) | 360 | 14 | 0 | 18 | 18 |
| Long Context (LongBench) | 20 | 0 | 0 | 0 | 0 |
| Tool Use (ToolBench) | 10 | 0 | 0 | 0 | 0 |
| RAG (MS MARCO) | 598 | 1 | 0 | 1 | 1 |
| Dialogue (MT-Bench) | 16 | 3 | 0 | 0 | 0 |


---

**Report Generated:** 2026-03-03T13:44:35.943453
**Status:** FREE Tier Benchmarked