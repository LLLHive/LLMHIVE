# Provider billing & connectivity status

**Last updated:** 2026-05-19 (GCP Secret Manager + live API probes)  
**Plan:** [ORCHESTRATION_RESILIENCE_PLAN.md](./ORCHESTRATION_RESILIENCE_PLAN.md)

Run the verify script locally with env loaded (or against GCP secrets):

```bash
python3 scripts/verify_direct_providers.py
```

## Direct providers (Phase 1)

| Provider | Env var | Key last-4 | Ping (script) | Auto-recharge ON | Monthly cap / notes |
|----------|---------|------------|---------------|------------------|---------------------|
| OpenAI | `OPENAI_API_KEY` | | | | Platform → Billing |
| Anthropic | `ANTHROPIC_API_KEY` | | | | Console → Billing |
| Google AI Studio | `GOOGLE_AI_API_KEY` | | | | AI Studio / GCP billing |
| xAI Grok | `GROK_API_KEY` | | | | xAI Console |
| DeepSeek | `DEEPSEEK_API_KEY` | | | | platform.deepseek.com |
| Mistral | `MISTRAL_API_KEY` | | | | _client not in repo yet_ |

**Gemini redundancy (no Vertex):** second AI Studio project + `GOOGLE_AI_API_KEY_2` when we wire Phase 3 optional bucket.

## Aggregators (Phase 2)

| Provider | Env var | Ping (script) | Auto-recharge ON | RPM / limits (from ping headers) |
|----------|---------|---------------|------------------|----------------------------------|
| OpenRouter | `OPENROUTER_API_KEY` | | | Credits → Auto-reload |
| Together AI | `TOGETHERAI_API_KEY` | | | |
| Groq | `GROQ_API_KEY` | | | |
| Cerebras | `CEREBRAS_API_KEY` | **OK** | Use `llama3.1-8b` (not deprecated `llama-3.3-70b`) | Wired in ROUTING_V2 |
| HuggingFace | `HF_TOKEN` | | | Subscription |

## Production secrets (Cloud Run)

Confirm each row above exists in GCP Secret Manager and is mounted on `llmhive-orchestrator`:

- [ ] Secret present in GCP
- [ ] Referenced in Cloud Run service env
- [ ] Matches last successful local ping

## Phase 3 — new secrets on Cloud Run (2026-05-19)

Mounted on `llmhive-orchestrator` but **not read by orchestrator code yet** (no `DeepInfraClient` / routing).

| Cloud Run env | GCP secret | Auth / list | Chat / inference | Action |
|---------------|------------|-------------|------------------|--------|
| `Cloudflare_Api_Key` | `cloudflare-api-key` | **OK** (token verify 200) | **OK** with `Cloudflare_Account_ID` — chat 200 on `@cf/meta/llama-3.1-8b-instruct` | Wire client in orchestrator |
| `Cloudflare_Account_ID` | `cloudflare-account-id` | **OK** (32-char id; Workers AI chat works) | Account metadata GET 403 (token scope); inference OK | No change needed for ID |
| `Kimi_K26_Api_Key` | `kimi-k26-api-key` | **OK** (`/v1/models` 200) | **Blocked** — Moonshot org **account suspended** | Reactivate at [platform.moonshot.ai](https://platform.moonshot.ai) |
| `DeepInfra_Api_Key` | `deepInfra_api_key` | **OK** (`/v1/models` 200) | **OK** — chat 200 on `Llama-3.3-70B-Instruct-Turbo` (funded account) | Catalog uses DeepInfra-native model IDs (not OpenRouter slugs) |
| `GEMINI_API_KEY_2` | `gemini-api-key-2` | **OK** (models list 200) | **OK** on `gemini-2.5-flash`; 429 on `gemini-2.0-flash` (quota) | Wire as spillover; prefer 2.5-flash |

Re-run probes:

```bash
export Cloudflare_Api_Key=$(gcloud secrets versions access latest --secret=cloudflare-api-key --project=llmhive-orchestrator)
export Kimi_K26_Api_Key=$(gcloud secrets versions access latest --secret=kimi-k26-api-key --project=llmhive-orchestrator)
export DeepInfra_Api_Key=$(gcloud secrets versions access latest --secret=deepInfra_api_key --project=llmhive-orchestrator)
export GEMINI_API_KEY_2=$(gcloud secrets versions access latest --secret=gemini-api-key-2 --project=llmhive-orchestrator)
python3 scripts/verify_direct_providers.py
```

## Phase 3 backlog (clients not wired)

| Provider | Status |
|----------|--------|
| Fireworks AI | `FIREWORKS_KEY` / `FIREWORKS_MODELS` → `fireworks-key`, `fireworks-models` |
| DeepInfra | **Wired** — use `meta-llama/Llama-3.3-70B-Instruct-Turbo` etc. in `scripts/deepinfra-models.json` |
| Replicate | Not wired |
| Moonshot (Kimi) | Secret OK; account suspended |
| Cloudflare Workers AI | Token OK; needs account ID |
| Qwen Cloud (DashScope) | Not wired |
| Second AI Studio (`GEMINI_API_KEY_2`) | Secret OK; use `gemini-2.5-flash` |

## ROUTING_V2 (wired 2026-05-19)

When `ROUTING_V2_ENABLED=true` (default) and the model is a **free slug** (`:free` or in `FREE_MODELS_DB`):

- **Direct APIs are tried first** (cost-ordered: Google, DeepSeek, Groq, Cerebras, DashScope, Cloudflare, DeepInfra, Fireworks, Hyperbolic, Azure Foundry, Together, HuggingFace).
- **OpenRouter is last** in the chain (spillover when direct quotas throttle).
- **Elite/paid models** are unchanged — still OpenRouter-primary when the gateway is configured.

Clients: `dashscope_client`, `deepinfra_client`, `azure_foundry_client`, `cloudflare_client`, `kimi_client` + existing Fireworks/Hyperbolic/Groq/Cerebras.

Disable spillover-first for debugging: `ROUTING_V2_ENABLED=false`.
