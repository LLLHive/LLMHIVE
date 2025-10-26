# OpenAI API Key Configuration Fix

## Summary

This fix addresses the "Service Unavailable" error in the Cloud Run service `llmhive-orchestrator` by properly configuring the `OPENAI_API_KEY` to be loaded from Google Cloud Secret Manager.

## Changes Made

### 1. Updated `app/app.py`
- Modified the startup event to load `OPENAI_API_KEY` from Secret Manager if not already set via environment variable
- Added informative logging for successful secret loading and graceful warnings for missing secrets
- The application can now run in two modes:
  - **Production Mode**: With valid API keys from Secret Manager
  - **Stub Mode**: Without API keys (for testing/development)

### 2. Updated `cloudbuild.yaml`
- Added `--update-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest` to the Cloud Run deployment configuration
- This ensures that Cloud Run automatically mounts the secret from Secret Manager as an environment variable

### 3. Updated `DEPLOYMENT.md`
- Corrected the secret naming convention to use `OPENAI_API_KEY` (uppercase) consistently
- Added the correct project ID and service account for the `llmhive-orchestrator` project
- Clarified that `cloudbuild.yaml` is already configured for `OPENAI_API_KEY`

## Manual Steps Required

**These steps MUST be completed manually before the fix will work:**

### Step 1: Create the Secret in Google Cloud Secret Manager

```bash
# Replace YOUR_OPENAI_API_KEY_VALUE with your actual OpenAI API key
echo -n "YOUR_OPENAI_API_KEY_VALUE" | gcloud secrets create OPENAI_API_KEY \
    --project=llmhive-orchestrator \
    --data-file=-
```

### Step 2: Grant the Cloud Run Service Account Access to the Secret

```bash
gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
    --project=llmhive-orchestrator \
    --role="roles/secretmanager.secretAccessor" \
    --member="serviceAccount:llmhive-orchestrator@llmhive-orchestrator.iam.gserviceaccount.com"
```

### Step 3: Deploy the Changes

After completing Steps 1 and 2, trigger a new deployment:

```bash
# Option A: Using Cloud Build (recommended)
gcloud builds submit --config cloudbuild.yaml --project=llmhive-orchestrator

# Option B: Manual deployment
gcloud run services update llmhive-orchestrator \
    --project=llmhive-orchestrator \
    --region=us-east1 \
    --update-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest
```

## Verification

After deployment, verify the service is working:

1. **Check the health endpoint:**
   ```bash
   curl https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz
   ```
   Should return: `{"status":"ok"}`

2. **Check the logs for successful secret loading:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision \
       AND resource.labels.service_name=llmhive-orchestrator \
       AND jsonPayload.message:OPENAI_API_KEY" \
       --project=llmhive-orchestrator \
       --limit=10 \
       --format=json
   ```
   Look for: `"OPENAI_API_KEY loaded from Secret Manager."`

3. **Test the OpenAI provider:**
   ```bash
   curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/api/v1/orchestration/ \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What is 2+2?", "models": ["gpt-4"]}'
   ```

## How It Works

The solution provides a two-tier approach for loading the API key:

### Tier 1: Cloud Run Native Secret Mounting (Recommended)
- Cloud Run automatically mounts the secret from Secret Manager as an environment variable
- The secret is available at container startup
- This is the most secure and efficient method
- Configured via `cloudbuild.yaml`: `--update-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest`

### Tier 2: Fallback via Secret Manager API
- If the environment variable is not set, the startup event will attempt to fetch the secret using the Secret Manager API
- This provides backward compatibility and flexibility
- Implemented in `app/app.py` startup event

## Troubleshooting

### Issue: "OPENAI_API_KEY secret could not be loaded"

**Possible causes:**
1. The secret `OPENAI_API_KEY` doesn't exist in Secret Manager
2. The service account doesn't have permission to access the secret
3. The secret name or project ID is incorrect

**Solution:**
- Verify the secret exists: `gcloud secrets describe OPENAI_API_KEY --project=llmhive-orchestrator`
- Check IAM permissions: `gcloud secrets get-iam-policy OPENAI_API_KEY --project=llmhive-orchestrator`
- Ensure the service account `llmhive-orchestrator@llmhive-orchestrator.iam.gserviceaccount.com` has the `roles/secretmanager.secretAccessor` role

### Issue: Application still using stub responses

**Possible cause:**
The secret is loading, but the value might be incorrect or the OpenAI API key is invalid.

**Solution:**
- Verify the secret value: `gcloud secrets versions access latest --secret=OPENAI_API_KEY --project=llmhive-orchestrator`
- Check Cloud Run logs for OpenAI API errors
- Test the API key directly using the OpenAI CLI or API

## Security Notes

- Never commit API keys directly in code or configuration files
- Always use Secret Manager for production deployments
- The `--update-env-vars` method (plain text) should only be used for development/testing
- Regularly rotate API keys and update the secrets in Secret Manager
- Use the principle of least privilege when granting IAM permissions

## Additional Resources

- [Google Cloud Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Secrets Documentation](https://cloud.google.com/run/docs/configuring/secrets)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
