# LLMHive ELITE Tier: 8-Category Industry Benchmark
**Test Date:** February 24, 2026
**API:** https://llmhive-orchestrator-792354158895.us-east1.run.app
**Reasoning Mode:** deep
**Strict Mode:** OFF

---

## 🎯 Executive Summary

**Overall Accuracy:** 88.1% (111/126)
**Total Cost:** $0.0419
**Average Cost per Category:** $0.0070
**Categories Tested:** 6

## 📊 Category Results

| Category | Score | Dataset | Status |
|----------|-------|---------|--------|
| Math (GSM8K) | **93.9%** | openai/gsm8k | ✅ |
| Multilingual (MMMLU) | **77.4%** | openai/MMMLU | ⚠️ |
| Long Context (LongBench) | **100.0%** | THUDM/LongBench | ✅ |
| Tool Use (ToolBench) | **100.0%** | ToolBench (OpenBMB) | ✅ |
| RAG (MS MARCO) | **36.6%** | microsoft/ms_marco v1.1 | ❌ |
| Dialogue (MT-Bench) | **6.2%** | lmsys/mt-bench | ❌ |

---

## 📋 Detailed Results

### Math (GSM8K)

- **Dataset:** openai/gsm8k
- **Sample Size:** 33
- **Correct:** 31/33 (93.9%)
- **Errors:** 0
- **Avg Latency:** 26277ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Multilingual (MMMLU)

- **Dataset:** openai/MMMLU
- **Sample Size:** 33
- **Correct:** 24/31 (77.4%)
- **Errors:** 2
- **Avg Latency:** 43296ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Long Context (LongBench)

- **Dataset:** THUDM/LongBench
- **Sample Size:** 17
- **Correct:** 17/17 (100.0%)
- **Errors:** 0
- **Avg Latency:** 12256ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### Tool Use (ToolBench)

- **Dataset:** ToolBench (OpenBMB)
- **Sample Size:** 8
- **Correct:** 8/8 (100.0%)
- **Errors:** 0
- **Avg Latency:** 8139ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

### RAG (MS MARCO)

- **Dataset:** microsoft/ms_marco v1.1
- **Sample Size:** 33
- **Correct:** 30/33 (36.6%)
- **Errors:** 0
- **Avg Latency:** 23062ms
- **Avg Cost:** $0.001269
- **Total Cost:** $0.0419

### Dialogue (MT-Bench)

- **Dataset:** lmsys/mt-bench
- **Sample Size:** 5
- **Correct:** 1/4 (6.2%)
- **Errors:** 1
- **Avg Latency:** 57045ms
- **Avg Cost:** $0.000000
- **Total Cost:** $0.0000

## 💰 Cost Analysis

| Category | Total Cost | Cost/Correct | Cost/Sample | Samples |
|----------|-----------|-------------|------------|---------|
| Math (GSM8K) | $0.0000 | $0.0000 | $0.0000 | 33 |
| Multilingual (MMMLU) | $0.0000 | $0.0000 | $0.0000 | 33 |
| Long Context (LongBench) | $0.0000 | $0.0000 | $0.0000 | 17 |
| Tool Use (ToolBench) | $0.0000 | $0.0000 | $0.0000 | 8 |
| RAG (MS MARCO) | $0.0419 | $0.0014 | $0.0013 | 33 |
| Dialogue (MT-Bench) | $0.0000 | $0.0000 | $0.0000 | 5 |
| **TOTAL** | **$0.0419** | **$0.0004** | **$0.0003** | **129** |


---

**Report Generated:** 2026-02-24T21:23:50.611137
**Status:** ELITE Tier Benchmarked