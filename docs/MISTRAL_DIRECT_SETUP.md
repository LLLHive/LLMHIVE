# Mistral AI direct connection — step-by-step

Use this to add Mistral as a direct provider (same pattern as DashScope / DeepInfra).

Official docs: [https://docs.mistral.ai](https://docs.mistral.ai)  
Pricing / model IDs: [https://mistral.ai/pricing#api](https://mistral.ai/pricing#api)

---

## Step 1 — Create API key

1. Go to [https://console.mistral.ai](https://console.mistral.ai)
2. Sign in → **API keys** → **Create new key**
3. Copy the key (starts with your workspace secret)

---

## Step 2 — Store in GCP Secret Manager

```bash
export PROJECT=llmhive-orchestrator
export MISTRAL_API_KEY='paste-key-here'

echo -n "$MISTRAL_API_KEY" | gcloud secrets create mistral-api-key \
  --project="$PROJECT" --replication-policy=automatic --data-file=- 2>/dev/null \
  || echo -n "$MISTRAL_API_KEY" | gcloud secrets versions add mistral-api-key \
  --project="$PROJECT" --data-file=-
```

---

## Step 3 — Mount on Cloud Run (`llmhive-orchestrator`)

In **Cloud Run → llmhive-orchestrator → Edit & deploy → Variables & secrets**:

| Name | Secret |
|------|--------|
| `MISTRAL_API_KEY` | `mistral-api-key` |

Or CLI:

```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --project=llmhive-orchestrator \
  --update-secrets=MISTRAL_API_KEY=mistral-api-key:latest
```

---

## Step 4 — Model catalog file

Create `scripts/mistral-models.json` (example — match your console):

```json
{
  "base_url": "https://api.mistral.ai/v1",
  "default_chat": "mistral_small",
  "chat": {
    "mistral_small": "mistral-small-latest",
    "mistral_large": "mistral-large-latest",
    "codestral": "codestral-latest",
    "devstral_small": "devstral-small-latest"
  },
  "openrouter_map": {
    "mistralai/mistral-small-3.1-24b-instruct:free": "mistral_small"
  }
}
```

Optional: store JSON in Secret Manager as `mistral-models` and set env `MISTRAL_MODELS`.

---

## Step 5 — Wire client in code (when ready)

1. Add `llmhive/src/llmhive/app/providers/mistral_client.py` using `CatalogClient` (copy `dashscope_client.py`)
2. Add `P_MISTRAL = "mistral"` in `provider_chain.py` + `Provider.MISTRAL` in `provider_router.py`
3. Register in `provider_router.__init__` and `_dispatch_provider`
4. Export from `providers/__init__.py`
5. Add probe to `scripts/verify_direct_providers.py` (already has `probe_mistral` stub)

---

## Step 6 — Test locally

```bash
export MISTRAL_API_KEY='your-key'
curl -s https://api.mistral.ai/v1/models \
  -H "Authorization: Bearer $MISTRAL_API_KEY" | head

curl -s https://api.mistral.ai/v1/chat/completions \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral-small-latest","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

Or after wiring:

```bash
./scripts/run_verify_with_gcp_secrets.sh
```

---

## Step 7 — Deploy

```bash
./scripts/deploy_orchestrator_routing_v2.sh
```

---

## Recommended model IDs (from Mistral pricing page)

| Use case | API model id |
|----------|----------------|
| Fast / cheap | `mistral-small-latest` |
| Strong general | `mistral-large-latest` |
| Coding | `codestral-latest` |
| Agents / code | `devstral-small-latest` |

Use `-latest` aliases so Mistral can roll forward versions without code changes.
