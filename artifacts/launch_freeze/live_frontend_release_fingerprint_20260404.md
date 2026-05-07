# Live Frontend Release Fingerprint

Date: `2026-04-04`

## Current Production Frontend

- Vercel production deployment id: `dpl_GkJBypfJBTRJ3NJUJcUeH7Xx5y5y`
- Vercel production deployment url: `https://llmhive-mut7l11sb-camilo-diazs-projects-84a2ae74.vercel.app`
- Canonical aliases:
  - `https://www.llmhive.ai`
  - `https://llmhive.vercel.app`

## Current Production Backend

- Cloud Run service: `llmhive-orchestrator`
- Latest ready revision: `llmhive-orchestrator-02209-ckf`
- Image: `gcr.io/llmhive-orchestrator/llmhive-orchestrator:48afd9dd-58fb-47de-bd20-d1d40938eaf5`
- Public health: `https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app/health`

Backend note:
- The backend was not changed during this frontend correction pass.
- No benchmark routing, model selection, cost telemetry, or Cloud Run runtime settings were changed.

## Release Base

- Isolated release worktree: `/Users/camilodiaz/LLMHIVE-market-release-current`
- Base commit used for the release candidate: `c1c136c58122963681f2961ee4dd8a040f62f239`
- Important caveat: this base commit is not itself a sufficient reproduction of the live frontend.
  - A direct rebuild from the base commit previously failed due to a missing `hooks/use-model-registry.ts` type contract fix.
  - The live frontend therefore corresponds to the base commit plus the isolated release delta below.

## Exact Release Delta In Worktree

Files currently changed relative to the base commit in the isolated release worktree:

- `app/(business)/[slug]/page.tsx`
- `app/(marketing)/best-ai-assistant-for/[slug]/page.tsx`
- `app/(marketing)/case-studies/[slug]/page.tsx`
- `app/(marketing)/comparisons/[slug]/page.tsx`
- `app/(marketing)/comparisons/best-ai-assistant-for/[slug]/page.tsx`
- `app/(marketing)/comparisons/industries/[industry]/[tool]/page.tsx`
- `app/(marketing)/comparisons/industries/[slug]/page.tsx`
- `app/(marketing)/comparisons/industries/roles/[slug]/page.tsx`
- `app/(marketing)/help/HelpClient.tsx`
- `app/(marketing)/industries/[slug]/page.tsx`
- `app/(marketing)/landing/page.tsx`
- `app/(marketing)/press/page.tsx`
- `app/(marketing)/use-cases/[slug]/page.tsx`
- `app/api/health/integrations/route.ts`
- `app/business-ops/navigation/page.tsx`
- `app/business-ops/page.tsx`
- `app/llms.txt/route.ts`
- `app/press/media-kit/route.ts`
- `app/press/press-release-long/route.ts`
- `app/press/press-release-wire/route.ts`
- `cloudbuild.yaml`
- `hooks/use-model-registry.ts`
- `package-lock.json`
- `proxy.ts`

## Why These Files Matter

The live frontend currently depends on three correction groups:

1. Dynamic public route compatibility
- The dynamic marketing and business pages above use the Next.js-compatible `params: Promise<...>` handling required by the current production runtime.
- Without these changes, public dynamic pages can fall back to `404` or incorrect `notFound()` behavior.

2. Public route and content safety
- `proxy.ts` contains the broader anonymous allowlist required for launch pages, business/trust pages, `llms.txt`, and `api/health/integrations`.
- The public content files above remove or replace links that would otherwise send anonymous visitors into protected app surfaces.

3. Frontend release/build correctness
- `hooks/use-model-registry.ts` contains the type contract fix needed for the production build to complete.
- `package-lock.json` reflects the dependency lockfile state used by the successful isolated frontend release build.

4. Non-frontend carryover in the worktree
- `cloudbuild.yaml` is also changed relative to the base commit in the isolated release worktree.
- It did not affect the frontend Vercel deploy in this correction pass, but it is part of the full worktree delta and should be tracked separately before any backend release action.

## Verified Live Outcomes

The following were re-verified after the corrected deploy:

- `https://www.llmhive.ai/press` renders publicly.
- `https://www.llmhive.ai/faq` renders publicly.
- `https://www.llmhive.ai/case-studies` renders publicly.
- `https://www.llmhive.ai/comparisons/llmhive-vs-chatgpt` renders publicly.
- `https://www.llmhive.ai/security` renders publicly.
- `https://www.llmhive.ai/help` renders publicly and points to `business-ops` instead of protected billing for the quick-link card.
- `https://www.llmhive.ai/business-ops` renders publicly without protected internal links.
- `https://www.llmhive.ai/business-ops/navigation` renders publicly without protected internal links.
- `https://www.llmhive.ai/api/health/integrations` returns `200` JSON.
- `https://www.llmhive.ai/llms.txt` renders publicly and no longer references protected app pages.

## Safe Operational Guidance

- Treat this artifact as the current frontend source-of-truth fingerprint for launch.
- Do not assume `c1c136c58122963681f2961ee4dd8a040f62f239` alone reproduces the live frontend.
- Before any further frontend deployment, either:
  - create a clean branch/commit that captures exactly this delta, or
  - rebuild a fresh isolated release candidate by replaying only this file set.
- File-level SHA256 source of truth for this live delta:
  - `artifacts/launch_freeze/live_frontend_release_hash_manifest_20260404.txt`
- Patch regeneration pattern from the isolated release worktree:

```bash
git -C /Users/camilodiaz/LLMHIVE-market-release-current diff HEAD -- \
  "app/(business)/[slug]/page.tsx" \
  "app/(marketing)/best-ai-assistant-for/[slug]/page.tsx" \
  "app/(marketing)/case-studies/[slug]/page.tsx" \
  "app/(marketing)/comparisons/[slug]/page.tsx" \
  "app/(marketing)/comparisons/best-ai-assistant-for/[slug]/page.tsx" \
  "app/(marketing)/comparisons/industries/[industry]/[tool]/page.tsx" \
  "app/(marketing)/comparisons/industries/[slug]/page.tsx" \
  "app/(marketing)/comparisons/industries/roles/[slug]/page.tsx" \
  "app/(marketing)/help/HelpClient.tsx" \
  "app/(marketing)/industries/[slug]/page.tsx" \
  "app/(marketing)/landing/page.tsx" \
  "app/(marketing)/press/page.tsx" \
  "app/(marketing)/use-cases/[slug]/page.tsx" \
  "app/api/health/integrations/route.ts" \
  "app/business-ops/navigation/page.tsx" \
  "app/business-ops/page.tsx" \
  "app/llms.txt/route.ts" \
  "app/press/media-kit/route.ts" \
  "app/press/press-release-long/route.ts" \
  "app/press/press-release-wire/route.ts" \
  "hooks/use-model-registry.ts" \
  "package-lock.json" \
  "proxy.ts"
```

## Explicit Non-Changes

- No backend deploy was performed as part of this fingerprinting step.
- No benchmark runs were started.
- No benchmark code, orchestration code, or provider routing logic was modified.
- No benchmark claims or category tables were changed in this step.
