# LLMHive Backend Deployment Guide

This guide covers deploying the LLMHive Python backend to Google Cloud Run.

## Prerequisites

1. **Google Cloud SDK** installed and authenticated
   ```bash
   # Install gcloud CLI
   # macOS
   brew install --cask google-cloud-sdk
   
   # Authenticate
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Docker** installed (for local testing)

3. **Enable required APIs**
   ```bash
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     secretmanager.googleapis.com \
     containerregistry.googleapis.com \
     firestore.googleapis.com
   ```

## Secret Setup

Create all required secrets in Google Secret Manager:

```bash
# API Keys
echo -n "your-openai-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-anthropic-key" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "your-grok-key" | gcloud secrets create grok-api-key --data-file=-
echo -n "your-gemini-key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your-deepseek-key" | gcloud secrets create deepseek-api-key --data-file=-
echo -n "your-tavily-key" | gcloud secrets create tavily-api-key --data-file=-
echo -n "your-pinecone-key" | gcloud secrets create pinecone-api-key --data-file=-

# Internal API key (for frontend-to-backend auth)
echo -n "your-internal-api-key" | gcloud secrets create api-key --data-file=-

# Stripe (for billing)
echo -n "sk_live_..." | gcloud secrets create stripe-secret-key --data-file=-
echo -n "whsec_..." | gcloud secrets create stripe-webhook-secret --data-file=-
```

**Important:** Use `echo -n` to avoid newlines in secrets.

## Deployment Options

### Option 1: Manual Deploy (Quick)

```bash
cd llmhive
./scripts/deploy.sh
```

This will:
1. Build the Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run
4. Run health check

### Option 2: Dry Run (Preview)

```bash
./scripts/deploy.sh --dry-run
```

### Option 3: Local Testing

```bash
./scripts/deploy.sh --local
```

### Option 4: Automated CI/CD (Recommended)

Set up Cloud Build trigger for automatic deployments:

```bash
# Connect GitHub repository
gcloud builds triggers create github \
  --repo-name=LLMHIVE \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=llmhive/cloudbuild.yaml \
  --description="Deploy LLMHive backend on push to main"
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Yes |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No (default: INFO) |
| `ENVIRONMENT` | Environment name (production, staging, development) | No |
| `ALLOW_STUB_PROVIDER` | Enable stub provider for testing | No |
| `PINECONE_INDEX_NAME` | Pinecone index for vector storage | No (default: llmhive-memory) |

### Cloud Run Settings

Current production configuration:
- **Memory:** 2Gi
- **CPU:** 2
- **Min instances:** 0 (scales to zero)
- **Max instances:** 20
- **Timeout:** 300s
- **Concurrency:** 80

## Firestore Setup

> **Note:** If you already have a Firestore database configured, skip this section.

1. Create Firestore database in Native mode (only for new projects):
   ```bash
   gcloud firestore databases create --location=us-east1
   ```

2. Create indexes (optional, for better query performance):
   ```bash
   # The indexes will be auto-created on first query
   ```

**Existing Implementation:** The Firestore integration is already fully implemented in:
- `llmhive/src/llmhive/app/firestore_db.py` - Core client
- `llmhive/src/llmhive/app/services/conversations_firestore.py` - Conversations service
- `llmhive/src/llmhive/app/routers/conversations.py` - API endpoints

## Pinecone Setup

> **Note:** If you already have a Pinecone index configured, skip this section.

1. Create a Pinecone index via the Pinecone Console or CLI (only for new projects):
   ```bash
   pc index create \
     -n llmhive-memory \
     -m cosine \
     -c aws \
     -r us-east-1 \
     --model llama-text-embed-v2 \
     --field_map text=content
   ```

2. Set the `PINECONE_API_KEY` secret in Secret Manager

**Existing Implementation:** The Pinecone integration is already fully implemented in:
- `llmhive/src/llmhive/app/knowledge/pinecone_kb.py` - Knowledge base (859 lines)
- `llmhive/src/llmhive/app/rlhf/pinecone_feedback.py` - RLHF feedback storage
- `llmhive/src/llmhive/app/memory/vector_store.py` - Vector store abstraction
- `llmhive/src/llmhive/app/learning/answer_store.py` - Answer caching

## Monitoring

### View Logs

```bash
# Stream logs
gcloud run services logs read llmhive-orchestrator --region=us-east1 --follow

# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator" --limit=100
```

### Health Check

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe llmhive-orchestrator --region=us-east1 --format='value(status.url)')

# Check health
curl "$SERVICE_URL/health"

# View API docs
open "$SERVICE_URL/docs"
```

### Metrics

View metrics in Cloud Console:
- **Cloud Run > Services > llmhive-orchestrator > Metrics**
- Latency, request count, container instances, memory/CPU usage

## Troubleshooting

### Common Issues

**1. Container fails to start**
```bash
# Check logs for startup errors
gcloud run services logs read llmhive-orchestrator --region=us-east1 --limit=50
```

**2. Secret access denied**
```bash
# Grant Cloud Run access to secrets
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

**3. Firestore connection issues**
- Ensure Firestore API is enabled
- Verify the service account has `roles/datastore.user`

**4. High latency on cold starts**
- Increase `--min-instances` to 1 for warm instances
- Reduce container size by optimizing dependencies

### Rollback

```bash
# List revisions
gcloud run revisions list --service=llmhive-orchestrator --region=us-east1

# Rollback to previous revision
gcloud run services update-traffic llmhive-orchestrator \
  --region=us-east1 \
  --to-revisions=llmhive-orchestrator-PREVIOUS_REVISION=100
```

## Frontend Integration

Update your Vercel environment variables:

```env
# .env.production (Vercel)
ORCHESTRATOR_API_BASE_URL=https://llmhive-orchestrator-HASH-ue.a.run.app
NEXT_PUBLIC_API_BASE_URL=https://llmhive-orchestrator-HASH-ue.a.run.app
LLMHIVE_API_KEY=your-internal-api-key
```

## Cost Optimization

1. **Scale to zero**: Default configuration scales to 0 instances when idle
2. **Right-size resources**: Start with 1Gi/1CPU and scale up as needed
3. **Use Cloud Run min instances**: Set to 0 for dev, 1 for prod to reduce cold starts
4. **Monitor usage**: Set up billing alerts in GCP Console

## Security Best Practices

1. **Never commit secrets** - Use Secret Manager
2. **Use service accounts** - Avoid default compute SA for production
3. **Enable Cloud Armor** - For DDoS protection (optional)
4. **Regular secret rotation** - Rotate API keys periodically
5. **Audit logging** - Enable Data Access audit logs

---

## Quick Deploy Checklist

- [ ] GCP project created and selected
- [ ] Required APIs enabled
- [ ] Secrets created in Secret Manager
- [ ] Firestore database created
- [ ] Pinecone index created
- [ ] Run `./scripts/deploy.sh`
- [ ] Verify health check passes
- [ ] Update frontend env vars
- [ ] Test end-to-end flow

