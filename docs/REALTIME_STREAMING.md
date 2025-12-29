# Real-Time Event Streaming & Collaboration

This document describes the real-time event streaming (SSE) and multi-user collaboration features in LLMHive.

## Overview

LLMHive provides two real-time features:

1. **Orchestration Event Streaming**: Real-time visibility into the orchestration process (model calls, tool invocations, etc.)
2. **Collaborative Sessions**: Multi-user shared sessions with real-time message synchronization

Both features use **Server-Sent Events (SSE)** rather than WebSockets for compatibility with serverless platforms like Vercel.

---

## 1. Orchestration Event Streaming

### Why SSE?

| Factor | SSE | WebSocket |
|--------|-----|-----------|
| Serverless compatibility | ✅ Works on Vercel | ❌ Not supported |
| One-way server→client | ✅ Perfect fit | ⚠️ Overkill |
| Auto-reconnection | ✅ Built into EventSource | ❌ Manual implementation |
| Complexity | ✅ Simple HTTP | ⚠️ Protocol upgrade required |

### Endpoint

```
GET /api/v1/events/orchestration/{session_id}
```

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dev_mode` | bool | false | Include verbose debug events |
| `filter` | string | null | Comma-separated event types to include |

### Event Types

| Type | Description | Details |
|------|-------------|---------|
| `strategy_selected` | Orchestration strategy chosen | strategy, reason |
| `model_call` | Model inference started | model, prompt_preview |
| `model_response` | Model inference completed | model, tokens, latency_ms |
| `tool_invoked` | External tool called | tool_type, query |
| `tool_result` | Tool returned result | tool_type, success, latency_ms |
| `verification` | Answer verification result | passed, verdict |
| `step` | Generic orchestration step | step, description |
| `error` | Error occurred | error_type, message |
| `complete` | Orchestration finished | success, summary |

### Usage (JavaScript)

```javascript
// Connect to SSE stream
const sessionId = 'my-session-123';
const es = new EventSource(`/api/v1/events/orchestration/${sessionId}?dev_mode=true`);

// Handle orchestration events
es.addEventListener('orchestration_event', (e) => {
    const event = JSON.parse(e.data);
    console.log(`[${event.type}] ${event.message}`);
    
    if (event.details) {
        console.log('  Details:', event.details);
    }
});

// Handle keepalive
es.addEventListener('keepalive', (e) => {
    console.log('Connection alive');
});

// Handle connection events
es.onopen = () => console.log('Connected to SSE stream');
es.onerror = () => console.log('SSE error, will auto-reconnect');
```

### Emitting Events (Backend)

From orchestrator code, emit events using the helper functions:

```python
from llmhive.app.routers.sse_events import (
    emit_strategy_selected,
    emit_model_call,
    emit_model_response,
    emit_tool_invoked,
    emit_complete,
)

# When strategy is selected
emit_strategy_selected(session_id, "parallel_race", "Fast query detected")

# When calling a model
emit_model_call(session_id, "gpt-4o", "What is 2+2?")

# When model responds
emit_model_response(session_id, "gpt-4o", tokens=150, latency_ms=340.5)

# When complete
emit_complete(session_id, success=True, summary="Answered in 2.3s")
```

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Orchestrator  │────▶│  EventBroadcaster │────▶│   SSE Clients   │
│                 │     │   (singleton)     │     │                 │
│ emit_*() calls  │     │  session→queues   │     │  EventSource()  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

The `EventBroadcaster` maintains session-scoped queues. When an event is emitted, it's pushed to all connected clients for that session.

---

## 2. Collaborative Sessions

### Features

- **Invite-based access**: Share sessions via invite token/URL
- **Persistent messages**: Message history stored (in-memory or database)
- **Real-time sync**: SSE streaming for live updates
- **Access control**: Owner, editor, viewer roles

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/collaborate` | Create a new session |
| POST | `/api/v1/collaborate/join` | Join via invite token |
| GET | `/api/v1/collaborate/{id}` | Get session info |
| GET | `/api/v1/collaborate/{id}/history` | Get message history |
| GET | `/api/v1/collaborate/{id}/participants` | List participants |
| POST | `/api/v1/collaborate/{id}/messages` | Send a message |
| GET | `/api/v1/collaborate/{id}/stream` | SSE stream |
| DELETE | `/api/v1/collaborate/{id}` | Delete (owner only) |

### Creating a Session

```bash
curl -X POST https://api.llmhive.ai/api/v1/collaborate \
  -H 'Content-Type: application/json' \
  -H 'X-User-ID: alice' \
  -d '{
    "title": "Team Brainstorm",
    "description": "Discussing Q1 planning",
    "is_public": true,
    "max_participants": 5
  }'
```

Response:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "invite_token": "abc123...",
  "invite_url": "https://api.llmhive.ai/collaborate/join?token=abc123...",
  "title": "Team Brainstorm",
  "created_at": "2025-12-28T12:00:00Z"
}
```

### Joining a Session

```bash
curl -X POST https://api.llmhive.ai/api/v1/collaborate/join \
  -H 'Content-Type: application/json' \
  -H 'X-User-ID: bob' \
  -d '{
    "invite_token": "abc123...",
    "display_name": "Bob"
  }'
```

### Sending Messages

```bash
curl -X POST https://api.llmhive.ai/api/v1/collaborate/{session_id}/messages \
  -H 'Content-Type: application/json' \
  -H 'X-User-ID: alice' \
  -d '{
    "content": "Hello everyone!",
    "message_type": "user"
  }'
```

### Real-Time Updates

```javascript
const sessionId = 'session-id-here';
const es = new EventSource(`/api/v1/collaborate/${sessionId}/stream`);

es.onmessage = (e) => {
    const event = JSON.parse(e.data);
    
    switch (event.type) {
        case 'new_message':
            console.log('New message:', event.message);
            break;
        case 'participant_joined':
            console.log('User joined:', event.user_id);
            break;
        case 'participant_left':
            console.log('User left:', event.user_id);
            break;
        case 'session_deleted':
            console.log('Session was deleted');
            es.close();
            break;
    }
};
```

### Access Levels

| Level | Permissions |
|-------|-------------|
| owner | Create session, delete session, full access |
| editor | Send messages, view history |
| viewer | View history only |

### Storage

**Development (In-Memory)**:
- Uses `InMemorySessionStore` when no database is configured
- All data is lost on restart

**Production (Database)**:
- SQLAlchemy models in `llmhive/src/llmhive/app/models/collaboration.py`
- Tables: `collaborative_sessions`, `session_messages`, `session_participants`

---

## Security Considerations

### Authentication

Currently, user identity is extracted from the `X-User-ID` header. In production, integrate with your authentication system:

```python
# In collaborate.py, modify get_user_id_from_request()
def get_user_id_from_request(request: Request) -> str:
    # Integrate with your auth system
    user = get_authenticated_user(request)
    return user.id
```

### Invite Token Security

- Tokens are generated using `secrets.token_urlsafe(24)` (cryptographically secure)
- Tokens are 32+ characters long
- Consider adding token expiration for time-limited invites

### Rate Limiting

Consider adding rate limiting to prevent abuse:
- SSE connections per user
- Messages per minute per session
- Session creation per user per day

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLMHIVE_DEV_MODE` | false | Enable verbose dev mode globally |
| `DATABASE_URL` | - | PostgreSQL connection string for persistent storage |

### Customization

**Keepalive Interval**: Change the keepalive ping frequency in `sse_events.py`:

```python
# In event_stream_generator()
event = await asyncio.wait_for(queue.get(), timeout=15.0)  # Adjust timeout
```

**Message History Limit**: Adjust in `collaborate.py`:

```python
# In get_messages()
return messages[offset:offset + limit]  # Default limit: 100
```

---

## Testing

### SSE Events Tests

```bash
pytest llmhive/tests/test_sse_events.py -v
```

### Collaboration Tests

```bash
pytest llmhive/tests/test_collaboration.py -v
```

### Manual Testing

1. Start the server: `uvicorn llmhive.app.main:app --reload`
2. Open SSE test: `curl -N http://localhost:8000/api/v1/events/orchestration/test-session`
3. Emit test event: `curl http://localhost:8000/api/v1/events/orchestration/test-session/test`

---

## Future Enhancements

- [ ] WebSocket upgrade for bidirectional communication (when infrastructure supports)
- [ ] Typing indicators in collaborative sessions
- [ ] File/image sharing in sessions
- [ ] Session archival and export
- [ ] Presence indicators (online/offline status)
- [ ] Token expiration for invites
- [ ] Integration with OpenTelemetry for SSE metrics

