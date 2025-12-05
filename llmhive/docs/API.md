# LLMHive API Documentation

## Overview

LLMHive provides a REST API for multi-model LLM orchestration. The API allows you to:

- Send chat messages with configurable reasoning modes
- Execute code in a sandboxed environment
- Configure reasoning methods
- List available LLM models/agents

**Base URL**: `https://api.llmhive.ai` (production) or `http://localhost:8080` (local)

**API Version**: v1

## Authentication

All endpoints except health checks require authentication via API key.

```http
X-API-Key: your-api-key
```

## Endpoints

### Chat

#### POST /v1/chat

Send a chat message with multi-model orchestration.

**Request Body:**

```json
{
  "prompt": "What is the capital of France?",
  "models": ["gpt-4o", "claude-sonnet-4"],
  "reasoning_mode": "standard",
  "reasoning_method": "chain-of-thought",
  "domain_pack": "default",
  "agent_mode": "team",
  "tuning": {
    "prompt_optimization": true,
    "output_validation": true,
    "answer_structure": true,
    "learn_from_chat": true
  },
  "orchestration": {
    "accuracy_level": 3,
    "enable_hrm": false,
    "enable_deep_consensus": false,
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "metadata": {
    "chat_id": "conv-123",
    "user_id": "user-456"
  },
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
  ]
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | User prompt/question |
| `models` | string[] | No | List of model IDs to use. Auto-selected if not provided |
| `reasoning_mode` | enum | No | `fast`, `standard`, or `deep` (default: `standard`) |
| `reasoning_method` | enum | No | Advanced reasoning method (see below) |
| `domain_pack` | enum | No | Domain specialization (see below) |
| `agent_mode` | enum | No | `single` or `team` (default: `team`) |
| `tuning` | object | No | Tuning options |
| `orchestration` | object | No | Orchestration settings |
| `metadata` | object | No | Request metadata |
| `history` | array | No | Conversation history |

**Reasoning Modes:**
- `fast` - Quick response with minimal processing
- `standard` - Balanced quality and speed
- `deep` - Maximum quality with extended reasoning

**Reasoning Methods:**
- `chain-of-thought` - Step-by-step reasoning
- `tree-of-thought` - Explore multiple reasoning paths
- `react` - Reason + Act pattern
- `plan-and-solve` - Create plan then execute
- `self-consistency` - Multiple reasoning paths with voting
- `reflexion` - Self-reflection and correction

**Domain Packs:**
- `default` - General purpose
- `medical` - Healthcare/medical context
- `legal` - Legal/compliance context
- `marketing` - Marketing/advertising context
- `coding` - Software development context
- `research` - Academic/research context
- `finance` - Financial/investment context

**Response:**

```json
{
  "message": "The capital of France is Paris.",
  "models_used": ["gpt-4o", "claude-sonnet-4"],
  "reasoning_mode": "standard",
  "reasoning_method": "chain-of-thought",
  "domain_pack": "default",
  "agent_mode": "team",
  "used_tuning": {
    "prompt_optimization": true,
    "output_validation": true,
    "answer_structure": true,
    "learn_from_chat": true
  },
  "metadata": {
    "chat_id": "conv-123"
  },
  "tokens_used": 150,
  "latency_ms": 1200,
  "agent_traces": [
    {
      "agent_id": "agent-1",
      "agent_name": "researcher",
      "contribution": "Verified geographical fact",
      "confidence": 0.95
    }
  ],
  "extra": {
    "strategy": "consensus"
  }
}
```

---

### Agents

#### GET /agents

List available LLM models and their status.

**Response:**

```json
{
  "agents": [
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "openai",
      "available": true,
      "description": "OpenAI's flagship multimodal model",
      "capabilities": {
        "vision": true,
        "codeExecution": true,
        "webSearch": true,
        "reasoning": true
      }
    },
    {
      "id": "claude-sonnet-4",
      "name": "Claude Sonnet 4",
      "provider": "anthropic",
      "available": true,
      "description": "Anthropic's latest and most capable model",
      "capabilities": {
        "vision": true,
        "codeExecution": true,
        "webSearch": false,
        "reasoning": true
      }
    }
  ],
  "source": "backend"
}
```

---

### Code Execution

#### POST /v1/execute/python

Execute Python code in a sandboxed environment.

**Request Body:**

```json
{
  "code": "print('Hello, World!')",
  "language": "python",
  "session_token": "session-abc123"
}
```

**Response (Success):**

```json
{
  "success": true,
  "output": "Hello, World!\n",
  "error": null,
  "metadata": {
    "execution_time_ms": 50,
    "tokens_used": 10
  }
}
```

**Response (Error):**

```json
{
  "success": false,
  "output": "",
  "error": "SyntaxError: invalid syntax",
  "metadata": {
    "execution_result": {}
  }
}
```

**Security Notes:**
- Code runs in a sandboxed environment with resource limits
- Network access is disabled by default
- Maximum execution time: 5 seconds
- Maximum memory: 512 MB

---

### Reasoning Configuration

#### GET /reasoning-config

Get current reasoning configuration.

**Query Parameters:**
- `user_id` (optional): User identifier for per-user config

**Response:**

```json
{
  "mode": "auto",
  "selectedMethods": []
}
```

#### POST /reasoning-config

Save reasoning configuration.

**Request Body:**

```json
{
  "mode": "manual",
  "selectedMethods": ["chain-of-thought", "self-consistency"]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Reasoning configuration saved. Mode: manual, Methods: 2",
  "config": {
    "mode": "manual",
    "selectedMethods": ["chain-of-thought", "self-consistency"]
  }
}
```

#### GET /reasoning-methods

List available reasoning methods.

**Response:**

```json
[
  "chain-of-thought",
  "tree-of-thought",
  "self-consistency",
  "reflexion",
  "react",
  "meta-prompting",
  "step-back",
  "analogical-reasoning",
  "socratic-method",
  "decomposition"
]
```

---

### Health Checks

#### GET /healthz

Primary health check endpoint (for Cloud Run, Kubernetes).

**Response:**

```json
{
  "status": "ok"
}
```

#### GET /health/ready

Readiness check with provider status.

**Response:**

```json
{
  "status": "ready",
  "providers": ["openai", "anthropic", "stub"],
  "provider_count": 3,
  "circuit_breakers": {}
}
```

#### GET /health/live

Simple liveness check.

**Response:**

```json
{
  "status": "alive"
}
```

---

## Error Responses

All errors follow a standard format:

```json
{
  "error": {
    "code": "E1001",
    "message": "Invalid request parameters",
    "details": {
      "field": "prompt",
      "reason": "Field is required"
    },
    "recoverable": true
  },
  "correlation_id": "abc123",
  "request_id": "req-456",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `E1000` | 500 | Internal server error |
| `E1001` | 400 | Validation error |
| `E1002` | 404 | Resource not found |
| `E1003` | 401 | Unauthorized |
| `E1004` | 403 | Forbidden |
| `E2001` | 429 | Rate limited |
| `E2002` | 504 | Timeout |
| `E3001` | 503 | Provider unavailable |
| `E3002` | 504 | Provider timeout |
| `E3003` | 429 | Provider rate limited |
| `E3004` | 503 | All providers failed |
| `E3005` | 503 | Circuit breaker open |

---

## Response Headers

All responses include tracking headers:

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique request identifier |
| `X-Correlation-ID` | Correlation ID for distributed tracing |
| `X-Response-Time-Ms` | Server processing time in milliseconds |
| `X-Models-Used` | JSON array of models used (chat endpoint) |
| `X-Tokens-Used` | Total tokens consumed (chat endpoint) |
| `X-Latency-Ms` | Backend processing latency (chat endpoint) |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/v1/chat` | 100 requests | per minute |
| `/v1/execute/python` | 20 requests | per minute |
| `/agents` | 200 requests | per minute |
| Other endpoints | 500 requests | per minute |

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642000000
```

---

## Stub Endpoints (Future Features)

These endpoints are placeholders for upcoming features:

### POST /v1/analyze/file
Analyze uploaded files (not yet implemented)

### POST /v1/generate/image
Generate images from prompts (not yet implemented)

### POST /v1/visualize/data
Create data visualizations (not yet implemented)

### POST /v1/collaborate
Collaboration features (not yet implemented)

---

## OpenAPI Specification

The full OpenAPI specification is available at:

- JSON: `/openapi.json`
- Interactive docs: `/docs` (Swagger UI)
- ReDoc: `/redoc`

---

## TypeScript Types

TypeScript types matching the API are available in `lib/api-types.generated.ts`.

To regenerate:

```bash
cd llmhive
python scripts/generate_types.py -o ../lib/api-types.generated.ts
```

---

## Examples

### cURL - Basic Chat

```bash
curl -X POST https://api.llmhive.ai/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "Explain quantum computing in simple terms",
    "reasoning_mode": "standard"
  }'
```

### cURL - Team Mode with Consensus

```bash
curl -X POST https://api.llmhive.ai/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "What are the pros and cons of microservices?",
    "models": ["gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"],
    "agent_mode": "team",
    "orchestration": {
      "enable_deep_consensus": true,
      "accuracy_level": 5
    }
  }'
```

### Python - Using the API

```python
import httpx

client = httpx.Client(
    base_url="https://api.llmhive.ai",
    headers={"X-API-Key": "your-api-key"}
)

response = client.post("/v1/chat", json={
    "prompt": "Write a Python function to calculate fibonacci numbers",
    "domain_pack": "coding",
    "reasoning_mode": "deep"
})

result = response.json()
print(result["message"])
print(f"Models used: {result['models_used']}")
print(f"Latency: {result['latency_ms']}ms")
```

### JavaScript/TypeScript - Using the API

```typescript
import type { ChatRequest, ChatResponse } from './lib/api-types.generated'

const response = await fetch('https://api.llmhive.ai/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    prompt: 'Explain the theory of relativity',
    reasoning_mode: 'deep',
    domain_pack: 'research'
  } satisfies ChatRequest)
})

const result: ChatResponse = await response.json()
console.log(result.message)
```
