# Vertex AI Service Impact Analysis
**Date:** November 27, 2025
**Issue:** Google Vertex AI service stopped

## Executive Summary

Based on codebase analysis, **Vertex AI is NOT directly used** in the LLMHive codebase. However, stopping Vertex AI may affect:

1. **Gemini model access** (if configured via Vertex AI instead of Generative AI API)
2. **GCP authentication** (if using Vertex AI service account)
3. **Future RAG vector store** (planned but not implemented)

## Current Codebase Status

### ✅ What's NOT Using Vertex AI

1. **Gemini Model Access**
   - Currently uses `GEMINI_API_KEY` environment variable
   - Configured in `llmhive/src/llmhive/app/config.py`
   - Uses Google's Generative AI SDK (not Vertex AI)
   - **Status:** Should work independently of Vertex AI

2. **RAG Vector Store**
   - Currently uses **Pinecone** (not Vertex AI)
   - `VECTOR_DB_TYPE` environment variable defaults to `pinecone`
   - Vertex AI vector store is marked as **TODO** (not implemented)
   - **Status:** No impact - Vertex AI not used

3. **LLM Providers**
   - OpenAI (direct API)
   - Anthropic (direct API)
   - Grok (direct API)
   - DeepSeek (direct API)
   - **Status:** No Vertex AI dependency

### ⚠️ Potential Impact Areas

#### 1. Gemini Model Access (If Using Vertex AI)

**Current Configuration:**
```python
# llmhive/src/llmhive/app/config.py
gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
```

**Impact Scenarios:**

**Scenario A: Using Generative AI API (Current Setup)**
- ✅ **No Impact** - Uses `GEMINI_API_KEY` with Google's Generative AI SDK
- Works independently of Vertex AI
- Access via: `https://generativelanguage.googleapis.com`

**Scenario B: Using Vertex AI for Gemini**
- ❌ **Will Break** - If Gemini models are accessed via Vertex AI endpoints
- Would need: `GOOGLE_APPLICATION_CREDENTIALS` or Vertex AI service account
- Access via: `https://us-east1-aiplatform.googleapis.com`
- **Check:** Your deployment configuration

**How to Check:**
```bash
# Check Cloud Run environment variables
gcloud run services describe llmhive-orchestrator \
  --region us-east1 \
  --format='value(spec.template.spec.containers[0].env)'

# Look for:
# - GEMINI_API_KEY (Generative AI API - OK)
# - GOOGLE_APPLICATION_CREDENTIALS (Vertex AI - Will break)
# - VERTEX_AI_PROJECT_ID (Vertex AI - Will break)
```

#### 2. GCP Connector (BigQuery/Cloud Logging)

**File:** `llmhive/src/llmhive/app/services/gcp_connector.py`

**Current Implementation:**
- Uses Application Default Credentials (ADC)
- Uses BigQuery and Cloud Logging APIs
- **Does NOT use Vertex AI API**

**Impact:**
- ✅ **No Direct Impact** - GCP Connector doesn't use Vertex AI
- ⚠️ **Potential Indirect Impact** - If Vertex AI service account is used for authentication
- If ADC relies on Vertex AI service account, BigQuery/Logging access may fail

**How to Check:**
```python
# Check if GCP connector is enabled
# Look for GCP_PROJECT_ID environment variable
# Check Cloud Run logs for GCP connector errors
```

#### 3. Cloud Build & Deployment

**File:** `cloudbuild.yaml`

**Current Configuration:**
- Uses `gcr.io/cloud-builders/docker` (Container Registry)
- Uses `gcr.io/google.com/cloudsdktool/cloud-sdk` (Cloud SDK)
- Deploys to Cloud Run
- **Does NOT use Vertex AI**

**Impact:**
- ✅ **No Impact** - Build process doesn't use Vertex AI
- Cloud Build uses separate services (Container Registry, Cloud Run)

## Affected Components Checklist

### ✅ No Impact (Not Using Vertex AI)

- [x] **RAG System** - Uses Pinecone, not Vertex AI
- [x] **OpenAI Provider** - Direct API access
- [x] **Anthropic Provider** - Direct API access
- [x] **Grok Provider** - Direct API access
- [x] **DeepSeek Provider** - Direct API access
- [x] **Cloud Build Pipeline** - Uses Container Registry, not Vertex AI
- [x] **Cloud Run Deployment** - Uses Cloud Run service, not Vertex AI
- [x] **Settings Persistence** - In-memory (no Vertex AI)
- [x] **Code Execution** - Uses MCP 2 sandbox, not Vertex AI

### ⚠️ Potential Impact (Needs Verification)

- [ ] **Gemini Model Access** - Check if using Vertex AI endpoints
- [ ] **GCP Connector Authentication** - Check if using Vertex AI service account
- [ ] **Future RAG Vector Store** - Planned but not implemented

## Diagnostic Steps

### Step 1: Check Gemini Model Access Method

```bash
# Check Cloud Run environment variables
gcloud run services describe llmhive-orchestrator \
  --region us-east1 \
  --format='value(spec.template.spec.containers[0].env)' | grep -i gemini

# Expected (OK):
# GEMINI_API_KEY=your-api-key

# Problem (Will break):
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/vertex-ai-key.json
# VERTEX_AI_PROJECT_ID=your-project-id
```

### Step 2: Check GCP Connector Status

```bash
# Check if GCP_PROJECT_ID is set
gcloud run services describe llmhive-orchestrator \
  --region us-east1 \
  --format='value(spec.template.spec.containers[0].env)' | grep -i gcp

# Check Cloud Run logs for GCP connector errors
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=llmhive-orchestrator AND \
  textPayload=~'GCP connector'" \
  --limit 50
```

### Step 3: Test Gemini Model Access

```bash
# Test if Gemini models are accessible
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "Test message",
    "reasoning_mode": "standard",
    "domain_pack": "default",
    "agent_mode": "team"
  }'

# Check response for Gemini-related errors
```

### Step 4: Check Cloud Run Logs

```bash
# Check for Vertex AI related errors
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=llmhive-orchestrator AND \
  (textPayload=~'vertex' OR textPayload=~'Vertex' OR textPayload=~'VERTEX')" \
  --limit 50

# Check for authentication errors
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=llmhive-orchestrator AND \
  (textPayload=~'authentication' OR textPayload=~'credentials' OR textPayload=~'permission')" \
  --limit 50
```

## Resolution Steps

### If Gemini Models Are Affected

**Option 1: Switch to Generative AI API (Recommended)**
```bash
# Ensure GEMINI_API_KEY is set in Cloud Run
gcloud run services update llmhive-orchestrator \
  --region us-east1 \
  --update-secrets=GEMINI_API_KEY=gemini-api-key:latest

# Verify the key is accessible
gcloud run services describe llmhive-orchestrator \
  --region us-east1 \
  --format='value(spec.template.spec.containers[0].env)'
```

**Option 2: Re-enable Vertex AI Service**
- Go to Google Cloud Console
- Navigate to Vertex AI API
- Enable the service
- Ensure service account has Vertex AI permissions

### If GCP Connector Is Affected

**Option 1: Use Separate Service Account**
```bash
# Create a service account for BigQuery/Logging (not Vertex AI)
gcloud iam service-accounts create llmhive-gcp-connector \
  --display-name="LLMHive GCP Connector"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:llmhive-gcp-connector@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:llmhive-gcp-connector@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"
```

**Option 2: Disable GCP Connector**
```bash
# Remove GCP_PROJECT_ID environment variable
gcloud run services update llmhive-orchestrator \
  --region us-east1 \
  --remove-env-vars=GCP_PROJECT_ID
```

## Expected Behavior After Stopping Vertex AI

### ✅ Should Continue Working

1. **Core Orchestration**
   - OpenAI, Anthropic, Grok models
   - Model routing and fallback
   - Reasoning methods
   - RAG (Pinecone)

2. **Infrastructure**
   - Cloud Run deployment
   - Cloud Build pipeline
   - Container Registry

3. **Features**
   - Settings persistence
   - Code execution (MCP 2)
   - File analysis (stub)
   - Image generation (stub)

### ⚠️ May Break

1. **Gemini Models** (if using Vertex AI endpoints)
   - Model selection will fallback to other models
   - Error messages in logs
   - Failed requests when Gemini is selected

2. **GCP Connector** (if using Vertex AI service account)
   - BigQuery queries will fail
   - Cloud Logging access will fail
   - Error messages in logs

## Monitoring Recommendations

### Add Monitoring for Vertex AI Dependencies

```python
# Add to llmhive/src/llmhive/app/services/orchestrator_adapter.py
import logging

logger = logging.getLogger(__name__)

# Check Gemini availability
try:
    # Test Gemini API access
    if settings.gemini_api_key:
        # Test connection
        logger.info("Gemini API key configured")
    else:
        logger.warning("Gemini API key not configured")
except Exception as e:
    logger.error(f"Gemini API check failed: {e}")
```

### Add Health Check Endpoint

```python
# Add to llmhive/src/llmhive/app/routers/chat.py
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    status = {
        "status": "healthy",
        "providers": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "grok": bool(settings.grok_api_key),
            "gemini": bool(settings.gemini_api_key),
        }
    }
    return status
```

## Summary

### Impact Level: **LOW to MEDIUM**

**Most Likely Scenario:**
- ✅ **No Impact** - Codebase doesn't use Vertex AI directly
- Gemini models use Generative AI API (not Vertex AI)
- RAG uses Pinecone (not Vertex AI)

**Potential Issues:**
- ⚠️ If Gemini is configured via Vertex AI endpoints → Will break
- ⚠️ If GCP connector uses Vertex AI service account → May break

**Recommended Actions:**
1. Check Cloud Run environment variables for Vertex AI dependencies
2. Verify Gemini model access method
3. Test orchestration with Gemini models
4. Monitor Cloud Run logs for errors
5. Add health check endpoint for provider status

**Next Steps:**
1. Run diagnostic commands above
2. Check Cloud Run logs
3. Test Gemini model access
4. Update configuration if needed

---

**Last Updated:** November 27, 2025
**Status:** Analysis Complete - Low Impact Expected

