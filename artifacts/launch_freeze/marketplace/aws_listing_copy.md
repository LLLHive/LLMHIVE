# AWS Marketplace — paste-ready listing copy

**Product name:** LLMHive Multi-Model Orchestration API  
**Category:** Machine Learning / SaaS / Developer Tools  
**Owner:** Camilo Diaz — cdiaz@llmhive.ai

---

## Short description (max ~250 chars)

LLMHive orchestrates prompts across leading LLMs with one API. Benchmark-certified quality tiers, spend guardrails, and plans from $10/mo. https://www.llmhive.ai

---

## Long description

LLMHive is a multi-model AI orchestration platform delivered as a SaaS API and web workspace. Instead of locking into a single foundation model, teams send requests to LLMHive and the service routes each task across free and paid model pools for better accuracy, resilience, and cost control.

**What you get**

- Single integration point (`POST /v1/chat`) with API key authentication
- Automatic routing across major providers (OpenAI, Anthropic, Google, Groq, and more)
- Standard ($10/mo) and Premium ($20/mo) plans with spend-guard protection
- Enterprise per-seat pricing with SSO and compliance options
- Web workspace at https://www.llmhive.ai for interactive use

**Certified quality (frozen benchmark basis)**

- Free-tier orchestration: **93.3%** overall accuracy (March 2026 certification)
- Elite-tier orchestration: **93.5%** overall accuracy (April 2026 certification)

Evaluated across eight categories: reasoning, coding, math, multilingual, long context, tool use, RAG, and dialogue.

**Architecture**

Hosted on Google Cloud Run (us-east1) with secrets in GCP Secret Manager. Customer prompts are sent to selected third-party LLM providers over TLS. See product documentation for data flow and security.

**Support**

Email: cdiaz@llmhive.ai  
Documentation: https://www.llmhive.ai/help  
API quickstart: included in seller documentation package

---

## Highlights (bullet list)

- 93.3% / 93.5% certified orchestration accuracy (free / elite tiers)
- One API for multi-provider routing
- Plans from $10/month
- Spend guard protects margins at scale
- Enterprise SSO and per-seat pricing

---

## Support details (AWS form)

| Field | Value |
|-------|--------|
| Support email | cdiaz@llmhive.ai |
| Support URL | https://www.llmhive.ai/help |
| Support phone | N/A (email-first) |
| Support hours | 8am–10pm ET (launch); business hours post-launch |

---

## Pricing dimensions (suggested)

| Dimension API name | Description | Monthly price (USD) |
|--------------------|-------------|---------------------|
| `llmhive_standard` | Standard orchestration subscription | 10.00 |
| `llmhive_premium` | Premium orchestration subscription | 20.00 |
| `llmhive_enterprise_seat` | Enterprise per seat | 35.00 |

Confirm with finance before publish. Map to existing Stripe products.

---

## Legal links (fill before submit)

| Field | URL |
|-------|-----|
| Terms of service | https://www.llmhive.ai/terms *(verify)* |
| Privacy policy | https://www.llmhive.ai/privacy *(verify)* |
| EULA | *Legal to provide — see legal_checklist.md* |

---

## Test instructions for AWS validation

1. Seller provides validation account credentials (email + API key + paid subscription).
2. `GET {base_url}/health` → 200
3. `POST {base_url}/v1/chat` with sample prompt and `metadata.user_id` → 200
4. See `api_quickstart.md` in seller package.

**Base URL:** `https://llmhive-orchestrator-792354158895.us-east1.run.app`

---

## Submission checklist

- [ ] AWS Marketplace Seller account active
- [ ] Listing type chosen (SaaS contract recommended)
- [ ] Architecture PNG uploaded
- [ ] One-pager PDF uploaded
- [ ] Submit → record **Product ID** in `submission_tracker.md`
