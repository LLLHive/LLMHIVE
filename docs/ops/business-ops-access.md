# Business Ops (management-only)

Business Ops is **not** linked on the marketing site, home, chat header, sidebar, or settings. It is restricted to people who:

1. Can sign in to LLMHive with a company account (Clerk).
2. Know the **shared operations password** issued to the management team.

## URL

- Gate (sign in, then enter password): `https://www.llmhive.ai/business-ops/gate`
- After the cookie is set, the hub and subpages are under `https://www.llmhive.ai/business-ops` (e.g. `/business-ops/navigation`).

## Environment variables (production)

Set in the Vercel project (or your host) **Settings → Environment Variables** for **Production** (and Preview if you want the gate in preview):

| Variable | Purpose |
|----------|---------|
| `BUSINESS_OPS_GATE_PASSWORD` | Shared password managers enter at the gate (rotate periodically). |
| `BUSINESS_OPS_GATE_SECRET` | Server-only secret used to sign the httpOnly session cookie (use a long random string; rotating it invalidates existing sessions). |

If these are **not** set, the gate is **disabled** and `/business-ops` is only protected by normal Clerk auth (useful for local development).

## Operational notes

- The gate cookie is **httpOnly**, **7 days**, `SameSite=Lax`, `Secure` in production.
- To revoke everyone’s access immediately, rotate `BUSINESS_OPS_GATE_SECRET` (and optionally change `BUSINESS_OPS_GATE_PASSWORD`).
- Do **not** put the password in the repo, tickets, or customer-facing docs.
