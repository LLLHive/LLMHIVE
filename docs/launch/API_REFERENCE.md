# LLMHive API Reference

Complete API documentation for LLMHive v1.0.

## Base URL

```
Production: https://api.llmhive.io/v1
Staging: https://staging-api.llmhive.io/v1
Local: http://localhost:8080/v1
```

## Authentication

All API requests require authentication via Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.llmhive.io/v1/chat/completions
```

---

## Endpoints

### Chat Completions

#### `POST /v1/chat/completions`

Generate a response from LLMHive.

**Request Body:**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    }
  ],
  "model": "gpt-4o",
  "max_tokens": 1000,
  "temperature": 0.7,
  "accuracy_level": 3,
  "use_hrm": false,
  "use_consensus": false,
  "tools": []
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `messages` | array | Yes | Array of message objects |
| `model` | string | No | Preferred model (default: auto-selected) |
| `max_tokens` | int | No | Maximum tokens in response (default: 1000) |
| `temperature` | float | No | Sampling temperature 0-2 (default: 0.7) |
| `accuracy_level` | int | No | 1-5, higher = more accurate (default: 3) |
| `use_hrm` | bool | No | Enable hierarchical planning (default: false) |
| `use_consensus` | bool | No | Enable multi-model consensus (default: false) |
| `tools` | array | No | List of tools to enable |

**Message Object:**

```json
{
  "role": "user" | "assistant" | "system",
  "content": "Message content",
  "images": ["base64_image_data"],  // Optional for multimodal
  "audio": "base64_audio_data"      // Optional for audio input
}
```

**Response:**

```json
{
  "id": "chat-123456",
  "object": "chat.completion",
  "created": 1699000000,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 8,
    "total_tokens": 23
  },
  "metadata": {
    "orchestration_time_ms": 1234,
    "models_used": ["gpt-4o"],
    "tools_used": [],
    "consensus_score": null
  }
}
```

**Example:**

```bash
curl -X POST https://api.llmhive.io/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

---

### Multimodal Requests

#### Image Analysis

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What's in this image?",
      "images": ["data:image/jpeg;base64,/9j/4AAQ..."]
    }
  ]
}
```

#### Image Generation

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Generate an image of a sunset over mountains"
    }
  ],
  "tools": ["image_generation"]
}
```

**Response includes:**
```json
{
  "choices": [{
    "message": {
      "content": "Here's your generated image:",
      "images": ["https://storage.llmhive.io/images/abc123.png"]
    }
  }]
}
```

#### Audio Transcription

```json
{
  "messages": [
    {
      "role": "user",
      "audio": "data:audio/wav;base64,UklGR..."
    }
  ]
}
```

---

### Tools

#### `GET /v1/tools`

List available tools.

**Response:**

```json
{
  "tools": [
    {
      "name": "calculator",
      "description": "Perform mathematical calculations",
      "parameters": {
        "expression": "string"
      },
      "tier_required": "free"
    },
    {
      "name": "web_search",
      "description": "Search the web for information",
      "parameters": {
        "query": "string"
      },
      "tier_required": "pro"
    }
  ]
}
```

#### `POST /v1/tools/execute`

Execute a tool directly (advanced).

```json
{
  "tool": "calculator",
  "parameters": {
    "expression": "sqrt(144) + 10"
  }
}
```

---

### Memory

#### `GET /v1/memory`

Retrieve user memories.

**Query Parameters:**
- `category`: Filter by category (fact, preference, context)
- `limit`: Max results (default: 10)

**Response:**

```json
{
  "memories": [
    {
      "id": "mem_123",
      "content": "User prefers concise responses",
      "category": "preference",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### `POST /v1/memory`

Store a memory.

```json
{
  "content": "Remember that I prefer Python over JavaScript",
  "category": "preference"
}
```

#### `DELETE /v1/memory/{id}`

Delete a specific memory.

---

### Billing & Usage

#### `GET /v1/usage`

Get usage statistics.

**Response:**

```json
{
  "current_period": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-31T23:59:59Z",
    "requests_used": 500,
    "tokens_used": 125000,
    "cost_usd": 12.50
  },
  "limits": {
    "requests_per_month": 10000,
    "tokens_per_month": 1000000
  }
}
```

#### `GET /v1/subscription`

Get subscription details.

**Response:**

```json
{
  "tier": "pro",
  "status": "active",
  "current_period_end": "2024-02-01T00:00:00Z",
  "features": {
    "hrm_enabled": true,
    "consensus_enabled": true,
    "image_generation": true,
    "priority_support": true
  }
}
```

---

### Health & Status

#### `GET /healthz`

Liveness check.

```json
{"status": "ok"}
```

#### `GET /readyz`

Readiness check.

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "models": "ok"
  }
}
```

#### `GET /health`

Comprehensive health check.

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "providers": {
    "openai": "connected",
    "anthropic": "connected"
  },
  "memory_usage_mb": 512,
  "request_count_24h": 10000
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "You have exceeded your rate limit. Please upgrade your plan.",
    "type": "rate_limit_error",
    "details": {
      "limit": 100,
      "used": 100,
      "reset_at": "2024-01-15T11:00:00Z"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_request` | 400 | Malformed request |
| `authentication_error` | 401 | Invalid or missing API key |
| `permission_denied` | 403 | Insufficient tier/permissions |
| `not_found` | 404 | Resource not found |
| `rate_limit_exceeded` | 429 | Rate limit hit |
| `tier_limit_exceeded` | 429 | Monthly limit hit |
| `content_policy_violation` | 400 | Content blocked by safety |
| `model_unavailable` | 503 | Model temporarily unavailable |
| `internal_error` | 500 | Server error |

---

## Rate Limits

| Tier | Requests/min | Requests/month | Tokens/month |
|------|--------------|----------------|--------------|
| Free | 10 | 100 | 50,000 |
| Pro | 60 | 10,000 | 1,000,000 |
| Enterprise | 300 | Unlimited | Unlimited |

---

## SDKs

### Python

```python
from llmhive import LLMHive

client = LLMHive(api_key="your-key")

response = client.chat.completions.create(
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)

print(response.choices[0].message.content)
```

### JavaScript/TypeScript

```typescript
import { LLMHive } from '@llmhive/sdk';

const client = new LLMHive({ apiKey: 'your-key' });

const response = await client.chat.completions.create({
  messages: [{ role: 'user', content: 'Hello!' }],
  maxTokens: 100,
});

console.log(response.choices[0].message.content);
```

---

## Webhooks

Configure webhooks for billing events:

### Events

- `subscription.created`
- `subscription.updated`
- `subscription.cancelled`
- `invoice.paid`
- `invoice.failed`
- `usage.limit_warning` (80% of limit)
- `usage.limit_reached`

### Webhook Payload

```json
{
  "event": "subscription.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "user_id": "user_123",
    "tier": "pro",
    "subscription_id": "sub_abc123"
  }
}
```

---

## Changelog

### v1.0.0 (Current)
- Initial release
- Chat completions API
- Multimodal support (images, audio)
- Tool execution
- Memory management
- Billing integration

