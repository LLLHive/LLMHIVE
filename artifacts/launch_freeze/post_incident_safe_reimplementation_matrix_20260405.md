# Post-Incident Safe Reimplementation Matrix

Date: `2026-04-05`

## Purpose

This document does three things:

1. states plainly what caused the production drift incident
2. records the controls now preventing the same failure chain
3. separates changes into:
   - changes that can be reimplemented with effectively zero runtime risk
   - changes that may still be valuable, but cannot honestly be labeled `100% no-regression`

## What I Did Wrong

The production drift chain happened because I fixed launch workflows before fully closing the production automation path.

Exact failure pattern:

1. `main` was still writable by automation when I was working launch controls.
2. A scheduled workflow wrote bot commit `f0e67ab` to `main`.
3. That commit triggered both Vercel auto-deploy and the Cloud Build trigger watching `main`.
4. The backend rebuilt from a non-reproducible dependency basis.
5. The new image served the same feature set but drifted in response format on benchmark-sensitive prompts.

Important clarification:

- the benchmark drop was not traced to a deliberate runtime logic change in benchmark files
- the mistake was leaving the automation and rebuild path open long enough for an unintended deploy to happen

## Controls Now Blocking A Repeat

Remote controls verified after the incident:

- GitHub `main` branch protection is active with required review and admin enforcement
- Cloud Build trigger `llmhive` is still `disabled: true`
- Vercel project inspection no longer shows an attached Git repository section
- backend production traffic has been restored to certified revision `llmhive-orchestrator-02203-grk`

Repo-side controls added in this step:

- `scripts/verify_launch_automation_guards.py`
- `tests/test_launch_automation_guards.py`

These static checks verify that:

- recurring automation routes changes to automation branches plus PRs
- recurring automation does not push directly to `main`
- `secure-history.yml` remains manual-only
- `scheduled-benchmarks.yml` continues exporting both `API_KEY` and `LLMHIVE_API_KEY`
- `smoke-tests.yml` continues capturing Cloud Run latency diagnostics

## Changes That Are Safe To Reimplement With 100% Runtime Safety

These changes are safe because they do not alter serving code paths, model selection, benchmark scoring, pricing, scaling, or production deployment behavior.

### A. Operational controls

- keep GitHub `main` protected
- keep Cloud Build auto-deploy trigger disabled until an intentional release path is chosen
- keep Vercel disconnected from Git until post-launch automation is redesigned
- keep production pinned to the certified backend revision unless a controlled release is approved

Why this is safe:

- these controls reduce unauthorized drift
- they do not modify live request handling

### B. Workflow-only safety fixes

- route `modeldb_refresh.yml` commits to `automation/modeldb-refresh` and open/update a PR
- route `weekly-improvement.yml` commits to `automation/weekly-improvement` and open/update a PR
- route `auto-restore-critical-files.yaml` commits to `automation/restore-critical-files` and open/update a PR
- keep `secure-history.yml` manual-only
- keep `scheduled-benchmarks.yml` exporting both `API_KEY` and `LLMHIVE_API_KEY`
- keep `smoke-tests.yml` failure diagnostics for Cloud Run `/v1/chat`

Why this is safe:

- these changes affect GitHub automation behavior only
- they do not change frontend or backend runtime
- they do not alter benchmark implementation or live routing

### C. Static verification and documentation

- `scripts/verify_market_release_isolation.py`
- `tests/test_market_release_isolation.py`
- `scripts/verify_launch_automation_guards.py`
- `tests/test_launch_automation_guards.py`
- launch freeze artifacts documenting live identities, rollback basis, workflow fixes, and claim basis

Why this is safe:

- these are read/verify/document paths
- they add visibility and enforcement without changing production behavior

## Improvements Made After The Incident

Below is the comprehensive post-incident improvement inventory, classified by safety level.

### Safe to keep or reapply with effectively zero runtime risk

- GitHub `main` protection
- Cloud Build trigger disablement
- Vercel Git disconnect
- workflow PR-routing changes
- secret-fetch workflow fix for benchmark jobs
- smoke failure diagnostics artifact capture
- launch fingerprint artifacts
- source-of-truth launch plan artifacts
- static verification scripts and tests for launch isolation and automation guards

### Valuable, but not honest to label `100% no-regression`

These items may be correct and useful, but they touch runtime, frontend behavior, release composition, or future build behavior. They should not be described as `100% assurance` items.

- any backend rebuild reproducibility hardening
  - examples: pinning Python dependencies, lockfiles, changing Docker or Cloud Build install behavior
- any Cloud Run runtime setting changes
  - examples: scaling, concurrency, timeout, min instances
- any backend code changes related to answer formatting, telemetry, routing, or provider fallback
- any benchmark harness or scorer changes
- any frontend route, content, or middleware changes
- any release recut that bundles runtime files such as `cloudbuild.yaml`

Why these are excluded from the `100%` bucket:

- they can change what code or dependencies actually serve traffic
- they can affect latency, routing, formatting, or benchmark outcomes
- they require targeted validation, not blind reapplication

## Frontend Fixes From The Launch Recovery

These changes likely remain necessary for the frontend, but they are not `100% no-risk` reimplementation items because they affect public app behavior.

Examples:

- dynamic marketing route compatibility fixes
- `proxy.ts` anonymous allowlist expansion
- public content link corrections
- `app/api/health/integrations/route.ts` simplification
- `hooks/use-model-registry.ts` build contract fix

Recommended handling:

- treat the existing frontend fingerprint artifact as source of truth
- replay only from the fingerprinted file set when an intentional frontend release is required
- do not reapply ad hoc from memory

## Backend Reproducibility Hardening

This remains the right next technical project, but it is not a `100% no-regression` reimplementation item.

Desired direction:

- pin backend dependencies
- make future builds reproducible
- ensure future deploy provenance is traceable from commit to image to revision

Why it should be done separately:

- it changes future build outputs
- it needs isolated validation before any deploy
- it should happen on a branch, not directly on launch production

## Recommended No-Regressions Order

If the goal is to improve safety without risking benchmark or runtime behavior, the safe order is:

1. keep the remote controls active
2. keep the workflow-only PR-routing fixes
3. keep the benchmark secret-fetch and smoke-diagnostics workflow fixes
4. keep the static verification scripts and tests
5. keep the launch freeze artifacts current
6. defer reproducible-build changes to an isolated branch with validation

## Bottom Line

The only changes I can honestly classify as `100% safe to reimplement without affecting production performance or behavior` are:

- remote operational lock-downs
- workflow-only automation safety fixes
- static verification scripts/tests
- documentation and launch-source-of-truth artifacts

Everything else that touches runtime code, build resolution, frontend behavior, or benchmark logic should be treated as `high-confidence only after validation`, not `100% guaranteed`.
