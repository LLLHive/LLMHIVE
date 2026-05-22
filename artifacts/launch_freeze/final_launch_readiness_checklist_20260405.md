# Final Launch Readiness Checklist

Date: `2026-04-05` (gates refreshed 2026-05-22)  
**Current baseline:** [`launch_baseline_20260522.md`](./launch_baseline_20260522.md)

## Purpose

Operational go/no-go checklist for launch.

**Frozen benchmark basis (unchanged):**

- `benchmark_reports/category_benchmarks_free_20260331.json`
- `benchmark_reports/category_benchmarks_elite_20260401.json`

**Certified backend (2026-05-22):** `llmhive-orchestrator-02451-4fq` @ https://www.llmhive.ai

## Engineering status

- [x] Frontend public routes resolved
- [x] ROUTING_V2 + direct providers on orchestrator
- [x] Kimi account + secret OK
- [x] Launch owners assigned (`launch_owners.yaml`)
- [x] Workflow guards + benchmark freeze verifiers in repo
- [x] Smoke chat + latency path (benchmark secret; PR #189)
- [x] Marketplace submission pack prepared (portal submit = Sprint 2)

## Remaining before public marketing push

- [ ] Run `python3 scripts/verify_launch_gates.py` and archive JSON output
- [ ] Mark all gates below PASS or FAIL (do not leave blank)
- [ ] Pricing owner sign-off on live https://www.llmhive.ai/pricing
- [ ] AWS/GCP marketplace portal submit (optional for launch day)

## Owner slots

See `launch_owners.yaml` — Camilo Diaz / cdiaz@llmhive.ai (backup Paulina for launch approver).

## Go/No-Go Gates

Run: `./scripts/run_verify_launch_gates.sh` (loads GCP secrets + runs probes). Expect `"passed": true`.

### 1. Live identity gate

- [ ] PASS / FAIL: `www.llmhive.ai` loads (HTTP 200 or expected redirect)
- [ ] PASS / FAIL: `/`, `/press`, `/faq`, `/help`, `/case-studies`, `/comparisons/llmhive-vs-chatgpt`, `/sign-in`, `/llms.txt`, `/api/health/integrations`, `/pricing`
- [ ] PASS / FAIL: `/workspace` redirects unauthenticated users to sign-in (manual browser check)

Gate owner: **Camilo Diaz**

### 2. Backend serving gate

- [ ] PASS / FAIL: Traffic on certified revision `llmhive-orchestrator-02451-4fq`
- [ ] PASS / FAIL: `GET /health` → 200
- [ ] PASS / FAIL: `POST /v1/chat` with api-key + benchmark secret → 200, &lt; 55s
- [ ] PASS / FAIL: Production Smoke Tests workflow green on `main`

Gate owner: **Camilo Diaz**

### 3. Production freeze gate

- [ ] PASS / FAIL: GitHub `main` protection active
- [ ] PASS / FAIL: Cloud Build trigger `llmhive` disabled
- [ ] PASS / FAIL: Vercel manual deploy posture (no unintended auto-deploy)
- [ ] PASS / FAIL: No unapproved runtime deploy queued

Gate owner: **Camilo Diaz**

### 4. Benchmark claim gate

- [ ] PASS / FAIL: `python3 scripts/verify_benchmark_claim_freeze.py` passes
- [ ] PASS / FAIL: Marketing uses only 20260331 / 20260401 basis
- [ ] PASS / FAIL: No Lite/Pro old prices in new external copy
- [ ] PASS / FAIL: RAG / Elite cost wording per `benchmark_claim_basis.json`

Gate owner: **Camilo Diaz**

### 5. Pricing/package gate

- [ ] PASS / FAIL: Tier names: Free / Standard / Premium / Enterprise on live site
- [ ] PASS / FAIL: Prices: $0 / $10 / $20 / $35 seat match live `/pricing`
- [ ] PASS / FAIL: No contradictory package wording in launch materials

Gate owner: **Camilo Diaz**

### 6. Launch operations gate

- [x] PASS: Support, monitoring, launch approver, rollback assigned
- [ ] PASS / FAIL: Rollback refs shared with team
- [ ] PASS / FAIL: Launch-day contact list distributed

Gate owner: **Camilo Diaz**

## Required pre-launch commands

```bash
python3 scripts/verify_launch_automation_guards.py
python3 scripts/verify_benchmark_claim_freeze.py
./scripts/run_verify_launch_gates.sh
```

## Go/No-Go decision

Launch may proceed when all gates are **PASS**, CI smoke is green, and pricing/benchmark sign-offs are recorded in `launch_baseline_20260522.md`.
