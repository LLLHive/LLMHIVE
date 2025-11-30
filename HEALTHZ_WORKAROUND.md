# Healthz Endpoint 404 Issue - Workaround

## Current Status
- `/healthz` returns 404 (Google error page)
- `/health` works correctly ✅
- `/` works correctly ✅
- `/api/v1/system/healthz` works (but returns query not found)

## Analysis
The 404 is coming from Google's infrastructure, not FastAPI. This suggests:
1. Cloud Run might have a health check configuration that's intercepting `/healthz`
2. There might be a route conflict at the infrastructure level
3. The route might not be registered despite being in the code

## Workarounds

### Option 1: Use `/health` instead
The `/health` endpoint works perfectly and returns the same response:
```bash
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/health
# Returns: {"status":"ok"}
```

### Option 2: Configure Cloud Run Health Check
Set the health check path in Cloud Run:
```bash
gcloud run services update llmhive-orchestrator \
  --region=us-east1 \
  --health-check-path=/health \
  --project=llmhive-orchestrator
```

### Option 3: Use Root Endpoint
The root endpoint also works:
```bash
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/
# Returns: {"service":"LLMHive Orchestrator API","status":"online","version":"1.0.0"}
```

## Recommendation
Use `/health` as the health check endpoint since it's working correctly and returns the same payload as `/healthz` would.

## Next Steps
1. Configure Cloud Run to use `/health` for health checks
2. Update any monitoring/alerting to use `/health` instead of `/healthz`
3. Document that `/health` is the primary health check endpoint

