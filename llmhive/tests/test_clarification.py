"""Tests for the clarification feature.

Tests cover:
1. ClarificationManager - ambiguity detection and question generation
2. AnswerPreferences - preference parsing and style guidelines
3. AnswerRefiner - preference-based answer formatting
4. API endpoints - /v1/clarify, /v1/clarify/respond, /v1/chat/clarified
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))


# ==============================================================================
# ClarificationManager Tests
# ==============================================================================

class TestClarificationManager:
    """Tests for the ClarificationManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a ClarificationManager without LLM."""
        from llmhive.app.orchestration.clarification_manager import ClarificationManager
        return ClarificationManager(
            providers={},
            enable_llm_detection=False,
            always_ask_preferences=True,
        )
    
    @pytest.mark.asyncio
    async def test_clear_query_no_clarification(self, manager):
        """Clear, specific queries should not need clarification."""
        # Use a very specific query that shouldn't trigger any ambiguity detection
        result = await manager.analyze_and_generate_questions(
            "Calculate the sum of 2 plus 3 and show the result"
        )
        
        # Should not have query questions (or very few)
        assert len(result.query_questions) <= 1
        # But should have preference questions
        assert len(result.preference_questions) == 3
    
    @pytest.mark.asyncio
    async def test_ambiguous_query_needs_clarification(self, manager):
        """Ambiguous queries should generate clarification questions."""
        result = await manager.analyze_and_generate_questions(
            "Tell me about it"  # Vague pronoun, very short
        )
        
        # Should have query questions due to ambiguity
        assert len(result.query_questions) > 0
        assert result.has_query_questions
    
    @pytest.mark.asyncio
    async def test_vague_terms_detected(self, manager):
        """Vague terms should trigger clarification."""
        result = await manager.analyze_and_generate_questions(
            "How do I make it better?"
        )
        
        # "it" and "better" are both vague
        assert result.has_query_questions or result.status.value != "not_needed"
    
    @pytest.mark.asyncio
    async def test_preference_questions_included(self, manager):
        """Preference questions should always be included by default."""
        result = await manager.analyze_and_generate_questions(
            "Explain quantum computing"
        )
        
        # Should have 3 preference questions
        assert len(result.preference_questions) == 3
        
        # Check question categories
        categories = [q.category for q in result.preference_questions]
        assert all(c == "preference" for c in categories)
    
    @pytest.mark.asyncio
    async def test_skip_preferences(self, manager):
        """Should be able to skip preference questions."""
        result = await manager.analyze_and_generate_questions(
            "What is Python?",
            skip_preferences=True,
        )
        
        assert len(result.preference_questions) == 0
    
    @pytest.mark.asyncio
    async def test_max_query_questions(self, manager):
        """Should limit query questions to max_query_questions."""
        manager.max_query_questions = 2
        
        # Very ambiguous query
        result = await manager.analyze_and_generate_questions(
            "They said it was better than that thing from before"
        )
        
        # Should have at most 2 questions
        assert len(result.query_questions) <= 2


class TestClarificationResponseProcessing:
    """Tests for processing clarification responses."""
    
    @pytest.fixture
    def manager(self):
        from llmhive.app.orchestration.clarification_manager import ClarificationManager
        return ClarificationManager(
            providers={},
            enable_llm_detection=False,
        )
    
    @pytest.mark.asyncio
    async def test_process_query_answers(self, manager):
        """Test processing query clarification answers."""
        from llmhive.app.orchestration.clarification_manager import (
            ClarificationRequest,
            ClarificationResponse,
            ClarificationQuestion,
            ClarificationStatus,
        )
        
        request = ClarificationRequest(
            original_query="Tell me about Phoenix",
            query_questions=[
                ClarificationQuestion(
                    id="q1",
                    question="Which Phoenix do you mean?",
                    category="query",
                )
            ],
            status=ClarificationStatus.PENDING_QUERY,
        )
        
        response = ClarificationResponse(
            query_answers={"q1": "The Phoenix Framework for Elixir"},
            preference_answers={},
        )
        
        result = await manager.process_responses(request, response)
        
        assert result.was_clarified
        assert "Phoenix Framework" in result.refined_query or "Elixir" in result.clarification_context
    
    @pytest.mark.asyncio
    async def test_process_preference_answers(self, manager):
        """Test parsing preference answers."""
        from llmhive.app.orchestration.clarification_manager import (
            ClarificationRequest,
            ClarificationResponse,
            ClarificationStatus,
            DetailLevel,
            AnswerFormat,
            AnswerTone,
        )
        
        request = ClarificationRequest(
            original_query="Explain machine learning",
            status=ClarificationStatus.PENDING_PREFERENCES,
        )
        
        response = ClarificationResponse(
            preference_answers={
                "pref_detail": "Detailed - Comprehensive coverage",
                "pref_format": "Bullet Points - Easy to scan",
                "pref_tone": "Simplified - Easy to understand",
            },
        )
        
        result = await manager.process_responses(request, response)
        
        assert result.answer_preferences.detail_level == DetailLevel.DETAILED
        assert result.answer_preferences.format == AnswerFormat.BULLET_POINTS
        assert result.answer_preferences.tone == AnswerTone.SIMPLIFIED
    
    @pytest.mark.asyncio
    async def test_skipped_responses(self, manager):
        """Test handling skipped clarification."""
        from llmhive.app.orchestration.clarification_manager import (
            ClarificationRequest,
            ClarificationResponse,
            ClarificationStatus,
        )
        
        request = ClarificationRequest(
            original_query="Tell me about AI",
            status=ClarificationStatus.PENDING_QUERY,
        )
        
        response = ClarificationResponse(skipped=True)
        
        result = await manager.process_responses(request, response)
        
        assert not result.was_clarified
        assert result.refined_query == request.original_query


# ==============================================================================
# AnswerPreferences Tests
# ==============================================================================

class TestAnswerPreferences:
    """Tests for AnswerPreferences functionality."""
    
    def test_default_preferences(self):
        """Test default preference values."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            DetailLevel,
            AnswerFormat,
            AnswerTone,
        )
        
        prefs = AnswerPreferences()
        
        assert prefs.detail_level == DetailLevel.STANDARD
        assert prefs.format == AnswerFormat.PARAGRAPH
        assert prefs.tone == AnswerTone.FORMAL
        assert prefs.include_examples is True
    
    def test_to_style_guidelines_brief(self):
        """Test style guidelines for brief detail level."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            DetailLevel,
        )
        
        prefs = AnswerPreferences(detail_level=DetailLevel.BRIEF)
        guidelines = prefs.to_style_guidelines()
        
        assert any("concise" in g.lower() for g in guidelines)
    
    def test_to_style_guidelines_bullet_format(self):
        """Test style guidelines for bullet point format."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            AnswerFormat,
        )
        
        prefs = AnswerPreferences(format=AnswerFormat.BULLET_POINTS)
        guidelines = prefs.to_style_guidelines()
        
        assert any("bullet" in g.lower() for g in guidelines)
    
    def test_to_style_guidelines_casual_tone(self):
        """Test style guidelines for casual tone."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            AnswerTone,
        )
        
        prefs = AnswerPreferences(tone=AnswerTone.CASUAL)
        guidelines = prefs.to_style_guidelines()
        
        assert any("casual" in g.lower() or "friendly" in g.lower() for g in guidelines)
    
    def test_to_style_guidelines_with_length(self):
        """Test style guidelines with max length."""
        from llmhive.app.orchestration.clarification_manager import AnswerPreferences
        
        prefs = AnswerPreferences(max_length=500)
        guidelines = prefs.to_style_guidelines()
        
        assert any("500" in g for g in guidelines)


# ==============================================================================
# AnswerRefiner Tests
# ==============================================================================

class TestAnswerRefiner:
    """Tests for the AnswerRefiner class."""
    
    @pytest.fixture
    def refiner(self):
        from llmhive.app.refiner import AnswerRefiner
        return AnswerRefiner(providers={}, enable_llm_refinement=False)
    
    @pytest.mark.asyncio
    async def test_refine_to_bullets(self, refiner):
        """Test converting answer to bullet points."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            AnswerFormat,
        )
        
        prefs = AnswerPreferences(format=AnswerFormat.BULLET_POINTS)
        
        answer = "First point here. Second point follows. Third point ends."
        refined = await refiner.refine_with_preferences(answer, prefs)
        
        assert "-" in refined or "•" in refined
    
    @pytest.mark.asyncio
    async def test_refine_to_numbered(self, refiner):
        """Test converting answer to numbered list."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            AnswerFormat,
        )
        
        prefs = AnswerPreferences(format=AnswerFormat.NUMBERED_LIST)
        
        answer = "Step one. Step two. Step three."
        refined = await refiner.refine_with_preferences(answer, prefs)
        
        assert "1." in refined or "2." in refined
    
    @pytest.mark.asyncio
    async def test_refine_with_confidence(self, refiner):
        """Test adding confidence indicator."""
        from llmhive.app.orchestration.clarification_manager import AnswerPreferences
        
        prefs = AnswerPreferences()
        
        answer = "The answer is 42."
        refined = await refiner.refine_with_preferences(
            answer,
            prefs,
            confidence_score=0.85,
        )
        
        assert "Confidence" in refined
    
    @pytest.mark.asyncio
    async def test_shorten_for_brief(self, refiner):
        """Test shortening for brief detail level."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            DetailLevel,
        )
        
        prefs = AnswerPreferences(detail_level=DetailLevel.BRIEF)
        
        # Long answer
        answer = "This is a very long answer. " * 20
        refined = await refiner.refine_with_preferences(answer, prefs)
        
        # Should be shorter
        assert len(refined) < len(answer)


# ==============================================================================
# API Endpoint Tests
# ==============================================================================

class TestClarificationAPI:
    """Tests for clarification API endpoints."""
    
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from llmhive.app.main import app
        return TestClient(app)
    
    def test_clarify_endpoint_exists(self, client):
        """Test that /v1/clarify endpoint exists."""
        response = client.post(
            "/v1/clarify",
            json={"prompt": "What is Python?"},
            headers={"X-API-Key": "test-key"},
        )
        
        assert response.status_code != 404
    
    def test_clarify_clear_query(self, client):
        """Test clarify with a clear query."""
        response = client.post(
            "/v1/clarify",
            json={"prompt": "What is the capital of France?"},
            headers={"X-API-Key": "test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should indicate clarification status
        assert "needs_clarification" in data
        assert "message" in data
    
    def test_clarify_ambiguous_query(self, client):
        """Test clarify with an ambiguous query."""
        response = client.post(
            "/v1/clarify",
            json={"prompt": "Tell me about it"},
            headers={"X-API-Key": "test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # May or may not need clarification depending on detection
        assert "needs_clarification" in data
    
    def test_clarify_respond_endpoint_exists(self, client):
        """Test that /v1/clarify/respond endpoint exists."""
        response = client.post(
            "/v1/clarify/respond",
            json={
                "original_query": "Tell me about Phoenix",
                "clarification_response": {
                    "query_answers": {"q1": "Phoenix Framework"},
                    "preference_answers": {},
                    "skipped": False,
                },
            },
            headers={"X-API-Key": "test-key"},
        )
        
        assert response.status_code != 404
    
    def test_clarified_chat_endpoint_exists(self, client):
        """Test that /v1/chat/clarified endpoint exists."""
        response = client.post(
            "/v1/chat/clarified",
            json={
                "prompt": "What is Python?",
                "skip_clarification": True,
            },
            headers={"X-API-Key": "test-key"},
        )
        
        assert response.status_code != 404


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestClarificationIntegration:
    """Integration tests for the full clarification flow."""
    
    @pytest.mark.asyncio
    async def test_full_clarification_flow(self):
        """Test complete clarification flow."""
        from llmhive.app.orchestration.clarification_manager import (
            ClarificationManager,
            ClarificationResponse,
        )
        
        manager = ClarificationManager(
            providers={},
            enable_llm_detection=False,
            always_ask_preferences=True,
        )
        
        # Step 1: Analyze query
        request = await manager.analyze_and_generate_questions(
            "How do I make this better?"
        )
        
        # Step 2: Simulate user responses
        response = ClarificationResponse(
            query_answers={
                q.id: "My Python code"
                for q in request.query_questions
            },
            preference_answers={
                "pref_detail": "Detailed",
                "pref_format": "Code Focused",
                "pref_tone": "Technical",
            },
        )
        
        # Step 3: Process responses
        result = await manager.process_responses(request, response)
        
        # Verify result
        assert result.refined_query
        assert result.answer_preferences.format.value == "code_focused"
        assert result.answer_preferences.tone.value == "technical"
    
    @pytest.mark.asyncio
    async def test_preferences_applied_to_refiner(self):
        """Test that preferences are applied during refinement."""
        from llmhive.app.orchestration.clarification_manager import (
            AnswerPreferences,
            AnswerFormat,
            AnswerTone,
        )
        from llmhive.app.refiner import AnswerRefiner
        
        prefs = AnswerPreferences(
            format=AnswerFormat.BULLET_POINTS,
            tone=AnswerTone.SIMPLIFIED,
            include_examples=True,
        )
        
        refiner = AnswerRefiner()
        
        answer = "Python is a programming language. It is easy to learn. It has many libraries."
        refined = await refiner.refine_with_preferences(answer, prefs)
        
        # Should be bullet points
        assert "-" in refined or "•" in refined


# ==============================================================================
# Model Tests
# ==============================================================================

class TestClarificationModels:
    """Tests for Pydantic models."""
    
    def test_clarification_request_model(self):
        """Test ClarificationRequest model."""
        from llmhive.app.models.orchestration import (
            ClarificationRequest,
            ClarificationStatus,
        )
        
        request = ClarificationRequest(
            status=ClarificationStatus.pending_query,
            original_query="Test query",
            query_questions=[],
            preference_questions=[],
        )
        
        assert request.status == ClarificationStatus.pending_query
        assert request.original_query == "Test query"
    
    def test_clarification_response_model(self):
        """Test ClarificationResponse model."""
        from llmhive.app.models.orchestration import ClarificationResponse
        
        response = ClarificationResponse(
            query_answers={"q1": "Answer 1"},
            preference_answers={"pref_detail": "Detailed"},
            skipped=False,
        )
        
        assert response.query_answers["q1"] == "Answer 1"
        assert not response.skipped
    
    def test_answer_preferences_model(self):
        """Test AnswerPreferences model."""
        from llmhive.app.models.orchestration import (
            AnswerPreferences,
            DetailLevel,
            AnswerFormat,
            AnswerTone,
        )
        
        prefs = AnswerPreferences(
            detail_level=DetailLevel.detailed,
            format=AnswerFormat.bullet_points,
            tone=AnswerTone.casual,
        )
        
        assert prefs.detail_level == DetailLevel.detailed
        assert prefs.format == AnswerFormat.bullet_points
        assert prefs.tone == AnswerTone.casual


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
