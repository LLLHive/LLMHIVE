# Workload Identity Federation Setup for GitHub Actions

## Overview

Workload Identity Federation (WIF) allows GitHub Actions to authenticate to Google Cloud without storing long-lived service account keys. Instead, GitHub Actions gets short-lived tokens that are automatically rotated.

**Benefits over service account keys:**
- ✅ No secrets to store or rotate
- ✅ Short-lived credentials (1 hour by default)
- ✅ Better audit trail
- ✅ No risk of key leakage
- ✅ Google's recommended approach

## Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated
- Owner or IAM Admin role on the GCP project
- Admin access to the GitHub repository

## Setup Steps

### Step 1: Enable Required APIs

```bash
# Set your project
export PROJECT_ID="llmhive-orchestrator"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable iamcredentials.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable sts.googleapis.com
```

### Step 2: Create a Workload Identity Pool

```bash
# Create the pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Get the pool ID
export POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format="value(name)")

echo "Pool ID: $POOL_ID"
```

### Step 3: Create a Workload Identity Provider

```bash
# Replace with your GitHub org and repo
export GITHUB_ORG="LLLHive"
export GITHUB_REPO="LLMHIVE"

# Create the provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'"
```

### Step 4: Create a Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create "github-actions" \
  --project="${PROJECT_ID}" \
  --display-name="GitHub Actions (WIF)"

export SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# For Firestore access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"
```

### Step 5: Allow GitHub Actions to Impersonate the Service Account

```bash
# Get the project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Allow the pool to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"
```

### Step 6: Get the Provider Resource Name

```bash
# Get the full provider name (you'll need this for GitHub)
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

This will output something like:
```
projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

### Step 7: Configure GitHub Repository

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Value |
|-------------|-------|
| `WIF_PROVIDER` | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SERVICE_ACCOUNT` | `github-actions@llmhive-orchestrator.iam.gserviceaccount.com` |

### Step 8: Update GitHub Actions Workflow

Update your workflow to use WIF instead of `GCP_SA_KEY`:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write  # Required for WIF
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      # Continue with your deployment steps...
```

## Verify the Setup

### Test Authentication

Run a manual workflow dispatch to test:

```yaml
name: Test WIF Auth

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - uses: google-github-actions/setup-gcloud@v2
      
      - name: Test GCP Access
        run: |
          echo "Project: $(gcloud config get project)"
          echo "Account: $(gcloud config get account)"
          gcloud run services list --region=us-east1 --limit=1
```

### Check Audit Logs

View authentication events in Cloud Console:
1. Go to IAM & Admin → Audit Logs
2. Filter by `sts.googleapis.com` service
3. Look for `ExchangeToken` operations

## Migration Checklist

- [ ] Enable required APIs (Step 1)
- [ ] Create Workload Identity Pool (Step 2)
- [ ] Create Provider (Step 3)
- [ ] Create or update Service Account (Step 4)
- [ ] Allow impersonation (Step 5)
- [ ] Add `WIF_PROVIDER` secret to GitHub
- [ ] Add `WIF_SERVICE_ACCOUNT` secret to GitHub
- [ ] Update workflow files to use WIF
- [ ] Test with a manual workflow dispatch
- [ ] **After confirming WIF works:** Remove `GCP_SA_KEY` secret from GitHub
- [ ] **After confirming WIF works:** Delete the old service account key in GCP

## Troubleshooting

### "Permission denied" errors

1. Check the service account has the required roles
2. Verify the `principalSet` in Step 5 matches your repo exactly
3. Ensure `id-token: write` permission is set in the workflow

### "Token exchange failed" errors

1. Verify the provider resource name is correct
2. Check the attribute condition in the provider matches your org
3. Ensure the GitHub OIDC token is being generated (check workflow logs)

### "Caller does not have permission" errors

1. Check IAM policy bindings on the service account
2. Verify the workload identity user binding is correct
3. Try re-running Step 5 with the exact repository path

## Rollback

If WIF isn't working and you need to revert temporarily:

1. The old `GCP_SA_KEY` workflow still works if the secret exists
2. Change the auth step back to:
   ```yaml
   - uses: google-github-actions/auth@v2
     with:
       credentials_json: ${{ secrets.GCP_SA_KEY }}
   ```

## Security Best Practices

1. **Use attribute conditions** - Restrict which repos/branches can authenticate
2. **Least privilege** - Only grant necessary roles to the service account
3. **Monitor usage** - Set up alerts for unusual authentication patterns
4. **Rotate service accounts** - Even with WIF, periodically audit and rotate SAs

## Additional Resources

- [Google Cloud Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)

