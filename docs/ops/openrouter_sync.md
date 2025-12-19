# OpenRouter Sync - Operations Guide

## Overview

LLMHive syncs with OpenRouter to maintain an up-to-date model catalog. This enables:
- Dynamic model selection based on current availability
- Accurate pricing for cost calculations
- Automatic discovery of new models
- Category rankings for UI display

## Sync Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Cloud Scheduler │ ──> │  /api/openrouter │ ──> │   OpenRouter    │
│  (every 6 hours) │     │     /sync        │     │      API        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                 │
                                 v
                        ┌─────────────────┐
                        │    PostgreSQL   │
                        │  model_catalog  │
                        └─────────────────┘
```

## Sync Types

### 1. Regular Sync (Every 6 Hours)

**Endpoint**: `POST /api/openrouter/sync`

**What it does**:
- Fetches all models from OpenRouter Models API
- Updates model availability and pricing
- Marks models as inactive if removed
- Updates core ranking dimensions

**Cloud Scheduler Config**:
```bash
gcloud scheduler jobs create http openrouter-sync \
  --location=us-east1 \
  --schedule="0 */6 * * *" \
  --uri="https://YOUR_SERVICE/api/openrouter/sync" \
  --http-method=POST \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT \
  --headers="Content-Type=application/json"
```

### 2. Weekly Research Sync

**Endpoint**: `POST /api/openrouter/sync/research`

**What it does**:
- Full category rankings update
- New model discovery with alerts
- Capability matrix refresh
- Family mapping updates

**Cloud Scheduler Config**:
```bash
gcloud scheduler jobs create http openrouter-weekly-research \
  --location=us-east1 \
  --schedule="0 3 * * 0" \
  --uri="https://YOUR_SERVICE/api/openrouter/sync/research" \
  --http-method=POST \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT \
  --headers="Content-Type=application/json"
```

### 3. Manual Sync

For testing or immediate updates:

```bash
# Background sync (returns immediately)
curl -X POST https://YOUR_SERVICE/api/openrouter/sync \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Blocking sync (waits for completion)
curl -X POST https://YOUR_SERVICE/api/openrouter/sync/blocking \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### 4. CLI Sync

For local development:

```bash
# Full sync
python -m llmhive.app.openrouter.scheduler --sync

# Dry run (no database changes)
python -m llmhive.app.openrouter.scheduler --sync --dry-run
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OPENROUTER_API_KEY | Yes | - | API key for OpenRouter |
| SYNC_MIN_INTERVAL_MINUTES | No | 30 | Minimum time between syncs |
| SYNC_TIMEOUT_SECONDS | No | 300 | Request timeout |
| SYNC_BATCH_SIZE | No | 50 | Models per batch |

### Rate Limiting

OpenRouter has rate limits. The sync respects these by:
- Using exponential backoff on 429 responses
- Batching endpoint checks
- Caching ETag for conditional requests

## Monitoring

### Sync Status Endpoint

```http
GET /api/openrouter/sync/status
```

Response:
```json
{
  "last_sync_time": "2025-12-18T06:00:00Z",
  "last_sync_status": "completed",
  "models_in_catalog": 342,
  "last_sync_duration_seconds": 45.2,
  "next_scheduled_sync": "2025-12-18T12:00:00Z"
}
```

### Logs to Monitor

```bash
# Filter for sync-related logs
gcloud logging read 'resource.type="cloud_run_revision" AND "OpenRouter sync"'
```

Key log messages:
- `Starting OpenRouter sync`: Sync started
- `Synced X models`: Sync completed successfully
- `Sync failed`: Error during sync
- `Rate limited`: Hit OpenRouter rate limit

### Metrics

| Metric | Description |
|--------|-------------|
| `openrouter_sync_duration` | Time taken for sync |
| `openrouter_models_total` | Total models in catalog |
| `openrouter_models_added` | New models this sync |
| `openrouter_sync_errors` | Errors during sync |

## Troubleshooting

### Sync Not Running

1. **Check Cloud Scheduler**:
   ```bash
   gcloud scheduler jobs list --location=us-east1
   gcloud scheduler jobs describe openrouter-sync --location=us-east1
   ```

2. **Check service account permissions**:
   - Needs Cloud Run Invoker role

3. **Check Cloud Run logs**:
   ```bash
   gcloud run services logs read llmhive-backend --limit=50
   ```

### Sync Failing

1. **API Key Issues**:
   - Verify OPENROUTER_API_KEY is set
   - Check key hasn't expired
   - Verify key has read permissions

2. **Rate Limiting**:
   - Check for 429 errors in logs
   - Increase SYNC_MIN_INTERVAL_MINUTES
   - Contact OpenRouter for higher limits

3. **Database Issues**:
   - Check database connectivity
   - Verify migrations are applied
   - Check for deadlocks

### Missing Models

If expected models are missing:

1. **Check if model exists in OpenRouter**:
   ```bash
   curl https://openrouter.ai/api/v1/models | jq '.data[] | select(.id == "model/id")'
   ```

2. **Check if filtered out**:
   - Some models may be marked inactive
   - Check for capability filters

3. **Force refresh**:
   ```bash
   curl -X POST /api/openrouter/sync -d '{"force": true}'
   ```

### Pricing Incorrect

1. **Sync may be stale**: Trigger manual sync
2. **Pricing format changed**: Check OpenRouter API response
3. **Currency conversion**: All prices in USD

## Best Practices

1. **Don't sync too frequently**: Respect rate limits
2. **Monitor sync status**: Set up alerts for failures
3. **Keep bootstrap fallback**: Don't rely 100% on API
4. **Test with dry-run**: Use `dry_run=true` for testing
5. **Version your catalog**: Keep snapshots for rollback

