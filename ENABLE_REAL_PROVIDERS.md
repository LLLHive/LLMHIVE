# Enabling Real LLM Providers

## Current Status
✅ Chat endpoint is working  
⚠️ Currently using **stub provider** (placeholder responses)

## Why Stub Provider?
The orchestrator falls back to stub when:
1. No API keys are found in environment variables, OR
2. Provider initialization fails

## Steps to Enable Real Providers

### 1. Verify Secrets Exist in Secret Manager
```bash
# Check if secrets exist
gcloud secrets list --project=llmhive-orchestrator | grep -E "openai|grok|gemini|anthropic"
```

### 2. Verify Secrets Have Values
```bash
# Check if secrets have actual values (first few characters)
gcloud secrets versions access latest --secret="openai-api-key" --project=llmhive-orchestrator | head -c 10
gcloud secrets versions access latest --secret="grok-api-key" --project=llmhive-orchestrator | head -c 10
gcloud secrets versions access latest --secret="gemini-api-key" --project=llmhive-orchestrator | head -c 10
```

### 3. Verify Cloud Run Secret Mapping
The secrets should be mapped as environment variables:
- `OPENAI_API_KEY` → `openai-api-key:latest`
- `GROK_API_KEY` → `grok-api-key:latest`
- `GEMINI_API_KEY` → `gemini-api-key:latest`

### 4. Check Provider Initialization Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator AND textPayload=~'provider.*initialized'" --limit=10 --project=llmhive-orchestrator
```

### 5. Test After Configuration
```bash
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the capital of Cuba?"}'
```

## Expected Behavior

### With Real Providers:
```json
{
  "message": "The capital of Cuba is Havana...",
  "tokens_used": 150,
  "latency_ms": 1200,
  ...
}
```

### With Stub (Current):
```json
{
  "message": "Stub response for: Let's work this out step by step...",
  "tokens_used": 0,
  "latency_ms": 1,
  ...
}
```

## Troubleshooting

### If Providers Still Don't Initialize:

1. **Check Secret Values:**
   - Secrets must have actual API key values (not empty)
   - Keys must be valid and not expired

2. **Check Service Account Permissions:**
   ```bash
   gcloud run services describe llmhive-orchestrator --region=us-east1 \
     --format="value(spec.template.spec.serviceAccountName)"
   ```

3. **Verify Secret Access:**
   ```bash
   gcloud secrets get-iam-policy openai-api-key --project=llmhive-orchestrator
   ```

4. **Check Logs for Errors:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator AND severity>=WARNING" --limit=20 --project=llmhive-orchestrator
   ```

## Status
- ✅ Orchestrator implementation: Complete
- ✅ Chat endpoint: Working
- ⏭️ Real providers: Need API keys configured

