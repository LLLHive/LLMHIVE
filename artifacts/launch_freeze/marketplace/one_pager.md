# LLMHive — Multi-model AI orchestration (marketplace one-pager)

**Company:** LLMHive  
**Website:** https://www.llmhive.ai  
**Support:** cdiaz@llmhive.ai  
**Product type:** SaaS API — multi-model orchestration (not a single foundation model)

---

## Problem

Teams juggle multiple LLM APIs, rate limits, and quality tradeoffs. Single-model chat leaves accuracy, cost, and reliability on the table.

## Solution

LLMHive orchestrates requests across leading models and providers. One API routes each task to the best available model path, with spend guardrails and benchmark-certified quality tiers.

## Key capabilities

- **Multi-model orchestration** — automatic routing across free and paid model pools
- **Elite orchestration** — higher-accuracy paths for subscribers (spend-guard protected)
- **Knowledge & tools** — retrieval, calculator, reranker, and domain packs where enabled
- **API + workspace** — REST API for integrations; web workspace at llmhive.ai

## Proof points (frozen certification basis only)

| Tier | Overall accuracy | Basis date |
|------|------------------|------------|
| Free orchestration | 93.3% (544/583) | 2026-03-31 |
| Elite orchestration | 93.5% (547/585) | 2026-04-01 |

Eight categories: reasoning, coding, math, multilingual, long context, tool use, RAG, dialogue. Full tables: `benchmark_summary.md` in this pack.

## Pricing (verify live before contract)

| Plan | Price |
|------|--------|
| Standard | $10/month |
| Premium | $20/month |
| Enterprise | $35/seat/month (min 5 seats) |

See https://www.llmhive.ai/pricing

## Architecture (summary)

Customer → HTTPS API → LLMHive orchestrator (Google Cloud Run) → authorized LLM providers (OpenAI, Anthropic, Google, Groq, etc.). Customer data in prompts is sent to selected providers for inference; see `security_data_flow.md`.

## Ideal buyers

- Product teams shipping AI features without building routing logic
- Ops teams standardizing on one orchestration layer
- Enterprises needing SSO, audit, and predictable tiers

## Next steps

1. Sign up at https://www.llmhive.ai  
2. API quickstart: `api_quickstart.md`  
3. Enterprise: cdiaz@llmhive.ai

---

*Export this file to PDF for AWS/GCP portal uploads. Do not alter benchmark figures without updating `benchmark_claim_basis.json`.*
