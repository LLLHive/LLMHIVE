# Multi-Provider Setup Guide

## Overview

LLMHive FREE tier now uses **3 providers** for 2-3x capacity increase:

| Provider | Models | RPM | Speed | Cost |
|----------|--------|-----|-------|------|
| **Google AI** | Gemini | 15 | Fast | $0 |
| **Groq** | Llama | 50+ | Ultra-fast (LPU) | $0 |
| **OpenRouter** | All others | 20 | Medium | $0 |
| **TOTAL** | ~20 models | **~85 RPM** | - | **$0** |

---

## Step 1: Get Google AI API Key (30 seconds)

### Instructions

1. Visit **https://aistudio.google.com**
2. Sign in with your Gmail account (no credit card needed)
3. Click **"Get API Key"** or **"Create API Key"**
4. Copy the key (starts with `AIza...`)

### Add to Backend

```bash
# In backend terminal or .env file
export GOOGLE_AI_API_KEY="AIzaSy..."
```

### Verify

```bash
# Test Google AI connection
python3 -c "
from llmhive.src.llmhive.app.providers import get_google_client

client = get_google_client()
if client:
    print('✅ Google AI client initialized')
else:
    print('❌ GOOGLE_AI_API_KEY not set')
"
```

---

## Step 2: Get Groq API Key (2 minutes)

### Instructions

1. Visit **https://console.groq.com**
2. Sign up (free account, no credit card)
3. Go to **API Keys** section
4. Click **"Create API Key"**
5. Copy the key (starts with `gsk_...`)

### Add to Backend

```bash
# In backend terminal or .env file
export GROQ_API_KEY="gsk_..."
```

### Verify

```bash
# Test Groq connection
python3 -c "
from llmhive.src.llmhive.app.providers import get_groq_client

client = get_groq_client()
if client:
    print('✅ Groq client initialized (LPU-powered)')
else:
    print('❌ GROQ_API_KEY not set')
"
```

---

## Step 3: Verify Multi-Provider System

### Test All Providers

```bash
cd /Users/camilodiaz/LLMHIVE
python3 scripts/test_multi_provider.py
```

Expected output:
```
🧪 Testing Multi-Provider System
================================

✅ OpenRouter: Available ($96.16 credits, 20 RPM)
✅ Google AI: Available (15 RPM)
✅ Groq: Available (50+ RPM)

Total Capacity: ~85 RPM

Testing Gemini via Google AI...
✅ Gemini response: "Hello! 👋 ..." (2.3s)

Testing Llama via Groq...
✅ Llama response: "Hello! How can..." (1.8s)

Testing routing logic...
✅ google/gemini-2.0-flash-exp:free → Google AI
✅ meta-llama/llama-3.1-405b-instruct:free → Groq
✅ deepseek/deepseek-r1-0528:free → OpenRouter

🎉 Multi-provider system working! Expected 2-3x speedup.
```

---

## Troubleshooting

### "GOOGLE_AI_API_KEY not set"

**Solution**: Export the key in the backend environment:
```bash
# Check if set
echo $GOOGLE_AI_API_KEY

# If empty, set it
export GOOGLE_AI_API_KEY="AIzaSy..."

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export GOOGLE_AI_API_KEY="AIzaSy..."' >> ~/.zshrc
source ~/.zshrc
```

### "GROQ_API_KEY not set"

**Solution**: Same as above for Groq:
```bash
export GROQ_API_KEY="gsk_..."
```

### "Google AI rate limit (429)"

**Cause**: Exceeded 15 RPM on Google AI
**Solution**: System auto-fallbacks to OpenRouter. This is normal.

**Rate Limits**:
- Gemini 2.0 Flash: **15 RPM**, 200 RPD
- Can make **15 calls/minute** to Google AI
- After limit, falls back to OpenRouter

### "Groq rate limit (429)"

**Cause**: Exceeded Groq's RPM limit
**Solution**: System auto-fallbacks to OpenRouter.

**Check your limits**: https://console.groq.com/settings/limits

---

## Deployment to Production

### Cloud Run Environment Variables

Add to `cloudbuild.yaml` or Cloud Run settings:

```yaml
--update-secrets:
  GOOGLE_AI_API_KEY=google-ai-key:latest,
  GROQ_API_KEY=groq-key:latest,
  OPENROUTER_API_KEY=open-router-key:latest
```

### Google Secret Manager

```bash
# Store Google AI key
echo -n "AIzaSy..." | gcloud secrets create google-ai-key --data-file=-

# Store Groq key
echo -n "gsk_..." | gcloud secrets create groq-key --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding google-ai-key \
  --member="serviceAccount:YOUR-SERVICE-ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding groq-key \
  --member="serviceAccount:YOUR-SERVICE-ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Expected Performance Improvements

### Capacity

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total RPM** | 20 | ~85 | **+325%** |
| **Effective Queries/Min** | 10 | 40+ | **+300%** |
| **Benchmark Time** | 6+ min | 1.5-2 min | **3-4x faster** |

### Speed (Individual Models)

| Model | Provider | Before | After | Speedup |
|-------|----------|--------|-------|---------|
| Llama 3.1 405B | Groq LPU | 15-30s | 2-5s | **5-10x** |
| Llama 3.3 70B | Groq LPU | 5-10s | 1-2s | **3-5x** |
| Gemini Flash | Google Direct | 2-5s | 1-3s | **2x** |

### Cost

**Still $0/query!** All providers use free tiers.

---

## Model Routing Rules

The system automatically routes models to optimal providers:

### Gemini Models → Google AI (15 RPM)
- `google/gemini-2.0-flash-exp:free`
- `google/gemini-2.5-flash:free`

**Benefit**: Direct API = faster, independent limits

### Llama Models → Groq (50+ RPM, ultra-fast)
- `meta-llama/llama-3.1-405b-instruct:free`
- `meta-llama/llama-3.3-70b-instruct:free`
- `meta-llama/llama-3.2-3b-instruct:free`

**Benefit**: Groq LPU = 10x faster than GPU

### All Other Models → OpenRouter (20 RPM)
- DeepSeek R1
- Qwen models
- Other free models

**Benefit**: Access to 15+ additional models

### Automatic Fallback

If provider is rate-limited:
1. Google limited → Falls back to OpenRouter
2. Groq limited → Falls back to OpenRouter
3. OpenRouter limited → Exponential backoff + retry

---

## Monitoring

### Check Provider Status

```python
from llmhive.src.llmhive.app.providers import get_provider_router

router = get_provider_router()
status = router.get_capacity_status()

print(status)
# {
#   'openrouter': {'rpm_limit': 20, 'requests_in_window': 5, 'available': True},
#   'google': {'rpm_limit': 15, 'requests_in_window': 0, 'available': True},
#   'groq': {'rpm_limit': 50, 'requests_in_window': 0, 'available': True}
# }
```

### Check Logs

```bash
# See which provider handled each request
grep "Routing.*→" logs/backend.log

# Examples:
# Routing google/gemini-2.0-flash-exp:free → Google AI
# Routing meta-llama/llama-3.1-405b-instruct:free → Groq LPU
# Routing deepseek/deepseek-r1-0528:free → OpenRouter
```

---

## FAQ

### Q: What if I don't set up Google AI or Groq keys?

**A**: System falls back to OpenRouter only. Still works, just slower.

### Q: Do I need to change my application code?

**A**: No. Routing is automatic and transparent.

### Q: What if a provider goes down?

**A**: Automatic fallback to OpenRouter. Zero downtime.

### Q: Can I disable a provider?

**A**: Yes, just unset its API key. System adapts automatically.

### Q: Are there any costs?

**A**: No. All providers use 100% FREE tiers. No credit card needed.

### Q: What are the actual rate limits?

**Check in real-time**:
- Google: https://aistudio.google.com/usage
- Groq: https://console.groq.com/settings/limits
- OpenRouter: https://openrouter.ai/settings/credits

---

## Next Steps

1. ✅ Set up Google AI API key
2. ✅ Set up Groq API key
3. ✅ Run test script to verify
4. ✅ Deploy to production
5. ✅ Run benchmarks to see improvements
6. 📊 Monitor performance gains

**Expected Result**: FREE tier will be 2-3x faster with same quality!

---

Last Updated: January 31, 2026
