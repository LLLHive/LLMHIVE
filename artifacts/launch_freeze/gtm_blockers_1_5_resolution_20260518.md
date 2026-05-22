# GTM blockers 1–5 resolution status

Date: `2026-05-18`  
Item 6 (Kimi): **done** — account funded, GCP secret rotated, direct API verified.  
Item 8 (Marketplace launch): **pending** — non-code; see Sprint 2 checklist.

## Summary

| # | Blocker | Resolution | Verify |
|---|---------|------------|--------|
| 1 | Workflow-only CI safety fixes | Guards aligned with live workflows; six workflow files on `main` | `python3 scripts/verify_launch_automation_guards.py` |
| 2 | Intermittent slow `/v1/chat` outlier | Launch decision + 55s smoke budget; diagnostics on failure | `artifacts/launch_freeze/v1_chat_latency_launch_decision.md` |
| 3 | Freeze pricing/claims to one benchmark artifact | `benchmark_claim_basis.json` + verifier | `python3 scripts/verify_benchmark_claim_freeze.py` |
| 4 | Named support/monitoring owners | `launch_owners.yaml` template — **fill names before launch** | Manual |
| 5 | AWS/GCP marketplace listing | Sprint 2 prep checklist (non-code) | `marketplace_listing_prep_sprint2.md` |

## Item 1 — workflow-only CI

**Safe scope:** `.github/workflows/auto-restore-critical-files.yaml`, `modeldb_refresh.yml`, `scheduled-benchmarks.yml`, `secure-history.yml`, `smoke-tests.yml`, `weekly-improvement.yml` only.

**Push:** If `main` already contains these files, run verifiers locally; no product deploy required. If your branch diverged, open a PR with **only** those six files.

```bash
python3 scripts/verify_launch_automation_guards.py
python3 -m pytest tests/test_launch_automation_guards.py -q
```

## Item 2 — /v1/chat latency

No orchestrator routing changes. Smoke enforces `SMOKE_CHAT_MAX_MS` (default `55000`) on simple chat success path.

## Item 3 — benchmark freeze

Single manifest: `artifacts/launch_freeze/benchmark_claim_basis.json`.

## Item 4 — owners

Edit `artifacts/launch_freeze/launch_owners.yaml` and mirror names into `final_launch_readiness_checklist_20260405.md` owner slots.

## Item 5 — marketplace

Operational checklist only; target Sprint 2 per `docs/90_day_market_execution.md`.
