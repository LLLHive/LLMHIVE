# Benchmark Key Rotation Runbook

Date: `2026-04-02`

## Goal

Rotate the previously exposed benchmark/backend API key with minimal launch risk.

## Current Wiring

Backend:
- Cloud Run env `API_KEY` is sourced from Secret Manager secret `api-key` using `latest`.

Frontend/server routes:
- Vercel server routes use `LLMHIVE_API_KEY` when proxying to the backend.
- This means Vercel and Cloud Run must agree on the same key value during and after rotation.

Known frontend/server routes depending on `LLMHIVE_API_KEY`:
- `app/api/chat/route.ts`
- `app/api/execute/route.ts`
- `app/api/projects/route.ts`
- `app/api/conversations/route.ts`
- `app/api/openrouter/models/route.ts`
- `app/api/openrouter/rankings/route.ts`
- `app/api/billing/subscription/route.ts`
- `app/api/billing/portal/route.ts`
- `app/api/billing/verify-session/route.ts`
- `app/api/billing/cancel/route.ts`
- `app/api/billing/usage/route.ts`

GitHub Actions:
- Scheduled benchmark workflow fetches the same Secret Manager secret `api-key` through Workload Identity.

## Hard Rule

Do not rotate `api-key` in Google Secret Manager until Vercel access is restored and `LLMHIVE_API_KEY` can be updated safely.

If the backend key changes before Vercel is updated, production server routes on the frontend will begin sending the wrong `X-API-Key` header to Cloud Run.

## Safe Rotation Procedure

1. Restore Vercel access.
   - Confirm you can edit production environment variables for the deployed frontend project.
   - Confirm `LLMHIVE_API_KEY` exists in Vercel production env.

2. Generate a new strong key value.
   - Keep the old value available until verification completes.

3. Add a new Secret Manager version for `api-key`.
   - Do not delete the old version yet.

4. Update Vercel production env `LLMHIVE_API_KEY` to the new value.
   - Redeploy the frontend if Vercel does not hot-apply server env changes.

5. Roll a new Cloud Run revision so the backend picks up the new `latest` secret value deterministically.
   - Because the service references `api-key:latest`, a new revision is the safest way to ensure the container actually loads the new value.

6. Verify production manually.
   - `https://www.llmhive.ai/sign-in` still loads.
   - Authenticated app routes still work.
   - Backend chat with the new key returns `200`.
   - Frontend server routes that proxy to backend still work.

7. Verify GitHub Actions secret fetch path.
   - Re-run the scheduled benchmark workflow in a verification-only path or use equivalent secret-fetch validation.
   - Confirm the workflow still fetches `api-key` successfully via Workload Identity.
   - If GCP auth succeeds but the fetch step is skipped, treat that as a workflow bug and do not count it as successful WIF validation.
   - Preferred low-risk path: dispatch `Scheduled Benchmarks` with `mode=secrets_only`, `test_target=production`, and `enable_external=false` so the workflow verifies `api-key` retrieval without executing benchmark suites.

8. Revoke the old key.
   - Only after frontend, backend, and workflow validation all pass.
   - Disable any malformed intermediate versions as well; only the final good version should remain enabled.

## Suggested Verification Checks

Backend direct check:

```bash
curl -sS "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: NEW_KEY" \
  -d '{"prompt":"What is 2 + 2?","model":"auto","tier":"elite"}'
```

Secret fetch check:

```bash
gcloud secrets versions access latest --secret="api-key" --project="llmhive-orchestrator"
```

Cloud Run revision check:

```bash
gcloud run services describe llmhive-orchestrator --region us-east1 --format=json
```

## Current Blocker

The runtime rotation is now executable from this machine because Vercel access has been restored.

Remaining blocker:
- GitHub workflow verification is currently imperfect because several workflows authenticate to Google Cloud successfully but still skip their Secret Manager fetch step.
- Root cause from branch verification: those jobs lacked `id-token: write`, so GitHub never injected OIDC token request variables for `google-github-actions/auth`.
- Until that workflow gating issue is fixed, use direct runtime checks plus explicit GitHub secret alignment as mitigation, and treat end-to-end WIF validation as still pending.
