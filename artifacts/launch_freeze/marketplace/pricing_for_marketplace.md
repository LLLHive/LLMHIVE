# Pricing — marketplace dimension mapping

**Live surface:** https://www.llmhive.ai/pricing  
**Owner sign-off:** Camilo Diaz — cdiaz@llmhive.ai (`pricing_package` in `launch_owners.yaml`)

**Rule:** At submission time, open the live pricing page and confirm every price below. If the site differs, **the website wins**.

---

## Current live tiers (April 2026 GTM — from `app/pricing/PricingClient.tsx`)

| Marketplace label | Product name (site) | Monthly | Annual | Stripe / internal key | Notes |
|-------------------|---------------------|---------|--------|------------------------|-------|
| Free | Free (implicit) | $0 | $0 | `free` | Free-model orchestration |
| Standard | Standard | **$10** | **$100** | `lite` | Multi-model orchestration, KB, tools |
| Premium | Premium | **$20** | **$200** | `pro` | Top orchestration stack; spend guard |
| Enterprise | Enterprise | **$35/seat** | **$350/seat** | `enterprise` | Min 5 seats; SSO, audit, SLA |

### Feature bullets (for listing forms)

**Standard ($10/mo)**

- Multi-model orchestration
- Knowledge base access
- Calculator and reranker tools
- 90-day conversation memory
- Spend guard: switches to free orchestration when provider cap reached

**Premium ($20/mo)**

- Everything in Standard
- Benchmark-grade orchestration while spend guard allows
- Higher orchestration depth for paid workloads

**Enterprise ($35/seat/mo)**

- 400 Premium queries per seat per period (verify on site)
- Then unlimited Standard-tier orchestration
- SSO, audit logs, SLA (contact sales for custom terms)

---

## AWS Marketplace dimension suggestions

| Dimension | Unit | Example price | Maps to |
|-----------|------|---------------|---------|
| `standard_monthly` | Monthly subscription | $10 | Standard |
| `premium_monthly` | Monthly subscription | $20 | Premium |
| `enterprise_seat_monthly` | Per seat / month | $35 | Enterprise |

Use **SaaS contract** or **SaaS subscription** listing type per finance. Align invoicing with existing Stripe products.

---

## GCP Marketplace pricing suggestions

- List as **SaaS API / managed service** (not a VM image) if available in your partner program.
- Mirror AWS dimensions: Standard / Premium / Enterprise per seat.
- Private offer path for Enterprise (5+ seats).

---

## Historical note (do not use in new listings)

Older launch freeze docs referenced Lite $14.99 / Pro $29.99. **Superseded** by live Standard $10 / Premium $20. Do not paste old numbers into AWS/GCP forms.
