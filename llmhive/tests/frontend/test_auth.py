"""Tests for user authentication and sessions."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from llmhive.app.auth import verify_api_key, optional_api_key


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user object."""
    user = Mock()
    user.id = "admin-user-123"
    user.email = "admin@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def valid_api_key():
    """Provide a valid test API key."""
    return "test-api-key-12345"


# ==============================================================================
# API Key Authentication Tests
# ==============================================================================

class TestVerifyApiKey:
    """Test verify_api_key function."""
    
    def test_valid_api_key_returns_authenticated(self, valid_api_key):
        """Test authentication with valid API key."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            result = verify_api_key(provided_key=valid_api_key)
            assert result == "authenticated"
    
    def test_invalid_api_key_raises_401(self, valid_api_key):
        """Test authentication with invalid API key raises 401."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(provided_key="wrong-key")
            
            assert exc_info.value.status_code == 401
            assert "Invalid API Key" in exc_info.value.detail
    
    def test_missing_api_key_raises_401(self, valid_api_key):
        """Test authentication without API key raises 401."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(provided_key=None)
            
            assert exc_info.value.status_code == 401
    
    def test_no_api_key_configured_allows_all(self):
        """Test that requests are allowed when no API_KEY is configured."""
        # Remove API_KEY from environment
        env_without_key = {k: v for k, v in os.environ.items() if k != "API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            result = verify_api_key(provided_key=None)
            assert result == "unauthenticated-allowed"
    
    def test_no_api_key_configured_with_key_provided(self, valid_api_key):
        """Test that provided key is accepted when no API_KEY configured."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            # Should still allow since no API_KEY is required
            result = verify_api_key(provided_key=valid_api_key)
            assert result == "unauthenticated-allowed"
    
    def test_empty_api_key_header(self, valid_api_key):
        """Test authentication with empty API key header."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(provided_key="")
            
            # Empty string is falsy, should be treated as missing
            assert exc_info.value.status_code == 401


# ==============================================================================
# Optional API Key Tests
# ==============================================================================

class TestOptionalApiKey:
    """Test optional_api_key function."""
    
    def test_valid_key_returns_authenticated(self, valid_api_key):
        """Test optional auth with valid key."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            result = optional_api_key(provided_key=valid_api_key)
            assert result == "authenticated"
    
    def test_missing_key_returns_anonymous(self, valid_api_key):
        """Test optional auth without key returns anonymous."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            result = optional_api_key(provided_key=None)
            assert result == "anonymous"
    
    def test_invalid_key_returns_anonymous(self, valid_api_key):
        """Test optional auth with invalid key returns anonymous."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            # Invalid key should fall back to anonymous (not raise)
            result = optional_api_key(provided_key="wrong-key")
            assert result == "anonymous"
    
    def test_no_api_key_configured(self):
        """Test optional auth when no API_KEY configured."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            # Should return something (either anonymous or unauthenticated-allowed)
            result = optional_api_key(provided_key=None)
            assert result in ("anonymous", "unauthenticated-allowed")


# ==============================================================================
# Role-Based Access Tests
# ==============================================================================

class TestRoleBasedAccess:
    """Test role-based access control patterns."""
    
    def test_admin_user_has_admin_role(self, mock_admin_user):
        """Test admin user has admin role."""
        assert mock_admin_user.role == "admin"
    
    def test_standard_user_has_user_role(self, mock_user):
        """Test standard user has user role."""
        assert mock_user.role == "user"
        assert mock_user.role != "admin"
    
    def test_role_check_pattern(self, mock_user, mock_admin_user):
        """Test typical role check pattern."""
        
        def check_admin_access(user):
            """Check if user has admin access."""
            if user.role != "admin":
                raise HTTPException(status_code=403, detail="Forbidden")
            return True
        
        # Admin should have access
        assert check_admin_access(mock_admin_user) is True
        
        # Regular user should be denied
        with pytest.raises(HTTPException) as exc_info:
            check_admin_access(mock_user)
        assert exc_info.value.status_code == 403


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestAuthErrorHandling:
    """Test error handling in authentication."""
    
    def test_clear_error_messages(self, valid_api_key):
        """Test error messages are clear and user-friendly."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(provided_key="invalid")
            
            error_detail = exc_info.value.detail
            # Should be concise
            assert len(error_detail) < 100
            # Should not expose the actual key
            assert valid_api_key not in error_detail
    
    def test_no_sensitive_info_in_error(self, valid_api_key):
        """Test no sensitive information is exposed in errors."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(provided_key="wrong-key")
            
            error_detail = exc_info.value.detail.lower()
            # Should not contain the actual API key
            assert valid_api_key.lower() not in error_detail
            assert "wrong-key" not in error_detail


# ==============================================================================
# Edge Cases Tests
# ==============================================================================

class TestAuthEdgeCases:
    """Test edge cases in authentication."""
    
    def test_whitespace_only_key(self, valid_api_key):
        """Test handling of whitespace-only API key."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            with pytest.raises(HTTPException):
                verify_api_key(provided_key="   ")
    
    def test_key_with_special_characters(self):
        """Test API key with special characters."""
        special_key = "key-with-special_chars!@#$%"
        with patch.dict(os.environ, {"API_KEY": special_key}):
            result = verify_api_key(provided_key=special_key)
            assert result == "authenticated"
    
    def test_very_long_key(self):
        """Test very long API key."""
        long_key = "k" * 1000
        with patch.dict(os.environ, {"API_KEY": long_key}):
            result = verify_api_key(provided_key=long_key)
            assert result == "authenticated"
    
    def test_unicode_key(self):
        """Test API key with unicode characters."""
        unicode_key = "test-key-🔐-secret"
        with patch.dict(os.environ, {"API_KEY": unicode_key}):
            result = verify_api_key(provided_key=unicode_key)
            assert result == "authenticated"
    
    def test_case_sensitive_comparison(self, valid_api_key):
        """Test that key comparison is case-sensitive."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            # Uppercase version should fail
            with pytest.raises(HTTPException):
                verify_api_key(provided_key=valid_api_key.upper())


# ==============================================================================
# Security Tests
# ==============================================================================

class TestAuthSecurity:
    """Test security aspects of authentication."""
    
    @pytest.mark.skip(reason="Timing tests are inherently flaky and not reliable in CI")
    def test_timing_attack_resistance(self, valid_api_key):
        """Test that auth doesn't leak timing information.
        
        Note: This test is skipped because timing measurements are inherently
        unreliable in automated test environments due to system variability.
        """
        import time
        
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            # Measure time for valid key
            start = time.perf_counter()
            try:
                verify_api_key(provided_key=valid_api_key)
            except HTTPException:
                pass
            valid_time = time.perf_counter() - start
            
            # Measure time for invalid key of same length
            wrong_key = "x" * len(valid_api_key)
            start = time.perf_counter()
            try:
                verify_api_key(provided_key=wrong_key)
            except HTTPException:
                pass
            invalid_time = time.perf_counter() - start
            
            # Times should be similar (within 100x - very lenient due to variability)
            assert invalid_time < valid_time * 100
    
    def test_constant_error_message(self, valid_api_key):
        """Test that error message is constant regardless of reason."""
        with patch.dict(os.environ, {"API_KEY": valid_api_key}):
            # Missing key error
            try:
                verify_api_key(provided_key=None)
            except HTTPException as e:
                missing_error = e.detail
            
            # Wrong key error
            try:
                verify_api_key(provided_key="wrong")
            except HTTPException as e:
                wrong_error = e.detail
            
            # Error messages should be the same (to not leak info)
            assert missing_error == wrong_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
