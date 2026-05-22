# AWS / GCP marketplace listing prep (Sprint 2)

Date: `2026-05-18`  
Plan reference: `docs/90_day_market_execution.md` (Sprint 2, days 31–60)  
**Owner:** Camilo Diaz — cdiaz@llmhive.ai (`launch_owners.yaml` → `marketplace_sprint2`)

**Submission pack (ready to use):** [`marketplace/`](./marketplace/README.md)

This is **non-code** GTM work. It does not change production runtime.

## Goal

Submit **2+ cloud marketplace listings** (AWS Marketplace + Google Cloud Marketplace) with LLMHive positioned as an orchestration / API product aligned to frozen benchmark and pricing claims.

## Prerequisites (must be PASS before submission)

- [x] Launch owners assigned (`launch_owners.yaml`)
- [x] Benchmark claim freeze verifier in repo (`verify_benchmark_claim_freeze.py`)
- [ ] Production smoke green on canonical orchestrator URL
- [ ] Pricing page matches `pricing_for_marketplace.md` (verify live `/pricing`)
- [x] Support runbook: [`marketplace/support_matrix.md`](./marketplace/support_matrix.md)
- [ ] Legal sign-off: [`marketplace/legal_checklist.md`](./marketplace/legal_checklist.md)

## Implementation steps (in order)

### 1. Owner

- [x] `launch_owners.yaml` → `marketplace_sprint2` = Camilo Diaz / cdiaz@llmhive.ai

### 2. Gather artifacts (in repo — no new product code)

| Artifact | File |
|----------|------|
| One-pager | [`marketplace/one_pager.md`](./marketplace/one_pager.md) → export PDF |
| API quickstart | [`marketplace/api_quickstart.md`](./marketplace/api_quickstart.md) |
| Benchmark numbers | [`marketplace/benchmark_summary.md`](./marketplace/benchmark_summary.md) |
| Pricing | [`marketplace/pricing_for_marketplace.md`](./marketplace/pricing_for_marketplace.md) |
| Support | [`marketplace/support_matrix.md`](./marketplace/support_matrix.md) |
| Security / data flow | [`marketplace/security_data_flow.md`](./marketplace/security_data_flow.md) |
| Architecture | [`marketplace/architecture.md`](./marketplace/architecture.md) |

### 3. AWS Marketplace

- [ ] Seller account → [AWS Marketplace Management Portal](https://aws.amazon.com/marketplace/management/partner-tools/listings)
- [ ] Paste copy from [`marketplace/aws_listing_copy.md`](./marketplace/aws_listing_copy.md)
- [ ] Upload one-pager PDF + architecture diagram
- [ ] Map pricing dimensions (see `pricing_for_marketplace.md`)
- [ ] Legal: EULA / terms links from `legal_checklist.md`
- [ ] Create validation test account + API key
- [ ] Submit → record ID in [`marketplace/submission_tracker.md`](./marketplace/submission_tracker.md)

### 4. Google Cloud Marketplace

- [ ] Partner Advantage / Producer Portal
- [ ] Paste copy from [`marketplace/gcp_listing_copy.md`](./marketplace/gcp_listing_copy.md)
- [ ] SaaS solution listing (prefer API SaaS over VM)
- [ ] Pricing aligned to live tiers
- [ ] Submit → record ID in `submission_tracker.md`

### 5. Track feedback

- [ ] Update `submission_tracker.md` after each reviewer round
- [ ] Week 8 retro: both listings live or documented blockers

## AWS checklist (detail)

- [ ] Choose listing type (SaaS contract vs pay-as-you-go) with finance
- [ ] Product title, short/long description (`aws_listing_copy.md`)
- [ ] Support email / URL
- [ ] Architecture diagram PNG
- [ ] Security questionnaire (`security_data_flow.md`)
- [ ] Pricing dimensions → Standard / Premium / Enterprise
- [ ] EULA / terms (legal)
- [ ] Test account for AWS validation

## GCP checklist (detail)

- [ ] Producer Portal access
- [ ] Solution listing copy (`gcp_listing_copy.md`)
- [ ] Deployable offering = SaaS API (not VM unless required)
- [ ] Support + documentation URL
- [ ] Pricing model
- [ ] Test account for Google validation

## Deliverable

- [ ] AWS submission ID in `submission_tracker.md`
- [ ] GCP submission ID in `submission_tracker.md`
- [ ] Status review in Sprint 2 week 8 retro

## Out of scope

- Runtime code changes
- New benchmark runs for marketing
- Auto-deploy or marketplace-driven infra changes
