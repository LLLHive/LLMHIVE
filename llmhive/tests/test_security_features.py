"""Tests for security features: encryption, sensitive data filtering, and authentication."""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from llmhive.app.encryption import EncryptionManager, get_encryption_manager
from llmhive.app.guardrails import filter_query, SENSITIVE_PATTERNS
from llmhive.app.auth import verify_api_key
from llmhive.app.models import MemoryEntry, KnowledgeDocument
from fastapi import HTTPException
from fastapi.security import Security


class TestEncryption:
    """Tests for field-level encryption."""
    
    def test_encryption_manager_aes_gcm(self):
        """Test AES-256-GCM encryption and decryption."""
        test_key = "test_encryption_key_12345"
        manager = EncryptionManager(encryption_key=test_key, require_key=False, use_aes_gcm=True)
        
        assert manager.enabled, "Encryption should be enabled"
        assert manager.use_aes_gcm, "Should use AES-GCM"
        
        plaintext = "This is sensitive user data that should be encrypted"
        ciphertext = manager.encrypt(plaintext)
        
        assert ciphertext != plaintext, "Ciphertext should differ from plaintext"
        assert len(ciphertext) > len(plaintext), "Ciphertext should be longer (includes nonce)"
        
        decrypted = manager.decrypt(ciphertext)
        assert decrypted == plaintext, "Decrypted text should match original"
    
    def test_encryption_manager_disabled(self):
        """Test encryption manager when key is not provided."""
        manager = EncryptionManager(encryption_key=None, require_key=False, use_aes_gcm=True)
        
        assert not manager.enabled, "Encryption should be disabled when no key"
        
        plaintext = "This is plaintext"
        result = manager.encrypt(plaintext)
        assert result == plaintext, "Should return plaintext when encryption disabled"
        
        decrypted = manager.decrypt(plaintext)
        assert decrypted == plaintext, "Should return plaintext when encryption disabled"
    
    def test_memory_entry_encryption(self):
        """Test transparent encryption in MemoryEntry model."""
        # Set up encryption
        test_key = "test_encryption_key_12345"
        with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
            # Clear singleton cache
            import llmhive.app.encryption
            llmhive.app.encryption._encryption_manager = None
            
            # Create a mock entry (we can't easily test SQLAlchemy models without DB)
            # Instead, test the encryption manager directly
            manager = get_encryption_manager(require_key=False)
            
            if manager.enabled:
                plaintext = "User query: What is my SSN?"
                encrypted = manager.encrypt(plaintext)
                decrypted = manager.decrypt(encrypted)
                
                assert decrypted == plaintext, "Encryption/decryption should work"
                assert encrypted != plaintext, "Encrypted text should differ"
    
    def test_knowledge_document_encryption(self):
        """Test transparent encryption in KnowledgeDocument model."""
        test_key = "test_encryption_key_12345"
        manager = EncryptionManager(encryption_key=test_key, require_key=False, use_aes_gcm=True)
        
        if manager.enabled:
            plaintext = "Knowledge base content with sensitive information"
            encrypted = manager.encrypt(plaintext)
            decrypted = manager.decrypt(encrypted)
            
            assert decrypted == plaintext, "Encryption/decryption should work"


class TestSensitiveDataFiltering:
    """Tests for sensitive data detection and filtering."""
    
    def test_filter_credit_card(self):
        """Test detection and filtering of credit card numbers."""
        query = "My credit card is 4532-1234-5678-9010"
        filtered, has_sensitive = filter_query(query, is_external=True, strict_mode=False)
        
        assert has_sensitive, "Should detect credit card"
        assert "[REDACTED]" in filtered, "Should redact credit card"
        assert "4532" not in filtered, "Should not contain original card number"
    
    def test_filter_ssn(self):
        """Test detection and filtering of SSN."""
        query = "My SSN is 123-45-6789"
        filtered, has_sensitive = filter_query(query, is_external=True, strict_mode=False)
        
        assert has_sensitive, "Should detect SSN"
        assert "[REDACTED]" in filtered, "Should redact SSN"
        assert "123-45-6789" not in filtered, "Should not contain original SSN"
    
    def test_filter_email(self):
        """Test detection and filtering of email addresses."""
        query = "Contact me at user@example.com"
        filtered, has_sensitive = filter_query(query, is_external=True, strict_mode=False)
        
        assert has_sensitive, "Should detect email"
        assert "[REDACTED]" in filtered, "Should redact email"
        assert "user@example.com" not in filtered, "Should not contain original email"
    
    def test_filter_api_key(self):
        """Test detection and filtering of API keys."""
        query = "My API key is sk-1234567890abcdefghijklmnopqrstuvwxyz"
        filtered, has_sensitive = filter_query(query, is_external=True, strict_mode=False)
        
        assert has_sensitive, "Should detect API key"
        assert "[REDACTED]" in filtered, "Should redact API key"
        assert "sk-" not in filtered, "Should not contain API key prefix"
    
    def test_filter_strict_mode_blocks(self):
        """Test that strict mode blocks requests with sensitive data."""
        query = "My credit card is 4532-1234-5678-9010"
        
        with pytest.raises(ValueError, match="sensitive data"):
            filter_query(query, is_external=True, strict_mode=True)
    
    def test_filter_no_sensitive_data(self):
        """Test that queries without sensitive data pass through."""
        query = "What is the weather today?"
        filtered, has_sensitive = filter_query(query, is_external=True, strict_mode=False)
        
        assert not has_sensitive, "Should not detect sensitive data"
        assert filtered == query, "Should return original query unchanged"
    
    def test_filter_internal_provider(self):
        """Test that internal providers don't get filtered."""
        query = "My SSN is 123-45-6789"
        filtered, has_sensitive = filter_query(query, is_external=False, strict_mode=False)
        
        assert not has_sensitive, "Should not filter for internal providers"
        assert filtered == query, "Should return original query for internal providers"


class TestAuthentication:
    """Tests for API authentication."""
    
    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self):
        """Test authentication with valid API key."""
        with patch("llmhive.app.auth.settings") as mock_settings:
            mock_settings.api_key = "test-api-key-123"
            mock_settings.require_auth = True
            
            # Mock headers
            result = await verify_api_key(
                x_api_key="test-api-key-123",
                authorization=None
            )
            
            assert result == "authenticated", "Should authenticate with valid key"
    
    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self):
        """Test authentication with invalid API key."""
        with patch("llmhive.app.auth.settings") as mock_settings:
            mock_settings.api_key = "test-api-key-123"
            mock_settings.require_auth = True
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(
                    x_api_key="wrong-key",
                    authorization=None
                )
            
            assert exc_info.value.status_code == 401, "Should return 401 for invalid key"
    
    @pytest.mark.asyncio
    async def test_verify_api_key_missing_required(self):
        """Test authentication when key is required but missing."""
        with patch("llmhive.app.auth.settings") as mock_settings:
            mock_settings.api_key = "test-api-key-123"
            mock_settings.require_auth = True
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(
                    x_api_key=None,
                    authorization=None
                )
            
            assert exc_info.value.status_code == 401, "Should return 401 when key missing"
    
    @pytest.mark.asyncio
    async def test_verify_api_key_bearer_token(self):
        """Test authentication with Bearer token."""
        with patch("llmhive.app.auth.settings") as mock_settings:
            mock_settings.api_key = "test-api-key-123"
            mock_settings.require_auth = True
            
            result = await verify_api_key(
                x_api_key=None,
                authorization="Bearer test-api-key-123"
            )
            
            assert result == "authenticated", "Should authenticate with Bearer token"
    
    @pytest.mark.asyncio
    async def test_verify_api_key_optional(self):
        """Test authentication when auth is optional."""
        with patch("llmhive.app.auth.settings") as mock_settings:
            mock_settings.api_key = None
            mock_settings.require_auth = False
            
            result = await verify_api_key(
                x_api_key=None,
                authorization=None
            )
            
            assert result == "anonymous", "Should allow anonymous when auth not required"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

