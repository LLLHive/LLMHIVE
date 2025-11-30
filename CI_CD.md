# CI/CD Pipeline Documentation

## Overview

LLMHive uses GitHub Actions for continuous integration (CI) and continuous deployment (CD). The pipeline automatically runs tests on every push and pull request, and deploys to Google Cloud Run when changes are merged to the `main` branch.

## Pipeline Workflow

### Continuous Integration (CI)

The CI pipeline runs on:
- **Push events** to `main` or `develop` branches
- **Pull requests** targeting `main` or `develop` branches

**CI Steps:**
1. **Checkout code** - Retrieves the latest code from the repository
2. **Set up Python** - Installs Python 3.11 (matching project requirements)
3. **Cache dependencies** - Caches pip dependencies for faster subsequent runs
4. **Install dependencies** - Installs project dependencies from `requirements.txt`
5. **Run tests** - Executes the test suite using pytest
6. **Upload test results** - Stores test artifacts for review

**Test Configuration:**
- Python version: 3.11
- Test framework: pytest with pytest-asyncio
- Test directory: `llmhive/tests/`
- Environment: Uses SQLite for testing (no external dependencies required)

### Continuous Deployment (CD)

The CD pipeline runs **only** when:
- Tests pass successfully
- The event is a **push** (not a pull request)
- The branch is `main`

**CD Steps:**
1. **Authenticate to Google Cloud** - Uses service account credentials from GitHub secrets
2. **Set up Cloud SDK** - Configures gcloud CLI with project credentials
3. **Build Docker image** - Builds the application Docker image
4. **Push to Google Container Registry** - Uploads the image to GCR
5. **Deploy to Cloud Run** - Deploys the new image to the Cloud Run service
6. **Verify deployment** - Performs a health check to ensure the service is running

**Deployment Configuration:**
- Service name: `llmhive-orchestrator`
- Region: `us-east1`
- Platform: Cloud Run (managed)
- Authentication: Public (unauthenticated)
- Resources:
  - Memory: 2Gi
  - CPU: 2
  - Max instances: 10
  - Min instances: 0
  - Timeout: 300 seconds

## Required GitHub Secrets

To enable the CI/CD pipeline, you must configure the following secrets in your GitHub repository:

### Required Secrets

1. **`GCP_PROJECT_ID`**
   - Description: Your Google Cloud Project ID
   - Example: `llmhive-production-12345`
   - How to get: From Google Cloud Console → Project Settings

2. **`GCP_SA_KEY`**
   - Description: Service account JSON key with Cloud Run deployment permissions
   - How to create:
     ```bash
     # Create a service account
     gcloud iam service-accounts create github-actions \
       --display-name="GitHub Actions CI/CD"
     
     # Grant necessary permissions
     gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/run.admin"
     
     gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/storage.admin"
     
     gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/iam.serviceAccountUser"
     
     # Create and download the key
     gcloud iam service-accounts keys create key.json \
       --iam-account=github-actions@PROJECT_ID.iam.gserviceaccount.com
     ```
   - How to add: Copy the entire JSON content and paste it as the secret value

### Optional: Workload Identity Federation (Recommended for Production)

For better security, use Workload Identity Federation instead of service account keys:

1. **`WIF_PROVIDER`** - Workload Identity Pool Provider
2. **`WIF_SERVICE_ACCOUNT`** - Service account email for WIF

See [Google Cloud documentation](https://cloud.google.com/iam/docs/workload-identity-federation) for setup instructions.

## Secret Manager Configuration

The deployment uses Google Cloud Secret Manager for API keys. Ensure these secrets exist in Secret Manager:

- `openai-api-key`
- `anthropic-api-key`
- `grok-api-key`
- `gemini-api-key`
- `tavily-api-key`
- `deepseek-api-key`
- `manus-api-key`

To create a secret:
```bash
echo -n "your-api-key" | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy="automatic"
```

## Workflow File Location

The CI/CD workflow is defined in:
```
.github/workflows/ci-cd.yaml
```

## Customizing the Pipeline

### Changing Python Version

Edit `.github/workflows/ci-cd.yaml`:
```yaml
env:
  PYTHON_VERSION: "3.11"  # Change to desired version
```

### Changing Service Name or Region

Edit `.github/workflows/ci-cd.yaml`:
```yaml
env:
  SERVICE_NAME: "llmhive-orchestrator"  # Change service name
  REGION: "us-east1"  # Change region
```

### Adding Test Steps

Add additional test steps in the `test` job:
```yaml
- name: Run linting
  run: |
    pip install ruff
    ruff check .
```

### Modifying Deployment Configuration

Edit the `Deploy to Cloud Run` step in `.github/workflows/ci-cd.yaml`:
```yaml
gcloud run deploy "${{ env.SERVICE_NAME }}" \
  --image "$IMAGE" \
  --region "${{ env.REGION }}" \
  --memory=4Gi \  # Increase memory
  --cpu=4 \  # Increase CPU
  --max-instances=20 \  # Increase max instances
  ...
```

## Manual Deployment

If you need to deploy manually (e.g., for rollback or testing):

### Using Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Using gcloud directly

```bash
# Build and push image
IMAGE="gcr.io/PROJECT_ID/llmhive-orchestrator:manual-$(date +%s)"
docker build -t "$IMAGE" .
docker push "$IMAGE"

# Deploy
gcloud run deploy llmhive-orchestrator \
  --image "$IMAGE" \
  --region us-east1 \
  --platform managed
```

## Rollback Procedure

To rollback to a previous version:

1. **Find the previous revision:**
   ```bash
   gcloud run revisions list \
     --service=llmhive-orchestrator \
     --region=us-east1
   ```

2. **Rollback to specific revision:**
   ```bash
   gcloud run services update-traffic llmhive-orchestrator \
     --region=us-east1 \
     --to-revisions=REVISION_NAME=100
   ```

3. **Or deploy a specific image:**
   ```bash
   gcloud run deploy llmhive-orchestrator \
     --image gcr.io/PROJECT_ID/llmhive-orchestrator:COMMIT_SHA \
     --region us-east1
   ```

## Monitoring and Debugging

### View Workflow Runs

1. Go to your GitHub repository
2. Click on the **Actions** tab
3. View workflow runs, logs, and status

### View Deployment Logs

```bash
# View Cloud Run service logs
gcloud run services logs read llmhive-orchestrator \
  --region us-east1 \
  --limit 50

# Stream logs in real-time
gcloud run services logs tail llmhive-orchestrator \
  --region us-east1
```

### Check Service Status

```bash
# Describe the service
gcloud run services describe llmhive-orchestrator \
  --region us-east1

# Check service health
curl https://SERVICE_URL/healthz
```

## Troubleshooting

### Tests Fail

- Check test logs in the Actions tab
- Run tests locally: `pytest tests/ -v`
- Ensure all dependencies are installed

### Deployment Fails

- Verify GitHub secrets are correctly set
- Check service account has necessary permissions
- Ensure Secret Manager secrets exist
- Review Cloud Run logs for errors

### Image Build Fails

- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Test build locally: `docker build -t test .`

### Service Not Responding

- Check Cloud Run service status
- Review service logs
- Verify environment variables and secrets
- Check service URL is accessible

## Best Practices

1. **Never commit secrets** - Always use GitHub secrets
2. **Test locally first** - Run tests before pushing
3. **Review PRs carefully** - Ensure tests pass before merging
4. **Monitor deployments** - Check service health after deployment
5. **Use feature branches** - Test changes in branches before merging to main
6. **Tag releases** - Consider adding release tags for important versions

## Security Considerations

- **Service Account Keys**: Rotate keys regularly
- **Workload Identity**: Prefer Workload Identity Federation over keys
- **Secret Manager**: Use Secret Manager for all sensitive data
- **Least Privilege**: Grant only necessary permissions to service accounts
- **Audit Logs**: Monitor Cloud Run and GitHub Actions audit logs

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)


