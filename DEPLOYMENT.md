# LLMHive Orchestrator Deployment Guide

## Prerequisites

- Google Cloud Project with Cloud Run enabled
- Docker installed (for local testing)
- gcloud CLI installed and authenticated
- API keys for desired LLM providers

## Understanding the Service

The LLMHive Orchestrator can run in two modes:

1. **Stub Mode** (default): Returns placeholder responses. Useful for testing deployment.
2. **Production Mode**: Connects to real LLM providers using API keys.

## Quick Start - Deploy to Cloud Run

### Option 1: Using Cloud Build (Recommended)

1. **Trigger the build and deployment:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

2. **Add API keys after deployment:**
   ```bash
   gcloud run services update llmhive-orchestrator \
     --region=us-east1 \
     --update-env-vars=OPENAI_API_KEY=your-openai-key-here
   ```

### Option 2: Manual Deployment with API Keys

Deploy with environment variables directly:

```bash
# Build the Docker image
gcloud builds submit --tag gcr.io/PROJECT_ID/llmhive-orchestrator

# Deploy with API keys
gcloud run deploy llmhive-orchestrator \
  --image gcr.io/PROJECT_ID/llmhive-orchestrator \
  --region us-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars=OPENAI_API_KEY=your-key,ANTHROPIC_API_KEY=your-key \
  --timeout=300 \
  --port=8080
```

## Configuring LLM Providers

### Supported Providers

The orchestrator supports the following providers:

| Provider | Environment Variable | Models Supported |
|----------|---------------------|------------------|
| OpenAI | `OPENAI_API_KEY` | gpt-4, gpt-3.5-turbo, gpt-4o, etc. |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-opus, claude-3-sonnet, etc. |
| Grok (xAI) | `GROK_API_KEY` | grok-beta, etc. |
| Google Gemini | `GEMINI_API_KEY` | gemini-pro, gemini-ultra, etc. |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat, deepseek-coder, etc. |
| Manus | `MANUS_API_KEY` | Various proxied models |

### Adding API Keys

#### Method 1: Environment Variables (Simple)

```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --update-env-vars=OPENAI_API_KEY=sk-...,ANTHROPIC_API_KEY=sk-ant-...
```

#### Method 2: Secret Manager (Recommended for Production)

1. **Create secrets in Secret Manager:**
   ```bash
   echo -n "your-openai-key" | gcloud secrets create OPENAI_API_KEY \
     --project=llmhive-orchestrator \
     --data-file=-
   echo -n "your-anthropic-key" | gcloud secrets create ANTHROPIC_API_KEY \
     --project=llmhive-orchestrator \
     --data-file=-
   ```

2. **Grant Cloud Run access to secrets:**
   ```bash
   gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
     --project=llmhive-orchestrator \
     --role="roles/secretmanager.secretAccessor" \
     --member="serviceAccount:llmhive-orchestrator@llmhive-orchestrator.iam.gserviceaccount.com"
   
   gcloud secrets add-iam-policy-binding ANTHROPIC_API_KEY \
     --project=llmhive-orchestrator \
     --role="roles/secretmanager.secretAccessor" \
     --member="serviceAccount:llmhive-orchestrator@llmhive-orchestrator.iam.gserviceaccount.com"
   ```

3. **Update Cloud Run service to use secrets:**
   ```bash
   gcloud run services update llmhive-orchestrator \
     --project=llmhive-orchestrator \
     --region=us-east1 \
     --update-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest
   ```

   **Note:** The `cloudbuild.yaml` is already configured to mount the `OPENAI_API_KEY` secret. If you've created the secret in Secret Manager and granted the necessary permissions, the secret will be automatically available on the next deployment via Cloud Build.

#### Method 3: Update cloudbuild.yaml

The `cloudbuild.yaml` is already configured to mount the `OPENAI_API_KEY` secret from Secret Manager:

```yaml
- '--update-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest'
```

To add additional API keys (e.g., Anthropic), edit the `cloudbuild.yaml` deploy step and add more secret mappings:

```yaml
- '--update-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest'
```

Alternatively, you can use plain environment variables (not recommended for production):

```yaml
- '--update-env-vars=ANTHROPIC_API_KEY=your-actual-anthropic-key'
```

After making changes, rebuild and redeploy:
```bash
gcloud builds submit --config cloudbuild.yaml
```

## Verifying Deployment

### 1. Check Health Endpoints

```bash
# Root health check (required by Cloud Run)
curl https://your-service-url.run.app/healthz

# API health check
curl https://your-service-url.run.app/api/v1/healthz
```

Both should return: `{"status":"ok"}`

### 2. Check Provider Configuration

```bash
curl https://your-service-url.run.app/api/v1/orchestration/providers
```

**Without API keys (stub mode):**
```json
{
  "available_providers": ["stub"],
  "provider_model_summary": {"stub": []}
}
```

**With API keys configured:**
```json
{
  "available_providers": ["openai", "anthropic", "grok", "stub"],
  "provider_model_summary": {
    "openai": [...],
    "anthropic": [...],
    ...
  }
}
```

### 3. Test Orchestration

```bash
curl -X POST https://your-service-url.run.app/api/v1/orchestration/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of France?",
    "models": ["gpt-4", "claude-3-sonnet"]
  }'
```

## Troubleshooting

### Issue: `/healthz` returns 404

**Symptoms:** 
- `/` endpoint works
- `/api/v1/healthz` works
- But `/healthz` returns 404

**Cause:**
This issue was caused by Docker build cache in CloudBuild. The `/healthz` endpoint was added to the code, but cached Docker layers from previous builds were being reused, causing the old code (without the endpoint) to be deployed.

**Fix:**
The `cloudbuild.yaml` has been updated to include the `--no-cache` flag, which ensures fresh builds without using cached layers. Make sure you're using the latest version from the repository (commit 84b0a6f or later).

**To apply the fix:**
```bash
# 1. Pull the latest code with the fix
git pull

# 2. Redeploy with the updated cloudbuild.yaml (which includes --no-cache)
gcloud builds submit --config cloudbuild.yaml

# 3. Get your service URL
SERVICE_URL=$(gcloud run services describe llmhive-orchestrator --region=us-east1 --format='value(status.url)')
echo "Service URL: $SERVICE_URL"

# 4. Test the endpoint (should return {"status":"ok"})
curl $SERVICE_URL/healthz

# 5. Check deployment logs to verify the new revision
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator" --limit 50
```

### Issue: Only Getting Stub Responses

**Symptoms:**
- All responses start with "This is a stub response..."
- `/api/v1/orchestration/providers` only shows "stub"

**Cause:** No API keys configured

**Solution:**
1. Add API keys using one of the methods above
2. Verify with the providers endpoint
3. Check Cloud Run logs for provider initialization messages

### Issue: Provider Not Initializing

**Check the logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator" --limit 50 --format=json
```

Look for messages like:
- "OpenAI provider configured" ✓ Good
- "OpenAI provider not configured; skipping" ✗ Missing API key

## Local Testing

### Using Docker

1. **Build the image:**
   ```bash
   docker build -t llmhive-orchestrator .
   ```

2. **Run with API keys:**
   ```bash
   docker run -p 8080:8080 \
     -e OPENAI_API_KEY=your-key \
     -e ANTHROPIC_API_KEY=your-key \
     llmhive-orchestrator
   ```

3. **Test endpoints:**
   ```bash
   curl http://localhost:8080/healthz
   curl http://localhost:8080/api/v1/orchestration/providers
   ```

### Using Python directly

1. **Install dependencies:**
   ```bash
   cd llmhive
   pip install -e .
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run the application:**
   ```bash
   cd llmhive
   uvicorn llmhive.app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

## Production Checklist

Before deploying to production:

- [ ] API keys are stored in Secret Manager (not plain text)
- [ ] Service account has minimal required permissions
- [ ] Health checks are configured and passing
- [ ] Monitoring and logging are enabled
- [ ] Timeout values are appropriate (300s recommended)
- [ ] Concurrency settings are tested under load
- [ ] Database URL is configured for production (not SQLite)
- [ ] CORS settings are reviewed for security
- [ ] Authentication is enabled if needed (remove `--allow-unauthenticated`)

## Monitoring

### Key Metrics to Watch

1. **Request latency**: Should be under 30s for most requests
2. **Error rate**: Should be < 1%
3. **Provider availability**: Check provider status regularly
4. **Instance count**: Monitor for autoscaling behavior

### Setting Up Alerts

```bash
# Example: Alert on high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="LLMHive High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

## Support

For issues or questions:
1. Check the logs: `gcloud logging read ...`
2. Verify provider configuration: `/api/v1/orchestration/providers`
3. Test health endpoints: `/healthz` and `/api/v1/healthz`
4. Review this deployment guide
