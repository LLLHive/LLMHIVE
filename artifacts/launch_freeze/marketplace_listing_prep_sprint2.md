# AWS / GCP marketplace listing prep (Sprint 2)

Date: `2026-05-18`  
Plan reference: `docs/90_day_market_execution.md` (Sprint 2, days 31–60)  
Owner: see `artifacts/launch_freeze/launch_owners.yaml` → `marketplace_sprint2`

This is **non-code** GTM work. It does not change production runtime.

## Goal

Submit **2+ cloud marketplace listings** (AWS Marketplace + Google Cloud Marketplace) with LLMHive positioned as an orchestration / API product aligned to frozen benchmark and pricing claims.

## Prerequisites (must be PASS before submission)

- [ ] Launch owners assigned (`launch_owners.yaml`)
- [ ] Benchmark claim freeze verified: `python3 scripts/verify_benchmark_claim_freeze.py`
- [ ] Production smoke green on canonical orchestrator URL
- [ ] Pricing page matches `pricing_package` owner sign-off
- [ ] Support runbook + escalation path documented for marketplace buyers

## AWS Marketplace checklist

- [ ] Choose listing type (SaaS contract vs pay-as-you-go) with finance
- [ ] Product title, short/long description aligned to `benchmark_claim_basis.json`
- [ ] Support email / URL from `launch_owners.yaml`
- [ ] Architecture diagram (orchestrator + API, no overstated SLAs)
- [ ] Security questionnaire draft (data flow: API → Cloud Run → providers)
- [ ] Pricing dimensions mapped to Lite / Pro / Enterprise (match live site)
- [ ] EULA / terms link (legal review)
- [ ] Test account + API key for AWS validation team
- [ ] Submit listing; track AWS review feedback

## GCP Marketplace checklist

- [ ] Partner Advantage / Producer Portal access confirmed
- [ ] Solution listing copy (same claim basis as AWS)
- [ ] Deployable offering definition (if VM/listing requires — prefer API SaaS listing if available)
- [ ] Service account / billing integration documented
- [ ] Support contacts and documentation URL
- [ ] Pricing model aligned to live tiers
- [ ] Submit listing; track Google review feedback

## Shared artifacts to prepare

| Artifact | Purpose |
|----------|---------|
| One-pager PDF | Buyer-facing overview |
| API quickstart | `docs/launch/API_REFERENCE.md` excerpt |
| Benchmark summary | From `category_benchmarks_*_20260331` / `20260401` **only** |
| SLA statement | Match `production_hardened` / tier docs — no new promises |
| Support matrix | Hours, severity levels, escalation |

## Deliverable

- [ ] AWS submission ID recorded
- [ ] GCP submission ID recorded
- [ ] Status review in Sprint 2 week 8 retro

## Out of scope (this doc)

- Runtime code changes
- New benchmark runs for marketing
- Auto-deploy or marketplace-driven infra changes
