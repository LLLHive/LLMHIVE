# Restoring Grok and Gemini responses (no more stub fallbacks)

When the orchestrator prints `No configured LLM providers produced real responses` it means
all non-stub providers failed to initialize or their API calls failed at runtime. This runbook 
focuses on Grok (xAI) and Google Gemini because both share the same failure pattern reported 
in the logs.

**Key distinction:** If you see providers like `openai` or `grok` in the available providers 
list but still get stub responses, it means the providers loaded successfully but their API 
calls are failing. Check the error message for "Recent errors:" to see specific failure details.

## 1. Understand the orchestration flow

During startup the orchestrator loads API keys from the settings object or from environment
variables via `_get_key(...)`. Providers are only added when the relevant key is non-empty;
otherwise the provider is skipped and the stub remains.【F:llmhive/src/llmhive/app/orchestrator.py†L120-L198】

When no real providers survive initialization every request returns the stub placeholder,
triggering the error you observed.【F:llmhive/src/llmhive/app/orchestrator.py†L200-L214】

## 2. Confirm deployment wiring

Use the `/api/v1/orchestration/providers` endpoint to list the providers that reached the
runtime. The presence of `stub` with no `grok` or `gemini` entries confirms a configuration
problem rather than an application bug.【F:llmhive/src/llmhive/app/api/orchestration.py†L45-L65】

**How to call the diagnostic endpoint:**
```bash
# If running locally (default port 8080)
curl http://localhost:8080/api/v1/orchestration/providers

# If deployed to Cloud Run
curl https://your-service-url.run.app/api/v1/orchestration/providers

# Or open in your browser:
# http://localhost:8080/api/v1/orchestration/providers
```

## 3. Validate Grok configuration

1. **Secret or environment value** – Ensure the `GROK_API_KEY` secret contains the actual xAI
   key and that it is enabled in Secret Manager (if you deploy on Cloud Run) or present in your
   `.env` file for local runs. The orchestrator also accepts `grok_api_key` in settings, but it
   ultimately resolves to the same key lookup.【F:llmhive/src/llmhive/app/config.py†L16-L58】【F:llmhive/src/llmhive/app/orchestrator.py†L144-L182】
2. **IAM permissions** – The Cloud Run service account must have `Secret Manager Secret
   Accessor` on the Grok secret so `_get_key(...)` can pull the value at startup.
3. **Environment injection** – Double check the Cloud Run revision or container launch command
   actually passes `GROK_API_KEY` to the process (for Cloud Run the value should reference
   `projects/<project>/secrets/GROK_API_KEY:latest`).
4. **Client dependency** – Grok reuses the OpenAI Python client. The image must include the
   `openai` package so the provider can instantiate the client without raising a
   `ProviderNotConfiguredError`.【F:llmhive/src/llmhive/app/services/grok_provider.py†L1-L105】

Redeploy after correcting any of the above so the new revision picks up the key.

## 4. Validate Gemini configuration

1. **Secret or environment value** – Confirm `GEMINI_API_KEY` is populated and enabled. The
   settings layer exposes `gemini_api_key`, so either name works with `_get_key(...)`.【F:llmhive/src/llmhive/app/config.py†L16-L58】【F:llmhive/src/llmhive/app/orchestrator.py†L184-L198】
2. **IAM permissions** – Grant the same service account the `Secret Manager Secret Accessor`
   role on the Gemini secret or export the variable locally.
3. **Environment injection** – Verify Cloud Run (or your process manager) injects the secret as
   an environment variable, again using the `projects/<project>/secrets/GEMINI_API_KEY:latest`
   format for Cloud Run.
4. **Client dependency** – Gemini requires the `google-generativeai` package to be installed in
   the runtime image. Missing this dependency causes the provider import to fail and the
   orchestrator to skip Gemini.【F:llmhive/src/llmhive/app/services/gemini_provider.py†L1-L98】

## 5. Runtime validation

After redeploying, tail the startup logs. A healthy run prints `Grok provider configured.` and
`Gemini provider configured.` followed by a list of providers that now includes both names.
Finally re-run `/api/v1/orchestration/providers` or exercise the UI to confirm real responses.

If one provider still falls back to the stub, repeat the relevant steps above. The orchestrator
will continue to serve stub responses until it can read a valid key and import the provider
libraries, so the presence of stub results is always a configuration signal rather than a
runtime crash.【F:llmhive/src/llmhive/app/orchestrator.py†L120-L214】
