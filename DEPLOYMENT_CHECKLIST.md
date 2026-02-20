# LLMHive — Deployment Gating Checklist

**Date:** _______________
**Commit:** _______________
**Branch:** _______________
**Reviewer:** _______________

---

## Pre-Deploy Requirements

All items must be checked before deploying to production.

### Suite Completeness

- [ ] All 8 categories executed (Reasoning, Coding, Math, Multilingual, Long Context, Tool Use, RAG, Dialogue)
- [ ] No skipped categories
- [ ] Micro-validation (`scripts/micro_validation.py`) passed all thresholds
- [ ] Full suite (`scripts/final_full_suite_runner.sh`) completed without error

### Performance Thresholds

| Category | Metric | Threshold | Actual | Pass? |
|---|---|---|---|---|
| HumanEval | Accuracy | >= 92% | ____% | [ ] |
| MMLU | Accuracy | >= 78% | ____% | [ ] |
| MMMLU | Accuracy | >= 82% | ____% | [ ] |
| GSM8K | Accuracy | >= 94% | ____% | [ ] |
| LongBench | Accuracy | >= 95% | ____% | [ ] |
| ToolBench | Accuracy | >= 83% | ____% | [ ] |
| RAG (MRR@10) | Accuracy | >= 40% | ____% | [ ] |
| Dialogue | Avg Score | >= 7.0/10 | ____/10 | [ ] |

### Infrastructure Health

- [ ] Infra failure rate < 2% across all categories
- [ ] Retry rate < 10% across all categories
- [ ] Circuit breaker not triggered more than 5 times total
- [ ] No silent category skips detected

### Cost Controls

- [ ] Total benchmark cost within expected budget ($______)
- [ ] Cost per correct answer within acceptable range
- [ ] No runaway retry storms observed

### Code Integrity

- [ ] Zero-regression audit passed (prompt, routing, model selection, decoding, RAG unchanged)
- [ ] All unit tests pass
- [ ] No linter errors introduced
- [ ] PR approved by at least one reviewer

### Deployment Readiness

- [ ] Cloud Run revision identified for rollback
- [ ] `ROLLBACK_PROTOCOL.md` reviewed and understood
- [ ] Monitoring dashboards configured
- [ ] Alerting thresholds set for error rate spikes

---

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Engineer | | | |
| Reviewer | | | |

---

## Post-Deploy Verification

- [ ] Smoke test passed on production endpoint
- [ ] Canary traffic validated (if applicable)
- [ ] No error rate increase within first 30 minutes
- [ ] Previous revision retained as rollback target
