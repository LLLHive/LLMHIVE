# Version 2.0 — deferred features

This document tracks experiences that are **intentionally out of scope** for the current production deployment. Use it when planning the next major release.

## Discover hub

- **Production behavior:** Requests to `/discover` and `/discover/*` **permanently redirect (308)** to `/` via `next.config.mjs`. The old route and cards are **not** served.
- **Implementation (parked):** `components/v2-deferred/discover-page-full-impl.tsx` (`DiscoverPageFullImpl`). Not imported by any route.

## How to ship Discover in a future release

1. Add an `app/discover/page.tsx` (and layout/metadata as needed) that uses `DiscoverPageFullImpl` or merged code.
2. **Remove** the `/discover` entries from `redirects()` in `next.config.mjs` so the page can render.
3. Re-add `ROUTES.DISCOVER` in `lib/routes.ts`, sidebar/footer links, and `/discover` in `proxy.ts` public routes if required.
4. Update this document.

## Backlog

| Feature | Status | Code / notes |
|--------|--------|----------------|
| **Discover hub** | Deferred | See above. |
| *(add rows as you park other pages)* | | |
