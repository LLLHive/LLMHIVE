# LLMHive ELITE Tier: 8-Category Industry Benchmark
**Test Date:** February 26, 2026
**API:** https://llmhive-orchestrator-792354158895.us-east1.run.app
**Reasoning Mode:** deep
**Strict Mode:** OFF

---

## 🎯 Executive Summary

**Overall Accuracy:** 81.8% (202/247)
**Total Cost:** $0.2524
**Average Cost per Category:** $0.0841
**Categories Tested:** 3

## 📊 Category Results

| Category | Score | Dataset | Status |
|----------|-------|---------|--------|
| General Reasoning (MMLU) | **66.0%** | lighteval/mmlu | ⚠️ |
| Coding (HumanEval) | **89.8%** | openai/human_eval | ✅ |
| Math (GSM8K) | **93.9%** | openai/gsm8k | ✅ |

---

## 📋 Detailed Results

### General Reasoning (MMLU)

- **Dataset:** lighteval/mmlu
- **Sample Size:** 100
- **Correct:** 66/100 (66.0%)
- **Errors:** 0
- **Avg Latency:** 5800ms
- **Avg Cost:** $0.002320
- **Total Cost:** $0.2320

### Coding (HumanEval)

- **Dataset:** openai/human_eval
- **Sample Size:** 50
- **Correct:** 44/49 (89.8%)
- **Errors:** 1
- **Avg Latency:** 60349ms
- **Avg Cost:** $0.000416
- **Total Cost:** $0.0204

### Math (GSM8K)

- **Dataset:** openai/gsm8k
- **Sample Size:** 100
- **Correct:** 92/98 (93.9%)
- **Errors:** 2
- **Avg Latency:** 27649ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

## 💰 Cost Analysis

| Category | Total Cost | Cost/Correct | Cost/Sample | Samples |
|----------|-----------|-------------|------------|---------|
| General Reasoning (MMLU) | $0.2320 | $0.0035 | $0.0023 | 100 |
| Coding (HumanEval) | $0.0204 | $0.0005 | $0.0004 | 50 |
| Math (GSM8K) | $0.0000 | $0.0000 | $0.0000 | 100 |
| **TOTAL** | **$0.2524** | **$0.0012** | **$0.0010** | **250** |


## 🛡️ Execution Integrity Summary

| Category | API Calls | Errors | Infra Failures | Retries | Fallback Used |
|----------|-----------|--------|----------------|---------|---------------|
| General Reasoning (MMLU) | 128 | 8 | 0 | 3 | 3 |
| Coding (HumanEval) | 105 | 6 | 0 | 0 | 0 |
| Math (GSM8K) | 562 | 18 | 0 | 21 | 21 |


---

**Report Generated:** 2026-02-26T18:33:59.658122
**Status:** ELITE Tier Benchmarked