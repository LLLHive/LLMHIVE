"""Tests for Dialogue System.

These tests verify:
1. Ambiguity detection
2. Clarification handling
3. Suggestion generation
4. Task scheduling
5. Dialogue manager integration
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Import modules under test
from llmhive.app.dialogue.ambiguity import (
    AmbiguityDetector,
    AmbiguityResult,
    AmbiguityType,
    detect_ambiguity,
)
from llmhive.app.dialogue.clarification import (
    ClarificationHandler,
    ClarificationRequest,
    ClarificationState,
    ParsedResponse,
)
from llmhive.app.dialogue.suggestions import (
    SuggestionEngine,
    Suggestion,
    SuggestionType,
    SuggestionConfig,
)
from llmhive.app.dialogue.scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskStatus,
    TaskType,
    parse_time_expression,
    parse_reminder_request,
)
from llmhive.app.dialogue.manager import (
    DialogueManager,
    DialogueResult,
    DialogueState,
    PreProcessResult,
)


# ==============================================================================
# Ambiguity Detection Tests
# ==============================================================================

class TestAmbiguityDetector:
    """Tests for AmbiguityDetector."""
    
    @pytest.fixture
    def detector(self):
        return AmbiguityDetector(sensitivity=0.3)
    
    def test_detect_vague_reference(self, detector):
        """Test detecting vague references."""
        result = detector.detect("What is it?")
        
        assert result.is_ambiguous
        assert AmbiguityType.VAGUE_REFERENCE in result.ambiguity_types
    
    def test_detect_broad_topic(self, detector):
        """Test detecting broad topics."""
        result = detector.detect("Tell me about the law")
        
        assert result.is_ambiguous
        assert len(result.clarifying_questions) > 0
    
    def test_detect_python_ambiguity(self, detector):
        """Test detecting Python ambiguity."""
        result = detector.detect("What is Python?")
        
        # Should detect multiple meanings
        assert result.is_ambiguous
        assert any("programming" in q.lower() or "snake" in q.lower() 
                  for q in result.clarifying_questions)
    
    def test_detect_incomplete_question(self, detector):
        """Test detecting incomplete questions."""
        result = detector.detect("Tell me about")
        
        assert result.is_ambiguous
        assert AmbiguityType.INCOMPLETE_QUESTION in result.ambiguity_types
    
    def test_clear_question_not_ambiguous(self, detector):
        """Test clear questions are not flagged."""
        result = detector.detect("What is the capital of France?")
        
        # Clear factual question should not be ambiguous
        assert not result.is_ambiguous or result.confidence < 0.5
    
    def test_short_query_ambiguous(self, detector):
        """Test very short queries are ambiguous."""
        result = detector.detect("hi")
        
        assert result.is_ambiguous
    
    def test_context_dependent(self, detector):
        """Test context-dependent responses."""
        result = detector.detect("yes", conversation_context=None)
        
        assert result.is_ambiguous
        assert AmbiguityType.MISSING_CONTEXT in result.ambiguity_types


# ==============================================================================
# Clarification Handler Tests
# ==============================================================================

class TestClarificationHandler:
    """Tests for ClarificationHandler."""
    
    @pytest.fixture
    def handler(self):
        return ClarificationHandler(max_clarification_attempts=3)
    
    def test_parse_clarify_tags(self, handler):
        """Test parsing [CLARIFY] tags."""
        response = """[CLARIFY]Which Python library are you interested in?
- NumPy for numerical computing
- Pandas for data analysis
- Flask for web development[/CLARIFY]"""
        
        result = handler.parse_response(response)
        
        assert result.needs_clarification
        assert "Which Python library" in result.clarification_question
        assert len(result.clarification_options) > 0
    
    def test_parse_inline_clarify(self, handler):
        """Test parsing inline [CLARIFY: ...] tags."""
        response = "I need more info. [CLARIFY: Which version are you using?]"
        
        result = handler.parse_response(response)
        
        assert result.needs_clarification
        assert "version" in result.clarification_question.lower()
    
    def test_parse_no_clarification(self, handler):
        """Test response without clarification."""
        response = "The capital of France is Paris."
        
        result = handler.parse_response(response)
        
        assert not result.needs_clarification
        assert result.clean_response == response
    
    def test_create_clarification(self, handler):
        """Test creating clarification request."""
        request = handler.create_clarification(
            session_id="session1",
            original_query="Tell me about Python",
            clarification_question="Programming language or snake?",
        )
        
        assert request.state == ClarificationState.AWAITING_RESPONSE
        assert handler.has_pending("session1")
    
    def test_resolve_clarification(self, handler):
        """Test resolving clarification."""
        handler.create_clarification(
            session_id="session1",
            original_query="Tell me about Python",
            clarification_question="Which one?",
        )
        
        request = handler.resolve_clarification("session1", "The programming language")
        
        assert request is not None
        assert request.state == ClarificationState.RESOLVED
        assert request.user_response == "The programming language"
        assert not handler.has_pending("session1")
    
    def test_build_clarified_query(self, handler):
        """Test building clarified query."""
        clarified = handler.build_clarified_query(
            original_query="Tell me about Python",
            clarification_response="The programming language",
        )
        
        assert "Python" in clarified
        assert "programming language" in clarified
    
    def test_skip_clarification(self, handler):
        """Test skipping clarification."""
        handler.create_clarification(
            session_id="session1",
            original_query="Test",
            clarification_question="Test?",
        )
        
        request = handler.skip_clarification("session1")
        
        assert request.state == ClarificationState.SKIPPED
        assert not handler.has_pending("session1")


# ==============================================================================
# Suggestion Engine Tests
# ==============================================================================

class TestSuggestionEngine:
    """Tests for SuggestionEngine."""
    
    @pytest.fixture
    def engine(self):
        config = SuggestionConfig(
            enabled=True,
            suggestion_probability=1.0,  # Always suggest for testing
            free_tier_enabled=True,
            pro_tier_enabled=True,
        )
        return SuggestionEngine(config)
    
    def test_parse_suggest_tags(self, engine):
        """Test parsing [SUGGEST] tags."""
        response = """The weather is sunny.

[SUGGEST]Would you like a 5-day forecast?[/SUGGEST]"""
        
        clean, suggestions = engine.parse_suggestions(response)
        
        assert "5-day forecast" not in clean
        assert len(suggestions) == 1
        assert "forecast" in suggestions[0].text
    
    def test_parse_multiple_suggestions(self, engine):
        """Test parsing multiple suggestions."""
        response = """Here's the code.

[SUGGEST]Want me to add error handling?[/SUGGEST]
[SUGGEST]I can show alternative implementations.[/SUGGEST]"""
        
        clean, suggestions = engine.parse_suggestions(response)
        
        assert len(suggestions) == 2
    
    def test_generate_suggestions_weather(self, engine):
        """Test generating suggestions for weather domain."""
        suggestions = engine.generate_suggestions(
            query="What's the weather in Tokyo?",
            response="It's sunny with 22°C.",
            user_tier="pro",
            domain="weather",
        )
        
        assert len(suggestions) > 0
    
    def test_generate_suggestions_respects_tier(self):
        """Test tier-based suggestion control."""
        config = SuggestionConfig(
            enabled=True,
            suggestion_probability=1.0,
            free_tier_enabled=False,
            pro_tier_enabled=True,
        )
        engine = SuggestionEngine(config)
        
        # Free tier - no suggestions
        suggestions = engine.generate_suggestions(
            query="Test",
            response="Response",
            user_tier="free",
        )
        assert len(suggestions) == 0
        
        # Pro tier - get suggestions
        suggestions = engine.generate_suggestions(
            query="Test",
            response="Response",
            user_tier="pro",
        )
        # May or may not have suggestions based on domain
    
    def test_session_limit(self, engine):
        """Test suggestion session limit."""
        engine.config.max_per_session = 2
        
        # Generate suggestions until limit
        for i in range(5):
            engine.generate_suggestions(
                query=f"Query {i}",
                response="Response",
                session_id="test_session",
                user_tier="pro",
            )
        
        # Should hit limit
        suggestions = engine.generate_suggestions(
            query="Final query",
            response="Response",
            session_id="test_session",
            user_tier="pro",
        )
        
        # After limit, no more suggestions
        assert len(suggestions) == 0


# ==============================================================================
# Task Scheduler Tests
# ==============================================================================

class TestTimeParser:
    """Tests for time expression parsing."""
    
    def test_parse_minutes(self):
        """Test parsing minutes."""
        result = parse_time_expression("in 5 minutes")
        assert result == timedelta(minutes=5)
        
        result = parse_time_expression("in 30 mins")
        assert result == timedelta(minutes=30)
    
    def test_parse_hours(self):
        """Test parsing hours."""
        result = parse_time_expression("in 2 hours")
        assert result == timedelta(hours=2)
        
        result = parse_time_expression("in 1 hour")
        assert result == timedelta(hours=1)
    
    def test_parse_days(self):
        """Test parsing days."""
        result = parse_time_expression("in 3 days")
        assert result == timedelta(days=3)
    
    def test_parse_special_expressions(self):
        """Test parsing special expressions."""
        result = parse_time_expression("tomorrow")
        assert result == timedelta(days=1)
        
        result = parse_time_expression("in half an hour")
        assert result == timedelta(minutes=30)
    
    def test_parse_reminder_request(self):
        """Test parsing full reminder requests."""
        result = parse_reminder_request("remind me in 1 hour to check the oven")
        
        assert result is not None
        delay, task = result
        assert delay == timedelta(hours=1)
        assert "check the oven" in task


class TestTaskScheduler:
    """Tests for TaskScheduler."""
    
    @pytest.fixture
    def scheduler(self):
        return TaskScheduler(check_interval=0.1)
    
    @pytest.mark.asyncio
    async def test_schedule_reminder(self, scheduler):
        """Test scheduling a reminder."""
        task = await scheduler.schedule_reminder(
            user_id="user1",
            message="Test reminder",
            delay_seconds=60,
        )
        
        assert task.status == TaskStatus.PENDING
        assert task.user_id == "user1"
        assert "Test reminder" in task.message
    
    @pytest.mark.asyncio
    async def test_schedule_at_time(self, scheduler):
        """Test scheduling at specific time."""
        run_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        task = await scheduler.schedule_at(
            user_id="user1",
            message="Meeting",
            run_at=run_at,
        )
        
        assert task.run_at == run_at
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, scheduler):
        """Test cancelling a task."""
        task = await scheduler.schedule_reminder(
            user_id="user1",
            message="Cancel me",
            delay_seconds=3600,
        )
        
        success = await scheduler.cancel_task(task.id)
        
        assert success
        assert scheduler.get_task(task.id).status == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_get_user_tasks(self, scheduler):
        """Test getting user's tasks."""
        await scheduler.schedule_reminder("user1", "Task 1", 60)
        await scheduler.schedule_reminder("user1", "Task 2", 120)
        await scheduler.schedule_reminder("user2", "Task 3", 60)
        
        user1_tasks = scheduler.get_user_tasks("user1")
        
        assert len(user1_tasks) == 2
    
    @pytest.mark.asyncio
    async def test_task_execution(self, scheduler):
        """Test task execution callback."""
        executed_tasks = []
        
        async def callback(task):
            executed_tasks.append(task)
        
        scheduler.on_task_due(callback)
        await scheduler.start()
        
        # Schedule task for immediate execution
        task = await scheduler.schedule_reminder(
            user_id="user1",
            message="Execute now",
            delay_seconds=0,
        )
        
        # Wait for execution
        await asyncio.sleep(0.5)
        await scheduler.stop()
        
        assert len(executed_tasks) == 1
        assert executed_tasks[0].id == task.id
        assert executed_tasks[0].status == TaskStatus.COMPLETED


# ==============================================================================
# Dialogue Manager Tests
# ==============================================================================

class TestDialogueManager:
    """Tests for DialogueManager."""
    
    @pytest.fixture
    def manager(self):
        return DialogueManager(
            enable_clarification=True,
            enable_suggestions=True,
            enable_scheduling=True,
        )
    
    @pytest.mark.asyncio
    async def test_pre_process_clear_query(self, manager):
        """Test pre-processing clear query."""
        result = await manager.pre_process_query(
            query="What is the capital of France?",
            session_id="session1",
        )
        
        assert result.should_proceed
        assert not result.needs_clarification
    
    @pytest.mark.asyncio
    async def test_pre_process_reminder(self, manager):
        """Test pre-processing reminder request."""
        result = await manager.pre_process_query(
            query="Remind me in 1 hour to call mom",
            session_id="session1",
            user_id="user1",
        )
        
        assert result.is_schedule_request
        assert result.schedule_info is not None
        assert "call mom" in result.schedule_info["message"]
    
    @pytest.mark.asyncio
    async def test_process_response_with_clarification(self, manager):
        """Test processing response with clarification."""
        response = """[CLARIFY]Which programming language are you asking about?
- Python
- JavaScript
- Java[/CLARIFY]"""
        
        result = await manager.process_response(
            response=response,
            query="How do I write a function?",
            session_id="session1",
        )
        
        assert result.needs_clarification
        assert result.state == DialogueState.AWAITING_CLARIFICATION
    
    @pytest.mark.asyncio
    async def test_process_response_with_suggestions(self, manager):
        """Test processing response with suggestions."""
        response = """The weather is sunny.
        
[SUGGEST]Would you like a 5-day forecast?[/SUGGEST]"""
        
        result = await manager.process_response(
            response=response,
            query="What's the weather?",
            session_id="session1",
            user_tier="pro",
        )
        
        assert not result.needs_clarification
        assert len(result.suggestions) > 0
        assert "sunny" in result.final_response
    
    @pytest.mark.asyncio
    async def test_clarification_flow(self, manager):
        """Test full clarification flow."""
        # First query - might need clarification
        pre1 = await manager.pre_process_query(
            query="Tell me about it",
            session_id="session1",
        )
        
        # Assume clarification was needed and user responds
        if not pre1.should_proceed:
            # User provides clarification
            pre2 = await manager.pre_process_query(
                query="I mean the Python programming language",
                session_id="session1",
            )
            
            assert pre2.should_proceed
            assert "Python" in pre2.modified_query
    
    def test_get_session_state(self, manager):
        """Test getting session state."""
        state = manager.get_session_state("new_session")
        
        assert state == DialogueState.NORMAL
    
    def test_clear_session(self, manager):
        """Test clearing session state."""
        manager._session_states["session1"] = DialogueState.AWAITING_CLARIFICATION
        manager.clear_session("session1")
        
        assert manager.get_session_state("session1") == DialogueState.NORMAL


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestDialogueIntegration:
    """Integration tests for dialogue system."""
    
    @pytest.mark.asyncio
    async def test_full_dialogue_flow(self):
        """Test complete dialogue flow."""
        manager = DialogueManager()
        
        # Clear question - should proceed
        pre = await manager.pre_process_query(
            query="What is machine learning?",
            session_id="test_session",
        )
        assert pre.should_proceed
        
        # Simulate LLM response with suggestion
        response = """Machine learning is a subset of AI that enables 
systems to learn from data.

[SUGGEST]Would you like examples of ML applications?[/SUGGEST]"""
        
        result = await manager.process_response(
            response=response,
            query="What is machine learning?",
            session_id="test_session",
            user_tier="pro",
        )
        
        assert "Machine learning" in result.final_response
        assert not result.needs_clarification
    
    @pytest.mark.asyncio
    async def test_reminder_flow(self):
        """Test reminder scheduling flow."""
        manager = DialogueManager()
        
        # Schedule reminder
        pre = await manager.pre_process_query(
            query="Remind me in 5 minutes to take a break",
            session_id="test_session",
            user_id="user1",
        )
        
        assert pre.is_schedule_request
        assert pre.schedule_info is not None
        assert "take a break" in pre.schedule_info["message"]
    
    @pytest.mark.asyncio
    async def test_ambiguous_to_clear_flow(self):
        """Test flow from ambiguous to clarified query."""
        manager = DialogueManager()
        
        # Step 1: Ambiguous query
        pre1 = await manager.pre_process_query(
            query="What is it?",
            session_id="test_session",
        )
        
        # This might trigger clarification
        if not pre1.should_proceed:
            assert pre1.needs_clarification
            
            # Step 2: User clarifies
            pre2 = await manager.pre_process_query(
                query="The weather in Tokyo",
                session_id="test_session",
            )
            
            # Should now proceed with clarified context
            assert pre2.should_proceed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

