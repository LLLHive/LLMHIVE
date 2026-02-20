# LLMHive — Rollback Protocol

Emergency and planned rollback procedures for the LLMHive orchestrator deployed on Google Cloud Run.

---

## 1. Identify Current and Previous Revisions

```bash
# List the last 5 revisions
gcloud run revisions list \
  --service llmhive-orchestrator \
  --region us-east1 \
  --project "$GCP_PROJECT_ID" \
  --sort-by "~creationTimestamp" \
  --limit 5

# Identify which revision is currently serving traffic
gcloud run services describe llmhive-orchestrator \
  --region us-east1 \
  --project "$GCP_PROJECT_ID" \
  --format "value(status.traffic)"
```

---

## 2. Rollback Traffic to Previous Revision

```bash
# Replace PREVIOUS_REVISION with the revision name from step 1
PREVIOUS_REVISION="llmhive-orchestrator-XXXXXXX"

gcloud run services update-traffic llmhive-orchestrator \
  --region us-east1 \
  --project "$GCP_PROJECT_ID" \
  --to-revisions "$PREVIOUS_REVISION=100"
```

---

## 3. Git Tag Restore

```bash
# List recent tags
git tag --sort=-creatordate | head -10

# Checkout the last known-good tag
git checkout tags/v<VERSION> -b rollback-v<VERSION>

# Or revert to a specific commit
git checkout <COMMIT_HASH> -b rollback-<COMMIT_HASH>
```

---

## 4. Redeploy Known-Good Version

```bash
# Build and deploy the rolled-back code
gcloud run deploy llmhive-orchestrator \
  --source . \
  --region us-east1 \
  --project "$GCP_PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars "DEPLOYMENT_TAG=rollback-$(date +%Y%m%d)"
```

---

## 5. Emergency: Disable Verification Toggle

If the verify pipeline is causing cascading failures but the core service is healthy, disable verification without redeploying:

```bash
gcloud run services update llmhive-orchestrator \
  --region us-east1 \
  --project "$GCP_PROJECT_ID" \
  --update-env-vars "DISABLE_VERIFICATION=true"
```

To re-enable:

```bash
gcloud run services update llmhive-orchestrator \
  --region us-east1 \
  --project "$GCP_PROJECT_ID" \
  --remove-env-vars "DISABLE_VERIFICATION"
```

---

## 6. Verification After Rollback

After executing a rollback:

1. **Smoke test** the production endpoint:
   ```bash
   curl -s -X POST "$LLMHIVE_API_URL/v1/chat" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"prompt": "What is 2+2?", "reasoning_mode": "basic"}' \
     | python3 -m json.tool
   ```

2. **Check health endpoint**:
   ```bash
   curl -s "$LLMHIVE_API_URL/healthz" | python3 -m json.tool
   ```

3. **Monitor error rates** for 15 minutes via Cloud Run metrics dashboard.

4. **Run micro-validation** to confirm baseline performance:
   ```bash
   python3 scripts/micro_validation.py --dry-run
   ```

---

## 7. Escalation Contacts

| Role | Contact | When to Escalate |
|---|---|---|
| On-call Engineer | (fill in) | Any production incident |
| Tech Lead | (fill in) | Rollback fails or repeats within 24h |
| Infrastructure | (fill in) | Cloud Run platform issues |

---

## 8. Post-Incident

After any rollback:

- [ ] Create incident report
- [ ] Identify root cause
- [ ] Add regression test for the failure
- [ ] Re-run full benchmark suite before next deploy attempt
