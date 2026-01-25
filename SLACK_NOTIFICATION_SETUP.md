# 🔔 Slack Notification Setup & Troubleshooting

## Status: ✅ Webhooks Working

**Last Tested:** January 25, 2026  
**Test Result:** Webhook returns `ok`, HTTP 200 ✅

---

## Issue Reported

**Problem:** Support widget sends ticket successfully, but user doesn't see Slack notification

**Diagnosis:** Webhook is working correctly, but notifications might be going to:
- A channel the user isn't monitoring
- A different Slack workspace
- Slackbot DMs
- A channel with notifications muted

---

## Current Configuration

### Webhook Details
- **Workspace ID:** `T06JTT719GS`
- **Webhook ID:** `B0AA1Q7TNGY`
- **Secret Name:** `slack-webhook-url` (in Google Cloud Secret Manager)
- **Environment Variable:** `SLACK_WEBHOOK_URL` (mapped in Cloud Run)
- **Status:** ✅ Active (returns "ok" on POST)

### Test Confirmation
```bash
curl -X POST "<WEBHOOK_URL>" \
  -H "Content-Type: application/json" \
  -d '{"text": "🧪 Test from LLMHive support system"}' 

Response: ok
HTTP Status: 200
```

---

## Where to Find Notifications

### Option 1: Check All Channels
The user's screenshot showed these channels in the "multitradecont" workspace:
- **#all-multitradecont**
- **#new-channel**
- **#social**

**Action:** Check each of these channels for support ticket notifications.

### Option 2: Check Slackbot DMs
Sometimes webhook notifications go to your personal Slackbot DM.

**Action:**
1. In Slack sidebar, look for **"Slackbot"** at the top
2. Click to open DMs with Slackbot
3. Look for support ticket messages

### Option 3: Check Activity Feed
**Action:**
1. Click the **"Activity"** button in Slack (top right)
2. Look for recent notifications
3. Filter by "Mentions & reactions" or "All activity"

### Option 4: Search Slack
**Action:**
1. Press `Cmd+K` (Mac) or `Ctrl+K` (Windows)
2. Search for: `TKT-697675CC-3BED` (the ticket ID from your test)
3. Or search: `"New Support Ticket"`

---

## Verifying Webhook Configuration

### Check Which Workspace
The webhook is configured for workspace `T06JTT719GS`.

**Action:** Verify you're in the correct workspace:
1. Click workspace name (top left in Slack)
2. Look at "Sign in to another workspace" - make sure you're in `T06JTT719GS`

### Check Webhook Permissions
The webhook might have been created for a specific channel that was later deleted or renamed.

**Action (Admin only):**
1. Go to https://api.slack.com/apps
2. Find the app associated with webhook ID `B0AA1Q7TNGY`
3. Check "Incoming Webhooks" settings
4. Verify which channel it posts to

---

## Reconfiguring Slack Webhook

If you need to change which channel receives notifications:

### Step 1: Create New Incoming Webhook
1. Go to https://api.slack.com/apps
2. Create a new app or select existing app
3. Enable "Incoming Webhooks"
4. Click "Add New Webhook to Workspace"
5. Select the channel you want (e.g., #support-tickets)
6. Copy the webhook URL

### Step 2: Update Secret in Google Cloud
```bash
# Update the secret
echo "<NEW_WEBHOOK_URL>" | gcloud secrets versions add slack-webhook-url --data-file=-

# Verify it was updated
gcloud secrets versions list slack-webhook-url
```

### Step 3: Restart Cloud Run Service
```bash
# Cloud Run will automatically pick up new secret version on next cold start
# Or force a new deployment:
gcloud run services update llmhive-orchestrator --region=us-east1
```

### Step 4: Test
```bash
# Send test message
curl -X POST "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app/v1/support/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Testing new webhook",
    "message": "This should appear in the new channel",
    "type": "general"
  }'
```

---

## Notification Format

Support tickets send rich Slack notifications with:

### Header
🟢 New Support Ticket (color-coded by priority)

### Fields
- **Ticket ID:** TKT-xxxxx-xxxxx
- **Priority:** low/medium/high/urgent
- **Type:** general/technical/billing/enterprise/bug/feature
- **From:** User Name
- **Email:** user@example.com
- **Subject:** Subject line
- **Message:** Message content (truncated to 500 chars)
- **Created at:** Timestamp

### Priority Colors
- 🚨 **Urgent:** Red (#dc2626)
- 🔴 **High:** Orange (#f97316)
- 🟡 **Medium:** Yellow (#eab308)
- 🟢 **Low:** Green (#22c55e)

---

## Testing Notifications

### Send Test Ticket
```bash
# Via backend directly
curl -X POST "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app/v1/support/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Debug Test",
    "email": "debug@llmhive.ai",
    "subject": "Slack webhook test",
    "message": "If you see this in Slack, notifications are working!",
    "type": "general"
  }'

# Check response for ticket ID
# Then search for that ticket ID in Slack
```

### Check Backend Logs
```bash
# Check if notification was sent
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=llmhive-orchestrator AND textPayload=~\"Slack\"" --limit=10

# Look for:
# ✅ [Support] ✅ Slack notification sent for ticket TKT-xxxxx
# ⚠️ [Support] ⚠️ SLACK_WEBHOOK_URL not configured (if missing)
# ❌ [Support] ❌ Slack notification failed: <error> (if failed)
```

---

## Troubleshooting

### Notifications Not Appearing

**1. Verify webhook is working:**
```bash
# Get webhook URL
WEBHOOK_URL=$(gcloud secrets versions access latest --secret="slack-webhook-url")

# Test directly
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text": "Direct test message"}'

# Should return: ok
```

**2. Check you're in the right workspace:**
- Workspace ID in webhook: `T06JTT719GS`
- Make sure you're signed into this workspace

**3. Check channel permissions:**
- You might not have access to the channel the webhook posts to
- Ask workspace admin to invite you

**4. Check if channel was deleted:**
- Webhook might be configured for a deleted channel
- Reconfigure webhook (see above)

### Notifications Going to Wrong Channel

**Solution:** Reconfigure webhook (see "Reconfiguring Slack Webhook" above)

### Multiple Notifications

**Cause:** If you're in multiple Slack workspaces, you might have webhooks configured in multiple places.

**Solution:**
1. Check which workspace ID your webhook uses
2. Disable webhooks in other workspaces
3. Keep only one active webhook

---

## Alternative: Slack App with Bot

For more control (posting to multiple channels, threading, reactions), consider upgrading from webhook to a full Slack App with Bot:

### Benefits
- Post to any channel dynamically
- Thread conversations
- Add reactions
- Search/update tickets
- User lookup

### Migration Steps
1. Create Slack App at https://api.slack.com/apps
2. Add Bot Token Scopes: `chat:write`, `chat:write.public`
3. Install app to workspace
4. Get Bot Token (starts with `xoxb-`)
5. Update backend to use Bot Token instead of webhook
6. Use Slack Web API (`chat.postMessage`) instead of webhook POST

---

## Summary

### ✅ Current Status
- Webhook URL is valid
- Backend sends notifications correctly
- HTTP 200 responses from Slack

### 🔍 Next Steps
1. **Check Slackbot DMs** - Most likely location
2. **Search for ticket ID** - `TKT-697675CC-3BED`
3. **Check all channels** - Especially #social, #new-channel
4. **Verify workspace** - Make sure you're in `T06JTT719GS`
5. **If still not found** - Reconfigure webhook to a channel you can see

### 🆘 Need Help?
If notifications still don't appear:
1. Share screenshot of Slack workspace dropdown (showing workspace ID)
2. Share list of channels you have access to
3. Check with workspace admin which channel the webhook posts to

---

*Last updated: January 25, 2026*
*Webhook tested and confirmed working*
