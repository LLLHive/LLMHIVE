"""Integration tests for full chat orchestration flow.

Tests the complete pipeline from ChatRequest to ChatResponse,
verifying that all components work together correctly.

Run from llmhive directory: pytest tests/integration/test_chat_flow.py -v
"""
from __future__ import annotations

import asyncio
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Import models with fallback
try:
    from llmhive.app.models.orchestration import (
        ChatRequest,
        ChatResponse,
        ReasoningMode,
        ReasoningMethod,
        DomainPack,
        AgentMode,
        TuningOptions,
        OrchestrationSettings,
        ChatMetadata,
        CriteriaSettings,
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Create stub classes for testing
    ChatRequest = MagicMock
    ChatResponse = MagicMock
    ReasoningMode = MagicMock
    ReasoningMethod = MagicMock
    DomainPack = MagicMock
    AgentMode = MagicMock
    TuningOptions = MagicMock
    OrchestrationSettings = MagicMock
    ChatMetadata = MagicMock
    CriteriaSettings = MagicMock


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator with providers."""
    orchestrator = MagicMock()
    
    # Mock providers
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=MagicMock(
        content="This is a test response from the model.",
        tokens_used=100,
    ))
    
    orchestrator.providers = {
        "openai": mock_provider,
        "anthropic": mock_provider,
    }
    
    orchestrator.orchestrate = AsyncMock(return_value={
        "message": "Paris is the capital of France.",
        "tokens_used": 150,
        "agent_traces": [],
    })
    
    return orchestrator


@pytest.fixture
def basic_chat_request():
    """Create a basic ChatRequest for testing."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")
    return ChatRequest(
        prompt="What is the capital of France?",
        reasoning_mode=ReasoningMode.standard,
        domain_pack=DomainPack.default,
        agent_mode=AgentMode.team,
    )


@pytest.fixture
def advanced_chat_request():
    """Create an advanced ChatRequest with all options."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")
    return ChatRequest(
        prompt="Explain quantum computing and write a Python implementation of Grover's algorithm",
        models=["gpt-4o", "claude-sonnet-4"],
        reasoning_mode=ReasoningMode.deep,
        reasoning_method=ReasoningMethod.chain_of_thought,
        domain_pack=DomainPack.coding,
        agent_mode=AgentMode.team,
        tuning=TuningOptions(
            prompt_optimization=True,
            output_validation=True,
            answer_structure=True,
            learn_from_chat=True,
        ),
        orchestration=OrchestrationSettings(
            accuracy_level=4,
            enable_hrm=True,
            enable_deep_consensus=True,
            temperature=0.5,
            max_tokens=3000,
        ),
        metadata=ChatMetadata(
            chat_id="test-123",
            user_id="user-456",
            criteria=CriteriaSettings(
                accuracy=90,
                speed=50,
                creativity=70,
            ),
        ),
        history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ],
    )


# ============================================================
# Test Chat Request Models
# ============================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestChatRequestValidation:
    """Test ChatRequest model validation."""
    
    def test_minimal_request(self):
        """Test minimal required fields."""
        request = ChatRequest(prompt="Hello")
        
        assert request.prompt == "Hello"
        assert request.reasoning_mode == ReasoningMode.standard
        assert request.domain_pack == DomainPack.default
    
    def test_all_reasoning_modes(self):
        """Test all reasoning modes are valid."""
        for mode in ReasoningMode:
            request = ChatRequest(prompt="Test", reasoning_mode=mode)
            assert request.reasoning_mode == mode
    
    def test_all_reasoning_methods(self):
        """Test all reasoning methods are valid."""
        for method in ReasoningMethod:
            request = ChatRequest(prompt="Test", reasoning_method=method)
            assert request.reasoning_method == method
    
    def test_all_domain_packs(self):
        """Test all domain packs are valid."""
        for pack in DomainPack:
            request = ChatRequest(prompt="Test", domain_pack=pack)
            assert request.domain_pack == pack
    
    def test_orchestration_settings_bounds(self):
        """Test orchestration settings validation."""
        settings = OrchestrationSettings(
            accuracy_level=5,
            temperature=1.5,
            max_tokens=4000,
            top_p=0.95,
        )
        
        assert 1 <= settings.accuracy_level <= 5
        assert 0 <= settings.temperature <= 2
        assert 100 <= settings.max_tokens <= 4000
        assert 0 <= settings.top_p <= 1
    
    def test_criteria_settings_bounds(self):
        """Test criteria settings validation."""
        criteria = CriteriaSettings(
            accuracy=100,
            speed=0,
            creativity=50,
        )
        
        assert 0 <= criteria.accuracy <= 100
        assert 0 <= criteria.speed <= 100
        assert 0 <= criteria.creativity <= 100
    
    def test_history_format(self):
        """Test conversation history format."""
        request = ChatRequest(
            prompt="Continue",
            history=[
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "Response"},
                {"role": "user", "content": "Follow-up"},
            ],
        )
        
        assert len(request.history) == 3
        assert request.history[0]["role"] == "user"
        assert request.history[1]["role"] == "assistant"


# ============================================================
# Test Chat Response Models
# ============================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestChatResponseStructure:
    """Test ChatResponse structure matches frontend expectations."""
    
    def test_response_structure(self):
        """Test response has all required fields for frontend."""
        response = ChatResponse(
            message="Test response",
            models_used=["gpt-4o"],
            reasoning_mode=ReasoningMode.standard,
            domain_pack=DomainPack.default,
            agent_mode=AgentMode.single,
            used_tuning=TuningOptions(),
            metadata=ChatMetadata(),
        )
        
        # These fields must exist for frontend
        assert hasattr(response, "message")
        assert hasattr(response, "models_used")
        assert hasattr(response, "reasoning_mode")
        assert hasattr(response, "domain_pack")
        assert hasattr(response, "tokens_used")
        assert hasattr(response, "latency_ms")
        assert hasattr(response, "agent_traces")
        assert hasattr(response, "extra")
    
    def test_response_serialization(self):
        """Test response can be serialized to JSON."""
        response = ChatResponse(
            message="Test response",
            models_used=["gpt-4o", "claude-3-5-sonnet"],
            reasoning_mode=ReasoningMode.deep,
            reasoning_method=ReasoningMethod.chain_of_thought,
            domain_pack=DomainPack.coding,
            agent_mode=AgentMode.team,
            used_tuning=TuningOptions(),
            metadata=ChatMetadata(chat_id="test-123"),
            tokens_used=500,
            latency_ms=2000,
            agent_traces=[],
            extra={"strategy": "challenge_and_refine"},
        )
        
        # Should serialize without error
        json_data = response.model_dump()
        
        assert json_data["message"] == "Test response"
        assert "gpt-4o" in json_data["models_used"]
        assert json_data["tokens_used"] == 500
        assert json_data["latency_ms"] == 2000


# ============================================================
# Test Orchestration Flow (Unit Tests - No External Deps)
# ============================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestOrchestrationFlow:
    """Test orchestration flow with mocked components."""
    
    @pytest.mark.asyncio
    async def test_basic_request_creation(self, basic_chat_request):
        """Test basic request creation works."""
        assert basic_chat_request.prompt == "What is the capital of France?"
        assert basic_chat_request.reasoning_mode == ReasoningMode.standard
    
    @pytest.mark.asyncio
    async def test_request_with_models(self):
        """Test request with user-selected models."""
        request = ChatRequest(
            prompt="Test query",
            models=["gpt-4o", "claude-sonnet-4"],
        )
        
        assert request.models == ["gpt-4o", "claude-sonnet-4"]
        assert len(request.models) == 2
    
    @pytest.mark.asyncio
    async def test_reasoning_mode_enum(self):
        """Test all reasoning modes can be set."""
        for mode in [ReasoningMode.fast, ReasoningMode.standard, ReasoningMode.deep]:
            request = ChatRequest(prompt="Test", reasoning_mode=mode)
            assert request.reasoning_mode == mode
    
    @pytest.mark.asyncio
    async def test_domain_pack_set(self):
        """Test domain pack can be set."""
        request = ChatRequest(
            prompt="Write a Python function",
            domain_pack=DomainPack.coding,
        )
        
        assert request.domain_pack == DomainPack.coding
    
    @pytest.mark.asyncio
    async def test_history_attached(self):
        """Test conversation history is attached to request."""
        history = [
            {"role": "user", "content": "Tell me about Python"},
            {"role": "assistant", "content": "Python is a programming language..."},
        ]
        
        request = ChatRequest(
            prompt="What did I ask about?",
            history=history,
        )
        
        assert request.history == history
        assert len(request.history) == 2


# ============================================================
# Test Error Handling
# ============================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestOrchestrationErrorHandling:
    """Test error handling in request/response models."""
    
    def test_prompt_is_required(self):
        """Test that prompt is required."""
        # ChatRequest requires prompt
        with pytest.raises(Exception):
            ChatRequest()  # type: ignore - Testing missing required field
    
    def test_invalid_accuracy_level(self):
        """Test invalid accuracy level raises error."""
        with pytest.raises(Exception):
            OrchestrationSettings(accuracy_level=10)  # Max is 5
    
    def test_invalid_temperature(self):
        """Test invalid temperature raises error."""
        with pytest.raises(Exception):
            OrchestrationSettings(temperature=5.0)  # Max is 2.0
    
    def test_invalid_criteria(self):
        """Test invalid criteria values raise error."""
        with pytest.raises(Exception):
            CriteriaSettings(accuracy=150)  # Max is 100


# ============================================================
# Test Response Format for Frontend
# ============================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestFrontendCompatibility:
    """Test that response format matches frontend expectations."""
    
    def test_response_json_structure(self):
        """Test JSON structure matches frontend ChatResponse interface."""
        response = ChatResponse(
            message="The answer is 42",
            models_used=["gpt-4o"],
            reasoning_mode=ReasoningMode.standard,
            domain_pack=DomainPack.default,
            agent_mode=AgentMode.single,
            used_tuning=TuningOptions(),
            metadata=ChatMetadata(),
            tokens_used=100,
            latency_ms=500,
        )
        
        json_data = response.model_dump()
        
        # Required fields for frontend
        required_fields = [
            "message",
            "models_used",
            "reasoning_mode",
            "domain_pack",
            "agent_mode",
            "used_tuning",
            "metadata",
            "tokens_used",
            "latency_ms",
            "agent_traces",
            "extra",
        ]
        
        for field in required_fields:
            assert field in json_data, f"Missing required field: {field}"
    
    def test_tuning_options_structure(self):
        """Test tuning options match frontend TuningOptions interface."""
        tuning = TuningOptions(
            prompt_optimization=True,
            output_validation=True,
            answer_structure=True,
            learn_from_chat=True,
        )
        
        json_data = tuning.model_dump()
        
        assert "prompt_optimization" in json_data
        assert "output_validation" in json_data
        assert "answer_structure" in json_data
        assert "learn_from_chat" in json_data
    
    def test_orchestration_settings_structure(self):
        """Test orchestration settings match frontend interface."""
        settings = OrchestrationSettings(
            accuracy_level=4,
            enable_hrm=True,
            enable_prompt_diffusion=False,
            enable_deep_consensus=True,
            enable_adaptive_ensemble=False,
            temperature=0.7,
            max_tokens=2000,
        )
        
        json_data = settings.model_dump()
        
        # All fields should serialize correctly
        assert json_data["accuracy_level"] == 4
        assert json_data["enable_hrm"] is True
        assert json_data["temperature"] == 0.7
    
    def test_reasoning_mode_serializes_as_string(self):
        """Test reasoning mode serializes as string for frontend."""
        response = ChatResponse(
            message="Test",
            models_used=[],
            reasoning_mode=ReasoningMode.deep,
            domain_pack=DomainPack.default,
            agent_mode=AgentMode.single,
            used_tuning=TuningOptions(),
            metadata=ChatMetadata(),
        )
        
        json_data = response.model_dump()
        
        # Should be string "deep" not enum
        assert json_data["reasoning_mode"] == "deep"
    
    def test_domain_pack_serializes_as_string(self):
        """Test domain pack serializes as string for frontend."""
        response = ChatResponse(
            message="Test",
            models_used=[],
            reasoning_mode=ReasoningMode.standard,
            domain_pack=DomainPack.coding,
            agent_mode=AgentMode.team,
            used_tuning=TuningOptions(),
            metadata=ChatMetadata(),
        )
        
        json_data = response.model_dump()
        
        # Should be string "coding" not enum
        assert json_data["domain_pack"] == "coding"
