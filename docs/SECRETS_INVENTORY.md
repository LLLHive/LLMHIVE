# LLMHIVE Secrets Inventory

This document lists all secrets required for the application to function correctly.
**Keep this in sync with `cloudbuild.yaml`!**

## How Secrets Work

1. **Secret values** are stored in Google Cloud Secret Manager (persist across deployments)
2. **cloudbuild.yaml** tells Cloud Run which secrets to inject as environment variables
3. **The app** reads secrets via `os.getenv("SECRET_NAME")`

⚠️ **Important**: If you add a secret manually to Cloud Run, you MUST also add it to
`cloudbuild.yaml` or it will be lost on the next deployment!

---

## Required Secrets (24 total)

### LLM Provider API Keys

| Environment Variable | Secret Manager ID | Required | Notes |
|---------------------|-------------------|----------|-------|
| `OPENAI_API_KEY` | `openai-api-key` | Yes | GPT models |
| `ANTHROPIC_API_KEY` | `anthropic-api-key` | Yes | Claude models |
| `GROK_API_KEY` | `grok-api-key` | Optional | xAI Grok |
| `GEMINI_API_KEY` | `gemini-api-key` | Yes | Google Gemini |
| `DEEPSEEK_API_KEY` | `deepseek-api-key` | Optional | DeepSeek |
| `OPENROUTER_API_KEY` | `open-router-key` | Yes | Model routing |

### Search & Tools

| Environment Variable | Secret Manager ID | Required | Notes |
|---------------------|-------------------|----------|-------|
| `TAVILY_API_KEY` | `tavily-api-key` | Yes | Web search |
| `API_KEY` | `api-key` | Yes | Internal API auth |

### Pinecone Vector Database

| Environment Variable | Secret Manager ID | Required | Notes |
|---------------------|-------------------|----------|-------|
| `PINECONE_API_KEY` | `pinecone-api-key` | Yes | Main Pinecone key |
| `PINECONE_HOST_ORCHESTRATOR_KB` | `pinecone-host-orchestrator-kb` | Yes | Knowledge base |
| `PINECONE_HOST_MODEL_KNOWLEDGE` | `pinecone-host-model-knowledge` | Yes | Model metadata |
| `PINECONE_HOST_MEMORY` | `pinecone-host-memory` | Yes | Conversation memory |
| `PINECONE_HOST_RLHF_FEEDBACK` | `pinecone-host-rlhf-feedback` | Yes | User feedback |
| `PINECONE_HOST_AGENTIC_QUICKSTART_TEST` | `pinecone-host-agentic-quickstart-test` | Optional | Testing |

### Stripe Payments

| Environment Variable | Secret Manager ID | Required | Notes |
|---------------------|-------------------|----------|-------|
| `STRIPE_SECRET_KEY` | `stripe-secret-key` | Yes | Backend API key |
| `STRIPE_WEBHOOK_SECRET` | `stripe-webhook-secret` | Yes | Webhook verification |
| `STRIPE_PUBLISHABLE_KEY` | `stripe-publishable-key` | Yes | Frontend key |
| `STRIPE_PRICE_ID_BASIC_MONTHLY` | `stripe-price-id-basic-monthly` | Yes | Pricing |
| `STRIPE_PRICE_ID_BASIC_ANNUAL` | `stripe-price-id-basic-annual` | Yes | Pricing |
| `STRIPE_PRICE_ID_PRO_MONTHLY` | `stripe-price-id-pro-monthly` | Yes | Pricing |
| `STRIPE_PRICE_ID_PRO_ANNUAL` | `stripe-price-id-pro-annual` | Yes | Pricing |
| `STRIPE_PRICE_ID_ENTERPRISE_MONTHLY` | `stripe-price-id-enterprise-monthly` | Yes | Pricing |
| `STRIPE_PRICE_ID_ENTERPRISE_ANNUAL` | `stripe-price-id-enterprise-annual` | Yes | Pricing |

### Authentication

| Environment Variable | Secret Manager ID | Required | Notes |
|---------------------|-------------------|----------|-------|
| `CLERK_SECRET_KEY` | `clerk-secret-key` | Yes | Auth backend |

---

## Adding a New Secret

### 1. Create in Secret Manager

```bash
# Create the secret
gcloud secrets create my-secret-id --replication-policy="automatic"

# Add the value
echo -n "secret-value-here" | gcloud secrets versions add my-secret-id --data-file=-
```

### 2. Add to cloudbuild.yaml

Add to the `--update-secrets` list:

```yaml
MY_ENV_VAR=my-secret-id:latest,\
```

### 3. Update this inventory

Add a row to the appropriate table above.

### 4. Commit and push

```bash
git add cloudbuild.yaml docs/SECRETS_INVENTORY.md
git commit -m "feat: Add MY_ENV_VAR secret"
git push origin main
```

---

## Verifying Secrets in Production

### Check Cloud Run Configuration

```bash
gcloud run services describe llmhive-orchestrator --region us-east1 \
  --format='table(spec.template.spec.containers[0].env[].name)'
```

### Check Secret Manager

```bash
gcloud secrets list --filter="name:projects/*/secrets/*"
```

---

## Troubleshooting

### Symptom: Secret exists in Secret Manager but app can't read it

**Cause**: Secret not listed in `cloudbuild.yaml`

**Fix**: Add the secret mapping to `--update-secrets` in `cloudbuild.yaml`

### Symptom: Secret was working but disappeared after deployment

**Cause**: `cloudbuild.yaml` was edited and the secret was accidentally removed

**Fix**: 
1. Restore the secret to `cloudbuild.yaml`
2. Push changes
3. Redeploy

### Symptom: "Secret not found" error during deployment

**Cause**: Secret doesn't exist in Secret Manager yet

**Fix**: Create the secret first:
```bash
gcloud secrets create secret-id --replication-policy="automatic"
gcloud secrets versions add secret-id --data-file=- <<< "value"
```
