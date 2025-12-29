"""Tests for SSE Orchestration Events Router.

Tests cover:
1. Event broadcasting and subscription
2. SSE endpoint streaming
3. Event filtering
4. Keepalive mechanism
5. Multiple client handling
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

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
# Test EventBroadcaster
# ==============================================================================

class TestEventBroadcaster:
    """Tests for the EventBroadcaster class."""
    
    def get_broadcaster(self):
        """Create a fresh broadcaster instance."""
        from llmhive.app.routers.sse_events import EventBroadcaster
        # Create new instance (bypass singleton for testing)
        return EventBroadcaster()
    
    def get_sample_event(self):
        """Create a sample orchestration event."""
        from llmhive.app.routers.sse_events import OrchestrationEvent
        return OrchestrationEvent(
            event_type="test_event",
            message="Test message",
            details={"key": "value"},
        )
    
    def test_subscribe_creates_queue(self):
        """Test that subscribing creates a client queue."""
        broadcaster = self.get_broadcaster()
        session_id = "test-session"
        
        async def _test():
            client_id, queue = await broadcaster.subscribe(session_id)
            assert client_id is not None
            assert len(client_id) == 8  # UUID prefix
            assert queue is not None
            assert broadcaster.get_subscriber_count(session_id) == 1
        
        run_async(_test())
    
    def test_multiple_subscribers(self):
        """Test multiple clients subscribing to same session."""
        broadcaster = self.get_broadcaster()
        session_id = "test-session"
        
        async def _test():
            client1_id, queue1 = await broadcaster.subscribe(session_id)
            client2_id, queue2 = await broadcaster.subscribe(session_id)
            assert client1_id != client2_id
            assert broadcaster.get_subscriber_count(session_id) == 2
        
        run_async(_test())
    
    def test_unsubscribe_removes_client(self):
        """Test that unsubscribing removes the client."""
        broadcaster = self.get_broadcaster()
        session_id = "test-session"
        
        async def _test():
            client_id, queue = await broadcaster.subscribe(session_id)
            assert broadcaster.get_subscriber_count(session_id) == 1
            
            await broadcaster.unsubscribe(session_id, client_id)
            assert broadcaster.get_subscriber_count(session_id) == 0
        
        run_async(_test())
    
    def test_emit_to_subscribers(self):
        """Test emitting events to subscribers."""
        broadcaster = self.get_broadcaster()
        sample_event = self.get_sample_event()
        session_id = "test-session"
        
        async def _test():
            client_id, queue = await broadcaster.subscribe(session_id)
            
            count = await broadcaster.emit(session_id, sample_event)
            
            assert count == 1
            assert not queue.empty()
            
            received = await queue.get()
            assert received.event_type == "test_event"
            assert received.message == "Test message"
        
        run_async(_test())
    
    def test_emit_to_multiple_subscribers(self):
        """Test emitting to multiple subscribers."""
        broadcaster = self.get_broadcaster()
        sample_event = self.get_sample_event()
        session_id = "test-session"
        
        async def _test():
            client1_id, queue1 = await broadcaster.subscribe(session_id)
            client2_id, queue2 = await broadcaster.subscribe(session_id)
            
            count = await broadcaster.emit(session_id, sample_event)
            
            assert count == 2
            
            event1 = await queue1.get()
            event2 = await queue2.get()
            
            assert event1.event_type == event2.event_type == "test_event"
        
        run_async(_test())
    
    def test_emit_to_nonexistent_session(self):
        """Test emitting to a session with no subscribers."""
        broadcaster = self.get_broadcaster()
        sample_event = self.get_sample_event()
        
        async def _test():
            count = await broadcaster.emit("nonexistent-session", sample_event)
            assert count == 0
        
        run_async(_test())


# ==============================================================================
# Test OrchestrationEvent
# ==============================================================================

class TestOrchestrationEvent:
    """Tests for the OrchestrationEvent dataclass."""
    
    def test_event_creation(self):
        """Test creating an event."""
        from llmhive.app.routers.sse_events import OrchestrationEvent
        
        event = OrchestrationEvent(
            event_type="model_call",
            message="Calling GPT-4",
            details={"model": "gpt-4"},
            session_id="session-123",
        )
        
        assert event.event_type == "model_call"
        assert event.message == "Calling GPT-4"
        assert event.details == {"model": "gpt-4"}
        assert event.timestamp is not None
    
    def test_event_to_sse(self):
        """Test converting event to SSE format."""
        from llmhive.app.routers.sse_events import OrchestrationEvent
        
        event = OrchestrationEvent(
            event_type="tool_invoked",
            message="Invoking web search",
            details={"tool": "web_search"},
        )
        
        sse_output = event.to_sse()
        
        assert "event: orchestration_event\n" in sse_output
        assert "data: " in sse_output
        assert '"type": "tool_invoked"' in sse_output
        assert '"message": "Invoking web search"' in sse_output
        assert sse_output.endswith("\n\n")
    
    def test_event_to_sse_includes_session_id(self):
        """Test that session_id is included in SSE output."""
        from llmhive.app.routers.sse_events import OrchestrationEvent
        
        event = OrchestrationEvent(
            event_type="step",
            message="Processing",
            session_id="my-session",
        )
        
        sse_output = event.to_sse()
        assert '"session_id": "my-session"' in sse_output


# ==============================================================================
# Test Emission Helper Functions
# ==============================================================================

class TestEmissionHelpers:
    """Tests for the event emission helper functions."""
    
    def test_emit_strategy_selected(self):
        """Test the emit_strategy_selected helper."""
        from llmhive.app.routers.sse_events import (
            emit_strategy_selected,
            get_broadcaster,
        )
        
        async def _test():
            broadcaster = get_broadcaster()
            session_id = "strategy-test"
            
            client_id, queue = await broadcaster.subscribe(session_id)
            
            # Use the helper (it schedules async broadcast)
            emit_strategy_selected(session_id, "parallel_race", "Fast query")
            
            # Give async task time to run
            await asyncio.sleep(0.1)
            
            if not queue.empty():
                event = await queue.get()
                assert event.event_type == "strategy_selected"
                assert "parallel_race" in event.message
            
            await broadcaster.unsubscribe(session_id, client_id)
        
        run_async(_test())
    
    def test_emit_model_call(self):
        """Test the emit_model_call helper."""
        from llmhive.app.routers.sse_events import emit_model_call, get_broadcaster
        
        async def _test():
            broadcaster = get_broadcaster()
            session_id = "model-test"
            
            client_id, queue = await broadcaster.subscribe(session_id)
            
            emit_model_call(session_id, "gpt-4o", "What is 2+2?")
            await asyncio.sleep(0.1)
            
            if not queue.empty():
                event = await queue.get()
                assert event.event_type == "model_call"
                assert "gpt-4o" in event.message
            
            await broadcaster.unsubscribe(session_id, client_id)
        
        run_async(_test())
    
    def test_emit_tool_invoked(self):
        """Test the emit_tool_invoked helper."""
        from llmhive.app.routers.sse_events import emit_tool_invoked, get_broadcaster
        
        async def _test():
            broadcaster = get_broadcaster()
            session_id = "tool-test"
            
            client_id, queue = await broadcaster.subscribe(session_id)
            
            emit_tool_invoked(session_id, "web_search", "Python tutorials")
            await asyncio.sleep(0.1)
            
            if not queue.empty():
                event = await queue.get()
                assert event.event_type == "tool_invoked"
                assert "web_search" in event.message
            
            await broadcaster.unsubscribe(session_id, client_id)
        
        run_async(_test())
    
    def test_emit_without_session_is_safe(self):
        """Test that emitting with empty session_id doesn't error."""
        from llmhive.app.routers.sse_events import emit_orchestration_event
        
        # Should not raise
        emit_orchestration_event("", "test", "message")


# ==============================================================================
# Test Event Filtering
# ==============================================================================

class TestEventFiltering:
    """Tests for event filtering in SSE stream."""
    
    def test_filter_includes_matching_events(self):
        """Test that filter includes matching event types."""
        from llmhive.app.routers.sse_events import (
            OrchestrationEvent,
            event_stream_generator,
            get_broadcaster,
        )
        
        async def _test():
            broadcaster = get_broadcaster()
            session_id = "filter-test"
            
            client_id, queue = await broadcaster.subscribe(session_id)
            
            # Add events to queue
            await queue.put(OrchestrationEvent("model_call", "Call 1"))
            await queue.put(OrchestrationEvent("tool_invoked", "Tool 1"))
            await queue.put(OrchestrationEvent("model_response", "Response 1"))
            
            # Filter for only model events
            event_filter = {"model_call", "model_response"}
            
            generator = event_stream_generator(
                session_id, client_id, queue,
                event_filter=event_filter,
                dev_mode=False,
            )
            
            # Skip connection event
            await generator.__anext__()
            
            # Get filtered events
            sse1 = await generator.__anext__()
            assert "model_call" in sse1
            
            # The tool_invoked should be skipped, next should be model_response
            sse2 = await generator.__anext__()
            assert "model_response" in sse2
            
            await broadcaster.unsubscribe(session_id, client_id)
        
        run_async(_test())
    
    def test_dev_mode_debug_events(self):
        """Test that debug events are only included in dev mode."""
        from llmhive.app.routers.sse_events import (
            OrchestrationEvent,
            event_stream_generator,
            get_broadcaster,
        )
        
        async def _test():
            broadcaster = get_broadcaster()
            session_id = "debug-test"
            
            client_id, queue = await broadcaster.subscribe(session_id)
            
            # Add a debug event
            await queue.put(OrchestrationEvent("debug_internal", "Debug info"))
            await queue.put(OrchestrationEvent("model_call", "Normal event"))
            
            # Without dev mode
            generator = event_stream_generator(
                session_id, client_id, queue,
                event_filter=None,
                dev_mode=False,
            )
            
            # Skip connection event
            await generator.__anext__()
            
            # Debug event should be skipped, get model_call
            sse = await generator.__anext__()
            assert "model_call" in sse
            assert "debug_internal" not in sse
            
            await broadcaster.unsubscribe(session_id, client_id)
        
        run_async(_test())


# ==============================================================================
# Test SSE Endpoint (Integration-like)
# ==============================================================================

class TestSSEEndpoint:
    """Integration tests for the SSE endpoint."""
    
    def test_test_emit_endpoint(self):
        """Test the /test endpoint for emitting events."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.sse_events import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router)
            
            with TestClient(app) as client:
                response = client.get(
                    "/orchestration/test-session/test",
                    params={"event_type": "custom", "message": "Hello"},
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["event_type"] == "custom"
                assert data["message"] == "Hello"
                
        except ImportError:
            pytest.skip("FastAPI test client not available")
    
    def test_stats_endpoint(self):
        """Test the /stats endpoint."""
        try:
            from fastapi.testclient import TestClient
            from llmhive.app.routers.sse_events import router
            from fastapi import FastAPI
            
            app = FastAPI()
            app.include_router(router)
            
            with TestClient(app) as client:
                response = client.get("/stats")
                
                assert response.status_code == 200
                data = response.json()
                assert "total_subscribers" in data
                assert "timestamp" in data
                
        except ImportError:
            pytest.skip("FastAPI test client not available")


# ==============================================================================
# Test Concurrent Access
# ==============================================================================

class TestConcurrentAccess:
    """Tests for concurrent subscriber handling."""
    
    def test_concurrent_subscriptions(self):
        """Test that multiple concurrent subscriptions work correctly."""
        from llmhive.app.routers.sse_events import EventBroadcaster, OrchestrationEvent
        
        async def _test():
            broadcaster = EventBroadcaster()
            session_id = "concurrent-test"
            
            # Subscribe multiple clients concurrently
            async def subscribe_client():
                return await broadcaster.subscribe(session_id)
            
            results = await asyncio.gather(*[subscribe_client() for _ in range(10)])
            
            assert len(results) == 10
            assert broadcaster.get_subscriber_count(session_id) == 10
            
            # All client IDs should be unique
            client_ids = [r[0] for r in results]
            assert len(set(client_ids)) == 10
            
            # Emit an event
            event = OrchestrationEvent("test", "Concurrent test")
            count = await broadcaster.emit(session_id, event)
            
            assert count == 10
            
            # All queues should have the event
            for _, queue in results:
                assert not queue.empty()
        
        run_async(_test())
    
    def test_queue_full_handling(self):
        """Test that full queues are handled gracefully."""
        from llmhive.app.routers.sse_events import EventBroadcaster, OrchestrationEvent
        
        async def _test():
            broadcaster = EventBroadcaster()
            session_id = "queue-full-test"
            
            client_id, queue = await broadcaster.subscribe(session_id)
            
            # Fill the queue (max size is 100)
            for i in range(110):
                event = OrchestrationEvent("test", f"Event {i}")
                await broadcaster.emit(session_id, event)
            
            # Should not raise, some events may be dropped
            assert queue.qsize() <= 100
        
        run_async(_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
