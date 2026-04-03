# Launch Readiness Audit

Date: `2026-04-02`

## Freeze Decision

- Production should be treated as frozen for launch.
- Do not run new broad orchestration changes on the production path.
- If more benchmark or routing improvements are desired, do them on a separate `v2` branch after launch.

## Locked Claim Basis

Approved benchmark basis for all market-facing assets:
- Free certification: `benchmark_reports/category_benchmarks_free_20260331.json`
- Elite certification: `benchmark_reports/category_benchmarks_elite_20260401.json`
- Leader references: `benchmark_configs/category_leaders_llmhive.json` (`version=2026-03-29`)

Notes:
- `RAG` must stay in native `MRR@10` format (`0.497`, `0.554`, `0.420`), not percentage accuracy.
- `Dialogue` cost telemetry is still not audit-grade and must not be described as confirmed zero spend.

## Live Production Identity

Backend service:
- Cloud Run service: `llmhive-orchestrator`
- Live URL: `https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app`
- Latest ready revision: `llmhive-orchestrator-02204-lzb`
- Previous ready revision: `llmhive-orchestrator-02203-grk`

Observed live backend status:
- `/health`: `200`
- `/build-info`: `200`, commit now exposed as `b9c27bf7-c825-485b-a914-e527b4dfa029`
- `/v1/chat` Free request: `200`
- `/v1/chat` Elite request: `200`

## Smoke Pass Summary

Public frontend routes checked:
- `https://llmhive.vercel.app/landing` -> `200`
- `https://llmhive.vercel.app/pricing` -> `200`
- `https://llmhive.vercel.app/privacy` -> `200`
- `https://llmhive.vercel.app/terms` -> `200`
- `https://llmhive.vercel.app/contact` -> `200`
- `https://www.llmhive.ai/sign-in` -> `200`, Clerk sign-in form renders
- `https://www.llmhive.ai/` -> `200` -> redirects into working sign-in flow

App entry routes checked:
- `https://llmhive.vercel.app/` -> redirects into sign-in flow
- `https://llmhive.vercel.app/models` -> redirects into sign-in flow
- `https://llmhive.vercel.app/orchestration` -> redirects into sign-in flow
- `https://llmhive.vercel.app/settings` -> redirects into sign-in flow

Observed hostname/auth mismatch:
- The canonical launch domain `https://www.llmhive.ai` works with Clerk.
- The public Vercel hostname `https://llmhive.vercel.app` previously triggered Clerk `origin_invalid` on `https://clerk.llmhive.ai/v1/client`.
- After the controlled Vercel deploy, `https://llmhive.vercel.app/sign-in` now returns `308` to `https://www.llmhive.ai/sign-in`, so Clerk only runs on the canonical domain.

Observed backend/preflight drift:
- Production preflight tooling was updated to understand the current `extra.tier_info` + `extra.cost_tracking` telemetry shape, so paid/free telemetry checks now pass cleanly against live production.
- After the controlled backend deploy from the isolated release worktree, `/build-info` now exposes commit and build time, and `/internal/launch_kpis` responds with the internal key.
- After Vercel access was restored and a controlled frontend deploy completed, the canonical redirect behavior is now live.

Latest refined preflight result:
- Paid/free tier telemetry checks: PASS
- Backend verification after deploy: PASS (`health`, `build_info`, `launch_kpis`)
- Frontend verification after deploy: PASS (`vercel_redirect`, `canonical_sign_in`)
- Remaining informational-only note: raw HTTP probe for `canonical_root_redirect` can still time out

Latest minimal-release verifier baseline:
- `vercel_redirect`: PASS (`308` to `https://www.llmhive.ai/sign-in`)
- `canonical_sign_in`: PASS
- `backend_health`: PASS
- `build_info`: PASS (`commit=b9c27bf7-c825-485b-a914-e527b4dfa029`)
- `launch_kpis`: PASS (`200` with internal key)
- `canonical_root_redirect`: informational-only; plain HTTP probes still time out even though browser verification reached the sign-in flow

Latest release-candidate safety finding:
- Cloud Run revision `llmhive-orchestrator-02204-lzb` is now live at 100% traffic from Cloud Build `b9c27bf7-c825-485b-a914-e527b4dfa029`.
- The backend metadata and internal KPI drift were resolved by the controlled backend deploy from the isolated release worktree.
- Vercel production deployment `https://llmhive-3cc5fuma6-camilo-diazs-projects-84a2ae74.vercel.app` is live and aliases `https://www.llmhive.ai` plus `https://llmhive.vercel.app`.
- The first frontend deploy attempt failed before going live because of a pre-existing TypeScript contract mismatch in `hooks/use-model-registry.ts`; that was fixed in the safe worktree and the retry deploy succeeded.
- The first isolated release candidate from `release/eliteplus-certified` must not be deployed: compared with the current committed benchmark-prep branch, it diverges in benchmark-critical files including `scripts/run_category_benchmarks.py`, `llmhive/src/llmhive/app/benchmarks/runner_llmhive.py`, and `tests/benchmarks/test_runner_llmhive_contract.py`.
- A safer replacement candidate was recut from committed SHA `c1c136c58122963681f2961ee4dd8a040f62f239` into `/Users/camilodiaz/LLMHIVE-market-release-current`.
- In that fresh worktree, the live fixes were applied and validated without touching benchmark-critical files.

## Benchmark Key Rotation Status

Current state:
- Cloud Run reads `API_KEY` from Secret Manager secret `api-key` using `latest`.
- Secret Manager version `3` is now the only enabled `api-key` version.
- Old exposed version `1` and malformed version `2` have both been disabled.
- Vercel `LLMHIVE_API_KEY` was updated across production, preview, and development, and the frontend was redeployed successfully.
- Cloud Run was rolled to revision `llmhive-orchestrator-02206-cct` so the backend picked up `api-key:latest`.
- A protected backend endpoint (`/v1/analyze/file`) accepts the new key and rejects the old key (`200` vs `401`).
- The GitHub Actions repository secret `API_KEY` now exists again and has been aligned to the rotated value.

Blocker:
- Runtime key rotation itself is complete.
- Residual CI/CD issue: multiple GitHub workflows authenticate to Google Cloud successfully but still skip their Secret Manager fetch step, so Workload Identity secret retrieval is not yet proven end-to-end by workflow execution.
- A workflow-only condition fix has been prepared locally in `.github/workflows/smoke-tests.yml`, `.github/workflows/quality-regression.yml`, `.github/workflows/scheduled-benchmarks.yml`, and `.github/workflows/weekly-improvement.yml`, but GitHub cannot use that fix until it is committed and pushed.
- `scheduled-benchmarks.yml` manual verification run `23927096244` failed with `401` because it never populated `LLMHIVE_API_KEY`; the benchmark secret-fetch step was skipped.
- `smoke-tests.yml` manual verification run `23927210730` succeeded overall, but both jobs also skipped the Secret Manager fetch step even after successful GCP auth.
- Root cause confirmed from live branch verification: the affected jobs were missing `id-token: write`, so `google-github-actions/auth` could not receive GitHub OIDC token variables and Secret Manager fetch steps were skipped afterward.
- Detailed procedure: `artifacts/launch_freeze/benchmark_key_rotation_runbook_20260402.md`

Safe rotation sequence:
1. Fix the GitHub workflow condition/gating bug so the GCP secret-fetch steps actually run after auth.
2. Re-run a workflow that explicitly fetches `api-key` from Secret Manager and confirm the step executes.
   - Preferred low-risk path: dispatch `Scheduled Benchmarks` with `mode=secrets_only`, `test_target=production`, and `enable_external=false` so the workflow verifies secret retrieval without running benchmark suites.
3. Keep version `3` as the active runtime key unless a further rotation is required.

## Rollback Procedure

Known live revision:
- `llmhive-orchestrator-02206-cct`

Known previous ready revision:
- `llmhive-orchestrator-02205-qx5`

One-command backend rollback:

```bash
gcloud run services update-traffic llmhive-orchestrator --region us-east1 --to-revisions llmhive-orchestrator-02205-qx5=100
```

One-command frontend rollback:

```bash
vercel rollback https://llmhive-kvch9npn6-camilo-diazs-projects-84a2ae74.vercel.app --scope camilo-diazs-projects-84a2ae74 --yes
```

## Launch Operations Basics

Verified present:
- Pricing page
- Contact page
- Privacy page
- Terms page
- Vercel analytics wrapper in production layout
- Optional GA and Meta Pixel hooks in layout

Still needs explicit human confirmation before launch:
- Pricing/package details are final
- Support ownership and response path are assigned
- KPI dashboards and alert routing are being watched by named owners
- Launch checklist ownership is assigned, not just documented

## Launch Blockers

P0 blockers before launch:
- Resolve the GitHub workflow secret-fetch gating bug so Workload Identity retrieval of `api-key` is actually exercised and not silently skipped.
- Rotate the previously exposed benchmark API key after Vercel env access is restored.
- Refresh live version/monitoring visibility so `build-info` and KPI checks reflect the running release accurately.

P1 cleanup before publishing claims:
- Keep all benchmark assets on the same locked artifact basis.
- Do not mix `MRR@10` decimals with percentage formatting across tables.

Release scoping note:
- Minimal safe release surface is documented in `artifacts/launch_freeze/minimal_release_surface_20260402.md`.
- Exact clean-branch release commands are documented in `artifacts/launch_freeze/minimal_release_commands_20260402.md`.
- Isolated release-candidate handoff is documented in `artifacts/launch_freeze/minimal_release_handoff_20260402.md`.
- Static benchmark-isolation verifier: `scripts/verify_market_release_isolation.py` (`passed: true`)
- Safe local no-regression gate: `python scripts/run_market_release_gate.py --json` (`passed: true`)
