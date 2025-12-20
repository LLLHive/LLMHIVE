# LLMHive Automated Weekly Improvement System

## Overview

The Automated Improvement System keeps LLMHive up-to-date with the latest AI developments:

| Component | Frequency | Purpose |
|-----------|-----------|---------|
| **Model Sync** | Every 6 hours | Updates model catalog from OpenRouter |
| **Rankings Sync** | Weekly (Sunday 3am UTC) | Syncs category rankings |
| **Research Agent** | Daily (6am UTC) | Scans for AI developments |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Google Cloud Scheduler                          │
│  ┌────────────────────┐    ┌────────────────────┐    ┌────────────┐│
│  │ Every 6 hours      │    │ Weekly (Sun 3am)   │    │ Daily 6am  ││
│  │ Model Sync         │    │ Rankings Sync      │    │ Research   ││
│  └─────────┬──────────┘    └─────────┬──────────┘    └──────┬─────┘│
│            │                         │                       │      │
│            ▼                         ▼                       ▼      │
│  ┌──────────────────────────────────────────────────────────────────┐
│  │              Cloud Run: llmhive-orchestrator                     │
│  │  POST /api/v1/openrouter/sync                                    │
│  │  POST /api/v1/openrouter/admin/run-full-sync                     │
│  │  POST /api/v1/agents/research/execute                            │
│  │                                                                   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐          │
│  │  │ Model Sync  │  │Rankings Sync│  │ Research Agent   │          │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘          │
│  │         │                │                   │                    │
│  │         ▼                ▼                   ▼                    │
│  │  ┌───────────────────────────────────────────────────────────┐   │
│  │  │                    SQLite Database                         │   │
│  │  │  openrouter_models | openrouter_categories                │   │
│  │  │  openrouter_ranking_entries | openrouter_model_alerts     │   │
│  │  └───────────────────────────────────────────────────────────┘   │
│  └──────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Vercel App    │
                    │   (Frontend)    │
                    └─────────────────┘
```

## Setup Instructions

### Step 1: Deploy Backend to Cloud Run

The backend must be deployed with the latest code that includes the initialization endpoints.

```bash
# Trigger Cloud Build manually
gcloud builds submit \
  --config=cloudbuild.yaml \
  --project=YOUR_PROJECT_ID

# Or use the Cloud Console:
# 1. Go to Cloud Build > Triggers
# 2. Click "Run" on the llmhive-orchestrator trigger
```

### Step 2: Initialize the Database

Once the backend is deployed, initialize the database tables and run the first sync:

```bash
# Initialize database and trigger first sync
curl -X POST "https://llmhive-orchestrator-YOUR_PROJECT.us-east1.run.app/api/v1/openrouter/admin/init-db?run_sync=true"

# Expected response:
# {
#   "status": "success",
#   "message": "Database initialization complete",
#   "tables_created": ["openrouter_categories", "openrouter_ranking_snapshots", ...],
#   "sync_triggered": true
# }
```

### Step 3: Set Up Cloud Scheduler Jobs

Run the setup script to create all scheduled jobs:

```bash
# Make script executable (if not already)
chmod +x scripts/setup_cloud_scheduler.sh

# Run with your project ID
./scripts/setup_cloud_scheduler.sh YOUR_PROJECT_ID us-east1
```

This creates three jobs:
- `llmhive-model-sync` - Every 6 hours
- `llmhive-rankings-sync-weekly` - Sunday 3am UTC
- `llmhive-research-agent` - Daily 6am UTC

### Step 4: Verify Setup

```bash
# Check scheduler jobs
gcloud scheduler jobs list --location=us-east1

# Check database status
curl "https://llmhive-orchestrator-YOUR_PROJECT.us-east1.run.app/api/v1/openrouter/rankings/status"

# Manually trigger a sync (optional)
curl -X POST "https://llmhive-orchestrator-YOUR_PROJECT.us-east1.run.app/api/v1/openrouter/admin/run-full-sync?blocking=true"
```

## API Endpoints

### Admin Endpoints (Internal Use)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/openrouter/admin/init-db` | POST | Initialize database tables |
| `/api/v1/openrouter/admin/run-full-sync` | POST | Trigger full rankings sync |
| `/api/v1/openrouter/sync` | POST | Sync model catalog |
| `/api/v1/openrouter/rankings/status` | GET | Get sync status |

### Query Parameters

**init-db:**
- `run_sync` (bool): Whether to run initial sync after creating tables

**run-full-sync:**
- `group` (string): Category group (usecase, language, programming)
- `view` (string): Time range (week, month, day, all)
- `limit` (int): Top N models per category
- `blocking` (bool): Wait for completion vs background

## Database Tables

| Table | Purpose |
|-------|---------|
| `openrouter_models` | Model catalog from OpenRouter |
| `openrouter_endpoints` | Provider endpoints per model |
| `openrouter_categories` | Ranking categories (programming, science, etc.) |
| `openrouter_ranking_snapshots` | Historical ranking snapshots |
| `openrouter_ranking_entries` | Top models per category |
| `openrouter_sync_status` | Sync operation history |
| `openrouter_model_alerts` | Alerts for new models |

## Troubleshooting

### "No such table" errors

The database hasn't been initialized. Run:
```bash
curl -X POST "https://YOUR_SERVICE_URL/api/v1/openrouter/admin/init-db"
```

### Rankings not updating

1. Check Cloud Scheduler jobs are running:
   ```bash
   gcloud scheduler jobs list --location=us-east1
   ```

2. Check sync status:
   ```bash
   curl "https://YOUR_SERVICE_URL/api/v1/openrouter/rankings/status"
   ```

3. Manually trigger a sync:
   ```bash
   curl -X POST "https://YOUR_SERVICE_URL/api/v1/openrouter/admin/run-full-sync?blocking=true"
   ```

### Frontend shows mock data

The frontend falls back to mock data when the backend is unreachable or has no data.
Ensure:
1. Backend is deployed and healthy
2. Database is initialized
3. At least one sync has completed
4. `ORCHESTRATOR_API_BASE_URL` is set in Vercel

## Monitoring

### Logs

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator" --limit=50

# View scheduler job logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit=20
```

### Metrics

- Cloud Run: Request count, latency, error rate
- Cloud Scheduler: Job execution success/failure
- Database: Row counts in rankings tables

## Cost Considerations

- Cloud Scheduler: 3 jobs = ~$0.30/month
- Cloud Run: Pay per request, ~$0-5/month for light usage
- Database: SQLite (no cost) or Cloud SQL (~$10/month minimum)

