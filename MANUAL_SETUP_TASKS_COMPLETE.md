# Complete Manual Setup Tasks for LLMHive
**Date:** November 27, 2025
**For:** Non-Technical Users
**Purpose:** Step-by-step instructions for all Vercel and Google Cloud configuration tasks

---

## ⚠️ IMPORTANT: Before You Start

**Please confirm these tasks are still needed:**
1. Check if Google Cloud Secret Manager secrets already exist
2. Check if Vercel environment variables are already set
3. Check if Cloud Run service is already deployed
4. Verify if API keys are already configured

**This list assumes you're starting from scratch. Skip tasks that are already completed.**

---

## 📋 TASK LIST (Ordered by Importance)

### 🔴 CRITICAL - Must Complete for System to Work

1. **Google Cloud: Create Secret Manager Secrets** (5 minutes)
2. **Vercel: Set Environment Variables** (3 minutes)
3. **Google Cloud: Verify Cloud Run Secret Mapping** (2 minutes)
4. **Test: Verify Frontend-Backend Connection** (2 minutes)

### 🟡 IMPORTANT - Recommended for Security

5. **Google Cloud: Set API Key for Backend Security** (3 minutes)
6. **Vercel: Set API Key for Frontend Security** (2 minutes)

### 🟢 OPTIONAL - Nice to Have

7. **Google Cloud: Verify Cloud Build Trigger** (2 minutes)
8. **Google Cloud: Set Up Monitoring** (5 minutes)

---

## 📝 DETAILED INSTRUCTIONS

### TASK 1: Google Cloud - Create Secret Manager Secrets
**Priority:** 🔴 CRITICAL  
**Time:** 5 minutes  
**Why:** Backend needs API keys to call LLM providers (OpenAI, Anthropic, Grok, Gemini)

#### Step-by-Step:

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com
   - Select your project: `792354158895` (or your project ID)

2. **Navigate to Secret Manager**
   - In the left menu, click "Security" → "Secret Manager"
   - Or search for "Secret Manager" in the top search bar

3. **Create Secret: `openai-api-key`**
   - Click "CREATE SECRET" button (top of page)
   - **Secret name:** Type exactly: `openai-api-key` (lowercase, with hyphens)
   - **Secret value:** Paste your OpenAI API key
     - Get it from: https://platform.openai.com/api-keys
   - Click "CREATE SECRET"
   - ✅ **Verify:** You should see "openai-api-key" in the list

4. **Create Secret: `anthropic-api-key` (Optional but Recommended)**
   - Click "CREATE SECRET" again
   - **Secret name:** Type exactly: `anthropic-api-key`
   - **Secret value:** Paste your Anthropic API key
     - Get it from: https://console.anthropic.com/settings/keys
   - Click "CREATE SECRET"
   - ✅ **Verify:** You should see "anthropic-api-key" in the list
   - ⚠️ **Note:** This is optional but recommended if you want to use Claude models

5. **Create Secret: `grok-api-key`**
   - Click "CREATE SECRET" again
   - **Secret name:** Type exactly: `grok-api-key`
   - **Secret value:** Paste your Grok API key
     - Get it from: https://x.ai/api (or your Grok provider)
   - Click "CREATE SECRET"
   - ✅ **Verify:** You should see "grok-api-key" in the list

6. **Create Secret: `gemini-api-key`**
   - Click "CREATE SECRET" again
   - **Secret name:** Type exactly: `gemini-api-key`
   - **Secret value:** Paste your Google Gemini API key
     - Get it from: https://makersuite.google.com/app/apikey
   - Click "CREATE SECRET"
   - ✅ **Verify:** You should see "gemini-api-key" in the list

7. **Create Secret: `tavily-api-key` (Optional - for web search)**
   - Click "CREATE SECRET" again
   - **Secret name:** Type exactly: `tavily-api-key`
   - **Secret value:** Paste your Tavily API key (if you have one)
   - Click "CREATE SECRET"
   - ✅ **Verify:** You should see "tavily-api-key" in the list

8. **Verify All Secrets Created**
   - You should see at least 3 required secrets:
     - ✅ `openai-api-key` (REQUIRED)
     - ✅ `grok-api-key` (REQUIRED)
     - ✅ `gemini-api-key` (REQUIRED)
     - ✅ `anthropic-api-key` (OPTIONAL - recommended)
     - ✅ `tavily-api-key` (OPTIONAL - for web search)

**✅ TASK 1 COMPLETE** - You've created all required secrets in Secret Manager.

---

### TASK 2: Vercel - Set Environment Variables
**Priority:** 🔴 CRITICAL  
**Time:** 3 minutes  
**Why:** Frontend needs to know where the backend is and how to authenticate

#### Step-by-Step:

1. **Open Vercel Dashboard**
   - Go to: https://vercel.com/dashboard
   - Log in to your account

2. **Select Your Project**
   - Find and click on your LLMHive project
   - If you don't see it, it might be named differently (check your GitHub repo name)

3. **Navigate to Settings**
   - Click "Settings" in the top menu
   - Click "Environment Variables" in the left sidebar

4. **Add Environment Variable: `ORCHESTRATOR_API_BASE_URL`**
   - Click "Add New" button
   - **Name:** Type exactly: `ORCHESTRATOR_API_BASE_URL` (all caps, with underscores)
   - **Value:** Type exactly: `https://llmhive-orchestrator-792354158895.us-east1.run.app`
     - ⚠️ **Important:** Replace `792354158895` with your actual Google Cloud project ID if different
   - **Environment:** Check all three boxes:
     - ✅ Production
     - ✅ Preview
     - ✅ Development
   - Click "Save"
   - ✅ **Verify:** You should see it in the list

5. **Add Environment Variable: `LLMHIVE_API_KEY` (Optional - for security)**
   - Click "Add New" button again
   - **Name:** Type exactly: `LLMHIVE_API_KEY`
   - **Value:** Create a secure random string (e.g., `llmhive-secret-key-2025-abc123xyz`)
     - ⚠️ **Important:** You'll need to use the same value in Task 5
   - **Environment:** Check all three boxes:
     - ✅ Production
     - ✅ Preview
     - ✅ Development
   - Click "Save"
   - ✅ **Verify:** You should see it in the list

6. **Verify All Variables**
   - You should see at least:
     - ✅ `ORCHESTRATOR_API_BASE_URL`
     - ✅ `LLMHIVE_API_KEY` (if you added it)

7. **Redeploy (Important!)**
   - After adding environment variables, you MUST redeploy
   - Go to "Deployments" tab
   - Click the three dots (⋮) on the latest deployment
   - Click "Redeploy"
   - Wait for deployment to complete (~2-3 minutes)

**✅ TASK 2 COMPLETE** - Frontend is now configured to connect to backend.

---

### TASK 3: Google Cloud - Verify Cloud Run Secret Mapping
**Priority:** 🔴 CRITICAL  
**Time:** 2 minutes  
**Why:** Cloud Run needs to load secrets from Secret Manager at runtime

#### Step-by-Step:

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com
   - Select your project

2. **Navigate to Cloud Run**
   - In the left menu, click "Cloud Run"
   - Or search for "Cloud Run" in the top search bar

3. **Select Your Service**
   - Find and click on: `llmhive-orchestrator`
   - If you don't see it, the service might not be deployed yet (that's OK, skip this task)

4. **Check Environment Variables**
   - Click on the service name
   - Scroll down to "Variables & Secrets" section
   - Look for "Secrets" tab
   - You should see:
     - ✅ `OPENAI_API_KEY` → `openai-api-key:latest`
     - ✅ `GROK_API_KEY` → `grok-api-key:latest`
     - ✅ `GEMINI_API_KEY` → `gemini-api-key:latest`
     - ✅ `TAVILY_API_KEY` → `tavily-api-key:latest` (if you created it)
     - ⚠️ **Note:** `ANTHROPIC_API_KEY` is not in cloudbuild.yaml but can be added manually if you want to use Claude models

5. **If Secrets Are Missing:**
   - Click "EDIT & DEPLOY NEW REVISION" button
   - Scroll to "Variables & Secrets" section
   - Click "ADD SECRET" for each missing secret:
     - **Name:** `OPENAI_API_KEY`
     - **Secret:** Select `openai-api-key` from dropdown
     - **Version:** Select `latest`
     - Click "ADD"
   - Repeat for: `GROK_API_KEY`, `GEMINI_API_KEY`, `TAVILY_API_KEY`
   - Click "DEPLOY" button at the bottom
   - Wait for deployment to complete (~2-3 minutes)

**✅ TASK 3 COMPLETE** - Cloud Run is now configured to use secrets.

---

### TASK 4: Test - Verify Frontend-Backend Connection
**Priority:** 🔴 CRITICAL  
**Time:** 2 minutes  
**Why:** Confirm everything is working

#### Step-by-Step:

1. **Open Your Live Site**
   - Go to: https://llmhive.vercel.app (or your Vercel URL)
   - Or: https://llmhive.ai (if you have a custom domain)

2. **Open Browser Developer Tools**
   - Press `F12` (Windows) or `Cmd+Option+I` (Mac)
   - Click "Console" tab

3. **Send a Test Message**
   - Type a simple message in the chat: "Hello, test message"
   - Click send
   - Watch the console for errors

4. **Check for Errors**
   - ✅ **Good:** No red errors in console, message gets a response
   - ❌ **Bad:** See errors like:
     - "Failed to fetch" → Backend URL is wrong (check Task 2)
     - "401 Unauthorized" → API key mismatch (check Tasks 2 and 5)
     - "Network error" → Backend might be down (check Cloud Run)

5. **Verify Response**
   - If you get an AI response, everything is working! ✅
   - If you get an error, check the specific error message and refer to troubleshooting below

**✅ TASK 4 COMPLETE** - System is verified and working.

---

### TASK 5: Google Cloud - Set API Key for Backend Security
**Priority:** 🟡 IMPORTANT  
**Time:** 3 minutes  
**Why:** Prevents unauthorized access to your backend API

#### Step-by-Step:

1. **Create a Secure API Key**
   - Generate a random string (e.g., `llmhive-secret-key-2025-abc123xyz`)
   - ⚠️ **Important:** Use the SAME value you used in Task 2 for `LLMHIVE_API_KEY`
   - Save this key somewhere safe (password manager)

2. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com
   - Select your project

3. **Navigate to Cloud Run**
   - Click "Cloud Run" in left menu
   - Click on `llmhive-orchestrator` service

4. **Add Environment Variable**
   - Click "EDIT & DEPLOY NEW REVISION" button
   - Scroll to "Variables & Secrets" section
   - Click "ADD VARIABLE"
   - **Name:** Type exactly: `API_KEY`
   - **Value:** Paste your secure API key (the same one from Task 2)
   - Click "ADD"
   - Click "DEPLOY" button
   - Wait for deployment (~2-3 minutes)

5. **Verify**
   - After deployment, go back to service details
   - Check "Variables & Secrets" section
   - You should see: ✅ `API_KEY` (with your value hidden)

**✅ TASK 5 COMPLETE** - Backend is now secured with API key.

---

### TASK 6: Vercel - Set API Key for Frontend Security
**Priority:** 🟡 IMPORTANT  
**Time:** 2 minutes  
**Why:** Frontend needs the API key to authenticate with backend

#### Step-by-Step:

1. **Open Vercel Dashboard**
   - Go to: https://vercel.com/dashboard
   - Select your LLMHive project

2. **Navigate to Environment Variables**
   - Click "Settings" → "Environment Variables"

3. **Verify `LLMHIVE_API_KEY` Exists**
   - Look for `LLMHIVE_API_KEY` in the list
   - If it's already there (from Task 2), you're done! ✅
   - If not, add it:
     - Click "Add New"
     - **Name:** `LLMHIVE_API_KEY`
     - **Value:** Use the SAME value from Task 5
     - **Environment:** Check all three boxes
     - Click "Save"

4. **Redeploy**
   - Go to "Deployments" tab
   - Click three dots (⋮) on latest deployment
   - Click "Redeploy"
   - Wait for completion

**✅ TASK 6 COMPLETE** - Frontend can now authenticate with backend.

---

### TASK 7: Google Cloud - Verify Cloud Build Trigger
**Priority:** 🟢 OPTIONAL  
**Time:** 2 minutes  
**Why:** Ensures automatic deployments when you push code

#### Step-by-Step:

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com
   - Select your project

2. **Navigate to Cloud Build**
   - Click "Cloud Build" in left menu
   - Click "Triggers" tab

3. **Check for Existing Trigger**
   - Look for a trigger named something like:
     - "llmhive-build-trigger"
     - "GitHub trigger"
     - Or your repository name
   - ✅ **If trigger exists:** You're done! It should automatically deploy on git push.
   - ❌ **If no trigger:** You'll need to create one (see below)

4. **Create Trigger (if needed)**
   - Click "CREATE TRIGGER" button
   - **Name:** `llmhive-auto-deploy`
   - **Event:** Select "Push to a branch"
   - **Source:** Connect your GitHub repository
   - **Branch:** `^main$` (or your main branch name)
   - **Configuration:** Select "Cloud Build configuration file"
   - **Location:** `/cloudbuild.yaml`
   - Click "CREATE"
   - ✅ **Verify:** Trigger appears in the list

**✅ TASK 7 COMPLETE** - Automatic deployments are configured.

---

### TASK 8: Google Cloud - Set Up Monitoring (Optional)
**Priority:** 🟢 OPTIONAL  
**Time:** 5 minutes  
**Why:** Helps you see if the system is working and catch errors

#### Step-by-Step:

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com
   - Select your project

2. **Navigate to Cloud Run**
   - Click "Cloud Run" → `llmhive-orchestrator`

3. **View Logs**
   - Click "LOGS" tab
   - You should see recent log entries
   - ✅ **Good:** See successful requests
   - ❌ **Bad:** See error messages (red text)

4. **Set Up Alerts (Optional)**
   - Click "Monitoring" in left menu
   - Click "Alerting" → "Create Policy"
   - **Name:** `LLMHive Error Alert`
   - **Condition:** Select "Cloud Run Service" → "Error Rate"
   - **Threshold:** Set to alert if error rate > 5%
   - Click "Save"

**✅ TASK 8 COMPLETE** - Monitoring is set up.

---

## 🔍 VERIFICATION CHECKLIST

After completing all tasks, verify everything is working:

- [ ] **Secret Manager:** All 4 secrets exist (`openai-api-key`, `grok-api-key`, `gemini-api-key`, `tavily-api-key`)
- [ ] **Vercel:** Environment variables set (`ORCHESTRATOR_API_BASE_URL`, `LLMHIVE_API_KEY`)
- [ ] **Cloud Run:** Secrets mapped correctly (check "Variables & Secrets" section)
- [ ] **Cloud Run:** `API_KEY` environment variable set (if using security)
- [ ] **Test:** Frontend can send messages and get responses
- [ ] **Test:** No errors in browser console
- [ ] **Test:** Backend logs show successful requests

---

## 🚨 TROUBLESHOOTING

### Problem: "Failed to fetch" error in browser
**Solution:**
- Check `ORCHESTRATOR_API_BASE_URL` in Vercel (Task 2)
- Verify the URL is correct: `https://llmhive-orchestrator-792354158895.us-east1.run.app`
- Make sure you redeployed Vercel after adding the variable

### Problem: "401 Unauthorized" error
**Solution:**
- Check `API_KEY` in Cloud Run matches `LLMHIVE_API_KEY` in Vercel (Tasks 5 and 6)
- Make sure both are set to the exact same value
- Redeploy both Cloud Run and Vercel after changes

### Problem: "500 Internal Server Error"
**Solution:**
- Check Cloud Run logs for specific error
- Verify all secrets are created in Secret Manager (Task 1)
- Verify secrets are mapped in Cloud Run (Task 3)

### Problem: No AI responses, just demo mode
**Solution:**
- Check `ORCHESTRATOR_API_BASE_URL` is set in Vercel (Task 2)
- Verify backend is running (check Cloud Run service status)
- Check browser console for errors

### Problem: Secrets not found in Cloud Run
**Solution:**
- Verify secrets exist in Secret Manager (Task 1)
- Check secret names are exactly: `openai-api-key`, `grok-api-key`, etc. (lowercase, with hyphens)
- Re-add secrets in Cloud Run (Task 3)

---

## 📞 NEED HELP?

If you encounter issues:
1. Check the troubleshooting section above
2. Review Cloud Run logs for error messages
3. Check browser console for frontend errors
4. Verify all environment variables are set correctly

---

## ✅ COMPLETION CHECKLIST

Mark tasks as complete as you finish them:

- [ ] Task 1: Google Cloud Secret Manager secrets created
- [ ] Task 2: Vercel environment variables set
- [ ] Task 3: Cloud Run secret mapping verified
- [ ] Task 4: Frontend-backend connection tested
- [ ] Task 5: Backend API key set (optional)
- [ ] Task 6: Frontend API key set (optional)
- [ ] Task 7: Cloud Build trigger verified (optional)
- [ ] Task 8: Monitoring set up (optional)

---

**Last Updated:** November 27, 2025  
**Status:** Ready for execution  
**Estimated Total Time:** 20-25 minutes (for all critical tasks)

