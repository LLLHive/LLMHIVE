"""Tests for Collaboration Feature.

Tests cover:
1. Session creation and management
2. Joining sessions via invite token
3. Message persistence and history
4. Participant management
5. SSE streaming for real-time updates
6. Access control (owner permissions)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))


# Helper to run async code in sync tests
def run_async(coro):
    """Run async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ==============================================================================
# Test InMemorySessionStore
# ==============================================================================

class TestInMemorySessionStore:
    """Tests for the in-memory session store."""
    
    def get_store(self):
        """Get a fresh store instance."""
        from llmhive.app.routers.collaborate import InMemorySessionStore
        return InMemorySessionStore()
    
    def test_create_session(self):
        """Test creating a new session."""
        store = self.get_store()
        
        async def _test():
            session = await store.create_session(
                session_id="test-session-1",
                owner_user_id="user-123",
                invite_token="token-abc123",
                title="Test Session",
            )
            
            assert session["session_id"] == "test-session-1"
            assert session["owner_user_id"] == "user-123"
            assert session["invite_token"] == "token-abc123"
            assert session["title"] == "Test Session"
            assert session["status"] == "active"
        
        run_async(_test())
    
    def test_get_session_by_id(self):
        """Test retrieving a session by ID."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="session-xyz",
                owner_user_id="user-1",
                invite_token="token-1",
            )
            
            session = await store.get_session("session-xyz")
            assert session is not None
            assert session["session_id"] == "session-xyz"
            
            # Non-existent session
            missing = await store.get_session("nonexistent")
            assert missing is None
        
        run_async(_test())
    
    def test_get_session_by_token(self):
        """Test retrieving a session by invite token."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="session-token-test",
                owner_user_id="user-1",
                invite_token="unique-token-123",
            )
            
            session = await store.get_session_by_token("unique-token-123")
            assert session is not None
            assert session["session_id"] == "session-token-test"
            
            # Invalid token
            missing = await store.get_session_by_token("wrong-token")
            assert missing is None
        
        run_async(_test())
    
    def test_add_participant(self):
        """Test adding participants to a session."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="collab-session",
                owner_user_id="owner-1",
                invite_token="token",
            )
            
            # Add a participant
            success = await store.add_participant(
                session_id="collab-session",
                user_id="user-2",
                display_name="Alice",
                access_level="editor",
            )
            assert success is True
            
            participants = await store.get_participants("collab-session")
            assert len(participants) == 2  # Owner + new participant
            
            # Find the new participant
            alice = next((p for p in participants if p["user_id"] == "user-2"), None)
            assert alice is not None
            assert alice["display_name"] == "Alice"
            assert alice["access_level"] == "editor"
        
        run_async(_test())
    
    def test_add_message(self):
        """Test adding messages to a session."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="message-session",
                owner_user_id="user-1",
                invite_token="token",
            )
            
            # Add messages
            msg1 = await store.add_message(
                session_id="message-session",
                content="Hello, world!",
                sender_user_id="user-1",
                message_type="user",
            )
            
            assert msg1["id"] == 1
            assert msg1["content"] == "Hello, world!"
            assert msg1["sender_user_id"] == "user-1"
            
            msg2 = await store.add_message(
                session_id="message-session",
                content="Hello back!",
                sender_user_id="user-2",
            )
            
            assert msg2["id"] == 2
            
            # Check message count
            count = await store.get_message_count("message-session")
            assert count == 2
        
        run_async(_test())
    
    def test_get_messages(self):
        """Test retrieving messages with pagination."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="paginated-session",
                owner_user_id="user-1",
                invite_token="token",
            )
            
            # Add 10 messages
            for i in range(10):
                await store.add_message(
                    session_id="paginated-session",
                    content=f"Message {i+1}",
                    sender_user_id="user-1",
                )
            
            # Get first 5
            messages = await store.get_messages("paginated-session", limit=5, offset=0)
            assert len(messages) == 5
            assert messages[0]["content"] == "Message 1"
            
            # Get next 5
            messages = await store.get_messages("paginated-session", limit=5, offset=5)
            assert len(messages) == 5
            assert messages[0]["content"] == "Message 6"
        
        run_async(_test())
    
    def test_delete_session(self):
        """Test deleting (archiving) a session."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="delete-me",
                owner_user_id="user-1",
                invite_token="token",
            )
            
            success = await store.delete_session("delete-me")
            assert success is True
            
            session = await store.get_session("delete-me")
            assert session["status"] == "deleted"
        
        run_async(_test())
    
    def test_max_participants(self):
        """Test that max_participants limit is enforced."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="limited-session",
                owner_user_id="owner",
                invite_token="token",
                max_participants=3,  # Owner + 2 more
            )
            
            # Add 2 participants (should succeed)
            success1 = await store.add_participant("limited-session", "user-2")
            success2 = await store.add_participant("limited-session", "user-3")
            assert success1 is True
            assert success2 is True
            
            # Adding 4th should fail
            success3 = await store.add_participant("limited-session", "user-4")
            assert success3 is False
            
            participants = await store.get_participants("limited-session")
            assert len(participants) == 3
        
        run_async(_test())


# ==============================================================================
# Test SSE Broadcasting
# ==============================================================================

class TestSSEBroadcasting:
    """Tests for SSE event broadcasting."""
    
    def get_store(self):
        from llmhive.app.routers.collaborate import InMemorySessionStore
        return InMemorySessionStore()
    
    def test_subscribe_and_broadcast(self):
        """Test subscribing and receiving broadcasts."""
        store = self.get_store()
        
        async def _test():
            # Create session
            await store.create_session(
                session_id="sse-session",
                owner_user_id="user-1",
                invite_token="token",
            )
            
            # Subscribe two clients
            client1_id, queue1 = await store.subscribe_sse("sse-session")
            client2_id, queue2 = await store.subscribe_sse("sse-session")
            
            assert client1_id != client2_id
            
            # Broadcast an event
            count = await store.broadcast_sse("sse-session", {
                "type": "test_event",
                "data": "hello",
            })
            
            assert count == 2
            
            # Both queues should have the event
            event1 = await queue1.get()
            event2 = await queue2.get()
            
            assert event1["type"] == "test_event"
            assert event2["type"] == "test_event"
        
        run_async(_test())
    
    def test_unsubscribe(self):
        """Test unsubscribing from SSE."""
        store = self.get_store()
        
        async def _test():
            await store.create_session(
                session_id="unsub-session",
                owner_user_id="user-1",
                invite_token="token",
            )
            
            client_id, queue = await store.subscribe_sse("unsub-session")
            
            # Unsubscribe
            await store.unsubscribe_sse("unsub-session", client_id)
            
            # Broadcast should reach 0 clients
            count = await store.broadcast_sse("unsub-session", {"type": "test"})
            assert count == 0
        
        run_async(_test())


# ==============================================================================
# Test API Endpoints
# ==============================================================================

class TestCollaborationAPI:
    """Integration tests for the collaboration API endpoints."""
    
    def test_create_session_endpoint(self):
        """Test POST /api/v1/collaborate endpoint."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.collaborate import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/collaborate",
                    json={
                        "title": "My Collaboration",
                        "description": "A test session",
                        "is_public": True,
                    },
                    headers={"X-User-ID": "test-user"},
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "session_id" in data
                assert "invite_token" in data
                assert "invite_url" in data
                assert data["title"] == "My Collaboration"
        
        except ImportError:
            pytest.skip("FastAPI test client not available")
    
    def test_get_session_info_endpoint(self):
        """Test GET /api/v1/collaborate/{session_id} endpoint."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.collaborate import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            with TestClient(app) as client:
                # Create a session first
                create_response = client.post(
                    "/api/v1/collaborate",
                    json={"title": "Info Test"},
                    headers={"X-User-ID": "user-1"},
                )
                session_id = create_response.json()["session_id"]
                
                # Get session info
                info_response = client.get(f"/api/v1/collaborate/{session_id}")
                
                assert info_response.status_code == 200
                data = info_response.json()
                assert data["session_id"] == session_id
                assert data["title"] == "Info Test"
                assert data["status"] == "active"
        
        except ImportError:
            pytest.skip("FastAPI test client not available")
    
    def test_join_session_endpoint(self):
        """Test POST /api/v1/collaborate/join endpoint."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.collaborate import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            with TestClient(app) as client:
                # Create a session
                create_response = client.post(
                    "/api/v1/collaborate",
                    json={"title": "Join Test", "is_public": True},
                    headers={"X-User-ID": "owner"},
                )
                invite_token = create_response.json()["invite_token"]
                
                # Join the session
                join_response = client.post(
                    "/api/v1/collaborate/join",
                    json={
                        "invite_token": invite_token,
                        "display_name": "Bob",
                    },
                    headers={"X-User-ID": "joiner"},
                )
                
                assert join_response.status_code == 200
                data = join_response.json()
                assert data["title"] == "Join Test"
                assert data["participant_count"] == 2
        
        except ImportError:
            pytest.skip("FastAPI test client not available")
    
    def test_send_and_get_messages(self):
        """Test message sending and retrieval."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.collaborate import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            with TestClient(app) as client:
                # Create session
                create_response = client.post(
                    "/api/v1/collaborate",
                    json={"title": "Message Test"},
                    headers={"X-User-ID": "user-1"},
                )
                session_id = create_response.json()["session_id"]
                
                # Send a message
                msg_response = client.post(
                    f"/api/v1/collaborate/{session_id}/messages",
                    json={"content": "Hello everyone!"},
                    headers={"X-User-ID": "user-1"},
                )
                
                assert msg_response.status_code == 200
                msg_data = msg_response.json()
                assert msg_data["content"] == "Hello everyone!"
                
                # Get history
                history_response = client.get(f"/api/v1/collaborate/{session_id}/history")
                
                assert history_response.status_code == 200
                history = history_response.json()
                assert history["total_messages"] == 1
                assert history["messages"][0]["content"] == "Hello everyone!"
        
        except ImportError:
            pytest.skip("FastAPI test client not available")
    
    def test_delete_session_owner_only(self):
        """Test that only owners can delete sessions."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.collaborate import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            with TestClient(app) as client:
                # Create session as owner
                create_response = client.post(
                    "/api/v1/collaborate",
                    json={"title": "Delete Test"},
                    headers={"X-User-ID": "owner-user"},
                )
                session_id = create_response.json()["session_id"]
                
                # Try to delete as non-owner (should fail)
                delete_response = client.delete(
                    f"/api/v1/collaborate/{session_id}",
                    headers={"X-User-ID": "other-user"},
                )
                assert delete_response.status_code == 403
                
                # Delete as owner (should succeed)
                delete_response = client.delete(
                    f"/api/v1/collaborate/{session_id}",
                    headers={"X-User-ID": "owner-user"},
                )
                assert delete_response.status_code == 200
                assert delete_response.json()["success"] is True
        
        except ImportError:
            pytest.skip("FastAPI test client not available")
    
    def test_invalid_invite_token(self):
        """Test that invalid invite tokens are rejected."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.collaborate import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/collaborate/join",
                    json={"invite_token": "invalid-token-12345678"},
                    headers={"X-User-ID": "joiner"},
                )
                
                assert response.status_code == 404
        
        except ImportError:
            pytest.skip("FastAPI test client not available")


# ==============================================================================
# Test Model Schemas
# ==============================================================================

class TestCollaborationModels:
    """Tests for Pydantic schemas."""
    
    def test_create_session_request_validation(self):
        """Test CreateSessionRequest validation."""
        from llmhive.app.routers.collaborate import CreateSessionRequest
        
        # Valid request
        request = CreateSessionRequest(
            title="Valid Title",
            max_participants=50,
        )
        assert request.title == "Valid Title"
        assert request.max_participants == 50
        
        # Default values
        default_request = CreateSessionRequest()
        assert default_request.is_public is False
        assert default_request.max_participants == 10
    
    def test_send_message_request_validation(self):
        """Test SendMessageRequest validation."""
        from llmhive.app.routers.collaborate import SendMessageRequest
        
        # Valid request
        request = SendMessageRequest(
            content="Hello!",
            message_type="user",
        )
        assert request.content == "Hello!"
        assert request.message_type == "user"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

