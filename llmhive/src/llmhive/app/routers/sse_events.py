"""Server-Sent Events (SSE) Router for Real-Time Orchestration Events.

This module provides SSE-based streaming of orchestration events to clients,
enabling real-time developer tracing and debugging without WebSocket connections.

**Why SSE over WebSocket:**
- SSE works over standard HTTP, making it compatible with serverless platforms
  like Vercel where persistent WebSockets are not fully supported
- SSE is simpler for one-way server-to-client streaming (which is our use case)
- SSE automatically handles reconnection on the client side (via EventSource API)
- SSE is sufficient for orchestration tracing where clients only receive events

**Endpoint:**
    GET /api/v1/events/orchestration/{session_id}
    
    Headers:
        Accept: text/event-stream
        Authorization: Bearer <token> (optional, for auth)
    
    Query Params:
        ?dev_mode=true - Enable verbose dev mode events
        ?filter=model_call,tool_invoked - Comma-separated event type filter

**Event Format (SSE):**
    event: orchestration_event
    data: {"type": "model_call", "timestamp": "...", "message": "...", "details": {...}}
    
    event: keepalive
    data: {"ping": true}

**Integration:**
    The orchestrator emits events via the EventBroadcaster class, which
    pushes them to all connected SSE clients for the given session.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from fastapi import APIRouter, Request, Query, HTTPException, status
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])


# ==============================================================================
# Event Types and Models
# ==============================================================================

@dataclass
class OrchestrationEvent:
    """A single orchestration event for SSE streaming."""
    event_type: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_sse(self) -> str:
        """Format as SSE message."""
        data = {
            "type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp,
        }
        if self.details:
            data["details"] = self.details
        if self.session_id:
            data["session_id"] = self.session_id
        
        return f"event: orchestration_event\ndata: {json.dumps(data)}\n\n"


# ==============================================================================
# Event Broadcaster (Session-Scoped Event Queues)
# ==============================================================================

class EventBroadcaster:
    """
    Manages event queues for SSE clients subscribed to orchestration events.
    
    Each session can have multiple SSE clients connected. When an event is
    emitted for a session, it's pushed to all connected clients' queues.
    
    Thread-safe using asyncio primitives.
    """
    _instance: Optional['EventBroadcaster'] = None
    
    def __init__(self):
        # session_id -> list of (client_id, asyncio.Queue)
        self._subscribers: Dict[str, Dict[str, asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
    
    @classmethod
    def get_instance(cls) -> 'EventBroadcaster':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def subscribe(self, session_id: str) -> tuple[str, asyncio.Queue]:
        """
        Subscribe to events for a session.
        
        Returns:
            Tuple of (client_id, event_queue)
        """
        client_id = str(uuid.uuid4())[:8]
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        async with self._lock:
            if session_id not in self._subscribers:
                self._subscribers[session_id] = {}
            self._subscribers[session_id][client_id] = queue
            logger.info(f"SSE client {client_id} subscribed to session {session_id}")
        
        return client_id, queue
    
    async def unsubscribe(self, session_id: str, client_id: str) -> None:
        """Unsubscribe a client from a session."""
        async with self._lock:
            if session_id in self._subscribers:
                if client_id in self._subscribers[session_id]:
                    del self._subscribers[session_id][client_id]
                    logger.info(f"SSE client {client_id} unsubscribed from session {session_id}")
                # Clean up empty session
                if not self._subscribers[session_id]:
                    del self._subscribers[session_id]
    
    async def emit(self, session_id: str, event: OrchestrationEvent) -> int:
        """
        Emit an event to all subscribers of a session.
        
        Returns:
            Number of clients that received the event
        """
        async with self._lock:
            subscribers = self._subscribers.get(session_id, {})
            count = 0
            for client_id, queue in list(subscribers.items()):
                try:
                    # Non-blocking put, drop if queue is full
                    queue.put_nowait(event)
                    count += 1
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for client {client_id}, dropping event")
            return count
    
    async def emit_to_all(self, event: OrchestrationEvent) -> int:
        """Emit an event to all subscribers across all sessions."""
        async with self._lock:
            count = 0
            for session_id, subscribers in self._subscribers.items():
                event.session_id = session_id
                for client_id, queue in subscribers.items():
                    try:
                        queue.put_nowait(event)
                        count += 1
                    except asyncio.QueueFull:
                        pass
            return count
    
    def get_subscriber_count(self, session_id: Optional[str] = None) -> int:
        """Get count of subscribers for a session or all sessions."""
        if session_id:
            return len(self._subscribers.get(session_id, {}))
        return sum(len(subs) for subs in self._subscribers.values())


def get_broadcaster() -> EventBroadcaster:
    """Get the global event broadcaster instance."""
    return EventBroadcaster.get_instance()


# ==============================================================================
# Event Emission Helpers (Called from Orchestrator)
# ==============================================================================

def emit_orchestration_event(
    session_id: str,
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit an orchestration event to connected SSE clients.
    
    This is the main function called from orchestrator code to broadcast events.
    It's designed to be non-blocking and fire-and-forget.
    
    Args:
        session_id: The session/chat ID to broadcast to
        event_type: Type of event (e.g., "model_call", "tool_invoked", "strategy_selected")
        message: Human-readable event description
        details: Optional structured details
    """
    if not session_id:
        return
    
    event = OrchestrationEvent(
        event_type=event_type,
        message=message,
        details=details,
        session_id=session_id,
    )
    
    # Schedule broadcast asynchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_async(session_id, event))
        else:
            # Fallback: synchronous logging only
            logger.debug(f"[SSE] {event_type}: {message}")
    except RuntimeError:
        # No event loop available
        logger.debug(f"[SSE] {event_type}: {message}")


async def _emit_async(session_id: str, event: OrchestrationEvent) -> None:
    """Async helper to emit event."""
    broadcaster = get_broadcaster()
    await broadcaster.emit(session_id, event)


# Convenience functions for common event types
def emit_strategy_selected(session_id: str, strategy: str, reason: str = "") -> None:
    """Emit when a strategy is selected."""
    emit_orchestration_event(
        session_id, "strategy_selected",
        f"Strategy chosen: {strategy}",
        {"strategy": strategy, "reason": reason}
    )


def emit_model_call(session_id: str, model: str, prompt_preview: str = "") -> None:
    """Emit when a model is being called."""
    preview = prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview
    emit_orchestration_event(
        session_id, "model_call",
        f"Calling model: {model}",
        {"model": model, "prompt_preview": preview}
    )


def emit_model_response(session_id: str, model: str, tokens: int = 0, latency_ms: float = 0) -> None:
    """Emit when a model responds."""
    emit_orchestration_event(
        session_id, "model_response",
        f"Model {model} responded ({tokens} tokens, {latency_ms:.0f}ms)",
        {"model": model, "tokens": tokens, "latency_ms": round(latency_ms, 2)}
    )


def emit_tool_invoked(session_id: str, tool_type: str, query: str = "") -> None:
    """Emit when a tool is invoked."""
    preview = query[:100] + "..." if len(query) > 100 else query
    emit_orchestration_event(
        session_id, "tool_invoked",
        f"Tool invoked: {tool_type}",
        {"tool_type": tool_type, "query": preview}
    )


def emit_tool_result(session_id: str, tool_type: str, success: bool, latency_ms: float = 0) -> None:
    """Emit when a tool returns a result."""
    status_str = "succeeded" if success else "failed"
    emit_orchestration_event(
        session_id, "tool_result",
        f"Tool {tool_type} {status_str}",
        {"tool_type": tool_type, "success": success, "latency_ms": round(latency_ms, 2)}
    )


def emit_verification_result(session_id: str, passed: bool, verdict: str = "") -> None:
    """Emit verification result."""
    status_str = "passed" if passed else "failed"
    emit_orchestration_event(
        session_id, "verification",
        f"Verification {status_str}",
        {"passed": passed, "verdict": verdict}
    )


def emit_step(session_id: str, step_name: str, description: str = "") -> None:
    """Emit a generic orchestration step."""
    emit_orchestration_event(
        session_id, "step",
        f"Step: {step_name}",
        {"step": step_name, "description": description}
    )


def emit_error(session_id: str, error_type: str, message: str) -> None:
    """Emit an error event."""
    emit_orchestration_event(
        session_id, "error",
        f"Error: {message}",
        {"error_type": error_type, "message": message}
    )


def emit_complete(session_id: str, success: bool, summary: str = "") -> None:
    """Emit orchestration completion event."""
    status_str = "completed successfully" if success else "completed with errors"
    emit_orchestration_event(
        session_id, "complete",
        f"Orchestration {status_str}",
        {"success": success, "summary": summary}
    )


# ==============================================================================
# SSE Streaming Endpoint
# ==============================================================================

async def event_stream_generator(
    session_id: str,
    client_id: str,
    queue: asyncio.Queue,
    event_filter: Optional[Set[str]] = None,
    dev_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted events from the queue.
    
    Args:
        session_id: Session being monitored
        client_id: Unique client identifier
        queue: Event queue for this client
        event_filter: Optional set of event types to include (None = all)
        dev_mode: If True, include verbose debug events
    """
    broadcaster = get_broadcaster()
    
    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'session_id': session_id, 'client_id': client_id})}\n\n"
        
        # Keepalive counter
        last_event_time = time.time()
        
        while True:
            try:
                # Wait for event with timeout (for keepalive)
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                
                # Apply filter
                if event_filter and event.event_type not in event_filter:
                    continue
                
                # Skip debug events in non-dev mode
                if not dev_mode and event.event_type.startswith("debug_"):
                    continue
                
                yield event.to_sse()
                last_event_time = time.time()
                
            except asyncio.TimeoutError:
                # Send keepalive if no events for 15 seconds
                yield f"event: keepalive\ndata: {json.dumps({'ping': True, 'time': time.time()})}\n\n"
                
    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for client {client_id}")
    except Exception as e:
        logger.error(f"SSE stream error for client {client_id}: {e}")
    finally:
        # Cleanup subscription
        await broadcaster.unsubscribe(session_id, client_id)


@router.get("/orchestration/{session_id}")
async def stream_orchestration_events(
    request: Request,
    session_id: str,
    dev_mode: bool = Query(default=False, description="Enable verbose dev mode events"),
    filter: Optional[str] = Query(default=None, description="Comma-separated event types to filter"),
) -> StreamingResponse:
    """
    Stream orchestration events for a session via Server-Sent Events (SSE).
    
    This endpoint provides real-time visibility into the orchestration process,
    allowing developers to trace model calls, tool invocations, and other events
    as they happen.
    
    **Connection:**
    - Keep-alive pings are sent every 15 seconds
    - Clients should use EventSource API for automatic reconnection
    
    **Example (JavaScript):**
    ```javascript
    const es = new EventSource('/api/v1/events/orchestration/my-session?dev_mode=true');
    es.addEventListener('orchestration_event', (e) => {
        console.log(JSON.parse(e.data));
    });
    es.addEventListener('keepalive', (e) => {
        console.log('Connection alive');
    });
    ```
    
    **Event Types:**
    - strategy_selected: Orchestration strategy chosen
    - model_call: Model inference started
    - model_response: Model inference completed
    - tool_invoked: External tool called
    - tool_result: Tool returned result
    - verification: Answer verification result
    - step: Generic orchestration step
    - error: Error occurred
    - complete: Orchestration finished
    
    Args:
        session_id: The session/chat ID to monitor
        dev_mode: Include verbose debug events
        filter: Comma-separated list of event types to include
    
    Returns:
        SSE stream of orchestration events
    """
    broadcaster = get_broadcaster()
    
    # Parse filter
    event_filter: Optional[Set[str]] = None
    if filter:
        event_filter = set(f.strip() for f in filter.split(","))
    
    # Subscribe to events
    client_id, queue = await broadcaster.subscribe(session_id)
    
    # Create generator
    generator = event_stream_generator(
        session_id=session_id,
        client_id=client_id,
        queue=queue,
        event_filter=event_filter,
        dev_mode=dev_mode,
    )
    
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/orchestration/{session_id}/test")
async def test_emit_event(
    session_id: str,
    event_type: str = Query(default="test", description="Event type to emit"),
    message: str = Query(default="Test event", description="Event message"),
) -> Dict[str, Any]:
    """
    Test endpoint to emit a sample event to a session.
    
    Useful for testing SSE connectivity without running a full orchestration.
    """
    event = OrchestrationEvent(
        event_type=event_type,
        message=message,
        session_id=session_id,
        details={"test": True, "timestamp": time.time()},
    )
    
    broadcaster = get_broadcaster()
    count = await broadcaster.emit(session_id, event)
    
    return {
        "success": True,
        "event_type": event_type,
        "message": message,
        "session_id": session_id,
        "clients_reached": count,
    }


@router.get("/stats")
async def get_sse_stats() -> Dict[str, Any]:
    """Get SSE connection statistics."""
    broadcaster = get_broadcaster()
    return {
        "total_subscribers": broadcaster.get_subscriber_count(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

