# LLMHive — Cloud Marketplace submission pack (Sprint 2)

**Owner:** Camilo Diaz — cdiaz@llmhive.ai (`launch_owners.yaml` → `marketplace_sprint2`)  
**Checklist:** [marketplace_listing_prep_sprint2.md](../marketplace_listing_prep_sprint2.md)  
**Plan:** [docs/90_day_market_execution.md](../../../docs/90_day_market_execution.md) (days 31–60)

This folder is **business / legal / listing** material only. No product deploy required.

## Package index

| File | Use |
|------|-----|
| [one_pager.md](./one_pager.md) | Buyer overview — export to PDF for portals |
| [api_quickstart.md](./api_quickstart.md) | Integration guide for marketplace reviewers |
| [benchmark_summary.md](./benchmark_summary.md) | Claims from frozen JSON only |
| [pricing_for_marketplace.md](./pricing_for_marketplace.md) | Tier mapping — verify against live `/pricing` before submit |
| [support_matrix.md](./support_matrix.md) | Support hours, severity, escalation |
| [security_data_flow.md](./security_data_flow.md) | Security questionnaire answers |
| [architecture.md](./architecture.md) | Diagram + narrative for AWS/GCP review |
| [aws_listing_copy.md](./aws_listing_copy.md) | Paste-ready AWS Marketplace fields |
| [gcp_listing_copy.md](./gcp_listing_copy.md) | Paste-ready Google Cloud Marketplace fields |
| [submission_tracker.md](./submission_tracker.md) | Record submission IDs and review status |
| [legal_checklist.md](./legal_checklist.md) | EULA, privacy, terms — legal sign-off |

## Before you submit

```bash
python3 scripts/verify_benchmark_claim_freeze.py
```

- [ ] Re-open https://www.llmhive.ai/pricing and confirm numbers match `pricing_for_marketplace.md`
- [ ] Legal reviews `legal_checklist.md` (EULA / privacy / DPA)
- [ ] Finance picks AWS listing type (SaaS contract vs pay-as-you-go)
- [ ] Create test account + API key for AWS/Google validation teams

## Portal links

- **AWS:** [AWS Marketplace Management Portal](https://aws.amazon.com/marketplace/management/partner-tools/listings)
- **GCP:** [Google Cloud Partner Advantage](https://partners.cloud.google.com/) → Producer Portal → Marketplace

## After submission

Update [submission_tracker.md](./submission_tracker.md) with product IDs, dates, and reviewer feedback.
