# Cloud Run Secret Manager Fix - Manual Steps Required

## Summary

This fix corrects the Cloud Run deployment configuration to use the proper Secret Manager secret IDs. The deployment was failing because it was trying to reference secrets with incorrect IDs.

**Root Cause:** Environment variable names (e.g., `OPENAI_API_KEY`) and Secret Manager secret IDs (e.g., `openai-api-key`) are different things. The deployment was incorrectly trying to use the environment variable name as the secret ID.

## What Was Fixed in Code

The following files have been updated in the repository:

1. **`cloudbuild.yaml`** - Fixed the `--set-secrets` parameter to map environment variables to correct secret IDs
2. **`DEPLOYMENT.md`** - Updated documentation to show correct secret creation and usage
3. **`OPENAI_API_KEY_FIX.md`** - Updated to reflect correct secret naming convention
4. **`llmhive/cloudrun.yaml`** - Added example showing proper secret configuration

## Manual Steps Required

**Prerequisites:**
- You need the following IAM permissions in the `llmhive-orchestrator` GCP project:
  - `secretmanager.secrets.create` or `secretmanager.secrets.get` (to create/verify secrets)
  - `secretmanager.secrets.setIamPolicy` (to grant access)
  - `run.services.get` and `run.services.update` (to update Cloud Run)
- If you don't have these permissions, share this document with your GCP administrator

Before the next deployment, you need to ensure the secrets exist in Secret Manager with the correct IDs:

### Step 1: Set your project

```bash
gcloud config set project llmhive-orchestrator
```

### Step 2: Verify secret IDs

Check what secrets currently exist:

```bash
gcloud secrets list --format='table(name)'
```

**Expected output:** You should see `openai-api-key`, `grok-api-key`, `gemini-api-key` (lowercase with hyphens).

**If you see uppercase names like `OPENAI_API_KEY`**, you have two options:

#### Option A: Create new secrets with correct IDs (Recommended if you're rotating keys)

```bash
# Create new secrets with correct IDs
echo -n "your-actual-openai-key" | gcloud secrets create openai-api-key \
  --project=llmhive-orchestrator \
  --data-file=-

echo -n "your-actual-grok-key" | gcloud secrets create grok-api-key \
  --project=llmhive-orchestrator \
  --data-file=-

echo -n "your-actual-gemini-key" | gcloud secrets create gemini-api-key \
  --project=llmhive-orchestrator \
  --data-file=-
```

Then delete the old secrets (after confirming the new ones work):
```bash
gcloud secrets delete OPENAI_API_KEY --project=llmhive-orchestrator
gcloud secrets delete GROK_API_KEY --project=llmhive-orchestrator
gcloud secrets delete GEMINI_API_KEY --project=llmhive-orchestrator
```

#### Option B: Copy existing secrets to new IDs (If you want to keep the same keys)

```bash
# Get the existing secret values and create new secrets
gcloud secrets versions access latest --secret=OPENAI_API_KEY | \
  gcloud secrets create openai-api-key --data-file=-

gcloud secrets versions access latest --secret=GROK_API_KEY | \
  gcloud secrets create grok-api-key --data-file=-

gcloud secrets versions access latest --secret=GEMINI_API_KEY | \
  gcloud secrets create gemini-api-key --data-file=-
```

### Step 3: Grant Cloud Run access to the secrets

```bash
# Get your Cloud Run service details
gcloud run services list --platform=managed --format='table(LOCATION,NAME,URL)'
```

Note the LOCATION (region, likely `us-east1`) and NAME (likely `llmhive-orchestrator`), then:

```bash
REGION="us-east1"  # Update if different
SERVICE="llmhive-orchestrator"  # Update if different

# Get the runtime service account
RUNTIME_SA=$(gcloud run services describe "$SERVICE" --region="$REGION" \
  --format='value(spec.template.spec.serviceAccountName)')

echo "Service Account: $RUNTIME_SA"

# Grant access to each secret
for SECRET in openai-api-key grok-api-key gemini-api-key; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --project=llmhive-orchestrator \
    --role="roles/secretmanager.secretAccessor" \
    --member="serviceAccount:$RUNTIME_SA"
done
```

### Step 4: Deploy the fixed configuration

Now deploy using the fixed `cloudbuild.yaml`:

```bash
gcloud builds submit --config cloudbuild.yaml --project=llmhive-orchestrator
```

Or manually update the service:

```bash
gcloud run services update "$SERVICE" --region="$REGION" \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest,GROK_API_KEY=grok-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest
```

### Step 5: Verify the mapping

```bash
gcloud run services describe "$SERVICE" --region="$REGION" \
  --format='table(
    spec.template.spec.containers[0].env[].name:label=ENV,
    spec.template.spec.containers[0].env[].valueFrom.secretKeyRef.name:label=SECRET,
    spec.template.spec.containers[0].env[].valueFrom.secretKeyRef.key:label=VERSION)'
```

You should see:
```
ENV              SECRET           VERSION
OPENAI_API_KEY   openai-api-key   latest
GROK_API_KEY     grok-api-key     latest
GEMINI_API_KEY   gemini-api-key   latest
```

## What if I Can't Execute These Steps?

If you don't have access to execute these gcloud commands, here's what needs to be communicated to whoever manages the GCP project:

### For the GCP Administrator:

1. **Create or rename these secrets in Secret Manager:**
   - `openai-api-key` (lowercase with hyphens)
   - `grok-api-key` (lowercase with hyphens)
   - `gemini-api-key` (lowercase with hyphens)

2. **Grant the Cloud Run service account read access:**
   - Role: `roles/secretmanager.secretAccessor`
   - Secrets: `openai-api-key`, `grok-api-key`, `gemini-api-key`
   - Member: The service account used by the `llmhive-orchestrator` Cloud Run service

3. **Update the Cloud Run service with the correct secret mappings:**
   ```
   --set-secrets=OPENAI_API_KEY=openai-api-key:latest,GROK_API_KEY=grok-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest
   ```

## Key Concepts

- **Environment Variable Name**: What your application code reads (e.g., `OPENAI_API_KEY`) - uses uppercase with underscores
- **Secret Manager Secret ID**: The name of the secret in GCP Secret Manager (e.g., `openai-api-key`) - uses lowercase with hyphens
- **Mapping Format**: `ENV_VAR_NAME=secret-id:version`

Example: `OPENAI_API_KEY=openai-api-key:latest` means:
- App reads from environment variable `OPENAI_API_KEY`
- Cloud Run populates it from Secret Manager secret `openai-api-key`
- Using version `latest`

## Troubleshooting

If deployment still fails with "Secret not found":

1. Verify secret exists: `gcloud secrets describe openai-api-key`
2. Check permissions: `gcloud secrets get-iam-policy openai-api-key`
3. Confirm service account: `gcloud run services describe llmhive-orchestrator --format='value(spec.template.spec.serviceAccountName)'`
4. Check the exact error message in Cloud Build logs

## Security Notes

- ✅ The code changes do NOT expose any secrets
- ✅ All secrets remain in Secret Manager
- ✅ Only the mapping configuration was fixed
- ⚠️ When you rotate keys (recommended after the leak), update the secrets in Secret Manager and redeploy
