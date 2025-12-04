"""Unit tests for Shared Memory Module."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytest

from llmhive.app.memory.shared_memory import (
    SharedMemoryManager,
    SharedMemoryEntry,
    SharedMemoryQuery,
    SharedMemoryResult,
    AccessControl,
    AccessLevel,
    MemoryCategory,
    InMemorySharedStore,
    get_shared_memory_manager,
)


class TestAccessControl:
    """Tests for AccessControl class."""
    
    def test_owner_can_read(self):
        """Test owner can always read."""
        acl = AccessControl(owner_id="user1", access_level=AccessLevel.PRIVATE)
        assert acl.can_read("user1") is True
    
    def test_private_blocks_others(self):
        """Test private blocks non-owners."""
        acl = AccessControl(owner_id="user1", access_level=AccessLevel.PRIVATE)
        assert acl.can_read("user2") is False
    
    def test_public_allows_all(self):
        """Test public allows everyone."""
        acl = AccessControl(owner_id="user1", access_level=AccessLevel.PUBLIC)
        assert acl.can_read("user2") is True
        assert acl.can_read("user3") is True
    
    def test_allowed_users(self):
        """Test allowed users list."""
        acl = AccessControl(
            owner_id="user1",
            access_level=AccessLevel.USER,
            allowed_users={"user2", "user3"},
        )
        assert acl.can_read("user2") is True
        assert acl.can_read("user3") is True
        assert acl.can_read("user4") is False
    
    def test_team_access(self):
        """Test team-level access."""
        acl = AccessControl(
            owner_id="user1",
            access_level=AccessLevel.TEAM,
            allowed_teams={"team_a"},
        )
        assert acl.can_read("user2", team_id="team_a") is True
        assert acl.can_read("user2", team_id="team_b") is False
    
    def test_owner_can_write(self):
        """Test owner can always write."""
        acl = AccessControl(owner_id="user1", read_only=False)
        assert acl.can_write("user1") is True
    
    def test_read_only_blocks_write(self):
        """Test read-only blocks non-owner writes."""
        acl = AccessControl(
            owner_id="user1",
            allowed_users={"user2"},
            read_only=True,
        )
        assert acl.can_write("user2") is False
        assert acl.can_write("user1") is True  # Owner can still write
    
    def test_expiration(self):
        """Test expiration check."""
        # Not expired
        acl = AccessControl(
            owner_id="user1",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        assert acl.is_expired() is False
        
        # Expired
        acl_expired = AccessControl(
            owner_id="user1",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert acl_expired.is_expired() is True
    
    def test_no_expiration(self):
        """Test no expiration set."""
        acl = AccessControl(owner_id="user1", expires_at=None)
        assert acl.is_expired() is False


class TestSharedMemoryEntry:
    """Tests for SharedMemoryEntry class."""
    
    def test_create_entry(self):
        """Test creating a memory entry."""
        acl = AccessControl(owner_id="user1")
        entry = SharedMemoryEntry(
            id="entry1",
            content="Test content",
            owner_id="user1",
            access_control=acl,
            category=MemoryCategory.FACT,
            tags=["test", "fact"],
        )
        
        assert entry.id == "entry1"
        assert entry.content == "Test content"
        assert entry.category == MemoryCategory.FACT
        assert "test" in entry.tags
    
    def test_is_verified(self):
        """Test verified property."""
        acl = AccessControl(owner_id="user1")
        entry = SharedMemoryEntry(
            id="entry1",
            content="Test",
            owner_id="user1",
            access_control=acl,
            metadata={"verified": True},
        )
        
        assert entry.is_verified is True
    
    def test_session_id(self):
        """Test session_id property."""
        acl = AccessControl(owner_id="user1")
        entry = SharedMemoryEntry(
            id="entry1",
            content="Test",
            owner_id="user1",
            access_control=acl,
            metadata={"session_id": "session123"},
        )
        
        assert entry.session_id == "session123"


class TestInMemorySharedStore:
    """Tests for InMemorySharedStore class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.store = InMemorySharedStore()
    
    @pytest.mark.asyncio
    async def test_store_and_get(self):
        """Test storing and retrieving an entry."""
        acl = AccessControl(owner_id="user1")
        entry = SharedMemoryEntry(
            id="entry1",
            content="Test content",
            owner_id="user1",
            access_control=acl,
        )
        
        await self.store.store(entry)
        retrieved = await self.store.get("entry1", "user1")
        
        assert retrieved is not None
        assert retrieved.content == "Test content"
    
    @pytest.mark.asyncio
    async def test_access_control_enforced(self):
        """Test access control is enforced on get."""
        acl = AccessControl(owner_id="user1", access_level=AccessLevel.PRIVATE)
        entry = SharedMemoryEntry(
            id="entry1",
            content="Private content",
            owner_id="user1",
            access_control=acl,
        )
        
        await self.store.store(entry)
        
        # Owner can access
        retrieved = await self.store.get("entry1", "user1")
        assert retrieved is not None
        
        # Others cannot
        retrieved = await self.store.get("entry1", "user2")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_query_by_user(self):
        """Test querying by user."""
        acl1 = AccessControl(owner_id="user1")
        acl2 = AccessControl(owner_id="user2")
        
        entry1 = SharedMemoryEntry(
            id="entry1", content="User1 content", owner_id="user1", access_control=acl1
        )
        entry2 = SharedMemoryEntry(
            id="entry2", content="User2 content", owner_id="user2", access_control=acl2
        )
        
        await self.store.store(entry1)
        await self.store.store(entry2)
        
        query = SharedMemoryQuery(user_id="user1")
        result = await self.store.query(query)
        
        assert len(result.entries) == 1
        assert result.entries[0].owner_id == "user1"
    
    @pytest.mark.asyncio
    async def test_query_by_category(self):
        """Test querying by category."""
        acl = AccessControl(owner_id="user1")
        
        entry1 = SharedMemoryEntry(
            id="entry1", content="Fact", owner_id="user1",
            access_control=acl, category=MemoryCategory.FACT
        )
        entry2 = SharedMemoryEntry(
            id="entry2", content="Preference", owner_id="user1",
            access_control=acl, category=MemoryCategory.PREFERENCE
        )
        
        await self.store.store(entry1)
        await self.store.store(entry2)
        
        query = SharedMemoryQuery(
            user_id="user1",
            categories=[MemoryCategory.FACT]
        )
        result = await self.store.query(query)
        
        assert len(result.entries) == 1
        assert result.entries[0].category == MemoryCategory.FACT
    
    @pytest.mark.asyncio
    async def test_query_by_tags(self):
        """Test querying by tags."""
        acl = AccessControl(owner_id="user1")
        
        entry1 = SharedMemoryEntry(
            id="entry1", content="Tagged", owner_id="user1",
            access_control=acl, tags=["important", "fact"]
        )
        entry2 = SharedMemoryEntry(
            id="entry2", content="Untagged", owner_id="user1",
            access_control=acl, tags=["other"]
        )
        
        await self.store.store(entry1)
        await self.store.store(entry2)
        
        query = SharedMemoryQuery(
            user_id="user1",
            tags=["important"]
        )
        result = await self.store.query(query)
        
        assert len(result.entries) == 1
        assert "important" in result.entries[0].tags
    
    @pytest.mark.asyncio
    async def test_update_entry(self):
        """Test updating an entry."""
        acl = AccessControl(owner_id="user1")
        entry = SharedMemoryEntry(
            id="entry1", content="Original", owner_id="user1", access_control=acl
        )
        
        await self.store.store(entry)
        
        success = await self.store.update(
            "entry1", "user1", {"content": "Updated"}
        )
        
        assert success is True
        
        retrieved = await self.store.get("entry1", "user1")
        assert retrieved.content == "Updated"
    
    @pytest.mark.asyncio
    async def test_delete_entry(self):
        """Test deleting an entry."""
        acl = AccessControl(owner_id="user1")
        entry = SharedMemoryEntry(
            id="entry1", content="To delete", owner_id="user1", access_control=acl
        )
        
        await self.store.store(entry)
        
        # Non-owner cannot delete
        success = await self.store.delete("entry1", "user2")
        assert success is False
        
        # Owner can delete
        success = await self.store.delete("entry1", "user1")
        assert success is True
        
        retrieved = await self.store.get("entry1", "user1")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_share_entry(self):
        """Test sharing an entry."""
        acl = AccessControl(owner_id="user1", access_level=AccessLevel.PRIVATE)
        entry = SharedMemoryEntry(
            id="entry1", content="Shareable", owner_id="user1", access_control=acl
        )
        
        await self.store.store(entry)
        
        # Before sharing
        retrieved = await self.store.get("entry1", "user2")
        assert retrieved is None
        
        # Share with user2
        success = await self.store.share("entry1", "user1", ["user2"])
        assert success is True
        
        # After sharing
        retrieved = await self.store.get("entry1", "user2")
        assert retrieved is not None


class TestSharedMemoryManager:
    """Tests for SharedMemoryManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SharedMemoryManager()
    
    @pytest.mark.asyncio
    async def test_store_memory(self):
        """Test storing memory."""
        entry_id = await self.manager.store_memory(
            content="Test memory content",
            owner_id="user1",
            category=MemoryCategory.CONTEXT,
            tags=["test"],
        )
        
        assert entry_id is not None
        assert len(entry_id) == 32
    
    @pytest.mark.asyncio
    async def test_store_empty_content(self):
        """Test storing empty content returns empty string."""
        entry_id = await self.manager.store_memory(
            content="",
            owner_id="user1",
        )
        
        assert entry_id == ""
    
    @pytest.mark.asyncio
    async def test_query_memory(self):
        """Test querying memory."""
        await self.manager.store_memory(
            content="First memory",
            owner_id="user1",
            category=MemoryCategory.FACT,
        )
        await self.manager.store_memory(
            content="Second memory",
            owner_id="user1",
            category=MemoryCategory.INSIGHT,
        )
        
        result = await self.manager.query_memory(
            user_id="user1",
            limit=10,
        )
        
        assert len(result.entries) == 2
    
    @pytest.mark.asyncio
    async def test_get_session_context(self):
        """Test getting session context."""
        await self.manager.store_memory(
            content="Session context",
            owner_id="user1",
            session_id="session123",
            category=MemoryCategory.CONTEXT,
        )
        
        entries = await self.manager.get_session_context(
            user_id="user1",
            session_id="session123",
        )
        
        assert len(entries) >= 1
    
    @pytest.mark.asyncio
    async def test_store_conversation_insight(self):
        """Test storing conversation insight."""
        entry_id = await self.manager.store_conversation_insight(
            user_id="user1",
            session_id="session123",
            insight="Important insight here",
            verified=True,
        )
        
        assert entry_id is not None
    
    @pytest.mark.asyncio
    async def test_store_user_preference(self):
        """Test storing user preference."""
        entry_id = await self.manager.store_user_preference(
            user_id="user1",
            preference_key="response_style",
            preference_value="concise",
        )
        
        assert entry_id is not None
    
    @pytest.mark.asyncio
    async def test_get_user_preferences(self):
        """Test getting user preferences."""
        await self.manager.store_user_preference(
            user_id="user1",
            preference_key="style",
            preference_value="formal",
        )
        await self.manager.store_user_preference(
            user_id="user1",
            preference_key="language",
            preference_value="english",
        )
        
        preferences = await self.manager.get_user_preferences("user1")
        
        assert "style" in preferences
        assert preferences["style"] == "formal"
    
    @pytest.mark.asyncio
    async def test_build_context_string(self):
        """Test building context string."""
        await self.manager.store_memory(
            content="Important fact",
            owner_id="user1",
            category=MemoryCategory.FACT,
        )
        await self.manager.store_memory(
            content="Session context",
            owner_id="user1",
            session_id="session123",
            category=MemoryCategory.CONTEXT,
        )
        
        context = await self.manager.build_context_string(
            user_id="user1",
            session_id="session123",
        )
        
        assert len(context) > 0
    
    @pytest.mark.asyncio
    async def test_share_memory(self):
        """Test sharing memory."""
        entry_id = await self.manager.store_memory(
            content="Shareable content",
            owner_id="user1",
            access_level=AccessLevel.PRIVATE,
        )
        
        success = await self.manager.share_memory(
            entry_id=entry_id,
            owner_id="user1",
            share_with=["user2", "user3"],
        )
        
        assert success is True


class TestGlobalInstance:
    """Tests for global instance."""
    
    def test_get_shared_memory_manager(self):
        """Test getting global instance."""
        manager1 = get_shared_memory_manager()
        manager2 = get_shared_memory_manager()
        
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

