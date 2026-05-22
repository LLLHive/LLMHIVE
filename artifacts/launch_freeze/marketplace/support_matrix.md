# Support matrix — marketplace buyers

**Primary contact:** cdiaz@llmhive.ai  
**Owner:** Camilo Diaz (`launch_owners.yaml` → `support`)  
**Website:** https://www.llmhive.ai/help (verify live)

---

## Support hours

| Period | Hours (ET) | Channel |
|--------|------------|---------|
| Launch week | 8:00 – 22:00 | Email |
| Standard | Business hours ET (define post-launch) | Email |
| Enterprise | Per contract / SLA | Email + designated CSM (TBD) |

**Escalation:** cdiaz@llmhive.ai → launch approver backup pdiaz@llmhive.ai

---

## Severity definitions

| Severity | Definition | Target response | Target resolution |
|----------|------------|-----------------|-------------------|
| **P1 — Critical** | Production API down; no workaround | 1 hour (business hours) | 4 hours |
| **P2 — High** | Major feature broken; partial workaround | 4 hours | 1 business day |
| **P3 — Medium** | Non-blocking defect; question on integration | 1 business day | 3 business days |
| **P4 — Low** | Feature request, documentation | 2 business days | Best effort |

*Enterprise customers may negotiate stricter SLA in private offer — document in contract, not in public marketplace listing unless legal approves.*

---

## What we support

- API authentication and `/v1/chat` integration questions
- Billing, subscription, and plan changes (Stripe-backed)
- Workspace access and sign-in (Clerk)
- Orchestration quality issues reproducible with request ID / timestamp

## What we do not support via standard tier

- Custom model fine-tuning on buyer infrastructure
- On-prem deployment (SaaS only unless separate enterprise agreement)
- Debugging buyer application code beyond API contract

---

## Information to include in tickets

1. Account email and `user_id` (if API)
2. Timestamp (UTC) and request ID if available
3. HTTP status and response body (redact secrets)
4. Plan tier (Standard / Premium / Enterprise)

---

## Status page

- Use GitHub Production Smoke Tests + Cloud Run monitoring internally
- Public status page: *TBD — add URL before marketplace go-live if required by AWS/GCP*
