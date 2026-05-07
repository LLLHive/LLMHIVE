# Launch Source-of-Truth Packet

Date: `2026-04-05`

## Purpose

This packet freezes the current launch basis in one place:

- what frontend is live
- what backend is live
- what benchmark artifacts are approved for claims
- what package/pricing language is live
- what still must be owned operationally before public launch

This document is operational and documentation-only. It does not authorize any further runtime changes.

## Live Production Identity

### Frontend

- Production deployment id: `dpl_5xM7JRURbxAZEYrv4G5cLC2pQqge`
- Production deployment URL: `https://llmhive-bwik0fj0p-camilo-diazs-projects-84a2ae74.vercel.app`
- Canonical aliases:
  - `https://www.llmhive.ai`
  - `https://llmhive.ai`
  - `https://llmhive.vercel.app`

### Frontend route status verified

Verified live on `www.llmhive.ai`:

- `/` is now the public marketing landing page
- `/workspace` is the authenticated app entry and redirects unauthenticated users to `sign-in`
- `/press` renders publicly
- `/faq` renders publicly
- `/help` renders publicly
- `/case-studies` renders publicly
- `/comparisons/llmhive-vs-chatgpt` renders publicly
- `/sign-in` renders publicly
- `/llms.txt` returns `200` as plain text
- `/api/health/integrations` returns `200` JSON

### Backend

- Cloud Run service: `llmhive-orchestrator`
- Latest ready revision: `llmhive-orchestrator-02210-mm7`
- Live traffic: `100% -> llmhive-orchestrator-02203-grk`

Important note:

- the serving revision for launch is `02203-grk`
- `02210-mm7` is newer but not serving traffic
- benchmark claims should be tied to the certified basis, not to `latestReadyRevisionName`

## Production Freeze Controls

Verified currently in force:

- GitHub `main` branch protection is enabled with required review and admin enforcement
- Cloud Build trigger `llmhive` is disabled
- Vercel project `llmhive` is not auto-connected to a Git production pipeline

Launch rule:

- do not reconnect Vercel Git
- do not re-enable the Cloud Build trigger
- do not loosen `main` protection before launch

## Locked Benchmark Claim Basis

Use these files as the approved benchmark basis for launch claims:

- Free: `benchmark_reports/category_benchmarks_free_20260331.json`
- Free summary: `benchmark_reports/category_benchmarks_free_20260331.md`
- Elite: `benchmark_reports/category_benchmarks_elite_20260401.json`
- Elite summary: `benchmark_reports/category_benchmarks_elite_20260401.md`
- Leader references: `benchmark_configs/category_leaders_llmhive.json`

### Free benchmark summary

- Overall accuracy: `93.3% (544/583)`
- Total cost: `$0.0000`
- Reasoning (MMLU): `85.1%`
- Coding (HumanEval): `96.0%`
- Math (GSM8K): `100.0%`
- Multilingual (MMMLU): `87.0%`
- Long Context (LongBench): `100.0%`
- Tool Use (ToolBench): `100.0%`
- RAG (MS MARCO): `49.7%`
- Dialogue (MT-Bench): `7.5 / 10`

### Elite benchmark summary

- Overall accuracy: `93.5% (547/585)`
- Total cost: `$7.7690`
- Reasoning (MMLU): `88.8%`
- Coding (HumanEval): `100.0%`
- Math (GSM8K): `97.9%`
- Multilingual (MMMLU): `88.4%`
- Long Context (LongBench): `100.0%`
- Tool Use (ToolBench): `100.0%`
- RAG (MS MARCO): `55.4%`
- Dialogue (MT-Bench): `7.2 / 10`

Claim rules:

- do not mix benchmark dates across surfaces
- keep `RAG` in native `MRR@10`/retrieval-style framing where applicable
- do not restate disputed zero-cost claims for Elite categories without recertification
- do not regenerate marketing tables from a different runtime basis

## Frozen Public Pricing And Package Basis

Public pricing/package wording currently exposed on the live pricing surface:

### Free

- Price: `$0`
- Positioning: `Try our orchestration technology`
- Core quotas:
  - `FREE Orchestration`
  - `UNLIMITED queries`
  - `Basic features`

### Lite

- Price: `$14.99/month`
- Positioning: `Unlock #1 AI quality`
- Core quotas:
  - `100 ELITE queries`
  - `Then UNLIMITED FREE`
  - `#1 in ALL categories`

### Pro

- Price: `$29.99/month`
- Positioning: `Maximum power for professionals`
- Core quotas:
  - `500 ELITE queries`
  - `Then UNLIMITED FREE`
  - `#1 in ALL + Full API`

### Enterprise

- Price: `$35/seat/month`
- Positioning: `Teams & compliance`
- Core quotas:
  - `400 ELITE/seat`
  - `Then UNLIMITED FREE`
  - `SSO + Compliance`
- Minimum: `5 seats ($175+/mo)`

Package freeze rule:

- do not change package names, prices, query quotas, or upgrade language before launch unless explicitly approved

## What Changed In The Frontend Recovery

The live frontend now reflects the intended launch behavior:

- root `/` is public marketing
- app experience moved to `/workspace`
- sign-in continues to work
- public launch/trust pages are no longer incorrectly auth-gated

This is now the live frontend basis to reference for launch.

## Remaining Must-Do Actions Before Launch

These are the remaining non-runtime launch actions:

1. Push the workflow-only safety fixes from the protected launch branch.
2. Freeze all market-facing benchmark tables and copy to the same approved artifact basis.
3. Assign named owners for:
   - support queue
   - production monitoring
   - launch go/no-go approval
4. Confirm rollback references are distributed to the launch owners.
5. Do not make additional runtime changes unless a new blocker is proven.

## Recommended Immediate Next Step

Next best step:

- finalize launch ownership and the benchmark/pricing freeze across all launch surfaces

Reason:

- the major frontend blocker is resolved
- backend traffic is pinned to the certified basis
- remaining work is operational alignment, not product change
