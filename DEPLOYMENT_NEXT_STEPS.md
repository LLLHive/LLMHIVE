# Deployment Next Steps

## Cloud Run Deployment with Google Cloud Secret Manager

The backend uses Google Cloud Secret Manager to securely store API keys. The secrets are mapped to environment variables in Cloud Run.

### Secret Names in Google Cloud Secret Manager

| Secret Name | Environment Variable | Description |
|-------------|---------------------|-------------|
| `openai-api-key` | `OPENAI_API_KEY` | OpenAI API key for GPT models |
| `anthropic-api-key` | `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `claude-api-key` | `CLAUDE_API_KEY` | Alternative Claude API key |
| `gemini-api-key` | `GEMINI_API_KEY` | Google Gemini API key |
| `grok-api-key` | `GROK_API_KEY` | xAI Grok API key |
| `deepseek-api-key` | `DEEPSEEK_API_KEY` | DeepSeek API key |
| `pinecone-api-key` | `PINECONE_API_KEY` | Pinecone vector database key |
| `stripe-secret-key` | `STRIPE_SECRET_KEY` | Stripe payment key |

### Deploy Backend to Cloud Run

```bash
cd llmhive

gcloud run deploy llmhive-orchestrator \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --timeout=300 \
  --memory=2Gi \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,CLAUDE_API_KEY=claude-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,GROK_API_KEY=grok-api-key:latest,DEEPSEEK_API_KEY=deepseek-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest,STRIPE_SECRET_KEY=stripe-secret-key:latest"
```

### Verify Deployment

1. **Check Service Health**
   ```bash
   curl https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz
   ```

2. **View Current Secret Mappings**
   ```bash
   gcloud run services describe llmhive-orchestrator --region=us-east1 \
     --format='table(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].valueFrom.secretKeyRef.key)'
   ```

3. **Check Logs for Provider Initialization**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator" --limit=50 --project=llmhive-orchestrator
   ```

### Provider Status

| Provider | Key Variable | Status |
|----------|--------------|--------|
| OpenAI | `OPENAI_API_KEY` | ✅ Configured |
| Anthropic/Claude | `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY` | ✅ Configured (both work) |
| Gemini | `GEMINI_API_KEY` | ✅ Configured |
| Grok | `GROK_API_KEY` | ✅ Configured |
| DeepSeek | `DEEPSEEK_API_KEY` | ✅ Configured |
| Pinecone | `PINECONE_API_KEY` | ✅ Configured (for Vector RAG) |
| Stripe | `STRIPE_SECRET_KEY` | ✅ Configured (for billing) |

### Add/Update a Secret in Google Cloud Secret Manager

```bash
# Create a new secret
echo -n "your-api-key-value" | gcloud secrets create secret-name --data-file=-

# Update an existing secret
echo -n "your-new-api-key-value" | gcloud secrets versions add secret-name --data-file=-

# View secret versions
gcloud secrets versions list secret-name
```

### Test Individual Providers

```bash
# Test with DeepSeek
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello", "models": ["deepseek-chat"]}'

# Test with Claude
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello", "models": ["claude-sonnet-4"]}'

# Test with Stripe (billing check)
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/billing/status
```

---

## Files Related to Secrets

| File | Purpose |
|------|---------|
| `llmhive/src/llmhive/app/config.py` | Settings with env var mappings |
| `llmhive/src/llmhive/app/orchestrator.py` | Provider initialization |
| `llmhive/src/llmhive/app/knowledge/pinecone_kb.py` | Pinecone knowledge base |
| `llmhive/src/llmhive/app/billing/payments.py` | Stripe integration |
| `llmhive/k8s/deployment.yaml` | Kubernetes secrets mapping |

