# Security & data flow — marketplace questionnaire draft

**Owner:** Camilo Diaz — cdiaz@llmhive.ai  
**Legal review required** before submitting to AWS/GCP security forms.

---

## Product summary

LLMHive is a **multi-tenant SaaS orchestration API**. Customers send prompts via HTTPS; the service selects and calls third-party LLM providers, then returns consolidated responses.

---

## Data flow (high level)

```
Customer application or browser
    │  TLS 1.2+
    ▼
LLMHive frontend (Vercel) — auth via Clerk; billing via Stripe
    │  TLS
    ▼
LLMHive orchestrator (Google Cloud Run, us-east1)
    │  TLS + provider API keys (GCP Secret Manager)
    ▼
Third-party LLM providers (e.g. OpenAI, Anthropic, Google, Groq, …)
```

**Customer content in scope:** Prompt text, optional conversation history, metadata (user_id, chat_id).  
**Not stored as training data** by LLMHive for provider models — subject to each provider’s API terms.

---

## Infrastructure

| Component | Provider | Region (production) |
|-----------|----------|-------------------|
| Orchestrator API | Google Cloud Run | us-east1 |
| Secrets | GCP Secret Manager | llmhive-orchestrator project |
| Frontend | Vercel | Global CDN |
| Auth | Clerk | SaaS |
| Billing | Stripe | SaaS |
| Optional vector / strategy data | Pinecone / Firestore | Per configuration |

---

## Authentication & access

- **API:** API key in `Authorization: Bearer` or `X-API-Key`
- **Paid orchestration:** Active subscription verified in Firestore (`user_id`)
- **Internal CI benchmarks:** Separate header `X-LLMHIVE-Scheduled-Benchmark-Secret` (not customer-facing)

---

## Encryption

- **In transit:** HTTPS for all customer and provider API calls
- **At rest:** GCP/Vercel/Stripe/Clerk default encryption for stored data; provider secrets in Secret Manager

---

## Data retention (verify with legal / privacy policy)

- Conversation memory: tier-dependent (e.g. 90-day retention on Standard — confirm privacy policy)
- Logs: Cloud Run request logs for operations and security (retention per GCP settings)
- Benchmark / telemetry: internal only; not sold

---

## Subprocessors (disclose in privacy policy)

Customers should be informed that prompts may be sent to:

- Foundation model API providers (OpenRouter, OpenAI, Anthropic, Google, Groq, etc. — routing-dependent)
- Clerk (authentication)
- Stripe (payments)
- Vercel (hosting)
- Google Cloud (compute)

---

## Compliance posture (honest statements)

| Framework | Status |
|-----------|--------|
| SOC 2 | *In progress / planned — see 90-day plan; do not claim certified unless complete* |
| GDPR | Privacy policy + DPA on request for Enterprise |
| HIPAA | Not supported unless separate BAA |

---

## Customer responsibilities

- Protect API keys
- Classify prompt data they send (PII, PHI, etc.)
- Configure retention and access in their organization

---

## Incident response

- Contact: cdiaz@llmhive.ai
- Escalation: see `support_matrix.md`
- Rollback: `artifacts/launch_freeze/launch_source_of_truth_packet_20260405.md`

---

## Questions mapping (typical marketplace forms)

| Question | Answer |
|----------|--------|
| Where is data processed? | Primarily US (GCP us-east1); providers may process globally per their terms |
| Do you train on customer data? | No — inference-only via third-party APIs |
| Can customers delete data? | Per privacy policy / account deletion flow — confirm with legal |
| Penetration test | *TBD — schedule if required by Enterprise marketplace review* |
