# LLMHive API quickstart — marketplace reviewers

**Production base URL (orchestrator):**

```
https://llmhive-orchestrator-792354158895.us-east1.run.app
```

**Customer-facing app:** https://www.llmhive.ai (workspace + billing)  
**Full reference:** `docs/launch/API_REFERENCE.md` (OpenAI-style paths; production smoke uses `/v1/chat` below)

---

## Authentication

Send the customer API key on every request:

```bash
export LLMHIVE_API_KEY="your-customer-api-key"
export BASE_URL="https://llmhive-orchestrator-792354158895.us-east1.run.app"
```

Headers (either is accepted):

- `Authorization: Bearer $LLMHIVE_API_KEY`
- `X-API-Key: $LLMHIVE_API_KEY`

Keys are issued after signup and paid subscription (see https://www.llmhive.ai/pricing). Marketplace validation accounts: contact cdiaz@llmhive.ai.

---

## Health check (no auth)

```bash
curl -sS "$BASE_URL/health"
```

Expect HTTP `200`.

---

## Chat orchestration

**Endpoint:** `POST /v1/chat`

Requires:

1. Valid API key (gateway auth)
2. Active paid subscription — pass Clerk `user_id` in `metadata.user_id` (same as production app)

```bash
curl -sS -X POST "$BASE_URL/v1/chat" \
  -H "Authorization: Bearer $LLMHIVE_API_KEY" \
  -H "X-API-Key: $LLMHIVE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Say hello in one sentence.",
    "max_tokens": 100,
    "stream": false,
    "metadata": {
      "user_id": "user_YOUR_CLERK_ID"
    }
  }'
```

**Success:** HTTP `200` with `message`, `content`, or `response` field.  
**402:** Missing or inactive subscription — complete checkout on llmhive.ai.  
**401:** Invalid API key.

### Example response shape

```json
{
  "message": "...",
  "models_used": ["..."],
  "metadata": { "chat_id": "..." }
}
```

---

## Integration via web app (recommended for trials)

1. Create account at https://www.llmhive.ai/sign-in  
2. Subscribe to Standard or Premium  
3. Use **Workspace** chat — requests proxy to the orchestrator with correct `user_id` and billing gates  

Direct API integration uses the same backend path as the workspace.

---

## Rate limits and timeouts

- Respect HTTP `429` — backoff and retry
- Client timeout: recommend **60s** for orchestrated requests
- Spend guard may route paid accounts to free orchestration when monthly provider cap is reached (see pricing FAQ on site)

---

## Support

- Email: cdiaz@llmhive.ai  
- Hours (launch): 8am–10pm ET — see `support_matrix.md`

---

## Compliance note for reviewers

Prompts and responses may be processed by third-party model providers (OpenAI, Anthropic, Google, etc.) according to routing logic. See `security_data_flow.md`.
