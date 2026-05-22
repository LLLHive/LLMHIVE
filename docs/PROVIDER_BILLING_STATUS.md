# Provider billing & connectivity status

**Last updated:** 2026-05-18 (GCP Secret Manager + live API probes)  
**Plan:** [ORCHESTRATION_RESILIENCE_PLAN.md](./ORCHESTRATION_RESILIENCE_PLAN.md)

Run the verify script locally with env loaded (or against GCP secrets):

```bash
./scripts/run_verify_with_gcp_secrets.sh
# or:
python3 scripts/verify_direct_providers.py
```

## Secret rotation & Cloud Run

Adding a new version in **GCP Secret Manager** does **not** reload secrets on already-running Cloud Run instances. After rotating any provider key:

1. Add the new secret version in GCP (`gcloud secrets versions add …`).
2. **Deploy a new revision** (Cloud Build / `scripts/deploy_orchestrator_routing_v2.sh`) **or** update the service so env mounts refresh, e.g.  
   `gcloud run services update llmhive-orchestrator --update-secrets=Kimi_K26_Api_Key=kimi-k26-api-key:latest …`
3. Re-run `./scripts/run_verify_with_gcp_secrets.sh` and confirm the provider row is **ok**.

Mounts use `:latest`; production only picks up the newest version when a **new revision** starts.

## Direct providers (Phase 1)

| Provider | Env var | Key last-4 | Ping (script) | Auto-recharge ON | Monthly cap / notes |
|----------|---------|------------|---------------|------------------|---------------------|
| OpenAI | `OPENAI_API_KEY` | | | | Platform → Billing |
| Anthropic | `ANTHROPIC_API_KEY` | | | | Console → Billing |
| Google AI Studio | `GOOGLE_AI_API_KEY` | | | | AI Studio / GCP billing |
| xAI Grok | `GROK_API_KEY` | | | | xAI Console |
| DeepSeek | `DEEPSEEK_API_KEY` | | | | platform.deepseek.com |
| Mistral | `MISTRAL_API_KEY` | | **OK** | | Wired in ROUTING_V2 (`mistral_client`) |

**Gemini redundancy (no Vertex):** second AI Studio project + `GEMINI_API_KEY_2` / `gemini-api-key-2` as spillover.

## Aggregators (Phase 2)

| Provider | Env var | Ping (script) | Auto-recharge ON | RPM / limits (from ping headers) |
|----------|---------|---------------|------------------|----------------------------------|
| OpenRouter | `OPENROUTER_API_KEY` | | | Credits → Auto-reload |
| Together AI | `TOGETHERAI_API_KEY` | | | |
| Groq | `GROQ_API_KEY` | | | |
| Cerebras | `CEREBRAS_API_KEY` | **OK** | Use `llama3.1-8b` (not deprecated `llama-3.3-70b`) | Wired in ROUTING_V2 |
| HuggingFace | `HF_TOKEN` | | | Subscription; needs Inference Providers scope |
| Moonshot (Kimi) | `Kimi_K26_Api_Key` | **OK** | [platform.kimi.ai](https://platform.kimi.ai) billing | Direct API `https://api.moonshot.ai/v1`; chat OK on `kimi-k2.6` |

## Production secrets (Cloud Run)

Confirm each row above exists in GCP Secret Manager and is mounted on `llmhive-orchestrator`:

- [ ] Secret present in GCP
- [ ] Referenced in Cloud Run service env (`llmhive/cloudbuild.yaml`)
- [ ] New revision deployed after last secret rotation
- [ ] Matches last successful local ping (`run_verify_with_gcp_secrets.sh`)

## Phase 3 — spillover secrets on Cloud Run

Mounted on `llmhive-orchestrator` and **read by orchestrator** via `spillover_provider_registry` + ROUTING_V2 (see commit `224b0e125`).

| Cloud Run env | GCP secret | Auth / list | Chat / inference | Status |
|---------------|------------|-------------|------------------|--------|
| `Cloudflare_Api_Key` | `cloudflare-api-key` | **OK** (token verify 200) | **OK** with `Cloudflare_Account_ID` — chat on Workers AI models | Wired |
| `Cloudflare_Account_ID` | `cloudflare-account-id` | **OK** (32-char id) | Account metadata GET 403 (token scope); inference OK | Wired |
| `Kimi_K26_Api_Key` | `kimi-k26-api-key` | **OK** (`/v1/models` 200) | **OK** — chat 200 on `kimi-k2.6` (account recharged; key rotated in GCP) | Wired — ROUTING_V2 + `kimi-models.json` |
| `DeepInfra_Api_Key` | `deepInfra_api_key` | **OK** (`/v1/models` 200) | **OK** — chat on DeepInfra-native IDs in `scripts/deepinfra-models.json` | Wired |
| `GEMINI_API_KEY_2` | `gemini-api-key-2` | **OK** (models list 200) | **OK** on `gemini-2.5-flash`; 429 possible on `gemini-2.0-flash` (quota) | Wired as spillover |
| `FIREWORKS_KEY` / `FIREWORKS_MODELS` | `fireworks-key`, `fireworks-models` | | | Wired |
| `HYPERBOLIC_KEY` / `HYPERBOLIC_MODELS` | `Hyperbolic-key`, `hyperbolic-models` | | | Wired |
| `DASHSCOPE_API_KEY` | `dashscope-api-key` | | | Wired |
| `MISTRAL_API_KEY` | `mistral-api-key` | | | Wired |
| `HF_TOKEN` | `Hf-token` | | | Wired (auth OK; some HF-router model IDs may 400) |

Re-run probes after any secret change (then redeploy):

```bash
./scripts/run_verify_with_gcp_secrets.sh
```

Or load secrets manually:

```bash
export Cloudflare_Api_Key=$(gcloud secrets versions access latest --secret=cloudflare-api-key --project=llmhive-orchestrator)
export Kimi_K26_Api_Key=$(gcloud secrets versions access latest --secret=kimi-k26-api-key --project=llmhive-orchestrator)
export DeepInfra_Api_Key=$(gcloud secrets versions access latest --secret=deepInfra_api_key --project=llmhive-orchestrator)
export GEMINI_API_KEY_2=$(gcloud secrets versions access latest --secret=gemini-api-key-2 --project=llmhive-orchestrator)
python3 scripts/verify_direct_providers.py
```

## Phase 3 backlog

| Provider | Status |
|----------|--------|
| Replicate | Not wired |
| Qwen Cloud (DashScope) | **Wired** — `dashscope_client` + catalog |
| Moonshot (Kimi) | **Wired** — account funded; use [platform.kimi.ai](https://platform.kimi.ai) for billing |
| Cloudflare Workers AI | **Wired** — requires `Cloudflare_Account_ID` for chat |
| Fireworks / Hyperbolic / DeepInfra / Mistral / HF | **Wired** in ROUTING_V2 + spillover registry |

## ROUTING_V2 (wired 2026-05-19)

When `ROUTING_V2_ENABLED=true` (default) and the model is a **free slug** (`:free` or in `FREE_MODELS_DB` / catalog sync):

- **Direct APIs are tried first** (cost-ordered: Google, DeepSeek, Groq, Cerebras, Kimi, DashScope, Cloudflare, DeepInfra, Fireworks, Hyperbolic, Azure Foundry, Together, HuggingFace, Mistral).
- **OpenRouter is last** in the chain (spillover when direct quotas throttle).
- **Elite/paid models** are unchanged — still OpenRouter-primary when the gateway is configured.

Clients: `dashscope_client`, `deepinfra_client`, `azure_foundry_client`, `cloudflare_client`, `kimi_client`, `mistral_client`, `hf_provider` + existing Fireworks/Hyperbolic/Groq/Cerebras.

Kimi OpenRouter slugs (`moonshotai/kimi-k2.6:free`, etc.) map via `scripts/kimi-models.json` → direct `kimi-k2.6` at startup (`direct_provider_catalog_sync`).

Disable spillover-first for debugging: `ROUTING_V2_ENABLED=false`.
