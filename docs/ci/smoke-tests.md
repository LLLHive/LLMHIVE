# Production Smoke Tests

This document describes the LLMHive production smoke test workflow and how to configure it.

## Overview

The smoke tests workflow (`smoke-tests.yml`) runs automated health checks against the production API to ensure it's functioning correctly. It runs:

- **Daily** at 6 AM UTC
- **After deployments** to the main branch
- **Manually** via workflow dispatch

## Workflow Structure

### Jobs

1. **smoke-tests**: Full smoke test suite including:
   - Health endpoint checks (`/healthz`, `/health`, `/api/v1/metrics/health`)
   - API endpoint availability
   - Authenticated endpoint tests (if API key provided)
   - Performance measurements

2. **critical-tests**: Quick critical health checks only (5 minute timeout)

3. **summary**: Aggregates results from both jobs

## Configuration

### Required Secrets

None are strictly required - the workflow will run with defaults.

### Optional Secrets

| Secret | Purpose | Behavior if Missing |
|--------|---------|---------------------|
| `PRODUCTION_API_URL` | Override default production URL | Uses `https://api.llmhive.ai` |
| `SMOKE_TEST_API_KEY` | API key for authenticated tests | Authenticated tests are skipped |
| `SLACK_WEBHOOK_URL` | Slack webhook for failure notifications | Notification step is skipped |

### Setting Up Secrets

1. Go to your repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with the appropriate value

### Slack Notifications

The workflow can send Slack notifications when smoke tests fail. To enable:

1. Create an Incoming Webhook in your Slack workspace
2. Add the webhook URL as `SLACK_WEBHOOK_URL` secret

**Important**: Notifications are:
- Only sent on failure (not on success)
- Only sent for scheduled/automated runs (not manual triggers)
- Only sent from the main repository (not forks)
- Never fail the workflow if the secret is missing

## Behavior When Secrets Are Missing

| Scenario | Behavior |
|----------|----------|
| No `PRODUCTION_API_URL` | Uses default `https://api.llmhive.ai` |
| No `SMOKE_TEST_API_KEY` | Authenticated tests are skipped |
| No `SLACK_WEBHOOK_URL` | Notification step is silently skipped |
| Fork without secrets | All optional features gracefully skip |

## Running Manually

1. Go to Actions → "Production Smoke Tests"
2. Click "Run workflow"
3. Optionally override:
   - Production URL
   - Enable success notifications

## Troubleshooting

### "Error: Need to provide at least one botToken or webhookUrl"

This error occurred when the Slack notification step ran without secrets. **This is fixed** - the workflow now checks if secrets exist before attempting to send notifications.

### Tests failing due to authentication

If tests fail with 401 errors, ensure `SMOKE_TEST_API_KEY` is set with a valid API key.

### Health checks timing out

Increase the timeout by modifying the workflow or check if the production service is experiencing issues.

## Local Development

Run smoke tests locally against a development server:

```bash
# Against local server
pytest tests/smoke/ --production-url=http://localhost:8000 -v

# Against staging
pytest tests/smoke/ --production-url=https://staging.llmhive.ai --api-key=your-key -v
```

## Related Workflows

- `quality-regression.yml`: Runs golden prompt quality tests
- `ci-cd.yaml`: Main CI/CD pipeline
- `e2e.yml`: End-to-end UI tests

