# Launch baseline addendum (2026-05-22)

Supersedes **serving revision** and **pricing names** in older freeze docs dated 2026-04-05.  
Benchmark claim basis is **unchanged** (still 20260331 free / 20260401 elite).

## Certified production identity (current)

| Component | Value |
|-----------|--------|
| Frontend | https://www.llmhive.ai (canonical host redirects to `https://llmhive.ai`) |
| Orchestrator URL | `https://llmhive-orchestrator-792354158895.us-east1.run.app` |
| Cloud Run service | `llmhive-orchestrator` (us-east1) |
| **Serving revision** | **`llmhive-orchestrator-02451-4fq`** (100% traffic) |
| Prior freeze revision | ~~`02203-grk`~~ — superseded by intentional post-freeze deploys (ROUTING_V2, providers) |

## Pricing (live site — source of truth)

| Tier | Monthly | Annual | Internal key |
|------|---------|--------|--------------|
| Free | $0 | $0 | `free` |
| Standard | $10 | $100 | `lite` |
| Premium | $20 | $200 | `pro` |
| Enterprise | $35/seat | $350/seat | `enterprise` (min 5 seats) |

Do **not** use Lite $14.99 / Pro $29.99 in new external copy.

## Smoke / CI (2026-05-22)

- Blocking smoke: `pytest tests/smoke/ -m "smoke and not quality"`
- Chat probe: `api-key` + `scheduled-benchmark-secret` header
- Latency budget: `SMOKE_CHAT_MAX_MS=55000`
- Quality benchmarks: separate job (`continue-on-error`)
- **Latest green run:** [Production Smoke Tests #26316889891](https://github.com/LLLHive/LLMHIVE/actions/runs/26316889891) — `main` @ `2705c7c80` (2026-05-22T23:30:14Z)

## Automated gate verify (step 2)

From repo root — **do not** run `verify_launch_gates.py` alone (not on PATH):

```bash
./scripts/run_verify_launch_gates.sh
```

Or manually:

```bash
python3 scripts/verify_launch_gates.py   # after exporting secrets (see script above)
```

Expect `"passed": true` on all checks after Vercel deploy `a2757ad` (proxy health fix).

## Frontend deploy (done)

- `proxy.ts`: `/api/health(.*)` public — deployed to production (`a2757ad`, latest `2705c7c80`).
- Vercel build warnings (e.g. env hints) are **non-blocking** unless a user-facing route or API regresses.

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Launch approver | Camilo Diaz | 2026-05-22 | Revision `02451-4fq` accepted for launch; gates PASS in checklist |
| Pricing | Camilo Diaz | 2026-05-22 | Free $0 / Standard $10 / Premium $20 / Enterprise $35 seat — matches live `/pricing` |
| Benchmark claims | Camilo Diaz | 2026-05-22 | Basis 20260331 + 20260401 only; `verify_benchmark_claim_freeze.py` passed |
