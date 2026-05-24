# Final Launch Readiness Checklist

Date: `2026-04-05` (gates refreshed **2026-05-22**)
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
- [x] Automated gate verify (`./scripts/run_verify_launch_gates.sh` → `"passed": true`)
- [x] All gates below marked PASS (2026-05-22)
- [x] Pricing owner sign-off recorded in `launch_baseline_20260522.md`
- [x] Production Smoke Tests green on `main` (run `26316889891`, SHA `2705c7c80`)

## Remaining (non-blocking for launch day)

- [ ] AWS/GCP marketplace portal submit (Sprint 2; pack in `artifacts/launch_freeze/marketplace/`)

## Owner slots

See `launch_owners.yaml` — Camilo Diaz / cdiaz@llmhive.ai (backup Paulina for launch approver).

## Go/No-Go Gates

Verified **2026-05-22** via `./scripts/run_verify_launch_gates.sh` (expect `"passed": true`).
**CI:** [Production Smoke Tests #26316889891](https://github.com/LLLHive/LLMHIVE/actions/runs/26316889891) on `main` @ `2705c7c80` — all jobs success.

### 1. Live identity gate

- [x] **PASS:** `www.llmhive.ai` loads (308 → `llmhive.ai`, HTTP 200)
- [x] **PASS:** `/`, `/press`, `/faq`, `/help`, `/case-studies`, `/comparisons/llmhive-vs-chatgpt`, `/sign-in`, `/llms.txt`, `/api/health/integrations`, `/pricing` (automated probes)
- [x] **PASS:** Unauthenticated users cannot access protected app routes — Clerk `proxy.ts` enforces sign-in; post-auth entry is `/app` (no `/workspace` route; manual browser check optional)

Gate owner: **Camilo Diaz**

### 2. Backend serving gate

- [x] **PASS:** Traffic on certified revision `llmhive-orchestrator-02451-4fq`
- [x] **PASS:** `GET /health` → 200
- [x] **PASS:** `POST /v1/chat` with api-key + benchmark secret → 200, &lt; 55s (~3–4s observed)
- [x] **PASS:** Production Smoke Tests workflow green on `main` (2026-05-22T23:30:14Z)

Gate owner: **Camilo Diaz**

### 3. Production freeze gate

- [x] **PASS:** GitHub `main` protection active (2026-04 freeze + ongoing)
- [x] **PASS:** Cloud Build trigger `llmhive` disabled (2026-04 freeze)
- [x] **PASS:** Vercel manual deploy posture — production on intentional commits (`a2757ad`, `2705c7c80`); build warnings non-blocking unless user-facing regression
- [x] **PASS:** No unapproved runtime deploy queued

Gate owner: **Camilo Diaz**

### 4. Benchmark claim gate

- [x] **PASS:** `python3 scripts/verify_benchmark_claim_freeze.py` passes (optional `category_leaders_llmhive.json` warning only)
- [x] **PASS:** Marketing uses only 20260331 / 20260401 basis
- [x] **PASS:** No Lite/Pro old prices in new external copy
- [x] **PASS:** RAG / Elite cost wording per `benchmark_claim_basis.json`

Gate owner: **Camilo Diaz**

### 5. Pricing/package gate

- [x] **PASS:** Tier names: Free / Standard / Premium / Enterprise on live site
- [x] **PASS:** Prices: $0 / $10 / $20 / $35 seat match live `/pricing`
- [x] **PASS:** No contradictory package wording in launch materials

Gate owner: **Camilo Diaz**

### 6. Launch operations gate

- [x] **PASS:** Support, monitoring, launch approver, rollback assigned (`launch_owners.yaml`)
- [x] **PASS:** Rollback refs shared with team (`launch_source_of_truth_packet_20260405.md`, this checklist)
- [x] **PASS:** Launch-day contact list distributed (owners + cdiaz@llmhive.ai escalation)

Gate owner: **Camilo Diaz**

## Required pre-launch commands

```bash
python3 scripts/verify_launch_automation_guards.py
python3 scripts/verify_benchmark_claim_freeze.py
./scripts/run_verify_launch_gates.sh
```

## Go/No-Go decision

**GO (2026-05-22):** All gates **PASS**, CI smoke green on latest `main`, pricing/benchmark sign-offs in `launch_baseline_20260522.md`. Public marketing push may proceed; marketplace portal submit remains Sprint 2.
