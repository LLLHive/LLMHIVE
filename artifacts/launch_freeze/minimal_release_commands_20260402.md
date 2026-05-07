# Minimal Release Commands

Date: `2026-04-02`

## Goal

Prepare and deploy only the minimal runtime fixes identified in this launch-readiness pass:
- `proxy.ts`
- `cloudbuild.yaml`

This procedure avoids deploying the broader dirty working tree.

## Preconditions

- Work from a clean branch based on `release/eliteplus-certified`.
- Do not merge or deploy the full current working tree.
- If you only need the user-facing hostname/auth fix, `proxy.ts` is the critical file.
- Include `cloudbuild.yaml` only if Cloud Build is still a real production deploy path.

## Safe Git Procedure

From the repo root:

```bash
git switch release/eliteplus-certified
git pull --ff-only origin release/eliteplus-certified
git switch -c release/minimal-launch-fix-20260402
```

Bring over only the minimal runtime files from the working branch:

```bash
git checkout eliteplus-decision-grade-bench-fixes -- proxy.ts cloudbuild.yaml
```

Confirm that only those files changed:

```bash
git status --short
git diff --stat
git diff -- proxy.ts cloudbuild.yaml
```

Expected changed files:
- `proxy.ts`
- `cloudbuild.yaml`

If any other file appears, stop and do not deploy.

## Recommended Validation Before Deploy

Run the safe no-regression gate first:

```bash
python scripts/run_market_release_gate.py --json
```

Expected outcome:
- `passed: true`
- focused release tests pass
- benchmark isolation passes

Frontend hostname fix:

```bash
git diff -- proxy.ts
```

Cloud Build metadata fix:

```bash
git diff -- cloudbuild.yaml
```

## Deployment Guidance

### If you are deploying the frontend fix

Deploy the branch/path you normally use for the frontend so the new `proxy.ts` is active.

Post-deploy verification:

```bash
python scripts/verify_minimal_launch_release.py --skip-backend
```

Expected outcome:
- `https://llmhive.vercel.app/...` redirects to `https://www.llmhive.ai/...`
- `https://www.llmhive.ai/sign-in` renders the Clerk form

### If you are deploying Cloud Run via Cloud Build

After the next Cloud Build-based deploy, verify:

```bash
python scripts/verify_minimal_launch_release.py --skip-frontend
```

Expected outcome:
- `commit` is not `unknown`
- `build_time` reflects the deploy

## Optional Commit Procedure

Only if you want the minimal fix committed on the clean release branch:

```bash
git add proxy.ts cloudbuild.yaml
git commit -m "fix: redirect vercel hostname and restore build metadata"
```

## Stop Conditions

Stop immediately if:
- more than the two expected runtime files are staged
- the deploy path tries to include unrelated branch changes
- Vercel or Cloud Run deployment tooling does not target the clean release branch

## Follow-Up After Minimal Deploy

1. Re-run the public smoke checks on `www.llmhive.ai`
2. Confirm `llmhive.vercel.app` no longer exposes a broken Clerk flow
3. Only then proceed to benchmark key rotation using:
   - `artifacts/launch_freeze/benchmark_key_rotation_runbook_20260402.md`
