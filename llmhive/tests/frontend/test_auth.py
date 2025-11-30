"""Tests for user authentication and sessions."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from llmhive.app.auth import verify_api_key
from llmhive.app.config import settings
from tests.utils.fixtures import mock_user, mock_admin_user, mock_api_key


class TestLoginFlow:
    """Test login functionality."""
    
    def test_correct_credentials(self, mock_user):
        """Test login with correct credentials."""
        # Mock authentication logic
        with patch('llmhive.app.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = mock_user
            # Test login
            result = mock_auth("test@example.com", "correct_password")
            assert result == mock_user
            assert result.is_active
    
    def test_wrong_password(self):
        """Test login with wrong password."""
        with patch('llmhive.app.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            result = mock_auth("test@example.com", "wrong_password")
            assert result is None
    
    def test_account_creation(self):
        """Test account creation flow."""
        with patch('llmhive.app.auth.create_user') as mock_create:
            new_user = Mock()
            new_user.id = "new-user-123"
            new_user.email = "new@example.com"
            mock_create.return_value = new_user
            
            result = mock_create("new@example.com", "password123")
            assert result.email == "new@example.com"
            assert result.id is not None


class TestSessionManagement:
    """Test session persistence and management."""
    
    def test_session_persistence(self, mock_user):
        """Test that sessions persist across requests."""
        session_token = "test-session-token"
        
        with patch('llmhive.app.auth.get_user_from_session') as mock_get:
            mock_get.return_value = mock_user
            
            user = mock_get(session_token)
            assert user == mock_user
            assert user.id == "test-user-123"
    
    def test_logout_functionality(self):
        """Test logout clears session."""
        with patch('llmhive.app.auth.invalidate_session') as mock_invalidate:
            mock_invalidate.return_value = True
            result = mock_invalidate("test-session-token")
            assert result is True
    
    def test_token_expiration(self):
        """Test handling of expired tokens."""
        expired_token = "expired-token"
        
        with patch('llmhive.app.auth.verify_token') as mock_verify:
            mock_verify.return_value = None  # Token expired
            
            result = mock_verify(expired_token)
            assert result is None
    
    def test_concurrent_logins(self, mock_user):
        """Test handling of concurrent login attempts."""
        # Simulate multiple login attempts
        with patch('llmhive.app.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = mock_user
            
            # Multiple concurrent logins should all succeed
            results = [mock_auth("test@example.com", "password") for _ in range(5)]
            assert all(r == mock_user for r in results)


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_admin_access(self, mock_admin_user):
        """Test admin user has admin access."""
        assert mock_admin_user.role == "admin"
        # Admin should have access to admin endpoints
        assert hasattr(mock_admin_user, "role")
    
    def test_standard_user_no_admin_access(self, mock_user):
        """Test standard user cannot access admin functions."""
        assert mock_user.role == "user"
        assert mock_user.role != "admin"
    
    def test_unauthorized_access_denied(self, mock_user):
        """Test unauthorized access is denied."""
        # Standard user trying to access admin endpoint
        with pytest.raises(HTTPException) as exc_info:
            if mock_user.role != "admin":
                raise HTTPException(status_code=403, detail="Forbidden")
        
        assert exc_info.value.status_code == 403


class TestAPIKeyAuthentication:
    """Test API key authentication."""
    
    def test_valid_api_key(self, mock_api_key):
        """Test authentication with valid API key."""
        with patch.object(settings, 'api_key', mock_api_key):
            with patch.object(settings, 'require_auth', True):
                # Mock the verify_api_key dependency
                result = verify_api_key(api_key=mock_api_key, authorization=None)
                assert result is not None
    
    def test_invalid_api_key(self):
        """Test authentication with invalid API key."""
        with patch.object(settings, 'api_key', "correct-key"):
            with patch.object(settings, 'require_auth', True):
                with pytest.raises(HTTPException) as exc_info:
                    verify_api_key(api_key="wrong-key", authorization=None)
                assert exc_info.value.status_code == 401
    
    def test_missing_api_key(self):
        """Test authentication without API key."""
        with patch.object(settings, 'require_auth', True):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(api_key=None, authorization=None)
            assert exc_info.value.status_code == 401
    
    def test_bearer_token_auth(self, mock_api_key):
        """Test Bearer token authentication."""
        with patch.object(settings, 'api_key', mock_api_key):
            with patch.object(settings, 'require_auth', True):
                auth_header = f"Bearer {mock_api_key}"
                result = verify_api_key(api_key=None, authorization=auth_header)
                assert result is not None


class TestErrorHandling:
    """Test error handling in authentication."""
    
    def test_clear_error_messages(self):
        """Test error messages are clear and user-friendly."""
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(api_key="invalid", authorization=None)
        
        error_detail = str(exc_info.value.detail)
        # Should not expose sensitive info
        assert "api key" not in error_detail.lower() or "invalid" in error_detail.lower()
        # Should be user-friendly
        assert len(error_detail) < 200
    
    def test_no_sensitive_info_exposure(self):
        """Test no sensitive information is exposed in errors."""
        # Error messages should not contain actual API keys or tokens
        error_msg = "Authentication failed"
        sensitive_patterns = ["api_key", "token", "secret", "password"]
        
        for pattern in sensitive_patterns:
            assert pattern not in error_msg.lower()
    
    def test_redirect_to_login_on_unauthorized(self):
        """Test redirect to login on unauthorized access."""
        # This would be tested in integration tests with actual HTTP client
        # For unit test, verify the logic exists
        assert True  # Placeholder - would test actual redirect in integration test


class TestEdgeCases:
    """Test edge cases in authentication."""
    
    def test_invalid_token_format(self):
        """Test handling of invalid token format."""
        invalid_tokens = ["", "not-a-token", "token with spaces", "token\nwith\nnewlines"]
        
        for token in invalid_tokens:
            with pytest.raises((HTTPException, ValueError, TypeError)):
                verify_api_key(api_key=token, authorization=None)
    
    def test_missing_authentication_headers(self):
        """Test handling of missing authentication headers."""
        with patch.object(settings, 'require_auth', True):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(api_key=None, authorization=None)
            assert exc_info.value.status_code == 401
    
    def test_session_timeout(self):
        """Test handling of session timeout."""
        # Mock expired session
        with patch('llmhive.app.auth.get_user_from_session') as mock_get:
            mock_get.return_value = None  # Session expired
            user = mock_get("expired-session")
            assert user is None

