"""Collaboration API Router for LLMHive.

This module provides REST and SSE endpoints for multi-user collaborative sessions.

**Endpoints:**

POST /api/v1/collaborate - Create a new collaborative session
POST /api/v1/collaborate/join - Join an existing session via invite token
GET  /api/v1/collaborate/{session_id} - Get session info
GET  /api/v1/collaborate/{session_id}/history - Get message history
GET  /api/v1/collaborate/{session_id}/participants - Get participant list
POST /api/v1/collaborate/{session_id}/messages - Send a message
GET  /api/v1/collaborate/{session_id}/stream - SSE stream for real-time updates
DELETE /api/v1/collaborate/{session_id} - Delete/archive a session

**Real-Time Updates:**

Uses Server-Sent Events (SSE) for real-time message broadcasting to all
connected participants. Each participant opens an SSE connection and receives:
- New messages from other participants
- Participant join/leave events
- Typing indicators (future)

**Storage:**

When a database is available, sessions and messages are persisted to PostgreSQL.
Without a database, falls back to in-memory storage (for development only).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status, Depends
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaborate", tags=["collaboration"])


# ==============================================================================
# In-Memory Storage (Fallback when DB unavailable)
# ==============================================================================

class InMemorySessionStore:
    """In-memory storage for collaborative sessions.
    
    This is a fallback for development/testing when no database is configured.
    In production, use the database-backed SessionManager instead.
    """
    _instance: Optional['InMemorySessionStore'] = None
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._messages: Dict[str, List[Dict[str, Any]]] = {}
        self._participants: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._sse_subscribers: Dict[str, Dict[str, asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
    
    @classmethod
    def get_instance(cls) -> 'InMemorySessionStore':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def create_session(
        self,
        session_id: str,
        owner_user_id: str,
        invite_token: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False,
        max_participants: int = 10,
    ) -> Dict[str, Any]:
        """Create a new collaborative session."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            session = {
                "session_id": session_id,
                "owner_user_id": owner_user_id,
                "invite_token": invite_token,
                "title": title,
                "description": description,
                "is_public": is_public,
                "max_participants": max_participants,
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "last_activity_at": now,
            }
            self._sessions[session_id] = session
            self._messages[session_id] = []
            self._participants[session_id] = {
                owner_user_id: {
                    "user_id": owner_user_id,
                    "display_name": None,
                    "access_level": "owner",
                    "is_active": True,
                    "joined_at": now,
                    "last_seen_at": now,
                }
            }
            self._sse_subscribers[session_id] = {}
            return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    async def get_session_by_token(self, invite_token: str) -> Optional[Dict[str, Any]]:
        """Get session by invite token."""
        for session in self._sessions.values():
            if session.get("invite_token") == invite_token:
                return session
        return None
    
    async def add_participant(
        self,
        session_id: str,
        user_id: str,
        display_name: Optional[str] = None,
        access_level: str = "viewer",
    ) -> bool:
        """Add a participant to a session."""
        async with self._lock:
            if session_id not in self._participants:
                return False
            
            session = self._sessions.get(session_id)
            if session and len(self._participants[session_id]) >= session.get("max_participants", 10):
                return False
            
            now = datetime.now(timezone.utc).isoformat()
            self._participants[session_id][user_id] = {
                "user_id": user_id,
                "display_name": display_name,
                "access_level": access_level,
                "is_active": True,
                "joined_at": now,
                "last_seen_at": now,
            }
            return True
    
    async def get_participants(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all participants in a session."""
        return list(self._participants.get(session_id, {}).values())
    
    async def add_message(
        self,
        session_id: str,
        content: str,
        sender_user_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        message_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a message to a session."""
        async with self._lock:
            if session_id not in self._messages:
                self._messages[session_id] = []
            
            messages = self._messages[session_id]
            sequence = len(messages) + 1
            now = datetime.now(timezone.utc).isoformat()
            
            message = {
                "id": sequence,
                "session_id": session_id,
                "message_type": message_type,
                "content": content,
                "sender_user_id": sender_user_id,
                "sender_name": sender_name,
                "sequence_number": sequence,
                "created_at": now,
                "metadata": metadata,
            }
            messages.append(message)
            
            # Update session activity
            if session_id in self._sessions:
                self._sessions[session_id]["last_activity_at"] = now
                self._sessions[session_id]["updated_at"] = now
            
            return message
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages from a session."""
        messages = self._messages.get(session_id, [])
        return messages[offset:offset + limit]
    
    async def get_message_count(self, session_id: str) -> int:
        """Get total message count in a session."""
        return len(self._messages.get(session_id, []))
    
    async def subscribe_sse(self, session_id: str) -> tuple[str, asyncio.Queue]:
        """Subscribe to SSE events for a session."""
        import uuid
        client_id = str(uuid.uuid4())[:8]
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        async with self._lock:
            if session_id not in self._sse_subscribers:
                self._sse_subscribers[session_id] = {}
            self._sse_subscribers[session_id][client_id] = queue
        
        return client_id, queue
    
    async def unsubscribe_sse(self, session_id: str, client_id: str) -> None:
        """Unsubscribe from SSE events."""
        async with self._lock:
            if session_id in self._sse_subscribers:
                self._sse_subscribers[session_id].pop(client_id, None)
    
    async def broadcast_sse(self, session_id: str, event: Dict[str, Any]) -> int:
        """Broadcast an event to all SSE subscribers."""
        count = 0
        subscribers = self._sse_subscribers.get(session_id, {})
        for queue in list(subscribers.values()):
            try:
                queue.put_nowait(event)
                count += 1
            except asyncio.QueueFull:
                pass
        return count
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["status"] = "deleted"
                return True
            return False


def get_session_store() -> InMemorySessionStore:
    """Get the session store instance."""
    return InMemorySessionStore.get_instance()


# ==============================================================================
# Helper Functions
# ==============================================================================

def generate_session_id() -> str:
    """Generate a unique session ID."""
    import uuid
    return str(uuid.uuid4())


def generate_invite_token() -> str:
    """Generate a secure invite token."""
    import secrets
    return secrets.token_urlsafe(24)


def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request (placeholder for auth integration)."""
    # Check headers for user ID
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return user_id
    
    # Check state for authenticated user
    if hasattr(request, "state") and hasattr(request.state, "user_id"):
        return request.state.user_id
    
    # Fallback: generate anonymous ID
    import uuid
    return f"anon-{str(uuid.uuid4())[:8]}"


# ==============================================================================
# Request/Response Models (using Pydantic)
# ==============================================================================

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    is_public: bool = False
    max_participants: int = Field(10, ge=2, le=100)


class CreateSessionResponse(BaseModel):
    session_id: str
    invite_token: str
    invite_url: str
    title: Optional[str]
    created_at: str


class JoinSessionRequest(BaseModel):
    invite_token: str = Field(..., min_length=8)
    display_name: Optional[str] = Field(None, max_length=100)


class JoinSessionResponse(BaseModel):
    session_id: str
    title: Optional[str]
    access_level: str
    participant_count: int
    message_count: int


class SessionInfoResponse(BaseModel):
    session_id: str
    title: Optional[str]
    description: Optional[str]
    status: str
    owner_user_id: str
    is_public: bool
    participant_count: int
    message_count: int
    created_at: str
    last_activity_at: str


class MessageSchema(BaseModel):
    id: int
    message_type: str
    content: str
    sender_user_id: Optional[str]
    sender_name: Optional[str]
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field("user")
    metadata: Optional[Dict[str, Any]] = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageSchema]
    total_messages: int
    has_more: bool


class ParticipantInfo(BaseModel):
    user_id: str
    display_name: Optional[str]
    access_level: str
    is_active: bool
    joined_at: str


class ParticipantsResponse(BaseModel):
    session_id: str
    participants: List[ParticipantInfo]
    total: int


# ==============================================================================
# API Endpoints
# ==============================================================================

@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: Request,
    body: CreateSessionRequest,
) -> CreateSessionResponse:
    """
    Create a new collaborative session.
    
    Returns a session ID and invite token that can be shared with others.
    The creator automatically becomes the session owner with full control.
    """
    store = get_session_store()
    user_id = get_user_id_from_request(request)
    
    session_id = generate_session_id()
    invite_token = generate_invite_token()
    
    session = await store.create_session(
        session_id=session_id,
        owner_user_id=user_id,
        invite_token=invite_token,
        title=body.title,
        description=body.description,
        is_public=body.is_public,
        max_participants=body.max_participants,
    )
    
    # Build invite URL
    base_url = str(request.base_url).rstrip("/")
    invite_url = f"{base_url}/collaborate/join?token={invite_token}"
    
    logger.info(f"Created collaborative session {session_id} by user {user_id}")
    
    return CreateSessionResponse(
        session_id=session_id,
        invite_token=invite_token,
        invite_url=invite_url,
        title=body.title,
        created_at=session["created_at"],
    )


@router.post("/join", response_model=JoinSessionResponse)
async def join_session(
    request: Request,
    body: JoinSessionRequest,
) -> JoinSessionResponse:
    """
    Join an existing collaborative session using an invite token.
    
    The invite token can be obtained from the invite URL shared by the session owner.
    """
    store = get_session_store()
    user_id = get_user_id_from_request(request)
    
    # Find session by invite token
    session = await store.get_session_by_token(body.invite_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite token",
        )
    
    if session["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This session is no longer active",
        )
    
    session_id = session["session_id"]
    
    # Add participant
    success = await store.add_participant(
        session_id=session_id,
        user_id=user_id,
        display_name=body.display_name,
        access_level="editor" if session["is_public"] else "viewer",
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session is full or you cannot join",
        )
    
    participants = await store.get_participants(session_id)
    message_count = await store.get_message_count(session_id)
    
    # Broadcast join event
    await store.broadcast_sse(session_id, {
        "type": "participant_joined",
        "user_id": user_id,
        "display_name": body.display_name,
        "participant_count": len(participants),
    })
    
    logger.info(f"User {user_id} joined session {session_id}")
    
    return JoinSessionResponse(
        session_id=session_id,
        title=session.get("title"),
        access_level="editor" if session["is_public"] else "viewer",
        participant_count=len(participants),
        message_count=message_count,
    )


@router.get("/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(
    request: Request,
    session_id: str,
) -> SessionInfoResponse:
    """Get information about a collaborative session."""
    store = get_session_store()
    
    session = await store.get_session(session_id)
    if not session or session["status"] == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    participants = await store.get_participants(session_id)
    message_count = await store.get_message_count(session_id)
    
    return SessionInfoResponse(
        session_id=session_id,
        title=session.get("title"),
        description=session.get("description"),
        status=session["status"],
        owner_user_id=session["owner_user_id"],
        is_public=session.get("is_public", False),
        participant_count=len(participants),
        message_count=message_count,
        created_at=session["created_at"],
        last_activity_at=session.get("last_activity_at", session["created_at"]),
    )


@router.get("/{session_id}/history", response_model=HistoryResponse)
async def get_session_history(
    request: Request,
    session_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HistoryResponse:
    """Get message history from a collaborative session."""
    store = get_session_store()
    
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    messages = await store.get_messages(session_id, limit=limit, offset=offset)
    total = await store.get_message_count(session_id)
    
    message_schemas = [
        MessageSchema(
            id=m["id"],
            message_type=m["message_type"],
            content=m["content"],
            sender_user_id=m.get("sender_user_id"),
            sender_name=m.get("sender_name"),
            created_at=m["created_at"],
            metadata=m.get("metadata"),
        )
        for m in messages
    ]
    
    return HistoryResponse(
        session_id=session_id,
        messages=message_schemas,
        total_messages=total,
        has_more=offset + limit < total,
    )


@router.get("/{session_id}/participants", response_model=ParticipantsResponse)
async def get_session_participants(
    request: Request,
    session_id: str,
) -> ParticipantsResponse:
    """Get list of participants in a collaborative session."""
    store = get_session_store()
    
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    participants = await store.get_participants(session_id)
    
    participant_infos = [
        ParticipantInfo(
            user_id=p["user_id"],
            display_name=p.get("display_name"),
            access_level=p["access_level"],
            is_active=p.get("is_active", True),
            joined_at=p["joined_at"],
        )
        for p in participants
    ]
    
    return ParticipantsResponse(
        session_id=session_id,
        participants=participant_infos,
        total=len(participants),
    )


@router.post("/{session_id}/messages", response_model=MessageSchema)
async def send_message(
    request: Request,
    session_id: str,
    body: SendMessageRequest,
) -> MessageSchema:
    """
    Send a message to a collaborative session.
    
    The message is stored and broadcast to all connected participants via SSE.
    """
    store = get_session_store()
    user_id = get_user_id_from_request(request)
    
    session = await store.get_session(session_id)
    if not session or session["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )
    
    # Get sender display name
    participants = await store.get_participants(session_id)
    sender_info = next(
        (p for p in participants if p["user_id"] == user_id),
        None
    )
    sender_name = sender_info.get("display_name") if sender_info else None
    
    # Add message
    message = await store.add_message(
        session_id=session_id,
        content=body.content,
        sender_user_id=user_id,
        sender_name=sender_name,
        message_type=body.message_type,
        metadata=body.metadata,
    )
    
    # Broadcast to SSE subscribers
    await store.broadcast_sse(session_id, {
        "type": "new_message",
        "message": {
            "id": message["id"],
            "message_type": message["message_type"],
            "content": message["content"],
            "sender_user_id": message["sender_user_id"],
            "sender_name": message["sender_name"],
            "created_at": message["created_at"],
            "metadata": message.get("metadata"),
        },
    })
    
    logger.debug(f"Message sent in session {session_id} by {user_id}")
    
    return MessageSchema(
        id=message["id"],
        message_type=message["message_type"],
        content=message["content"],
        sender_user_id=message.get("sender_user_id"),
        sender_name=message.get("sender_name"),
        created_at=message["created_at"],
        metadata=message.get("metadata"),
    )


@router.get("/{session_id}/stream")
async def stream_session_events(
    request: Request,
    session_id: str,
) -> StreamingResponse:
    """
    Stream real-time events from a collaborative session via SSE.
    
    Events include:
    - new_message: A new message was sent
    - participant_joined: A participant joined the session
    - participant_left: A participant left the session
    - typing: A participant is typing (future)
    
    **Usage (JavaScript):**
    ```javascript
    const es = new EventSource('/api/v1/collaborate/session-id/stream');
    es.addEventListener('message', (e) => {
        const event = JSON.parse(e.data);
        if (event.type === 'new_message') {
            console.log('New message:', event.message);
        }
    });
    ```
    """
    store = get_session_store()
    
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    client_id, queue = await store.subscribe_sse(session_id)
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send connection event
            yield f"event: connected\ndata: {json.dumps({'session_id': session_id, 'client_id': client_id})}\n\n"
            
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"event: keepalive\ndata: {json.dumps({'ping': True})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await store.unsubscribe_sse(session_id, client_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{session_id}")
async def delete_session(
    request: Request,
    session_id: str,
) -> Dict[str, Any]:
    """
    Delete (archive) a collaborative session.
    
    Only the session owner can delete a session.
    """
    store = get_session_store()
    user_id = get_user_id_from_request(request)
    
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    if session["owner_user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the session owner can delete the session",
        )
    
    success = await store.delete_session(session_id)
    
    if success:
        # Notify subscribers
        await store.broadcast_sse(session_id, {
            "type": "session_deleted",
            "session_id": session_id,
        })
    
    return {"success": success, "session_id": session_id}

