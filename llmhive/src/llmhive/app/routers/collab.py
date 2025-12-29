"""Real-Time Collaboration Router for LLMHive.

Enhancement-4: WebSocket-based collaboration scaffold.

This module provides:
- WebSocket endpoint for real-time session updates
- Session management for multiple participants
- Broadcast mechanism for trace events and messages
- Token-based authentication for session access

Usage:
    Connect to: ws://<server>/ws/session/{session_id}?token=<auth_token>
    
    Receive JSON messages with:
    - {"message": "..."} - Chat messages from other participants
    - {"trace_event": {...}} - Dev mode trace events
    - {"participant_joined": "..."} - Participant notifications
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["collaboration"])


# ==============================================================================
# Session Management
# ==============================================================================

@dataclass
class CollabSession:
    """Tracks active participants and messages for a collaboration session.
    
    Enhancement-4: Thread-safe session with broadcast capabilities.
    """
    id: str
    created_at: float = field(default_factory=time.time)
    participants: List[WebSocket] = field(default_factory=list)
    message_history: List[Dict] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)
    
    def add_participant(self, ws: WebSocket) -> None:
        """Add a participant to the session (thread-safe)."""
        with self._lock:
            if ws not in self.participants:
                self.participants.append(ws)
    
    def remove_participant(self, ws: WebSocket) -> None:
        """Remove a participant from the session (thread-safe)."""
        with self._lock:
            if ws in self.participants:
                self.participants.remove(ws)
    
    @property
    def participant_count(self) -> int:
        """Get current participant count."""
        with self._lock:
            return len(self.participants)
    
    async def broadcast(self, message: dict) -> None:
        """Send a message to all participants in the session.
        
        Failed sends result in participant removal.
        """
        with self._lock:
            participants_copy = list(self.participants)
        
        failed = []
        for ws in participants_copy:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"WebSocket send failed, removing participant: {e}")
                failed.append(ws)
        
        # Remove failed connections
        for ws in failed:
            self.remove_participant(ws)
        
        # Store in message history (limit to last 100)
        with self._lock:
            self.message_history.append(message)
            if len(self.message_history) > 100:
                self.message_history = self.message_history[-100:]


class CollabSessionManager:
    """Manages collaborative sessions.
    
    Enhancement-4: Thread-safe session manager with broadcast support.
    """
    _sessions: Dict[str, CollabSession] = {}
    _lock = Lock()
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[CollabSession]:
        """Get an existing session by ID."""
        with cls._lock:
            return cls._sessions.get(session_id)
    
    @classmethod
    def get_or_create_session(cls, session_id: str) -> CollabSession:
        """Get or create a session by ID."""
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session is None:
                session = CollabSession(id=session_id)
                cls._sessions[session_id] = session
                logger.info(f"Created new collaboration session: {session_id}")
            return session
    
    @classmethod
    def remove_session(cls, session_id: str) -> None:
        """Remove a session by ID."""
        with cls._lock:
            if session_id in cls._sessions:
                del cls._sessions[session_id]
                logger.info(f"Removed collaboration session: {session_id}")
    
    @classmethod
    def get_session_count(cls) -> int:
        """Get total number of active sessions."""
        with cls._lock:
            return len(cls._sessions)
    
    @classmethod
    def broadcast(cls, session_id: str, message: dict) -> None:
        """Convenience method to broadcast via session manager (fire-and-forget).
        
        Schedules broadcasts asynchronously to not block caller.
        """
        session = cls.get_session(session_id)
        if not session:
            return
        
        # Schedule broadcast asynchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(session.broadcast(message))
            else:
                # Fallback: run synchronously (should not happen in normal operation)
                loop.run_until_complete(session.broadcast(message))
        except RuntimeError:
            # No event loop available, skip broadcast
            logger.debug(f"No event loop for broadcast to session {session_id}")
    
    @classmethod
    def get_all_sessions_info(cls) -> List[Dict]:
        """Get info about all active sessions."""
        with cls._lock:
            return [
                {
                    "session_id": session.id,
                    "participant_count": session.participant_count,
                    "created_at": session.created_at,
                    "message_count": len(session.message_history),
                }
                for session in cls._sessions.values()
            ]


# ==============================================================================
# Token Verification (Placeholder)
# ==============================================================================

def verify_session_token(token: str, session_id: str) -> bool:
    """Verify that a token grants access to a session.
    
    Enhancement-4: Placeholder for integration with auth system.
    In production, this should validate against your auth service.
    
    Args:
        token: The authentication token
        session_id: The session to access
        
    Returns:
        True if access is granted, False otherwise
    """
    # For development: accept any non-empty token
    # In production: integrate with your auth system
    if not token:
        return False
    
    # Development mode: accept "dev" token for any session
    if token == "dev":
        return True
    
    # Accept tokens that match session_id (simple validation)
    if token == session_id:
        return True
    
    # Add real token validation here
    # Example: validate JWT, check session permissions, etc.
    
    return len(token) >= 8  # Accept any token with 8+ chars for now


# ==============================================================================
# WebSocket Endpoint
# ==============================================================================

@router.websocket("/session/{session_id}")
async def session_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(default=""),
) -> None:
    """
    WebSocket endpoint for real-time collaboration on a session.
    
    Enhancement-4: Enables multi-user collaboration and live trace updates.
    
    Args:
        websocket: The WebSocket connection
        session_id: Identifier for the collaboration session (e.g., chat_id)
        token: Authorization token for joining the session
        
    Messages sent TO clients:
        - {"message": "..."} - Chat messages from other participants
        - {"trace_event": {...}} - Dev mode trace events
        - {"participant_joined": "user_id"} - New participant notification
        - {"participant_left": "user_id"} - Participant left notification
        - {"history": [...]} - Message history on join
        
    Messages received FROM clients:
        - {"message": "..."} - Broadcast to all participants
        - {"ping": true} - Keep-alive ping (responds with {"pong": true})
    """
    # Token verification
    if not verify_session_token(token, session_id):
        await websocket.close(code=1008)  # Policy Violation: invalid token
        logger.warning(f"WebSocket connection rejected for session {session_id}: invalid token")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Get or create session
    session = CollabSessionManager.get_or_create_session(session_id)
    session.add_participant(websocket)
    
    # Update metrics
    try:
        from ..api.orchestrator_metrics import update_active_sessions
        update_active_sessions(CollabSessionManager.get_session_count())
    except Exception:
        pass
    
    logger.info(
        f"WebSocket client joined session {session_id} "
        f"(participants={session.participant_count})"
    )
    
    # Send connection acknowledgment and history
    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "participant_count": session.participant_count,
        })
        
        # Send recent message history
        if session.message_history:
            await websocket.send_json({
                "type": "history",
                "messages": session.message_history[-20:],  # Last 20 messages
            })
        
        # Notify other participants
        await session.broadcast({
            "type": "participant_joined",
            "participant_count": session.participant_count,
        })
    except Exception as e:
        logger.warning(f"Failed to send initial messages: {e}")
    
    try:
        # Main message loop
        while True:
            data = await websocket.receive_text()
            
            try:
                import json
                message = json.loads(data)
                
                # Handle ping/pong for keep-alive
                if message.get("ping"):
                    await websocket.send_json({"pong": True})
                    continue
                
                # Broadcast message to all participants
                if "message" in message:
                    broadcast_msg = {
                        "type": "message",
                        "message": message["message"],
                        "timestamp": time.time(),
                    }
                    await session.broadcast(broadcast_msg)
                    logger.debug(f"Broadcast message on session {session_id}")
                
            except json.JSONDecodeError:
                # Plain text message - broadcast as-is
                await session.broadcast({
                    "type": "message",
                    "message": data,
                    "timestamp": time.time(),
                })
            
    except WebSocketDisconnect:
        # Clean disconnect
        session.remove_participant(websocket)
        logger.info(
            f"Client disconnected from session {session_id} "
            f"(remaining={session.participant_count})"
        )
    except Exception as e:
        # Error during communication
        logger.error(f"WebSocket error on session {session_id}: {e}")
        session.remove_participant(websocket)
    finally:
        # Cleanup
        if session.participant_count == 0:
            # Remove empty session after a delay (allow reconnection)
            asyncio.create_task(_cleanup_empty_session(session_id, delay=60))
        else:
            # Notify remaining participants
            try:
                await session.broadcast({
                    "type": "participant_left",
                    "participant_count": session.participant_count,
                })
            except Exception:
                pass
        
        # Update metrics
        try:
            from ..api.orchestrator_metrics import update_active_sessions
            update_active_sessions(CollabSessionManager.get_session_count())
        except Exception:
            pass


async def _cleanup_empty_session(session_id: str, delay: float = 60) -> None:
    """Remove an empty session after a delay."""
    await asyncio.sleep(delay)
    session = CollabSessionManager.get_session(session_id)
    if session and session.participant_count == 0:
        CollabSessionManager.remove_session(session_id)
        logger.info(f"Cleaned up empty session {session_id}")


# ==============================================================================
# REST Endpoints for Session Info
# ==============================================================================

@router.get("/sessions", tags=["collaboration"])
async def list_sessions() -> Dict:
    """List all active collaboration sessions."""
    return {
        "sessions": CollabSessionManager.get_all_sessions_info(),
        "total": CollabSessionManager.get_session_count(),
    }


@router.get("/session/{session_id}/info", tags=["collaboration"])
async def get_session_info(session_id: str) -> Dict:
    """Get info about a specific session."""
    session = CollabSessionManager.get_session(session_id)
    if not session:
        return {"error": "Session not found", "session_id": session_id}
    
    return {
        "session_id": session.id,
        "participant_count": session.participant_count,
        "created_at": session.created_at,
        "message_count": len(session.message_history),
    }

