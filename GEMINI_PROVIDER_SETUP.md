# Restoring Google Gemini connectivity

This run book walks through the diagnostics and fixes to get real Google Gemini
responses instead of the stub provider. Follow it when the service previously
worked but now appears to have lost access to Gemini.

## 1. Confirm how configuration is loaded

The FastAPI app reads all provider secrets from environment variables or a
`.env` file during startup. Each provider has a dedicated setting field that
maps to its corresponding environment variable, including
`GEMINI_API_KEY` and `GEMINI_TIMEOUT_SECONDS`.【F:llmhive/src/llmhive/app/config.py†L16-L58】

If the setting is empty, the orchestrator falls back to the stub provider while
logging that Gemini is unavailable. Keep this in mind while reading the logs in
later steps.【F:llmhive/src/llmhive/app/orchestrator.py†L84-L205】

## 2. Check runtime logs

Start (or restart) the service and inspect the startup logs. During the FastAPI
`startup` event, the app lists the configured providers and warns when only the
stub is available. A healthy setup shows at least one real provider in the
`Configured providers` line.【F:llmhive/src/llmhive/app/main.py†L121-L130】

When Gemini is missing you will typically see:

```
INFO  Configured providers: ['stub']
WARNING ⚠️  Only stub provider is configured! No real LLM API keys found.
```

## 3. Ensure the Gemini client library is installed

`GeminiProvider` raises `ProviderNotConfiguredError` if the
`google-generativeai` package cannot be imported. Install it anywhere the
orchestrator runs:

```bash
pip install google-generativeai
```

If you build a deployment image, add the dependency to the image requirements
so the runtime includes the package.【F:llmhive/src/llmhive/app/services/gemini_provider.py†L34-L86】

## 4. Provide the GEMINI_API_KEY secret

Gemini will only initialize when an API key is present. Choose the option that
fits your environment:

### Local development (`.env`)

Create or update `.env` in the repository root:

```
GEMINI_API_KEY=your-google-genai-key
GEMINI_TIMEOUT_SECONDS=45
```

Restart the app so the settings layer reloads the values.【F:llmhive/src/llmhive/app/config.py†L12-L58】

### Cloud Run / containerized deployments

Update the service environment variables. For Cloud Run:

```bash
gcloud run services update llmhive-orchestrator \
  --region=YOUR_REGION \
  --update-env-vars=GEMINI_API_KEY=your-google-genai-key
```

Redeploy any other container platform with the new `GEMINI_API_KEY` value.

### GitHub Actions (for CI or GitHub-hosted runners)

1. Open the repository → **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret**, name it `GEMINI_API_KEY`, and paste the key.
3. Reference the secret inside workflows or deployment scripts, for example:

   ```yaml
   env:
     GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
   ```

4. Confirm that the deployment step passes the environment variable into the
   container or runtime (for example with `--update-env-vars` on `gcloud run`).

## 5. Verify at runtime

After the service restarts, call the provider diagnostic endpoint:

```bash
curl https://<your-host>/api/v1/orchestration/providers
```

The response should list `"gemini"` inside `available_providers` and show the
models exposed by the Gemini client.【F:llmhive/src/llmhive/app/api/orchestration.py†L45-L65】

If Gemini still does not appear, re-check each preceding step (library
installation, environment variable scope, secrets injection). The orchestrator
keeps the stub provider available, so a missing key always results in stub
responses until the key is restored.【F:llmhive/src/llmhive/app/orchestrator.py†L150-L205】
