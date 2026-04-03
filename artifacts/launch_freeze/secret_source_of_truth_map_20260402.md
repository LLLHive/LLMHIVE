# Secret Source Of Truth Map

Date: `2026-04-02`

## Goal

Define which platform owns which class of secret so launch operations do not drift across Google Cloud, Vercel, and GitHub.

## Current Secret Planes

### Google Secret Manager

Primary runtime source of truth for backend secrets used by Cloud Run.

Examples currently present:
- `api-key`
- `openai-api-key`
- `anthropic-api-key`
- `grok-api-key`
- `gemini-api-key`
- `deepseek-api-key`
- `open-router-key`
- `pinecone-api-key`
- `pinecone-host-*`
- `stripe-*`
- `clerk-secret-key`
- `slack-webhook-url`
- `resend-api-key`
- `llmhive-internal-admin-override-key`

### Vercel Environment Variables

Source of truth for frontend/server-route secrets and frontend-facing configuration that Vercel must know at runtime.

Production env names currently present:
- `LLMHIVE_API_KEY`
- `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_CLERK_SIGN_IN_URL`
- `NEXT_PUBLIC_CLERK_SIGN_UP_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `ORCHESTRATOR_API_BASE_URL`
- `AUTH_SECRET`
- `GITHUB_SECRET`
- `GITHUB_ID`

### GitHub Secrets

Source of truth for workflow authentication and workflow-only fallback values.

Repo secrets currently present:
- `API_KEY`
- `CLERK_SECRET_KEY`
- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `GEMINI_API_KEY`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`

## Ownership Rules

### Google should own

All backend/runtime secrets that Cloud Run loads directly:
- provider API keys
- `API_KEY`
- Pinecone secrets
- Stripe server secrets
- internal admin keys
- webhook URLs
- resend/slack/server-only integrations

Rule:
- If Cloud Run needs it, Google Secret Manager is the canonical source.

### Vercel should own

Only values required by the Next.js frontend or Vercel server routes:
- `LLMHIVE_API_KEY`
- frontend auth config
- frontend publishable keys
- backend base URLs
- server-route integration config that only Vercel executes

Rule:
- If Next.js server routes need it at request time, Vercel must have a copy.
- When the secret mirrors a Google runtime secret, rotation must update Vercel immediately after Google.

### GitHub should own

Workflow auth and workflow-only config:
- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`
- `GCP_SA_KEY` only if still required as fallback

Conditional fallback:
- `API_KEY` exists now because some workflows still reference `secrets.API_KEY`.

Rule:
- GitHub should not be the primary source of runtime secrets when Workload Identity + Secret Manager can fetch them.
- Keep a GitHub copy only when a workflow still depends on it or while migrating off legacy secret references.

## Current Drift Risks

### Intentional mirrored secret

`API_KEY` / `LLMHIVE_API_KEY`
- Google Secret Manager `api-key` is the backend source.
- Vercel `LLMHIVE_API_KEY` must match so server routes can proxy to backend.
- GitHub `API_KEY` currently exists as workflow compatibility support.

### Legacy GitHub secret references

`ci-cd.yaml` still references `secrets.API_KEY`.

Impact:
- Even after runtime rotation was completed safely, workflows may still consume GitHub-hosted values unless migrated fully to Secret Manager fetches.

### Workflow fetch gating

Several workflows authenticate to Google Cloud successfully but still skip their Secret Manager fetch step during GitHub execution.

Impact:
- Runtime is healthy.
- End-to-end WIF-based secret retrieval is not yet proven by workflow execution.

## Recommended End State

1. Keep Google Secret Manager as the canonical backend secret store.
2. Keep Vercel env only for frontend/server-route secrets and mirrored backend auth where required.
3. Reduce GitHub secrets to workflow auth plus temporary compatibility fallbacks.
4. Migrate workflows away from `secrets.API_KEY` where possible and prefer:
   - auth to Google
   - fetch from Secret Manager
   - fail clearly if fetch did not run

## Immediate Next Steps

1. Commit and push the workflow-only condition fix so GitHub runs the corrected workflow definitions.
2. Re-run a workflow that fetches `api-key` from Secret Manager and confirm the fetch step actually executes.
3. Decide whether to keep `API_KEY` in GitHub as a temporary fallback or remove that dependency from `ci-cd.yaml`.
4. Record final ownership for pricing, support, and dashboard watchers before launch.
