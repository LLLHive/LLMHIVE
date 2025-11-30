# Troubleshooting Task 4: 500 Internal Server Error
**Date:** November 27, 2025
**Issue:** POST /api/chat returns 500 error

---

## 🔍 Problem Identified

The `/api/chat` route was using an **outdated format** that didn't match the new FastAPI backend API.

### Issues Found:

1. **Wrong Endpoint:** Was calling `/chat` instead of `/v1/chat`
2. **Wrong Request Format:** Was sending old format instead of `ChatRequest` format
3. **Missing API Key Header:** Wasn't sending `X-API-Key` header
4. **Response Format Mismatch:** Frontend expects stream but route wasn't handling it correctly

---

## ✅ Solution Applied

I've updated `app/api/chat/route.ts` to:

1. ✅ Call the correct endpoint: `/v1/chat`
2. ✅ Send correct `ChatRequest` format with:
   - `prompt` (extracted from latest user message)
   - `reasoning_mode`, `domain_pack`, `agent_mode`
   - `tuning` options
   - `metadata` (chat_id, user_id, project_id)
   - `history` (conversation history)
3. ✅ Add `X-API-Key` header if `LLMHIVE_API_KEY` is set
4. ✅ Return streaming response that frontend expects

---

## 🔄 Next Steps

### Step 1: Verify Environment Variables in Vercel

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Verify these are set:
   - ✅ `ORCHESTRATOR_API_BASE_URL` = `https://llmhive-orchestrator-792354158895.us-east1.run.app`
   - ✅ `LLMHIVE_API_KEY` = (your API key, if you set one in Task 5)

### Step 2: Redeploy Vercel

After the code fix, you need to redeploy:

1. **Option A: Automatic (if connected to GitHub)**
   - The fix is in the code, so push to GitHub
   - Vercel will auto-deploy

2. **Option B: Manual Redeploy**
   - Go to Vercel Dashboard → Your Project → Deployments
   - Click the three dots (⋮) on the latest deployment
   - Click "Redeploy"
   - Wait for deployment to complete (~2-3 minutes)

### Step 3: Test Again

1. Go to https://www.llmhive.ai
2. Open browser console (F12)
3. Send a test message
4. Check for errors

---

## 🐛 If Still Getting Errors

### Error: "Failed to fetch" or Network Error
**Cause:** Backend URL is wrong or backend is down

**Fix:**
1. Check `ORCHESTRATOR_API_BASE_URL` in Vercel
2. Verify backend is running: Visit `https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz`
3. Should return: `{"status":"ok"}`

### Error: "401 Unauthorized"
**Cause:** API key mismatch

**Fix:**
1. Check `LLMHIVE_API_KEY` in Vercel matches `API_KEY` in Cloud Run
2. If you haven't set API keys yet, that's OK - backend allows unauthenticated requests if `API_KEY` is not set

### Error: "500 Internal Server Error" (Backend Error)
**Cause:** Backend is having issues

**Fix:**
1. Check Cloud Run logs:
   - Go to Google Cloud Console → Cloud Run → `llmhive-orchestrator` → Logs
   - Look for error messages
2. Common issues:
   - Missing API keys in Secret Manager (Task 1)
   - Secrets not mapped in Cloud Run (Task 3)
   - Backend code error

### Error: "No prompt provided"
**Cause:** Frontend not sending messages correctly

**Fix:**
- This should be fixed with the updated route
- If still happening, check browser console for the actual request payload

---

## 📋 Verification Checklist

After redeploying, verify:

- [ ] Vercel environment variables are set correctly
- [ ] Vercel deployment completed successfully
- [ ] Backend is accessible: `https://llmhive-orchestrator-792354158895.us-east1.run.app/healthz`
- [ ] No errors in browser console
- [ ] Test message gets a response (or at least a different error)

---

## 🔍 Debugging Steps

### 1. Check Vercel Function Logs

1. Go to Vercel Dashboard → Your Project → Functions
2. Click on `/api/chat`
3. View recent invocations
4. Check for error messages

### 2. Check Backend Logs

1. Go to Google Cloud Console → Cloud Run
2. Click on `llmhive-orchestrator`
3. Click "LOGS" tab
4. Look for recent requests and errors

### 3. Test Backend Directly

Use curl or Postman to test the backend:

```bash
curl -X POST https://llmhive-orchestrator-792354158895.us-east1.run.app/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "Hello, test message",
    "reasoning_mode": "standard",
    "domain_pack": "default",
    "agent_mode": "team"
  }'
```

If this works, the backend is fine and the issue is in the frontend route.

---

## ✅ Expected Behavior After Fix

1. **Frontend sends message** → `/api/chat` route receives it
2. **Route transforms request** → Matches FastAPI `ChatRequest` format
3. **Route calls backend** → `POST /v1/chat` with correct headers
4. **Backend processes** → Returns `ChatResponse` with message
5. **Route streams response** → Frontend receives and displays message

---

## 📝 Code Changes Summary

**File:** `app/api/chat/route.ts`

**Changes:**
- ✅ Updated to call `/v1/chat` endpoint (was `/chat`)
- ✅ Updated request format to match `ChatRequest` model
- ✅ Added `X-API-Key` header support
- ✅ Fixed response streaming to match frontend expectations
- ✅ Better error handling and logging

---

**Status:** ✅ Fix Applied - Ready for Testing  
**Next Action:** Redeploy Vercel and test again

