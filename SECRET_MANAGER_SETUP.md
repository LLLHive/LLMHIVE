# Provider Secret Configuration Checklist

This checklist walks you through configuring provider API keys (OpenAI, Grok, Anthropic, etc.) for the LLMHive Cloud Run deployment. Follow the steps in order and replace the placeholders (shown in ALL_CAPS) with your project-specific values.

---

## 0. Prerequisites

1. Install and authenticate the Google Cloud CLI.
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. Identify the following details before you begin:
   * `YOUR_PROJECT_ID` – Google Cloud project ID that owns the service.
   * `SERVICE_NAME` – Cloud Run service name (for example `llmhive-orchestrator`).
   * `REGION` – Cloud Run region (for example `us-east1`).
   * `IMAGE_URI` – Container image URI if you perform a full `gcloud run deploy` (for example `gcr.io/YOUR_PROJECT_ID/llmhive:latest`).
   * Actual API keys for each provider (`SECRET_VALUE` placeholders in the commands below).

---

## 1. Create provider secrets in Secret Manager

Run the following for each provider. Replace `YOUR_PROJECT_ID` and insert the real secret value instead of `SECRET_VALUE`.

```bash
# Example for OpenAI
gcloud secrets create openai-api-key --project=YOUR_PROJECT_ID

echo -n "SECRET_VALUE" | gcloud secrets versions add openai-api-key \
  --project=YOUR_PROJECT_ID --data-file=-

# Repeat for each provider you plan to use
# grok-api-key, anthropic-api-key, gemini-api-key, deepseek-api-key, manus-api-key
```

If a secret resource already exists, skip `gcloud secrets create` and add a new version with the second command.

---

## 2. Identify the Cloud Run service account

Retrieve the service account used by the Cloud Run revision:

```bash
gcloud run services describe SERVICE_NAME \
  --region REGION \
  --project=YOUR_PROJECT_ID \
  --format="value(spec.template.spec.serviceAccountName)"
```

*Copy the email address that command prints. It will be used as `YOUR_CLOUD_RUN_SA` in later steps.* If nothing is returned, the service uses the default compute service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`).

---

## 3. Grant the service account access to each secret

Grant the `roles/secretmanager.secretAccessor` role on every secret the service must read.

```bash
# Example for the OpenAI secret
gcloud secrets add-iam-policy-binding openai-api-key \
  --project=YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_CLOUD_RUN_SA" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for grok-api-key, anthropic-api-key, gemini-api-key, deepseek-api-key, manus-api-key
```

As an alternative you can grant the role at the project level, but per-secret access is recommended.

---

## 4. Attach secrets to the Cloud Run service as environment variables

Update the existing service so each environment variable references the appropriate secret version:

```bash
gcloud run services update SERVICE_NAME \
  --region REGION \
  --project=YOUR_PROJECT_ID \
  --update-secrets OPENAI_API_KEY=projects/YOUR_PROJECT_ID/secrets/openai-api-key:latest \
  --update-secrets GROK_API_KEY=projects/YOUR_PROJECT_ID/secrets/grok-api-key:latest \
  --update-secrets ANTHROPIC_API_KEY=projects/YOUR_PROJECT_ID/secrets/anthropic-api-key:latest \
  --update-secrets GEMINI_API_KEY=projects/YOUR_PROJECT_ID/secrets/gemini-api-key:latest \
  --update-secrets DEEPSEEK_API_KEY=projects/YOUR_PROJECT_ID/secrets/deepseek-api-key:latest \
  --update-secrets MANUS_API_KEY=projects/YOUR_PROJECT_ID/secrets/manus-api-key:latest
```

If you are deploying a fresh revision manually, you can provide the same mappings with `--set-secrets` during `gcloud run deploy`.

---

## 5. (Optional) Local verification

Before deploying, you can verify the application reads environment variables correctly by exporting the keys locally and starting the app:

```bash
export OPENAI_API_KEY="sk-..."
export GROK_API_KEY="grok-..."
uvicorn llmhive.app.main:app --reload
```

---

## 6. Redeploy and confirm

After the secrets are attached, Cloud Run will create a new revision automatically. Wait for the update to finish, then confirm the environment variables are present:

```bash
gcloud run services describe SERVICE_NAME \
  --region REGION \
  --project=YOUR_PROJECT_ID \
  --format="yaml(spec.template.spec.containers[0].env)"
```

The output should list entries such as `OPENAI_API_KEY` referencing the secrets configured above.

---

## 7. Diagnose provider availability

Use the diagnostics endpoint exposed by the service to confirm which providers were detected at runtime:

```bash
curl -sS https://SERVICE_URL/api/v1/providers | jq .
```

Expected result when keys are configured:

```json
{
  "available_providers": ["openai", "grok", "stub"],
  "unavailable_providers": [],
  "fail_on_stub": true
}
```

If only `"stub"` appears, revisit the previous steps to confirm secrets are attached and accessible.

---

## 8. Run an orchestration smoke test

```bash
curl -X POST "https://SERVICE_URL/api/v1/orchestration/" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the capital of Spain?","models":["grok","gpt-4"]}'
```

A healthy response includes natural-language answers and provider identifiers such as `"openai"` or `"grok"`. If the response contains placeholder text like `[gpt-4] Response to: ...` or the API returns `503`, check the diagnostics output and Cloud Run logs.

---

## 9. Collect logs if issues remain

Fetch recent Cloud Run logs to identify configuration errors:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME" \
  --project=YOUR_PROJECT_ID --limit 200 --order=desc --format="json" \
  | jq -r '.[].textPayload' \
  | grep -E "Provider mapping|Provider API keys|Provider configured|Provider call failed|401|403|timeout"
```

Look for messages that show missing API keys or provider call failures (401/403). Rotate keys or fix permissions accordingly, then redeploy.

---

## 10. Share verification results

After confirming the service works, capture the following for the engineering team:

* Output from `/api/v1/providers`.
* JSON from the orchestration smoke test.
* Any relevant log excerpts or Cloud Build IDs.

This information helps validate that the production deployment is using real LLM providers rather than the internal stub fallback.

