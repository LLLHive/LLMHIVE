# Final Launch Readiness Checklist

Date: `2026-04-05`

## Purpose

This is the operational go/no-go checklist for launch.

It is based on the current frozen launch basis:

- frontend deployment: `dpl_5xM7JRURbxAZEYrv4G5cLC2pQqge`
- frontend alias: `https://www.llmhive.ai`
- backend traffic: `100% -> llmhive-orchestrator-02203-grk`
- benchmark claim basis:
  - `benchmark_reports/category_benchmarks_free_20260331.json`
  - `benchmark_reports/category_benchmarks_elite_20260401.json`

This checklist is intentionally operational. It does not authorize any new runtime changes.

## Current Status

### Engineering status

- frontend public-route blocker: resolved
- frontend root/app split: resolved
- backend launch traffic pinned to certified serving revision: resolved
- unauthorized production automation paths: blocked

### Remaining launch blockers

- [x] Fill `artifacts/launch_freeze/launch_owners.yaml` (item 4) — done 2026-05-18
- [ ] Run `python3 scripts/verify_launch_automation_guards.py` on the branch you will merge (item 1)
- [ ] Run `python3 scripts/verify_benchmark_claim_freeze.py` before publishing claims (item 3)
- [ ] Sprint 2 marketplace submissions (item 5 — non-code; see `marketplace_listing_prep_sprint2.md`)

Resolved in-repo (2026-05-18):

- Workflow guard verifier aligned with `automation/weekly-improvement` (item 1)
- `/v1/chat` launch latency decision + smoke budget (item 2) — `v1_chat_latency_launch_decision.md`
- Benchmark claim manifest (item 3) — `benchmark_claim_basis.json`

## Owner Slots

Mirrors `artifacts/launch_freeze/launch_owners.yaml` (updated 2026-05-18):

- Launch approver: **Camilo Diaz** — cdiaz@llmhive.ai (backup: Paulina Diaz — pdiaz@llmhive.ai)
- Support owner: **Camilo Diaz** — cdiaz@llmhive.ai (hours: Launch week 8am–10pm ET; escalation: cdiaz@llmhive.ai)
- Production monitoring owner: **Camilo Diaz** — cdiaz@llmhive.ai
- Benchmark source-of-truth owner: **Camilo Diaz** — cdiaz@llmhive.ai
- Pricing/package owner: **Camilo Diaz** — cdiaz@llmhive.ai
- Rollback executor: **Camilo Diaz** — cdiaz@llmhive.ai
- Marketplace Sprint 2: **Camilo Diaz** — cdiaz@llmhive.ai

## Go/No-Go Gates

Each gate must be marked `PASS`, `FAIL`, or `N/A`.

### 1. Live identity gate

- [ ] PASS / FAIL: `www.llmhive.ai` resolves to deployment `dpl_5xM7JRURbxAZEYrv4G5cLC2pQqge`
- [ ] PASS / FAIL: `/` is the public marketing homepage
- [ ] PASS / FAIL: `/workspace` redirects unauthenticated users to `/sign-in`
- [ ] PASS / FAIL: `/press`, `/faq`, `/help`, `/case-studies`, and `/comparisons/llmhive-vs-chatgpt` render publicly
- [ ] PASS / FAIL: `/llms.txt` returns `200`
- [ ] PASS / FAIL: `/api/health/integrations` returns `200`

Gate owner: **Camilo Diaz** (cdiaz@llmhive.ai)

### 2. Backend serving gate

- [ ] PASS / FAIL: Cloud Run traffic remains `100% -> llmhive-orchestrator-02203-grk`
- [ ] PASS / FAIL: `/health` returns `200`
- [ ] PASS / FAIL: authenticated `/v1/chat` returns `200`
- [ ] PASS / FAIL: no new runtime deploy has replaced the serving revision

Gate owner: **Camilo Diaz** (cdiaz@llmhive.ai)

### 3. Production freeze gate

- [ ] PASS / FAIL: GitHub `main` protection remains active
- [ ] PASS / FAIL: Cloud Build trigger `llmhive` remains disabled
- [ ] PASS / FAIL: Vercel remains in manual deploy posture
- [ ] PASS / FAIL: no unapproved runtime change is queued for deployment

Gate owner: **Camilo Diaz** (cdiaz@llmhive.ai)

### 4. Benchmark claim gate

- [ ] PASS / FAIL: Free launch claims reference only `category_benchmarks_free_20260331`
- [ ] PASS / FAIL: Elite launch claims reference only `category_benchmarks_elite_20260401`
- [ ] PASS / FAIL: no mixed benchmark dates appear across website, press, investor, or internal launch docs
- [ ] PASS / FAIL: Elite cost wording does not overclaim disputed zero-cost telemetry
- [ ] PASS / FAIL: `RAG` wording stays in native retrieval/benchmark framing

Gate owner: **Camilo Diaz** (cdiaz@llmhive.ai)

### 5. Pricing/package gate

- [ ] PASS / FAIL: Free / Lite / Pro / Enterprise names match the live pricing page
- [ ] PASS / FAIL: public prices match the live pricing page
- [ ] PASS / FAIL: ELITE query quotas match the live pricing page
- [ ] PASS / FAIL: no contradictory package wording exists in launch materials

Gate owner: **Camilo Diaz** (cdiaz@llmhive.ai)

### 6. Launch operations gate

- [ ] PASS / FAIL: support owner assigned
- [ ] PASS / FAIL: monitoring owner assigned
- [ ] PASS / FAIL: launch approver assigned
- [ ] PASS / FAIL: rollback executor assigned
- [ ] PASS / FAIL: rollback references distributed to launch owners

Gate owner: **Camilo Diaz** (cdiaz@llmhive.ai)

## Required Pre-Launch Actions

Complete these before public launch:

1. Confirm workflow guards pass: `python3 scripts/verify_launch_automation_guards.py`.
2. Confirm benchmark freeze: `python3 scripts/verify_benchmark_claim_freeze.py` (basis: `benchmark_claim_basis.json`).
3. Freeze package/pricing wording to the live pricing surface (owner sign-off).
4. ~~Fill `launch_owners.yaml` and owner slots above.~~ Done — see Owner Slots.
5. Share rollback references and launch-day contacts.
6. `/v1/chat`: use smoke chat budget (`SMOKE_CHAT_MAX_MS=55000`); see `v1_chat_latency_launch_decision.md`.

## Launch Day Sequence

1. Reconfirm frontend deployment identity.
2. Reconfirm backend traffic identity.
3. Reconfirm production freeze controls.
4. Run targeted smoke only.
5. Confirm public pages and sign-in entry.
6. Confirm support owner and monitoring owner are active.
7. Publish launch assets.

## Rollback Reference

Rollback philosophy:

- use rollback only for a verified production issue
- prefer minimal rollback scope
- do not bundle new routing/benchmark/runtime changes into rollback actions

Current known-good references:

- frontend production deployment: `dpl_5xM7JRURbxAZEYrv4G5cLC2pQqge`
- backend serving revision: `llmhive-orchestrator-02203-grk`
- launch source of truth: `artifacts/launch_freeze/launch_source_of_truth_packet_20260405.md`

## Go/No-Go Decision

Launch may proceed only if all of the following are true:

- all gates above are `PASS`
- no new runtime changes are pending
- launch owners are assigned
- benchmark and pricing freeze is acknowledged

If any gate is `FAIL`, delay launch rather than making broad late-stage product changes.
