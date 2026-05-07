# Workflow Safeguards PR Handoff

Date: `2026-04-05`

## Purpose

This note identifies the correct launch workflow PR to review and merge, and records which PR should not be used.

## Correct PR

- Clean replacement PR: `#169`
- URL: `https://github.com/LLLHive/LLMHIVE/pull/169`

Why this is the correct PR:

- based directly on current `main`
- exactly one commit
- only six workflow files changed
- no frontend runtime code
- no backend runtime code
- no benchmark logic changes
- no pricing changes

Files in `#169`:

- `.github/workflows/auto-restore-critical-files.yaml`
- `.github/workflows/modeldb_refresh.yml`
- `.github/workflows/scheduled-benchmarks.yml`
- `.github/workflows/secure-history.yml`
- `.github/workflows/smoke-tests.yml`
- `.github/workflows/weekly-improvement.yml`

## PR That Should Not Be Merged

- Superseded PR: `#168`
- URL: `https://github.com/LLLHive/LLMHIVE/pull/168`

Why `#168` should not be merged:

- contains older unrelated commits
- contains unrelated files and historical artifacts
- is not a clean launch-safe representation of the workflow-only safeguard changes

## Current Merge Blockers On `#169`

- branch protection requires review
- one CI job is red

Important context:

- the failing CI job is part of the same baseline-red `CI/CD Pipeline` pattern already seen on `main`
- the failure is in app/provider tests, not in the six workflow files
- current evidence does not indicate the workflow-only PR introduced a new product/runtime regression

## Recommended Reviewer Decision Path

1. Review `#169` only.
2. Confirm the file list contains only the six workflow files above.
3. Confirm no runtime/product logic is included.
4. Approve `#169`.
5. Merge `#169`.
6. Leave `#168` closed or unmerged as superseded.

## Why This Matters For Launch

Merging `#169` is the cleanest way to make the launch-period automation posture match the already-frozen production posture:

- automation routes to PR branches instead of mutating `main`
- smoke workflow preserves better Cloud Run failure diagnostics
- scheduled benchmark workflow keeps the benchmark API key wiring needed for production HTTP runs
- secure history remains manual-only

This is the safest remaining repo-side change because it does not alter serving runtime behavior.
