# Minimal Release Surface

Date: `2026-04-02`

## Purpose

Define the smallest safe set of changes to move toward launch readiness without deploying the broader dirty working tree.

## Runtime-Critical Changes

These are the only code/config changes identified in this pass that directly affect launch behavior:

1. `proxy.ts`
   - Redirects `llmhive.vercel.app` to `https://www.llmhive.ai` before Clerk auth runs.
   - Fixes the broken auth flow on the public Vercel hostname caused by Clerk `origin_invalid`.

2. `cloudbuild.yaml`
   - Adds `BUILD_COMMIT` and `BUILD_TIME` to the Cloud Run deploy env.
   - Adds `INTERNAL_ADMIN_OVERRIDE_KEY` parity to the fallback Cloud Build deploy path.
   - Improves `/build-info` and internal monitoring readiness for future Cloud Build-based deploys.

## Documentation-Only Changes

These do not need to be part of a runtime deployment:

- `artifacts/category_gap_table.md`
- `artifacts/category_gap_table_marketing.md`
- `artifacts/launch_freeze/launch_readiness_audit_20260402.md`
- `artifacts/launch_freeze/benchmark_key_rotation_runbook_20260402.md`

## Safest Deployment Strategy

Because the current working tree contains many unrelated changes, do not deploy the whole branch directly.

Safest path:
1. Start from a clean release-oriented branch or the known release branch.
2. Bring over only:
   - `proxy.ts`
   - `cloudbuild.yaml` (if you still use Cloud Build directly for production deploys)
3. Deploy that minimal set.
4. Verify:
   - `https://llmhive.vercel.app` redirects to `https://www.llmhive.ai`
   - `https://www.llmhive.ai/sign-in` still renders Clerk correctly
   - `/build-info` returns a non-unknown commit after the next deploy path that carries build metadata

## Notes

- If production deploys are done exclusively through `.github/workflows/ci-cd.yaml`, the immediate user-facing fix is `proxy.ts`.
- `cloudbuild.yaml` still matters if Cloud Build remains a possible production path, because the currently live service appears to have been deployed without `BUILD_COMMIT` and `BUILD_TIME`.

## Benchmark Isolation

Static isolation check:
- `python scripts/verify_market_release_isolation.py`

Current result:
- `passed: true`
- overlap with benchmark-critical files: none

Protected benchmark-critical files:
- `scripts/run_category_benchmarks.py`
- `scripts/eval_mtbench.py`
- `scripts/eval_toolbench.py`
- `llmhive/src/llmhive/app/benchmarks/runner_llmhive.py`
- `llmhive/src/llmhive/app/orchestration/benchmark_config.py`
- `tests/benchmarks/test_runner_llmhive_contract.py`
- `tests/test_benchmark_prompt_guidance.py`
