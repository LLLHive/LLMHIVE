# Healthz Endpoint Fix

## Issue
The `/healthz` endpoint was returning 404, even though it was defined in `main.py`.

## Root Cause
FastAPI routes are matched in the order they're registered. The `/healthz` route was defined after the root `/` route, and there may have been a route matching order issue.

## Solution
Moved the `/healthz` route definition to be registered **before** the root `/` route to ensure it's matched first.

### Changes Made
1. Moved `HEALTH_PAYLOAD` definition to the top
2. Moved `/healthz` GET and HEAD route definitions before the root `/` route
3. This ensures health check endpoints are registered first and matched before other routes

### Code Changes
```python
# Before: /healthz was defined after /
@app.get("/", ...)
async def root(): ...

@app.get("/healthz", ...)
async def health_check(): ...

# After: /healthz is defined before /
@app.get("/healthz", ...)
async def health_check(): ...

@app.get("/", ...)
async def root(): ...
```

## Testing
After deployment, test with:
```bash
curl https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz
# Expected: {"status":"ok"}
```

## Status
- Build: ✅ SUCCESS (ID: `8a8e3e61-85e8-4ecf-bb26-da15a82bd39c`)
- Deployment: In progress
- Expected: `/healthz` should now return `{"status":"ok"}`

