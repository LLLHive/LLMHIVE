# UI launch readiness report

**Date:** 2026-04-20  
**Scope:** Automated UI audit (`npm run ui:audit`) plus interpretation for production launch.

---

## Executive summary

| Area | Status | Notes |
|------|--------|--------|
| Audit suite | **20/20 tests passed** | Full `tests/e2e/audit/ui-audit.spec.ts` run completed successfully |
| Route smoke (/, /models, /orchestration, /settings) | **Pass** | No visible error banners on load (see audit rules) |
| Rankings / category parity (mocked OpenRouter) | **Pass** | Categories and ordering checks passed under mocks |
| Click crawler (safe clicks) | **Pass** | No hard failures; some clicks skipped by design |
| Heuristic “issues” file | **2 items** | See below—not all are product bugs; some are audit expectations vs. current UX |

**Bottom line:** The automated suite does not block launch on test failures. Before go-live, treat the **two heuristic findings** as “verify or fix,” and complete the **manual / non-UI** checklist at the end.

---

## Automated run (reference)

- **Command:** `npm run ui:audit` (Playwright, Chromium, ~3+ minutes)
- **Artifacts:** `docs/ui_audit/reports/latest/` (gitignored; regenerate locally after each run)
- **Caveat:** `test.afterAll` runs per worker; the last worker’s summary may overwrite `issues.json` / `report.md`. For a single source of truth, re-run `npm run ui:audit:quick` after a full run, or run the full audit with **one worker**:  
  `npx playwright test tests/e2e/audit/ui-audit.spec.ts --project=chromium --workers=1`

---

## Issues flagged for launch (historical note)

Earlier runs recorded soft **P0/P1** items (`chat_no_input`, `chat_no_categories_dropdown`) when the audit looked for the model toolbar on the **marketing home** screen (toolbar only exists after **Start Chatting**). **Resolved in automation:** the chat UI tests now call `openChatFromHome()`, use `data-testid="chat-composer"` on the main `Textarea`, `data-testid="model-selector-trigger"` on the Models control, and assert **Browse by Category** plus **Programming** in the open menu. Re-run `npm run ui:audit` to refresh `issues.json`; failures should reflect real regressions rather than selector mistakes.

---

## Console noise (last run snapshot)

The generated `report.md` listed **browser console lines** such as “Failed to load resource: 400 / 401” on `/`, `/models`, and `/orchestration`. Separately, the audit’s **network failure** list can filter expected **unauthenticated billing** and **Clerk** responses in test environments.

**Interpretation for launch:**

- **401 / billing** when not signed in is often **expected** in dev/staging.
- **400** responses may be **Clerk**, analytics, or missing dev keys—confirm in **Network** tab on a staging build with production-like env vars.
- Do **not** treat raw console line count as a launch gate without triage on a **staging** URL with real keys.

---

## Accessibility (basic automated checks)

Latest run: **no `a11yViolations` entries** in the audit collector for the basic checks (images with `alt`, buttons with names, inputs with labels).

**Gap:** This is not WCAG 2.2 AA coverage. Plan at least one pass with keyboard-only navigation and a screen reader on core flows (new chat, send message, settings, billing link).

---

## What this audit does *not* cover (do before launch)

These are outside the current Playwright UI audit scope:

1. **Security / auth:** Session expiry, protected routes, API authorization.
2. **Payments:** Stripe webhooks, plan changes, receipt emails.
3. **Performance:** LCP, TTI, bundle size, API latency under load.
4. **SEO / legal:** Privacy policy, terms, cookie consent if required.
5. **Cross-browser:** Suite defaults to Chromium; spot-check Safari and mobile Safari.
6. **Production config:** Environment variables, Clerk production instance, OpenRouter keys, error monitoring (e.g. Sentry).

---

## Suggested order of work

1. **Manual smoke:** New chat → message send → model change → open Settings (15 minutes).  
2. **Resolve or document** the two heuristic items (composer visibility + category UX).  
3. **Staging pass** with production-like env: eliminate unexplained 400s on critical APIs.  
4. **Accessibility:** One dedicated keyboard + screen-reader pass on the main chat path.  
5. **Re-run** `npm run ui:audit` and optionally `npm run test:e2e` before tagging a release.

---

_Report produced from LLMHive UI audit tooling and codebase review. Regenerate machine output with `npm run ui:audit`._
