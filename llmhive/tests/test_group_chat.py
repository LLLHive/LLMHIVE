"""Tests for Group Chat collaboration feature.

This module validates the collaboration implementation:
- Session creation and management
- Participant joining/leaving
- Message handling
- SSE event streaming
- WebSocket collaboration
- Namespace isolation for multi-user sessions
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, List
from datetime import datetime, timezone

# Import the modules under test
from llmhive.app.routers.collaborate import (
    InMemorySessionStore,
    get_session_store,
    generate_session_id,
    generate_invite_token,
)
from llmhive.app.routers.collab import (
    CollabSession,
    CollabSessionManager,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def session_store():
    """Create a fresh in-memory session store."""
    # Reset the singleton for testing
    InMemorySessionStore._instance = None
    return InMemorySessionStore()


@pytest.fixture
def sample_session_id():
    return generate_session_id()


@pytest.fixture
def sample_invite_token():
    return generate_invite_token()


@pytest.fixture
def owner_user_id():
    return "owner_user_123"


# =============================================================================
# Test Session ID and Token Generation
# =============================================================================

class TestIdGeneration:
    """Tests for session ID and invite token generation."""
    
    def test_generate_session_id_format(self):
        """Test that session IDs are valid UUIDs."""
        session_id = generate_session_id()
        
        # UUID format: 8-4-4-4-12 hex chars
        parts = session_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12
    
    def test_generate_session_id_uniqueness(self):
        """Test that generated session IDs are unique."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique
    
    def test_generate_invite_token_format(self):
        """Test that invite tokens are URL-safe."""
        token = generate_invite_token()
        
        # URL-safe base64: alphanumeric plus - and _
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert all(c in valid_chars for c in token)
        assert len(token) >= 20  # Secure length
    
    def test_generate_invite_token_uniqueness(self):
        """Test that invite tokens are unique."""
        tokens = [generate_invite_token() for _ in range(100)]
        assert len(set(tokens)) == 100


# =============================================================================
# Test InMemorySessionStore
# =============================================================================

class TestInMemorySessionStore:
    """Tests for the in-memory session storage."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test creating a new collaborative session."""
        session = await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
            title="Test Session",
            description="A test collaborative session",
        )
        
        assert session["session_id"] == sample_session_id
        assert session["owner_user_id"] == owner_user_id
        assert session["invite_token"] == sample_invite_token
        assert session["title"] == "Test Session"
        assert session["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_session(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test retrieving a session by ID."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        session = await session_store.get_session(sample_session_id)
        
        assert session is not None
        assert session["session_id"] == sample_session_id
    
    @pytest.mark.asyncio
    async def test_get_session_by_token(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test retrieving a session by invite token."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        session = await session_store.get_session_by_token(sample_invite_token)
        
        assert session is not None
        assert session["session_id"] == sample_session_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_store):
        """Test getting a non-existent session returns None."""
        session = await session_store.get_session("nonexistent-id")
        assert session is None
    
    @pytest.mark.asyncio
    async def test_add_participant(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test adding a participant to a session."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        # Add a new participant
        new_user_id = "new_user_456"
        success = await session_store.add_participant(
            session_id=sample_session_id,
            user_id=new_user_id,
            display_name="New User",
            access_level="editor",
        )
        
        assert success is True
        
        # Verify participant was added
        participants = await session_store.get_participants(sample_session_id)
        user_ids = [p["user_id"] for p in participants]
        
        assert owner_user_id in user_ids
        assert new_user_id in user_ids
    
    @pytest.mark.asyncio
    async def test_participant_limit(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test that participant limit is enforced."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
            max_participants=2,  # Owner + 1 more
        )
        
        # First additional participant should succeed
        success1 = await session_store.add_participant(
            session_id=sample_session_id,
            user_id="user2",
        )
        assert success1 is True
        
        # Second additional should fail (exceeds limit)
        success2 = await session_store.add_participant(
            session_id=sample_session_id,
            user_id="user3",
        )
        assert success2 is False


# =============================================================================
# Test Message Handling
# =============================================================================

class TestMessageHandling:
    """Tests for message operations in sessions."""
    
    @pytest.mark.asyncio
    async def test_add_message(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test adding a message to a session."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        message = await session_store.add_message(
            session_id=sample_session_id,
            content="Hello, world!",
            sender_user_id=owner_user_id,
            sender_name="Owner",
            message_type="user",
        )
        
        assert message["content"] == "Hello, world!"
        assert message["sender_user_id"] == owner_user_id
        assert message["sequence_number"] == 1
    
    @pytest.mark.asyncio
    async def test_message_sequence_numbers(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test that message sequence numbers increment correctly."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        msg1 = await session_store.add_message(session_id=sample_session_id, content="First")
        msg2 = await session_store.add_message(session_id=sample_session_id, content="Second")
        msg3 = await session_store.add_message(session_id=sample_session_id, content="Third")
        
        assert msg1["sequence_number"] == 1
        assert msg2["sequence_number"] == 2
        assert msg3["sequence_number"] == 3
    
    @pytest.mark.asyncio
    async def test_get_messages(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test retrieving messages from a session."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        # Add several messages
        for i in range(5):
            await session_store.add_message(
                session_id=sample_session_id,
                content=f"Message {i+1}",
            )
        
        messages = await session_store.get_messages(sample_session_id)
        
        assert len(messages) == 5
        assert messages[0]["content"] == "Message 1"
        assert messages[4]["content"] == "Message 5"
    
    @pytest.mark.asyncio
    async def test_get_messages_pagination(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test message pagination."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        # Add 10 messages
        for i in range(10):
            await session_store.add_message(
                session_id=sample_session_id,
                content=f"Message {i+1}",
            )
        
        # Get first page
        page1 = await session_store.get_messages(sample_session_id, limit=3, offset=0)
        assert len(page1) == 3
        assert page1[0]["content"] == "Message 1"
        
        # Get second page
        page2 = await session_store.get_messages(sample_session_id, limit=3, offset=3)
        assert len(page2) == 3
        assert page2[0]["content"] == "Message 4"
    
    @pytest.mark.asyncio
    async def test_message_count(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test getting message count."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        # Initially zero
        count = await session_store.get_message_count(sample_session_id)
        assert count == 0
        
        # Add messages
        for _ in range(7):
            await session_store.add_message(session_id=sample_session_id, content="Msg")
        
        count = await session_store.get_message_count(sample_session_id)
        assert count == 7


# =============================================================================
# Test SSE Subscriptions
# =============================================================================

class TestSSESubscriptions:
    """Tests for Server-Sent Events subscriptions."""
    
    @pytest.mark.asyncio
    async def test_subscribe_sse(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test subscribing to SSE events."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        client_id, queue = await session_store.subscribe_sse(sample_session_id)
        
        assert client_id is not None
        assert len(client_id) == 8  # Short ID
        assert queue is not None
        assert isinstance(queue, asyncio.Queue)
    
    @pytest.mark.asyncio
    async def test_broadcast_sse(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test broadcasting events to SSE subscribers."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        # Subscribe two clients
        _, queue1 = await session_store.subscribe_sse(sample_session_id)
        _, queue2 = await session_store.subscribe_sse(sample_session_id)
        
        # Broadcast an event
        event = {"type": "message", "content": "Hello!"}
        count = await session_store.broadcast_sse(sample_session_id, event)
        
        assert count == 2
        
        # Both queues should have the event
        received1 = queue1.get_nowait()
        received2 = queue2.get_nowait()
        
        assert received1 == event
        assert received2 == event
    
    @pytest.mark.asyncio
    async def test_unsubscribe_sse(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test unsubscribing from SSE events."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        client_id, queue = await session_store.subscribe_sse(sample_session_id)
        
        # Unsubscribe
        await session_store.unsubscribe_sse(sample_session_id, client_id)
        
        # Broadcast should not reach the unsubscribed client
        event = {"type": "test"}
        count = await session_store.broadcast_sse(sample_session_id, event)
        
        assert count == 0


# =============================================================================
# Test Session Deletion
# =============================================================================

class TestSessionDeletion:
    """Tests for session deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_store, sample_session_id, sample_invite_token, owner_user_id):
        """Test deleting a session."""
        await session_store.create_session(
            session_id=sample_session_id,
            owner_user_id=owner_user_id,
            invite_token=sample_invite_token,
        )
        
        success = await session_store.delete_session(sample_session_id)
        assert success is True
        
        # Session should be marked as deleted
        session = await session_store.get_session(sample_session_id)
        assert session["status"] == "deleted"
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, session_store):
        """Test deleting a non-existent session."""
        success = await session_store.delete_session("nonexistent-id")
        assert success is False


# =============================================================================
# Test CollabSession (WebSocket)
# =============================================================================

class TestCollabSession:
    """Tests for WebSocket-based collaboration sessions."""
    
    def test_create_collab_session(self):
        """Test creating a collab session."""
        session = CollabSession(id="ws-session-123")
        
        assert session.id == "ws-session-123"
        assert session.participants == []
        assert session.message_history == []
    
    def test_add_remove_participant(self):
        """Test adding and removing participants."""
        session = CollabSession(id="test-session")
        
        mock_ws = MagicMock()
        
        session.add_participant(mock_ws)
        assert session.participant_count == 1
        
        session.remove_participant(mock_ws)
        assert session.participant_count == 0
    
    def test_no_duplicate_participants(self):
        """Test that the same participant can't be added twice."""
        session = CollabSession(id="test-session")
        mock_ws = MagicMock()
        
        session.add_participant(mock_ws)
        session.add_participant(mock_ws)  # Try to add again
        
        assert session.participant_count == 1


# =============================================================================
# Test CollabSessionManager
# =============================================================================

class TestCollabSessionManager:
    """Tests for the collaboration session manager."""
    
    def test_get_or_create_session(self):
        """Test getting or creating a session."""
        # Clear any existing sessions
        CollabSessionManager._sessions = {}
        
        session1 = CollabSessionManager.get_or_create_session("test-session")
        session2 = CollabSessionManager.get_or_create_session("test-session")
        
        # Should return the same session
        assert session1 is session2
        assert session1.id == "test-session"
    
    def test_get_nonexistent_session(self):
        """Test getting a non-existent session returns None."""
        CollabSessionManager._sessions = {}
        
        session = CollabSessionManager.get_session("nonexistent")
        assert session is None


# =============================================================================
# Test Feature Flag Integration
# =============================================================================

class TestGroupChatFeatureFlag:
    """Tests for Group Chat feature flag integration."""
    
    def test_feature_flag_exists(self):
        """Verify GROUP_CHAT feature flag is defined."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        
        assert FeatureFlags.GROUP_CHAT.value == "group_chat"
    
    def test_feature_can_be_toggled(self):
        """Test that the feature flag can be toggled."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        import os
        
        with patch.dict(os.environ, {"FEATURE_GROUP_CHAT": "true"}):
            assert is_feature_enabled(FeatureFlags.GROUP_CHAT) is True
        
        with patch.dict(os.environ, {"FEATURE_GROUP_CHAT": "false"}):
            assert is_feature_enabled(FeatureFlags.GROUP_CHAT) is False


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

