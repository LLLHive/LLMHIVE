"""
Tests for production hardening features:
- Health check endpoint (/healthz)
- Structured JSON logging
- Google Cloud Secret Manager integration
"""
import json
import logging
from io import StringIO
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient


def test_healthz_endpoint_exists():
    """Test that /healthz endpoint is registered and returns correct response."""
    import sys
    sys.path.insert(0, '.')
    from app.app import app as fastapi_app

    client = TestClient(fastapi_app)
    response = client.get('/healthz')

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_head_endpoint():
    """HEAD requests against /healthz should return 200 for Cloud Run probes."""
    import sys
    sys.path.insert(0, '.')
    from app.app import app as fastapi_app

    client = TestClient(fastapi_app)
    response = client.head('/healthz')

    assert response.status_code == 200
    assert not response.content  # HEAD responses should have no body


def test_structured_json_logging():
    """Test that structured JSON logging is configured correctly."""
    import sys
    sys.path.insert(0, '.')
    
    # Import app which sets up logging
    from app.app import app as fastapi_app, logger
    
    # Verify logger exists and has JSON formatter
    assert logger.name == "llmhive"
    assert len(logger.handlers) > 0
    
    # Check if handler has JSON formatter
    handler = logger.handlers[0]
    from pythonjsonlogger import jsonlogger
    assert isinstance(handler.formatter, jsonlogger.JsonFormatter)


def test_secret_manager_integration():
    """Test that Secret Manager integration works correctly."""
    import sys
    sys.path.insert(0, '.')
    from app.app import get_secret
    
    # Mock the secretmanager client
    with patch('app.app.secretmanager.SecretManagerServiceClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.payload.data.decode.return_value = "test_secret_value"
        mock_instance.access_secret_version.return_value = mock_response
        
        # Test get_secret function
        secret = get_secret("test-project", "test-secret")
        
        assert secret == "test_secret_value"
        mock_instance.access_secret_version.assert_called_once()


def test_secret_manager_error_handling():
    """Test that Secret Manager gracefully handles errors."""
    import sys
    sys.path.insert(0, '.')
    from app.app import get_secret
    
    # Mock the secretmanager client to raise an exception
    with patch('app.app.secretmanager.SecretManagerServiceClient') as mock_client:
        mock_client.side_effect = Exception("Connection error")
        
        # Test get_secret function returns empty string on error
        secret = get_secret("test-project", "test-secret")
        
        assert secret == ""


def test_startup_event_configuration():
    """Test that startup event is properly configured to load secrets."""
    import sys
    sys.path.insert(0, '.')
    
    # Import the app module to check startup configuration
    import app.app as app_module
    
    # Verify the startup_event function exists
    assert hasattr(app_module, 'startup_event')
    
    # Verify the get_secret function exists
    assert hasattr(app_module, 'get_secret')
    assert callable(app_module.get_secret)
    
    # Verify the app has the startup event registered
    from app.app import app as fastapi_app
    assert fastapi_app is not None


def test_config_has_project_id():
    """Test that config has PROJECT_ID field for GCP."""
    import sys
    sys.path.insert(0, '.')
    from app.config import settings
    
    assert hasattr(settings, 'PROJECT_ID')
    assert isinstance(settings.PROJECT_ID, str)
    # Should have default value
    assert len(settings.PROJECT_ID) > 0


def test_backward_compatibility_config():
    """Test that config maintains backward compatibility with existing settings."""
    import sys
    sys.path.insert(0, '.')
    from app.config import settings
    
    # Verify all required settings still exist
    required_settings = [
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'TAVILY_API_KEY',
        'MODEL_CONFIG_PATH',
        'PLANNING_MODEL',
        'CRITIQUE_MODEL',
        'SYNTHESIS_MODEL',
        'LOG_LEVEL',
        'APP_NAME',
        'APP_VERSION',
        'PROJECT_ID'
    ]
    
    for setting_name in required_settings:
        assert hasattr(settings, setting_name), f"Missing setting: {setting_name}"


def test_api_routes_preserved():
    """Test that existing API routes are preserved."""
    import sys
    sys.path.insert(0, '.')
    from app.app import app as fastapi_app

    client = TestClient(fastapi_app)

    # Test that /api/health still exists
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint_returns_status():
    """Root URL should return a friendly status payload instead of 404."""
    import sys
    sys.path.insert(0, '.')
    from app.app import app as fastapi_app

    client = TestClient(fastapi_app)
    response = client.get('/')

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["api_health"] == "/api/v1/healthz"


def test_api_v1_healthz_endpoint():
    """Ensure the documented /api/v1/healthz path is available."""
    import sys
    sys.path.insert(0, '.')
    from app.app import app as fastapi_app

    client = TestClient(fastapi_app)
    response = client.get('/api/v1/healthz')

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_orchestration_health_endpoint():
    """The orchestrator health check should also be exposed under /api/v1."""
    import sys
    sys.path.insert(0, '.')
    from app.app import app as fastapi_app

    client = TestClient(fastapi_app)
    response = client.get('/api/v1/orchestration/health')

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
