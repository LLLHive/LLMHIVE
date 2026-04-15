# Final Go-To-Market Plan

Date: `2026-04-04`

## Executive Summary

LLMHive is close to launch-ready, but launch should proceed only under a strict production freeze.

What is already true:
- production auto-drift has been stopped remotely
- `main` is now protected
- Cloud Build auto-deploy from `main` is disabled
- Vercel is disconnected from Git
- live frontend and backend source attribution have been mapped

What is still required before launch:
- commit and push the workflow-only safety fixes prepared locally
- re-run the narrow launch workflows manually from a controlled branch
- make a final decision on the intermittent slow `/v1/chat` outlier
- freeze pricing, benchmark claims, and launch messaging to one approved artifact basis
- assign named owners for support, dashboards, and incident response

Guiding rule:
- no runtime, routing, benchmark, or pricing logic changes unless they fix a proven launch blocker

## Current Freeze State

### Production controls already applied remotely

- GitHub `main` branch protection is active
- Cloud Build trigger `llmhive` on `main` is disabled
- Vercel project `llmhive` is disconnected from Git

### Local-only workflow hardening prepared but not yet pushed

- `.github/workflows/modeldb_refresh.yml`
- `.github/workflows/weekly-improvement.yml`
- `.github/workflows/auto-restore-critical-files.yaml`
- `.github/workflows/secure-history.yml`
- `.github/workflows/scheduled-benchmarks.yml`
- `.github/workflows/smoke-tests.yml`

These changes are workflow-only. They do not change product runtime behavior, gateway settings, or benchmark logic.

## Locked Claim Basis

Use one approved benchmark basis across investor, press, website, and internal launch materials.

Current locked basis:
- Free certification: `benchmark_reports/category_benchmarks_free_20260331.json`
- Elite certification: `benchmark_reports/category_benchmarks_elite_20260401.json`
- Leader references: `benchmark_configs/category_leaders_llmhive.json`

Claim rules:
- do not mix benchmark bases across surfaces
- keep `RAG` in native `MRR@10` form
- do not describe dialogue cost telemetry as confirmed zero-spend unless specifically re-certified
- do not rerun broad certification benchmarks unless runtime behavior changes

## Live Production Identity

### Frontend

- live frontend commit: `f0e67ab29ac1ebcccaa18822f1d66aad2a9b818b`
- current production alias: `https://www.llmhive.ai`
- production deploy was previously overwritten by the scheduled bot commit from `main`

### Backend

- Cloud Run service: `llmhive-orchestrator`
- live backend revision: `llmhive-orchestrator-02210-mm7`
- live backend source commit: `f0e67ab29ac1ebcccaa18822f1d66aad2a9b818b`

Important note:
- backend runtime `BUILD_COMMIT` metadata is not currently trustworthy as source-of-truth provenance
- trust the Cloud Build revision/build mapping instead of the env var

## Known Launch Risks

### P0: must be addressed before launch

1. Workflow-only safety fixes are not yet pushed.
   - If left uncommitted, scheduled GitHub automation may fail noisily against protected `main`.

2. Intermittent slow `/v1/chat` path is not fully closed.
   - Observed real request around `68.5s`
   - neighboring requests in same window were roughly `3s` to `16s`
   - logs point to provider retry/fallback behavior, not a constant gateway outage

3. Pricing and package freeze must be explicit.
   - launch should not proceed with ambiguous packaging or changing tier language

4. Named owners for support and monitoring must be explicit.
   - launch-week accountability cannot remain implicit

### P1: should be done before public push

1. Re-verify public marketing and trust surfaces on the live site.
2. Confirm all market-facing tables align to the locked benchmark basis.
3. Confirm support routing and customer communications templates.
4. Confirm launch checklist ownership.

## No-Regression Guardrails

Allowed before launch:
- workflow-only fixes
- documentation and launch artifacts
- operational lock-downs
- targeted manual smoke verification

Not allowed before launch unless a blocker is proven:
- orchestration routing changes
- provider selection changes
- benchmark scoring changes
- runtime scaling or concurrency changes
- frontend content/routing changes outside a verified blocker
- pricing logic changes without explicit approval

## Required Workstreams

### 1. Launch Control

Goal:
- ensure only intentional releases can reach production

Actions:
1. Commit and push the workflow-only safety fixes.
2. Keep `main` protected.
3. Keep Cloud Build trigger disabled until an intentional release path is chosen.
4. Keep Vercel disconnected from Git until post-launch automation policy is redesigned.

Success condition:
- no scheduled job can mutate or redeploy production automatically

### 2. Technical Readiness

Goal:
- prove current frozen production is acceptable for launch

Actions:
1. Manually rerun `Production Smoke Tests` from a controlled branch after workflow fixes land.
2. Manually rerun `Scheduled Benchmarks` in critical mode from the same controlled branch.
3. Use the smoke diagnostics artifact to inspect any future slow `/v1/chat` failures.
4. Decide whether the latency outlier is:
   - rare and launch-acceptable, or
   - a real blocker requiring a targeted fix

Success condition:
- smoke path is reliable enough for launch
- no new auth or workflow drift

### 3. Benchmark And Messaging Freeze

Goal:
- ensure every external claim is defensible and internally consistent

Actions:
1. Freeze all category tables to the approved artifact basis.
2. Freeze wording for Free, Elite, and Elite+ positioning.
3. Keep one owner responsible for benchmark-source-of-truth decisions.
4. Do not generate fresh broad benchmark claims unless code affecting runtime behavior changes.

Success condition:
- investor, press, website, and internal materials all match one approved basis

### 4. Commercial Readiness

Goal:
- remove ambiguity from what customers will buy and what they should expect

Actions:
1. Freeze pricing and package names.
2. Freeze upgrade path language.
3. Confirm billing and checkout surfaces are working.
4. Confirm Clerk/customer-account behavior is working.

Success condition:
- package definitions and payment paths are stable and understood

### 5. Support And Monitoring

Goal:
- ensure launch-week issues are seen and handled immediately

Actions:
1. Assign named owner for support queue.
2. Assign named owner for production monitoring.
3. Assign named approver for launch/no-launch call.
4. Confirm dashboards/alerts are being watched.
5. Confirm incident response path and escalation path.

Success condition:
- no launch-critical alert or ticket goes ownerless

## Launch Readiness Decision Gate

Launch may proceed only if all are true:

- workflow-only safety fixes are committed and pushed
- manual smoke rerun is acceptable
- manual critical benchmark rerun is acceptable
- pricing/package freeze is explicit
- launch asset basis is frozen
- support and dashboard owners are assigned
- rollback commands and last-known-good references are documented

If any of the above is false, delay launch rather than making broad late changes.

## Recommended Execution Order

1. Commit and push the workflow-only fixes only.
2. Manually rerun:
   - `Production Smoke Tests`
   - `Scheduled Benchmarks` in critical mode
3. Review the latency evidence from those reruns.
4. Decide whether the `/v1/chat` outlier is launch-acceptable.
5. Freeze pricing, package wording, and market-facing benchmark assets.
6. Confirm support and alert ownership.
7. Launch with no additional runtime changes.

## Launch Day Checklist

1. Confirm active frontend identity.
2. Confirm active backend revision.
3. Confirm no unauthorized production automation is enabled.
4. Run targeted smoke only.
5. Confirm public pages, auth entry, chat path, and billing basics.
6. Confirm support channel is staffed.
7. Confirm dashboards and alerts are active.
8. Publish launch assets.

## Rollback Philosophy

Use rollback only for a verified production issue, not for launch-day experimentation.

Rollback should always prefer:
1. known-good deployment/revision
2. minimal scope
3. no benchmark or routing changes bundled in

## Post-Launch Week 1

Do not use production for V2 experimentation.

Move all non-blocking improvements to a separate post-launch track:
- latency reduction
- routing improvements
- benchmark optimization
- packaging iteration
- UX improvements

Capture and triage:
- latency outliers
- support pain points
- conversion friction
- billing issues
- benchmark expectation mismatches

## Recommended Immediate Next Step

Next safest action:
- create one isolated workflow-only commit containing the six workflow files listed above, and push that branch for controlled manual reruns

Reason:
- this reduces launch risk without changing runtime behavior, gateway settings, or benchmark performance
