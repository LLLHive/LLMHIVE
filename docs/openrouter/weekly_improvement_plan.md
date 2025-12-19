# OpenRouter Rankings: Weekly Improvement Plan

This document outlines the automated improvement and validation process for keeping OpenRouter rankings current and accurate.

## 1. Weekly Sync Schedule

### Primary Sync Job
- **Schedule**: Weekly on Sundays at 2:00 AM UTC
- **Endpoint**: `POST /api/openrouter/rankings/sync?full=1`
- **Cloud Scheduler Job**: `openrouter-rankings-full-sync`
- **Operations**:
  1. `discover_categories()` - Find new/removed categories
  2. `sync_model_metadata()` - Update model catalog
  3. `sync_rankings()` - Fetch top 10 per category
  4. `validate_against_openrouter()` - Verify accuracy

### Quick Sync (Every 6 Hours)
- **Schedule**: Every 6 hours
- **Endpoint**: `POST /api/openrouter/sync`
- **Operations**:
  - Update model catalog from OpenRouter Models API
  - Enrich endpoint availability for top models

## 2. Data Synced

### Categories
- **Source**: OpenRouter rankings pages
- **Storage**: `openrouter_categories` table
- **Fields**: slug, display_name, group, parent_slug, depth, is_active
- **Discovery**: Dynamic discovery including nested categories (e.g., marketing/seo)

### Rankings
- **Source**: OpenRouter rankings API/pages
- **Storage**: `openrouter_ranking_snapshots` + `openrouter_ranking_entries`
- **Fields per entry**:
  - rank, model_id, model_name, author
  - tokens, share_pct
  - model_metadata (context_length, pricing, capabilities)

### Models
- **Source**: `https://openrouter.ai/api/v1/models`
- **Storage**: `openrouter_models` table
- **Update frequency**: Every 6 hours

## 3. Validation Step

After each sync, we run validation to ensure accuracy:

```python
async def validate_against_openrouter():
    """
    Validates synced rankings against live OpenRouter data.
    
    Always validates these categories:
    - programming, science, health, legal, marketing
    - marketing/seo, technology, finance, academia, roleplay
    
    Validation checks:
    1. Top 3 models match in order
    2. Model IDs are valid
    3. Share percentages are within 5% tolerance
    
    On mismatch:
    - Creates snapshot with status='failed_validation'
    - Logs ERROR severity alert
    - Returns non-zero exit for manual review
    """
```

## 4. Alerting Policy

### Error Levels

| Level | Condition | Action |
|-------|-----------|--------|
| INFO | Sync completed successfully | Log only |
| WARN | Minor drift detected (<5% share diff) | Log, continue |
| ERROR | Major drift or validation failure | Log, alert, create failed snapshot |
| CRITICAL | Sync completely failed | Alert on-call, require manual review |

### Alert Channels
- **Logs**: All events logged to Cloud Logging
- **Metrics**: Sync duration, success rate, drift % exposed via `/api/openrouter/rankings/status`
- **Monitoring**: Set up Cloud Monitoring alerts for:
  - `sync_duration_seconds > 300`
  - `validation_errors > 0`
  - `rankings_age_hours > 168` (stale data)

## 5. Handling OpenRouter Changes

### If HTML/JSON Structure Changes

1. **Detection**: Validation step will fail
2. **Action**:
   - Check OpenRouter rankings pages manually
   - Update parsing logic in `rankings_client.py`
   - Bump `PARSE_VERSION` in `rankings_sync.py`
   - Update test fixtures in `tests/fixtures/openrouter/`
   - Re-run sync

### If New Categories Appear

- Categories are discovered dynamically via `discover_categories()`
- New categories automatically added with `is_active=True`
- No code changes needed for new categories

### If Models Enter/Leave Rankings

- Rankings are fetched fresh each sync
- Models entering top 10 are automatically included
- Model catalog updated via models API sync

## 6. Measuring Drift & Impact

### Drift Detection

Tracked in `openrouter_ranking_snapshots`:
- `status`: success/fail/partial
- `error`: Drift description if failed
- `raw_payload_hash`: For detecting unchanged data

### Diff Report

Exposed via `GET /api/openrouter/rankings/diff?since=<timestamp>`:

```json
{
  "since": "2025-12-12T00:00:00Z",
  "changes": {
    "categories_added": ["data-analysis"],
    "categories_removed": [],
    "ranking_changes": [
      {
        "category": "programming",
        "model": "openai/gpt-5.2",
        "old_rank": null,
        "new_rank": 1,
        "change_type": "entered"
      },
      {
        "category": "programming",
        "model": "anthropic/claude-3-opus",
        "old_rank": 1,
        "new_rank": 3,
        "change_type": "dropped"
      }
    ]
  }
}
```

### Orchestrator Impact

The orchestrator uses rankings from DB for:
- High-accuracy model selection (verification fallback)
- Category-based routing
- Model team assembly

Performance tracked in `strategy_memory`:
- Strategy outcomes by category
- Model team success rates
- Cost vs. accuracy tradeoffs

## 7. Manual Sync Commands

### Trigger Full Sync
```bash
curl -X POST "https://api.llmhive.ai/api/openrouter/rankings/sync?full=1" \
  -H "Authorization: Bearer $API_KEY"
```

### Validate Rankings
```bash
curl -X POST "https://api.llmhive.ai/api/openrouter/rankings/validate" \
  -H "Authorization: Bearer $API_KEY"
```

### Check Status
```bash
curl "https://api.llmhive.ai/api/openrouter/rankings/status"
```

## 8. Rollback Procedure

If a sync introduces bad data:

1. Query previous successful snapshot:
```sql
SELECT * FROM openrouter_ranking_snapshots 
WHERE category_slug = 'programming' 
  AND status = 'success'
ORDER BY fetched_at DESC
LIMIT 2;
```

2. The UI and orchestrator always use the latest successful snapshot, so bad snapshots with `status='fail'` are automatically excluded.

3. To force a fresh sync:
```bash
curl -X POST "https://api.llmhive.ai/api/openrouter/rankings/sync?full=1"
```

## 9. Maintenance Checklist

### Weekly
- [ ] Review sync logs for warnings
- [ ] Check validation results
- [ ] Verify UI matches OpenRouter

### Monthly
- [ ] Review category list vs OpenRouter
- [ ] Check for deprecated models in rankings
- [ ] Update parsing logic if needed
- [ ] Review orchestrator model selection logs

### Quarterly
- [ ] Full audit of synced data vs OpenRouter
- [ ] Review and update seed categories
- [ ] Performance review of sync job
- [ ] Update documentation

