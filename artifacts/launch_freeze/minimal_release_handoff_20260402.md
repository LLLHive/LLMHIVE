# Minimal Release Handoff

Date: `2026-04-02`

## Release Candidate Identity

Isolated worktree:
- `/Users/camilodiaz/LLMHIVE-market-release-current`

Release branch:
- `release/minimal-launch-fix-from-current-20260402`

Source commit:
- `c1c136c58122963681f2961ee4dd8a040f62f239`

Candidate state:
- clean worktree created from the current committed benchmark-prep SHA
- backend deploy completed successfully via Cloud Build `b9c27bf7-c825-485b-a914-e527b4dfa029`
- live backend revision is now `llmhive-orchestrator-02204-lzb`
- frontend deploy completed successfully via Vercel production deployment `https://llmhive-3cc5fuma6-camilo-diazs-projects-84a2ae74.vercel.app`
- a pre-existing TypeScript contract issue in `hooks/use-model-registry.ts` had to be fixed before the frontend deploy would build
- the older candidate at `/Users/camilodiaz/LLMHIVE-market-release` is superseded and should not be deployed

## Runtime Scope

This release candidate contains only:
- `proxy.ts`
- `cloudbuild.yaml`
- `hooks/use-model-registry.ts` (required to fix a pre-existing frontend build break that blocked the safe deploy)

Benchmark overlap check:
- `passed: true`
- overlap with benchmark-critical files: none

## Why This Is Safe

- The release candidate was prepared in an isolated worktree, not in the main dirty branch.
- It was recut from the current committed benchmark-prep code line instead of from the older `release/eliteplus-certified` branch.
- The runtime-only deploy path stayed isolated from benchmark-critical files.
- Benchmark-critical files are unchanged relative to the source commit.
- The main working tree remains untouched.

## Intended Effects

1. `proxy.ts`
   - Redirect `https://llmhive.vercel.app` traffic to `https://www.llmhive.ai` before Clerk auth runs.

2. `cloudbuild.yaml`
   - Ensure Cloud Build-based deploys publish `BUILD_COMMIT`
   - Ensure Cloud Build-based deploys publish `BUILD_TIME`
   - Add `INTERNAL_ADMIN_OVERRIDE_KEY` parity to the fallback deploy path
   - Status: live and verified on production backend

3. `hooks/use-model-registry.ts`
   - Restore the TypeScript contract so the frontend production build succeeds
   - Status: live via the successful retry Vercel deploy

## Recommended Live-Change Sequence

1. Review the isolated release candidate
2. Deploy from the isolated release branch/worktree only
3. Run:

```bash
python scripts/verify_minimal_launch_release.py --json
```

4. Confirm expected movement:
- `vercel_redirect` -> PASS
- `canonical_sign_in` -> PASS
- `backend_health` -> PASS
- `build_info` -> PASS if backend was redeployed through the metadata-carrying path

5. Only after that, proceed to benchmark key rotation using:
- `artifacts/launch_freeze/benchmark_key_rotation_runbook_20260402.md`

## Current State

- Backend deployment from the safe isolated worktree succeeded.
- Backend verification passed for `health`, `build_info`, and `launch_kpis`.
- Frontend deployment from the safe isolated worktree succeeded.
- Frontend verification passed for `vercel_redirect` and `canonical_sign_in`.

## Explicit Non-Goals

- No new benchmark runs
- No orchestration tuning
- No routing changes affecting benchmark performance
- No deployment from the main dirty branch
