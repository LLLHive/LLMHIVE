# LLMHive ELITE Tier: 8-Category Industry Benchmark
**Test Date:** February 28, 2026
**API:** https://llmhive-orchestrator-792354158895.us-east1.run.app
**Reasoning Mode:** deep
**Strict Mode:** OFF

---

## 🎯 Executive Summary

**Overall Accuracy:** 84.5% (169/200)
**Total Cost:** $0.2080
**Average Cost per Category:** $0.1040
**Categories Tested:** 2

## 📊 Category Results

| Category | Score | Dataset | Status |
|----------|-------|---------|--------|
| General Reasoning (MMLU) | **75.0%** | lighteval/mmlu | ⚠️ |
| Math (GSM8K) | **94.0%** | openai/gsm8k | ✅ |

---

## 📋 Detailed Results

### General Reasoning (MMLU)

- **Dataset:** lighteval/mmlu
- **Sample Size:** 100
- **Correct:** 75/100 (75.0%)
- **Errors:** 0
- **Avg Latency:** 5200ms
- **Avg Cost:** $0.002080
- **Total Cost:** $0.2080

### Math (GSM8K)

- **Dataset:** openai/gsm8k
- **Sample Size:** 100
- **Correct:** 94/100 (94.0%)
- **Errors:** 0
- **Avg Latency:** 24878ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

## 💰 Cost Analysis

| Category | Total Cost | Cost/Correct | Cost/Sample | Samples |
|----------|-----------|-------------|------------|---------|
| General Reasoning (MMLU) | $0.2080 | $0.0028 | $0.0021 | 100 |
| Math (GSM8K) | $0.0000 | $0.0000 | $0.0000 | 100 |
| **TOTAL** | **$0.2080** | **$0.0012** | **$0.0010** | **200** |


## 🛡️ Execution Integrity Summary

| Category | API Calls | Errors | Infra Failures | Retries | Fallback Used |
|----------|-----------|--------|----------------|---------|---------------|
| General Reasoning (MMLU) | 408 | 44 | 0 | 20 | 20 |
| Math (GSM8K) | 1674 | 46 | 0 | 41 | 41 |


---

**Report Generated:** 2026-02-28T09:35:08.618144
**Status:** ELITE Tier Benchmarked