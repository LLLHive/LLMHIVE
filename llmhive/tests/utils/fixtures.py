"""Test fixtures and utilities for LLMHive testing."""
from __future__ import annotations

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock

from llmhive.app.config import settings
from llmhive.app.database import get_db
from llmhive.app.orchestrator import Orchestrator
from llmhive.app.models import User, MemoryEntry, KnowledgeDocument


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_user():
    """Mock user object."""
    user = Mock(spec=User)
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Mock admin user object."""
    user = Mock(spec=User)
    user.id = "admin-user-123"
    user.email = "admin@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def sample_prompt():
    """Sample user prompt for testing."""
    return "What is the capital of France?"


@pytest.fixture
def complex_prompt():
    """Complex multi-step prompt for testing."""
    return """
    I need to:
    1. Write a Python function to calculate fibonacci numbers
    2. Test it with various inputs
    3. Explain how it works
    4. Optimize it for performance
    """


@pytest.fixture
def ambiguous_prompt():
    """Ambiguous prompt for clarification testing."""
    return "Tell me about it."


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    return {
        "content": "The capital of France is Paris.",
        "model": "gpt-4",
        "tokens_used": 50,
        "confidence": 0.95,
    }


@pytest.fixture
def mock_multiple_responses():
    """Mock multiple LLM responses for aggregation testing."""
    return [
        {
            "content": "The capital of France is Paris.",
            "model": "gpt-4",
            "confidence": 0.95,
        },
        {
            "content": "Paris is the capital city of France.",
            "model": "claude-3",
            "confidence": 0.92,
        },
        {
            "content": "France's capital is Paris.",
            "model": "gemini-pro",
            "confidence": 0.90,
        },
    ]


@pytest.fixture
def conflicting_responses():
    """Mock conflicting responses for critique testing."""
    return [
        {
            "content": "The capital of France is Paris.",
            "model": "gpt-4",
            "confidence": 0.95,
        },
        {
            "content": "The capital of France is Lyon.",
            "model": "claude-3",
            "confidence": 0.88,
        },
    ]


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator instance."""
    orchestrator = Mock(spec=Orchestrator)
    orchestrator.providers = {
        "openai": Mock(),
        "anthropic": Mock(),
        "google": Mock(),
    }
    orchestrator.orchestrate = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_memory_entry():
    """Mock memory entry."""
    entry = Mock(spec=MemoryEntry)
    entry.id = "mem-123"
    entry.user_id = "test-user-123"
    entry.content = "Previous conversation about France"
    entry.embedding = [0.1] * 1536
    return entry


@pytest.fixture
def mock_knowledge_document():
    """Mock knowledge document."""
    doc = Mock(spec=KnowledgeDocument)
    doc.id = "doc-123"
    doc.user_id = "test-user-123"
    doc.content = "France is a country in Europe. Its capital is Paris."
    doc.embedding = [0.2] * 1536
    return doc


@pytest.fixture
def mock_tool_result():
    """Mock tool execution result."""
    return {
        "status": "success",
        "result": "4",
        "tool": "calculator",
        "execution_time": 0.1,
    }


@pytest.fixture
def large_text_input():
    """Large text input for performance testing."""
    return "A" * 100000  # 100KB of text


@pytest.fixture
def malicious_inputs():
    """Collection of malicious inputs for security testing."""
    return {
        "xss": "<script>alert('XSS')</script>",
        "sql_injection": "'; DROP TABLE users; --",
        "command_injection": "; rm -rf /",
        "path_traversal": "../../../etc/passwd",
        "large_payload": "A" * 1000000,  # 1MB
    }


@pytest.fixture
def event_loop():
    """Event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_api_key():
    """Mock API key for authentication."""
    return "test-api-key-12345"


@pytest.fixture
def mock_session_token():
    """Mock session token."""
    return "session-token-abc123"


@pytest.fixture
def mock_clarification_question():
    """Mock clarification question."""
    return {
        "question": "Which aspect of France would you like to know about?",
        "options": ["Geography", "History", "Culture", "Economy"],
        "round": 1,
    }


@pytest.fixture
def mock_plan():
    """Mock execution plan."""
    return {
        "steps": [
            {"role": "RESEARCH", "task": "Research France"},
            {"role": "ANALYZE", "task": "Analyze information"},
            {"role": "SYNTHESIZE", "task": "Synthesize answer"},
        ],
        "confidence": 0.85,
    }


@pytest.fixture
def mock_fact_check_result():
    """Mock fact-checking result."""
    return {
        "verified": True,
        "sources": ["https://example.com/france"],
        "confidence": 0.92,
        "claims": [
            {
                "claim": "Paris is the capital of France",
                "verified": True,
                "source": "https://example.com/france",
            }
        ],
    }


@pytest.fixture
def performance_metrics():
    """Performance metrics tracking."""
    return {
        "response_time": 0.0,
        "tokens_used": 0,
        "models_called": 0,
        "tools_used": 0,
        "memory_queries": 0,
    }


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings before each test."""
    original_values = {}
    yield
    # Restore original settings if needed


@pytest.fixture
def mock_web_search_result():
    """Mock web search result."""
    return {
        "query": "capital of France",
        "results": [
            {
                "title": "Paris - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Paris",
                "snippet": "Paris is the capital and most populous city of France.",
            }
        ],
        "total_results": 1000,
    }


@pytest.fixture
def mock_vector_search_result():
    """Mock vector search result."""
    return [
        {
            "id": "doc-1",
            "content": "France is a country in Europe.",
            "score": 0.95,
        },
        {
            "id": "doc-2",
            "content": "Paris is the capital of France.",
            "score": 0.92,
        },
    ]


@pytest.fixture
def error_scenarios():
    """Collection of error scenarios for testing."""
    return {
        "network_error": ConnectionError("Network connection failed"),
        "timeout": TimeoutError("Request timed out"),
        "rate_limit": Exception("Rate limit exceeded"),
        "invalid_key": Exception("Invalid API key"),
        "server_error": Exception("Internal server error"),
    }

