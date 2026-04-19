# Deferred UI (Version 2.0)

Code parked here is **not** imported by production routes. In production, **`/discover` redirects to `/`** (see `next.config.mjs`). Track re-integration in **`docs/version-2/README.md`**.

- **`discover-page-full-impl.tsx`** — full Discover hub (cards + sheets); wire into a new `app/discover/page.tsx` when removing the redirect.
