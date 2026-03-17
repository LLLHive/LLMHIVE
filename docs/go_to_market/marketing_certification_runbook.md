# Launch & Marketing Certification Runbook

This runbook describes how to produce a **marketing-certified** release pack from the certified Elite+ Firestore deployment, and how it differs from **launch certified**.

---

## Launch Certified vs Marketing Certified

| Aspect | Launch Certified | Marketing Certified |
|--------|------------------|---------------------|
| **Scope** | Online preflight + synthetic suite + telemetry proofs | Fresh eval + gate PASS + provenance |
| **Validation** | Live API: health, build-info, spend_decision, elite_plus, auth-gated KPIs | Offline benchmarks: category floors, cost p50/p95, paid escalation % |
| **Artifacts** | preflight_report.json, synthetic_prod_results.json | marketing_benchmark.json, marketing_benchmark.md, provenance.json |
| **Gate status** | N/A | Must be PASS (never UNKNOWN) |

**Launch certified** proves the deployed service behaves correctly (spend guardrails, telemetry, auth).  
**Marketing certified** proves the benchmark pack is derived from a fresh Elite+ eval and gate pass, with full provenance.

---

## Commands: Marketing-Certified Release Pack

From a clean clone:

```bash
git clone https://github.com/LLLHive/LLMHIVE.git
cd LLMHIVE
git checkout certified-eliteplus-firestore-2026-03-07

# Ensure required env vars for benchmarks exist (provider keys, pinecone, firestore, etc.)
# Do not echo secrets into logs.

python scripts/run_marketing_certified_release.py \
  --ref certified-eliteplus-firestore-2026-03-07 \
  --outdir artifacts/marketing_certified
```

---

## Acceptance Criteria Checklist

| Checklist Item | Verification |
|----------------|--------------|
| `artifacts/marketing_certified/marketing_benchmark.md` exists | File present |
| `marketing_benchmark.md` contains certified ref name | `certified-eliteplus-firestore-2026-03-07` |
| `marketing_benchmark.md` contains commit SHA | 12-char SHA |
| Gate status = PASS | `**Gate status:** PASS` |
| Sample sizes per category | Listed in Category Results table |
| Cost avg + p95 | Within targets |
| Paid escalation % | Within limits |
| Gate status is never UNKNOWN | Script exits 0 only when gate PASS |
| P0 categories pass | No P0 failures in gate |
| Provenance file present | `artifacts/marketing_certified/provenance.json` |
| Rerun is idempotent | Script overwrites outputs safely |

---

## Rollback Command

If deployment or certification fails:

```bash
gcloud run services update llmhive-orchestrator --region us-east1 \
  --update-env-vars "ELITE_PLUS_ENABLED=0,PREMIUM_DEFAULT_TIER=elite,ELITE_PUBLIC_ENABLED=1"
```

---

## Environment Variables

For marketing-certified run:

- **Provider keys**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc. (for benchmarks)
- **Pinecone**: `PINECONE_API_KEY`, `PINECONE_HOST_*` (if RAG/tool benchmarks run)
- **Firestore**: Uses default GCP project; `FIRESTORE_PROJECT_ID` if needed

For online preflight/synthetic (launch certified):

- `API_KEY` or `LLMHIVE_API_KEY`: for `/v1/chat` probes
- `INTERNAL_ADMIN_OVERRIDE_KEY`: for `/internal/launch_kpis` validation

---

## Go-to-Market: Full Evidence Pack + Production Freeze

### Phase 1 — Generate marketing-certified bundle

```bash
export MARKETING_REF="certified-eliteplus-firestore-2026-03-07"
export OUTDIR="artifacts/marketing_certified"
mkdir -p "$OUTDIR"

python3 scripts/run_marketing_certified_release.py \
  --ref "$MARKETING_REF" \
  --outdir "$OUTDIR"
```

### Phase 2 — Publish evidence pack

```bash
cd "$(git rev-parse --show-toplevel)"
ZIP_NAME="marketing_certified_eliteplus_${MARKETING_REF}.zip"
rm -f "$ZIP_NAME"
zip -r "$ZIP_NAME" "$OUTDIR/publish/"

# GitHub Release (if gh CLI available)
gh release create "$MARKETING_REF" \
  --title "Marketing Certified Elite+ ($MARKETING_REF)" \
  --notes-file "$OUTDIR/publish/README.md" \
  "$ZIP_NAME" \
  "$OUTDIR/publish/"*.md \
  "$OUTDIR/publish/"*.json \
  "$OUTDIR/publish/checksums.txt"

# Optional: Google Drive
rclone mkdir "gdrive:MarketingCertified/$MARKETING_REF" || true
rclone copy "$OUTDIR/publish/" "gdrive:MarketingCertified/$MARKETING_REF/"
rclone copy "$ZIP_NAME" "gdrive:MarketingCertified/$MARKETING_REF/"
```

### Phase 3 — Production freeze (no redeploy)

```bash
export PROD_URL="https://llmhive-orchestrator-792354158895.us-east1.run.app"

python3 scripts/run_prod_preflight.py --target "$PROD_URL"
python3 scripts/run_synthetic_prod_suite.py --target "$PROD_URL"
```

### Phase 4 — Record launch freeze snapshot

```bash
export PROD_URL="https://llmhive-orchestrator-792354158895.us-east1.run.app"
python3 scripts/record_launch_freeze.py
```

Creates `artifacts/launch_freeze/`:
- `prod_identity.json` — build-info, health
- `prod_env_snapshot.txt` — non-secret env
- `prod_memory_cpu_snapshot.txt` — Cloud Run resources (if gcloud available)
- `marketing_pack_pointer.txt` — ref, release URL, checksums (when publish/ exists)

### Rollback command

```bash
gcloud run services update llmhive-orchestrator --region us-east1 \
  --update-env-vars "ELITE_PLUS_ENABLED=0,PREMIUM_DEFAULT_TIER=elite,ELITE_PUBLIC_ENABLED=1"
```

---

## Related Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_marketing_certified_release.py` | Single entrypoint: eval → gate → marketing pack → provenance |
| `scripts/run_marketing_benchmark.py` | Requires `--gate-json` or `--require-gate-pass`; never outputs UNKNOWN |
| `scripts/run_prod_preflight.py` | Online launch readiness; `kpis_accessible` respects auth-gated endpoint |
| `scripts/run_synthetic_prod_suite.py` | Reads `INTERNAL_ADMIN_OVERRIDE_KEY` from env for internal endpoint checks |
| `scripts/record_launch_freeze.py` | Records prod identity, env snapshot, marketing pack pointer |
