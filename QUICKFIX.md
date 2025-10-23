# Quick Fix Guide for 404 and Stub Response Issues

This guide addresses the two main issues reported in production:
1. `/healthz` endpoint returning 404
2. Orchestration returning stub responses

> **Note:** This guide uses the production service URL `https://llmhive-orchestrator-792354158895.us-east1.run.app` and service name `llmhive-orchestrator`. Replace these with your actual values if different. You can find your service URL in the Cloud Run console or by running: `gcloud run services describe llmhive-orchestrator --region=us-east1 --format='value(status.url)'`

## Issue #1: `/healthz` Returns 404

### Verification

The `/healthz` endpoint IS properly defined in the code. Tests confirm it works:

```bash
cd llmhive && python -m pytest tests/test_health.py -v
# Result: 3/3 tests pass ✓
```

The startup logs also confirm the route is registered:
```
INFO - Registered routes:
INFO -   GET /healthz  ← Route is registered!
```

### Root Cause

The 404 error from Google (not from the application) indicates that **the latest code may not be deployed** to Cloud Run. This was caused by an incorrect project ID in `cloudbuild.yaml` which has now been fixed.

**Fix Applied:** `cloudbuild.yaml` now uses `$PROJECT_ID` instead of a hardcoded project name, ensuring deployment works correctly.

### Solution

Redeploy the service to Cloud Run with the latest code:

```bash
# From the repository root
# Cloud Build will automatically use your current project ID
gcloud builds submit --config cloudbuild.yaml
```

This will:
1. Build a new Docker image with the latest code
2. Push it to Container Registry
3. Deploy it to Cloud Run

### Verification After Deploy

```bash
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz
# Expected: {"status":"ok"}
```

If still getting 404, check Cloud Run logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator" --limit 50 | grep "Registered routes"
```

You should see: `GET /healthz` in the route list.

## Issue #2: Only Stub Responses

### Current Behavior

```json
{
  "available_providers": ["stub"],
  "provider_model_summary": {"stub": []}
}
```

Orchestration responses show:
```
"This is a stub response. The question '...' would normally be answered by a real LLM provider..."
```

### Root Cause

**This is expected behavior when no LLM provider API keys are configured.**

The orchestrator is working correctly - it falls back to stub provider when no real providers are available. The startup logs confirm this:

```
WARNING - ⚠️  Only stub provider is configured! No real LLM API keys found.
WARNING -    Set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, GROK_API_KEY, etc.
```

### Solution

Configure API keys for at least one LLM provider:

#### Option 1: Quick Fix (Environment Variables)

```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --update-env-vars=OPENAI_API_KEY=sk-your-actual-openai-key-here
```

#### Option 2: Production (Secret Manager - Recommended)

1. Create secret:
```bash
echo -n "sk-your-key" | gcloud secrets create openai-api-key --data-file=-
```

2. Grant access:
```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

3. Update service:
```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --update-secrets=OPENAI_API_KEY=openai-api-key:latest
```

#### Option 3: Via cloudbuild.yaml

Edit `cloudbuild.yaml` and uncomment these lines:
```yaml
# - '--update-env-vars=OPENAI_API_KEY=your-actual-openai-key'
```

Then rebuild:
```bash
gcloud builds submit --config cloudbuild.yaml
```

### Verification After Adding Keys

1. Check providers:
```bash
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/orchestration/providers
```

Expected (with OpenAI configured):
```json
{
  "available_providers": ["openai", "stub"],
  "provider_model_summary": {
    "openai": ["gpt-4", "gpt-3.5-turbo", ...],
    "stub": []
  }
}
```

2. Test orchestration:
```bash
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/orchestration/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is 2+2?","models":["gpt-4"]}'
```

You should now get real responses instead of stub messages.

3. Check logs:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 50 | grep -A2 "provider"
```

Look for: `INFO - ✓ 1 real provider(s) configured`

## Supported Provider API Keys

| Provider | Environment Variable | Example Model |
|----------|---------------------|---------------|
| OpenAI | `OPENAI_API_KEY` | gpt-4, gpt-3.5-turbo |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-opus |
| Grok (xAI) | `GROK_API_KEY` | grok-beta |
| Google Gemini | `GEMINI_API_KEY` | gemini-pro |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| Manus | `MANUS_API_KEY` | various |

You can configure multiple providers at once:
```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --update-env-vars=OPENAI_API_KEY=sk-...,ANTHROPIC_API_KEY=sk-ant-...,GROK_API_KEY=xai-...
```

## Complete Deployment Guide

For comprehensive deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Summary

### To Fix 404 Error
```bash
gcloud builds submit --config cloudbuild.yaml
```

### To Fix Stub Responses
```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --update-env-vars=OPENAI_API_KEY=your-key
```

### Verify Both Fixes
```bash
# Check health
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz

# Check providers  
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/orchestration/providers

# Test orchestration
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/orchestration/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello","models":["gpt-4"]}'
```
