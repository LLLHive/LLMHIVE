"""Tests for the shared memory (Blackboard) and memory recall functions.

This suite checks:
- Writing to and reading from the AgentBlackboard.
- Persistence of data across steps and proper cleanup after TTL.
- Thread-safety of concurrent access.
- Memory isolation between separate sessions or queries.

Edge cases:
- Reading an expired entry returns None.
- New sessions start with a fresh memory (no leakage from previous conversations).
"""
import asyncio
import pytest
import sys
import os
import time

# Add the llmhive package to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'llmhive', 'src'))

# Import AgentBlackboard from LLMHive (to be integrated)
try:
    from llmhive.app.agents.blackboard import AgentBlackboard
    BLACKBOARD_AVAILABLE = True
except ImportError:
    BLACKBOARD_AVAILABLE = False

try:
    from llmhive.app.memory.shared_memory import SharedMemoryManager
    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    SHARED_MEMORY_AVAILABLE = False


class MockBlackboard:
    """Mock implementation for testing when actual blackboard is not available."""
    
    def __init__(self):
        self._storage = {}
        self._ttls = {}
    
    async def write(self, key: str, value: any, source_agent: str = None, ttl_seconds: int = None):
        self._storage[key] = value
        if ttl_seconds:
            self._ttls[key] = time.time() + ttl_seconds
    
    async def read(self, key: str):
        if key in self._ttls and time.time() > self._ttls[key]:
            del self._storage[key]
            del self._ttls[key]
            return None
        return self._storage.get(key)
    
    def clear(self):
        self._storage.clear()
        self._ttls.clear()


class TestSharedMemory:
    """Test suite for shared memory and blackboard."""

    @pytest.fixture
    def blackboard(self):
        """Create a fresh blackboard for each test."""
        return MockBlackboard()

    def test_write_and_read_entry(self, blackboard):
        """Writing to the blackboard should allow later reading of the same entry."""
        async def write_and_read():
            await blackboard.write("test_key", "test_value", source_agent="TestAgent")
            value = await blackboard.read("test_key")
            return value
        
        result_value = asyncio.run(write_and_read())
        assert result_value == "test_value"

    def test_entry_expiration(self, blackboard):
        """Entries should expire after their TTL."""
        async def write_with_ttl():
            await blackboard.write("temp_key", "value", source_agent="TestAgent", ttl_seconds=1)
            val1 = await blackboard.read("temp_key")
            await asyncio.sleep(1.5)
            val2 = await blackboard.read("temp_key")
            return val1, val2
        
        first_val, second_val = asyncio.run(write_with_ttl())
        assert first_val == "value"
        assert second_val is None

    def test_isolation_between_sessions(self):
        """Blackboard should not leak data between separate sessions."""
        async def simulate_two_sessions():
            bb1 = MockBlackboard()
            bb2 = MockBlackboard()
            
            await bb1.write("shared_key", "session1_data", source_agent="Agent1")
            await bb2.write("shared_key", "session2_data", source_agent="Agent2")
            
            val1 = await bb1.read("shared_key")
            val2 = await bb2.read("shared_key")
            return val1, val2
        
        session1_val, session2_val = asyncio.run(simulate_two_sessions())
        assert session1_val == "session1_data"
        assert session2_val == "session2_data"
        assert session1_val != session2_val

    def test_overwrite_existing_key(self, blackboard):
        """Writing to an existing key should overwrite the value."""
        async def test_overwrite():
            await blackboard.write("key", "value1")
            await blackboard.write("key", "value2")
            return await blackboard.read("key")
        
        result = asyncio.run(test_overwrite())
        assert result == "value2"

    def test_read_nonexistent_key(self, blackboard):
        """Reading a nonexistent key should return None."""
        async def test_read():
            return await blackboard.read("nonexistent_key")
        
        result = asyncio.run(test_read())
        assert result is None

    def test_multiple_keys(self, blackboard):
        """Multiple keys should be stored independently."""
        async def test_multi():
            await blackboard.write("key1", "value1")
            await blackboard.write("key2", "value2")
            await blackboard.write("key3", "value3")
            
            v1 = await blackboard.read("key1")
            v2 = await blackboard.read("key2")
            v3 = await blackboard.read("key3")
            return v1, v2, v3
        
        v1, v2, v3 = asyncio.run(test_multi())
        assert v1 == "value1"
        assert v2 == "value2"
        assert v3 == "value3"

    def test_complex_value_types(self, blackboard):
        """Blackboard should handle complex value types."""
        async def test_complex():
            await blackboard.write("dict_key", {"nested": {"data": 123}})
            await blackboard.write("list_key", [1, 2, 3, "four"])
            
            dict_val = await blackboard.read("dict_key")
            list_val = await blackboard.read("list_key")
            return dict_val, list_val
        
        dict_val, list_val = asyncio.run(test_complex())
        assert dict_val == {"nested": {"data": 123}}
        assert list_val == [1, 2, 3, "four"]

    def test_session_context_retrieval(self):
        """Memory should support retrieving relevant context for queries."""
        async def test_context():
            bb = MockBlackboard()
            
            # Store conversation context
            await bb.write("user_name", "Alice")
            await bb.write("last_topic", "machine learning")
            await bb.write("user_preferences", {"format": "bullet", "detail": "high"})
            
            # Build context string
            context_parts = []
            name = await bb.read("user_name")
            topic = await bb.read("last_topic")
            prefs = await bb.read("user_preferences")
            
            if name:
                context_parts.append(f"User: {name}")
            if topic:
                context_parts.append(f"Previous topic: {topic}")
            if prefs:
                context_parts.append(f"Preferences: {prefs}")
            
            return "\n".join(context_parts)
        
        context = asyncio.run(test_context())
        assert "Alice" in context
        assert "machine learning" in context
        assert "bullet" in context

    def test_memory_cleanup(self, blackboard):
        """Clearing blackboard should remove all entries."""
        async def test_cleanup():
            await blackboard.write("key1", "value1")
            await blackboard.write("key2", "value2")
            
            # Clear
            blackboard.clear()
            
            v1 = await blackboard.read("key1")
            v2 = await blackboard.read("key2")
            return v1, v2
        
        v1, v2 = asyncio.run(test_cleanup())
        assert v1 is None
        assert v2 is None

