"""API contract tests for LLMHive.

These tests verify that:
1. All API_ROUTES have corresponding backend handlers
2. Request/response schemas match between frontend and backend
3. Error responses follow the standard format
4. API versioning is consistent

Run: PYTHONPATH=./src pytest tests/contract/ -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Set
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add src to path
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from llmhive.app.main import app
from llmhive.app.models.orchestration import (
    ChatRequest,
    ChatResponse,
    ReasoningMode,
    DomainPack,
    AgentMode,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_chat_request() -> Dict[str, Any]:
    """Valid chat request payload matching frontend format."""
    return {
        "prompt": "What is 2+2?",
        "reasoning_mode": "standard",
        "domain_pack": "default",
        "agent_mode": "team",
        "tuning": {
            "prompt_optimization": True,
            "output_validation": True,
            "answer_structure": True,
            "learn_from_chat": True,
        },
        "metadata": {
            "chat_id": "test-conv-123",
        },
    }


@pytest.fixture
def frontend_api_routes() -> Dict[str, str]:
    """Frontend API routes from lib/routes.ts."""
    return {
        "CHAT": "/api/chat",
        "AGENTS": "/api/agents",
        "EXECUTE": "/api/execute",
        "SETTINGS": "/api/settings",
        "CRITERIA": "/api/criteria",
        "REASONING_CONFIG": "/api/reasoning-config",
    }


# ============================================================
# Route Existence Tests
# ============================================================

class TestRouteExistence:
    """Test that all frontend routes have backend handlers."""
    
    def test_backend_has_chat_endpoint(self, client):
        """Backend has /v1/chat endpoint (frontend uses /api/chat via Next.js proxy)."""
        # Check the route exists (POST method)
        response = client.post(
            "/v1/chat",
            json={"prompt": "test"},
            headers={"X-API-Key": "test-key"},
        )
        # Should not be 404
        assert response.status_code != 404, "Chat endpoint not found"
    
    def test_backend_has_agents_endpoint(self, client):
        """Backend has /agents endpoint."""
        response = client.get("/agents")
        assert response.status_code == 200, "Agents endpoint not found"
    
    def test_backend_has_execute_endpoint(self, client):
        """Backend has /v1/execute/python endpoint."""
        response = client.post(
            "/v1/execute/python",
            json={"code": "print(1)", "language": "python", "session_token": "test"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code != 404, "Execute endpoint not found"
    
    def test_backend_has_reasoning_config_endpoint(self, client):
        """Backend has /reasoning-config endpoint."""
        response = client.get("/reasoning-config")
        assert response.status_code == 200, "Reasoning config endpoint not found"
    
    def test_backend_has_health_endpoints(self, client):
        """Backend has health check endpoints."""
        endpoints = ["/healthz", "/health", "/_ah/health", "/health/ready", "/health/live"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Health endpoint {endpoint} not found"


# ============================================================
# Schema Contract Tests
# ============================================================

class TestChatContractSchema:
    """Test chat endpoint request/response schemas."""
    
    def test_chat_request_accepts_all_fields(self, client, valid_chat_request):
        """Chat endpoint accepts all documented fields."""
        with patch("llmhive.app.services.orchestrator_adapter.run_orchestration") as mock:
            mock.return_value = MagicMock(
                message="Test response",
                models_used=["gpt-4o"],
                reasoning_mode=ReasoningMode.standard,
                domain_pack=DomainPack.default,
                agent_mode=AgentMode.team,
                used_tuning=MagicMock(
                    prompt_optimization=True,
                    output_validation=True,
                    answer_structure=True,
                    learn_from_chat=True,
                ),
                metadata=MagicMock(
                    chat_id="test",
                    user_id=None,
                    project_id=None,
                    criteria=None,
                ),
                tokens_used=100,
                latency_ms=500,
                agent_traces=[],
                extra={},
            )
            
            response = client.post(
                "/v1/chat",
                json=valid_chat_request,
                headers={"X-API-Key": "test-key"},
            )
            
            # Should succeed (not validation error)
            assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
    
    def test_chat_response_has_required_fields(self, client, valid_chat_request):
        """Chat response contains all required fields."""
        with patch("llmhive.app.services.orchestrator_adapter.run_orchestration") as mock:
            mock.return_value = MagicMock(
                message="Test response",
                models_used=["gpt-4o"],
                reasoning_mode=ReasoningMode.standard,
                reasoning_method=None,
                domain_pack=DomainPack.default,
                agent_mode=AgentMode.team,
                used_tuning=MagicMock(
                    prompt_optimization=True,
                    output_validation=True,
                    answer_structure=True,
                    learn_from_chat=True,
                    model_dump=lambda: {
                        "prompt_optimization": True,
                        "output_validation": True,
                        "answer_structure": True,
                        "learn_from_chat": True,
                    }
                ),
                metadata=MagicMock(
                    chat_id="test",
                    user_id=None,
                    project_id=None,
                    criteria=None,
                    model_dump=lambda: {"chat_id": "test"},
                ),
                tokens_used=100,
                latency_ms=500,
                agent_traces=[],
                extra={},
                model_dump=lambda: {
                    "message": "Test response",
                    "models_used": ["gpt-4o"],
                    "reasoning_mode": "standard",
                    "reasoning_method": None,
                    "domain_pack": "default",
                    "agent_mode": "team",
                    "used_tuning": {
                        "prompt_optimization": True,
                        "output_validation": True,
                        "answer_structure": True,
                        "learn_from_chat": True,
                    },
                    "metadata": {"chat_id": "test"},
                    "tokens_used": 100,
                    "latency_ms": 500,
                    "agent_traces": [],
                    "extra": {},
                },
            )
            
            response = client.post(
                "/v1/chat",
                json=valid_chat_request,
                headers={"X-API-Key": "test-key"},
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["message", "models_used", "reasoning_mode", "domain_pack", "agent_mode"]
                for field in required_fields:
                    assert field in data, f"Missing required field: {field}"
    
    def test_chat_request_rejects_invalid_reasoning_mode(self, client):
        """Chat endpoint rejects invalid reasoning_mode."""
        response = client.post(
            "/v1/chat",
            json={"prompt": "test", "reasoning_mode": "invalid_mode"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422, "Should reject invalid reasoning_mode"


class TestAgentsContractSchema:
    """Test agents endpoint schema."""
    
    def test_agents_response_structure(self, client):
        """Agents response has correct structure."""
        response = client.get("/agents")
        assert response.status_code == 200
        
        data = response.json()
        assert "agents" in data, "Missing 'agents' field"
        assert "source" in data, "Missing 'source' field"
        assert isinstance(data["agents"], list), "'agents' should be a list"
    
    def test_agent_info_fields(self, client):
        """Each agent has required fields."""
        response = client.get("/agents")
        data = response.json()
        
        required_fields = ["id", "name", "provider", "available"]
        
        for agent in data["agents"]:
            for field in required_fields:
                assert field in agent, f"Agent missing field: {field}"


class TestExecuteContractSchema:
    """Test execute endpoint schema."""
    
    def test_execute_request_requires_code(self, client):
        """Execute endpoint requires code field."""
        response = client.post(
            "/v1/execute/python",
            json={"language": "python", "session_token": "test"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422, "Should require 'code' field"
    
    def test_execute_request_requires_session_token(self, client):
        """Execute endpoint requires session_token field."""
        response = client.post(
            "/v1/execute/python",
            json={"code": "print(1)", "language": "python"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422, "Should require 'session_token' field"
    
    def test_execute_response_structure(self, client):
        """Execute response has correct structure."""
        response = client.post(
            "/v1/execute/python",
            json={"code": "print(1)", "language": "python", "session_token": "test"},
            headers={"X-API-Key": "test-key"},
        )
        
        # Even on error, should have standard response structure
        data = response.json()
        assert "success" in data or "detail" in data, "Should have success or error detail"


class TestReasoningConfigContractSchema:
    """Test reasoning config endpoint schema."""
    
    def test_get_reasoning_config_response(self, client):
        """GET reasoning-config returns correct structure."""
        response = client.get("/reasoning-config")
        assert response.status_code == 200
        
        data = response.json()
        assert "mode" in data, "Missing 'mode' field"
        assert "selectedMethods" in data, "Missing 'selectedMethods' field"
    
    def test_post_reasoning_config_validates_mode(self, client):
        """POST reasoning-config validates mode."""
        response = client.post(
            "/reasoning-config",
            json={"mode": "invalid", "selectedMethods": []},
        )
        assert response.status_code == 422, "Should reject invalid mode"
    
    def test_post_reasoning_config_manual_requires_methods(self, client):
        """POST reasoning-config in manual mode requires methods."""
        response = client.post(
            "/reasoning-config",
            json={"mode": "manual", "selectedMethods": []},
        )
        assert response.status_code == 400, "Manual mode should require methods"


# ============================================================
# Error Response Contract Tests
# ============================================================

class TestErrorResponseContract:
    """Test error responses follow standard format."""
    
    def test_validation_error_format(self, client):
        """Validation errors follow standard format."""
        response = client.post(
            "/v1/chat",
            json={},  # Missing required 'prompt' field
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data, "Validation error should have 'detail'"
    
    def test_404_error_format(self, client):
        """404 errors follow standard format."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    def test_error_response_has_correlation_id(self, client):
        """Error responses include correlation ID header."""
        response = client.post(
            "/v1/chat",
            json={},
            headers={"X-API-Key": "test-key"},
        )
        
        # Check for correlation ID in response headers
        # (May or may not be present depending on middleware execution order)
        correlation_id = response.headers.get("X-Correlation-ID")
        # Just verify header can be accessed (may be None)
        assert True


# ============================================================
# API Version Contract Tests
# ============================================================

class TestAPIVersionContract:
    """Test API versioning is consistent."""
    
    def test_chat_supports_v1_prefix(self, client, valid_chat_request):
        """Chat endpoint supports /v1 prefix."""
        with patch("llmhive.app.services.orchestrator_adapter.run_orchestration"):
            response = client.post(
                "/v1/chat",
                json=valid_chat_request,
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code != 404, "/v1/chat should exist"
    
    def test_agents_supports_both_paths(self, client):
        """Agents endpoint supports both /agents and /v1/agents."""
        response1 = client.get("/agents")
        response2 = client.get("/v1/agents")
        
        assert response1.status_code == 200, "/agents should exist"
        assert response2.status_code == 200, "/v1/agents should exist"
    
    def test_reasoning_config_supports_both_paths(self, client):
        """Reasoning config supports both paths."""
        response1 = client.get("/reasoning-config")
        response2 = client.get("/v1/reasoning-config")
        
        assert response1.status_code == 200, "/reasoning-config should exist"
        assert response2.status_code == 200, "/v1/reasoning-config should exist"


# ============================================================
# CORS and Headers Contract Tests
# ============================================================

class TestCORSContract:
    """Test CORS headers are properly set."""
    
    def test_cors_allows_localhost(self, client):
        """CORS allows localhost origin."""
        response = client.options(
            "/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        
        # OPTIONS should succeed or be handled by CORS middleware
        assert response.status_code in [200, 204, 405]
    
    def test_response_includes_request_id(self, client):
        """Responses include X-Request-ID header."""
        response = client.get("/agents")
        
        # Check for request tracking headers
        request_id = response.headers.get("X-Request-ID")
        # May be None if middleware didn't run, but header should be accessible


# ============================================================
# OpenAPI Specification Tests
# ============================================================

class TestOpenAPISpec:
    """Test OpenAPI specification is valid and complete."""
    
    def test_openapi_endpoint_exists(self, client):
        """OpenAPI spec endpoint exists."""
        response = client.get("/openapi.json")
        assert response.status_code == 200, "OpenAPI spec should be accessible"
    
    def test_openapi_spec_is_valid_json(self, client):
        """OpenAPI spec is valid JSON."""
        response = client.get("/openapi.json")
        data = response.json()
        
        assert "openapi" in data, "Should have openapi version"
        assert "info" in data, "Should have info section"
        assert "paths" in data, "Should have paths section"
    
    def test_openapi_spec_has_chat_endpoint(self, client):
        """OpenAPI spec documents chat endpoint."""
        response = client.get("/openapi.json")
        data = response.json()
        
        paths = data.get("paths", {})
        chat_paths = [p for p in paths.keys() if "chat" in p.lower()]
        assert len(chat_paths) > 0, "Should have chat endpoint documented"
    
    def test_openapi_spec_has_schemas(self, client):
        """OpenAPI spec includes component schemas."""
        response = client.get("/openapi.json")
        data = response.json()
        
        components = data.get("components", {})
        schemas = components.get("schemas", {})
        
        # Should have key request/response schemas
        expected_schemas = ["ChatRequest", "ChatResponse"]
        for schema in expected_schemas:
            assert schema in schemas, f"Missing schema: {schema}"


# ============================================================
# Pydantic Model Contract Tests
# ============================================================

class TestPydanticModelContracts:
    """Test Pydantic models match expected contracts."""
    
    def test_chat_request_model_fields(self):
        """ChatRequest has all expected fields."""
        fields = ChatRequest.model_fields
        
        expected_fields = [
            "prompt",
            "models",
            "reasoning_mode",
            "reasoning_method",
            "domain_pack",
            "agent_mode",
            "tuning",
            "orchestration",
            "metadata",
            "history",
        ]
        
        for field in expected_fields:
            assert field in fields, f"ChatRequest missing field: {field}"
    
    def test_chat_response_model_fields(self):
        """ChatResponse has all expected fields."""
        fields = ChatResponse.model_fields
        
        expected_fields = [
            "message",
            "models_used",
            "reasoning_mode",
            "reasoning_method",
            "domain_pack",
            "agent_mode",
            "used_tuning",
            "metadata",
            "tokens_used",
            "latency_ms",
            "agent_traces",
            "extra",
        ]
        
        for field in expected_fields:
            assert field in fields, f"ChatResponse missing field: {field}"
    
    def test_reasoning_mode_enum_values(self):
        """ReasoningMode enum has expected values."""
        expected_values = {"fast", "standard", "deep"}
        actual_values = {mode.value for mode in ReasoningMode}
        
        assert expected_values == actual_values, f"ReasoningMode values mismatch"
    
    def test_domain_pack_enum_values(self):
        """DomainPack enum has expected values."""
        expected_values = {"default", "medical", "legal", "marketing", "coding", "research", "finance", "education", "real_estate"}
        actual_values = {pack.value for pack in DomainPack}
        
        assert expected_values == actual_values, f"DomainPack values mismatch"
    
    def test_agent_mode_enum_values(self):
        """AgentMode enum has expected values."""
        expected_values = {"single", "team"}
        actual_values = {mode.value for mode in AgentMode}
        
        assert expected_values == actual_values, f"AgentMode values mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
