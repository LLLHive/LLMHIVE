# /v1/chat latency — launch decision

Date: `2026-05-18`  
Status: **Launch-acceptable with monitoring**

## Observation (pre-freeze)

- One production outlier near **68.5s** in a window where neighboring `/v1/chat` requests were **~3–16s**.
- Cloud Run logs indicated **provider retry / fallback**, not a steady gateway outage.

## Launch decision

| Policy | Value |
|--------|--------|
| Smoke request timeout | `60s` (`SMOKE_TIMEOUT`) |
| Smoke chat latency budget | `55s` (`SMOKE_CHAT_MAX_MS`) — fails smoke if exceeded on simple chat |
| Launch SLO (informal) | p50 &lt; 15s, p95 &lt; 45s for simple smoke prompt; investigate any single request &gt; 55s |
| Outlier handling | Do **not** block launch on a one-off 68s event if smoke passes on rerun; treat repeat &gt;55s as regression |

## What we did (no runtime routing change)

- Smoke tests record chat latency and assert the **55s** budget on successful simple chat (`tests/smoke/test_production.py`).
- Failed smoke runs upload Cloud Run `/v1/chat` latency diagnostics (`.github/workflows/smoke-tests.yml`).

## What we did not change (avoid regressions)

- No orchestrator provider-chain reordering.
- No benchmark or pricing logic changes.
- No Cloud Run timeout/concurrency changes in this workstream.

## If smoke fails on latency

1. Download the `smoke-diagnostics` artifact from the failed workflow run.
2. Inspect `cloud_run_post_summary.txt` for slow `/v1/chat` rows.
3. Check provider 429/retry patterns in orchestrator logs for the same timestamp.
4. Rerun smoke once; if it passes, treat as intermittent outlier per table above.
5. If two consecutive runs exceed 55s, escalate to production monitoring owner before launch.
