# LLMHive Deployment & Testing Guide (Non-Technical)

This guide walks you through deploying the LLMHive Orchestrator to Google Cloud Run and verifying that it is working. The steps assume you already have a Google Cloud project with Cloud Run and Cloud Build enabled.

---

## 1. Gather the information you need

Before you start, make sure you have the following items ready:

1. **Google Cloud project** – The project that owns the LLMHive service (example: `llmhive-orchestrator`).
2. **GitHub repository access** – The repo that contains the LLMHive code (this guide assumes the Cloud Build trigger is already connected to GitHub).
3. **Environment values** – Any API keys or secrets your models need (OpenAI, Grok/xAI, Anthropic, etc.). These are stored in Google Secret Manager and referenced by the Cloud Run service.

---

## 2. Deploy a new version from GitHub

1. **Open Cloud Build**
   1. Sign in to the [Google Cloud Console](https://console.cloud.google.com/).
   2. Choose the correct project from the selector in the top-left corner.
   3. Go to **Cloud Build → Triggers** in the left-hand menu.

2. **Run the deployment trigger**
   1. Find the trigger named **`llmhive-orchestrator`** (or the name used in your project).
   2. Click **Run**.
   3. In the dialog, select the GitHub branch you want to deploy (usually `main`).
   4. Confirm by clicking **Run trigger**. Cloud Build will now:
      - Build the Docker image using the repository’s `Dockerfile`.
      - Push the image to Artifact Registry.
      - Deploy it to Cloud Run using the settings in `cloudbuild.yaml`.

3. **Watch the build finish**
   1. You will see a build log. Wait until the status shows **SUCCESS** (this usually takes a few minutes).
   2. If the build fails, click into the build for detailed logs and share them with the engineering team.

---

## 3. Confirm the Cloud Run deployment

1. Open **Cloud Run** in the Google Cloud Console.
2. Click the service named **`llmhive-orchestrator`**.
3. In the **Revisions** tab you should see a new revision with a timestamp matching your build.
4. Confirm the revision shows **Serving traffic** and has **0% errors**.
5. Copy the **Service URL** at the top of the page – you will use this to test the API.

---

## 4. Verify the service is healthy

1. Open a new browser tab and go to `https://<SERVICE-URL>/api/v1/healthz`.
2. You should see a small JSON response that includes:
   ```json
   {"status": "ok", ...}
   ```
3. Scroll further down in the response (or use the Swagger UI at `https://<SERVICE-URL>` → **system → /api/v1/healthz → Execute**) to confirm:
   - The **Git commit** matches the revision you expect.
   - Each model provider you rely on shows `status: "ready"`. If a provider shows `error`, double-check its API key in Secret Manager or contact engineering.

---

## 5. Run a quick end-to-end test

1. In the Swagger UI at `https://<SERVICE-URL>`, open **orchestration → POST /api/v1/orchestration/**.
2. Click **Try it out**.
3. Fill in the sample request:
   ```json
   {
     "prompt": "What is the capital of Spain?",
     "models": ["GPT-4", "Grok"]
   }
   ```
4. Click **Execute**.
5. You should see a `200` response with:
   - `initial_responses` showing at least one model answer.
   - `provider` fields identifying which backend actually produced each answer (for example, `"openai"` or `"grok"`). If you see `"stub"` anywhere, the service is still using the internal placeholder and real credentials are missing.
   - `final_response` containing the synthesized answer. If the content looks like a placeholder (for example, `[GPT-4] Response to: ...`) or `final_provider` reports `"stub"`, the real model credentials may not be configured—contact engineering for help.

---

## 6. Share the results

After you finish the checks:

1. Take screenshots or copy the JSON response from the health check and orchestration test.
2. Share them with the engineering team along with the build ID (visible in the Cloud Build log). This helps confirm the correct version is live.

---

## Need to configure provider secrets?

If the `/api/v1/providers` diagnostics endpoint reports only the `stub` provider (or the orchestration API returns placeholder responses), follow the step-by-step **[Provider Secret Configuration Checklist](SECRET_MANAGER_SETUP.md)**. It includes exact `gcloud` commands for creating secrets, granting Cloud Run access, attaching the secrets as environment variables, and verifying that real providers such as OpenAI and Grok are active.

---

### Need help?
If any of the steps fail or the responses look incorrect:
- Copy the error message or screenshot.
- Note which step you were on.
- Send the details to the engineering team so they can investigate.

