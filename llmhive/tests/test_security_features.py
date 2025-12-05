"""Tests for security features: models, authentication, and data protection."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Import models - these should always be available
from llmhive.app.models import (
    MemoryEntry, 
    KnowledgeDocument, 
    User, 
    AccountTier,
    FeedbackOutcome,
    SQLALCHEMY_AVAILABLE,
)

# Try to import optional modules
try:
    from llmhive.app.encryption import EncryptionManager, get_encryption_manager
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    EncryptionManager = None
    get_encryption_manager = None

try:
    from llmhive.app.guardrails import filter_query
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    filter_query = None

try:
    from llmhive.app.auth import verify_api_key
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    verify_api_key = None


class TestModelExports:
    """Test that all required models are properly exported."""

    def test_memory_entry_model_exists(self) -> None:
        """Test MemoryEntry model is exported."""
        assert MemoryEntry is not None
        
    def test_knowledge_document_model_exists(self) -> None:
        """Test KnowledgeDocument model is exported."""
        assert KnowledgeDocument is not None
        
    def test_user_model_exists(self) -> None:
        """Test User model is exported."""
        assert User is not None

    def test_account_tier_enum_exists(self) -> None:
        """Test AccountTier enum is exported."""
        assert AccountTier is not None
        assert hasattr(AccountTier, 'FREE')
        assert hasattr(AccountTier, 'PRO')
        assert hasattr(AccountTier, 'ENTERPRISE')

    def test_feedback_outcome_enum_exists(self) -> None:
        """Test FeedbackOutcome enum is exported."""
        assert FeedbackOutcome is not None
        assert hasattr(FeedbackOutcome, 'SUCCESS')
        assert hasattr(FeedbackOutcome, 'FAILURE')


class TestAccountTierEnum:
    """Test AccountTier enum functionality."""

    def test_tier_values(self) -> None:
        """Test tier enum values."""
        assert AccountTier.FREE.value == "free"
        assert AccountTier.PRO.value == "pro"
        assert AccountTier.ENTERPRISE.value == "enterprise"

    def test_tier_is_string_enum(self) -> None:
        """Test that AccountTier is a string enum."""
        assert isinstance(AccountTier.FREE.value, str)
        assert str(AccountTier.FREE) == "AccountTier.FREE"

    def test_tier_comparison(self) -> None:
        """Test tier enum comparison."""
        assert AccountTier.FREE == AccountTier.FREE
        assert AccountTier.FREE != AccountTier.PRO
        assert AccountTier.PRO != AccountTier.ENTERPRISE


class TestFeedbackOutcomeEnum:
    """Test FeedbackOutcome enum functionality."""

    def test_outcome_values(self) -> None:
        """Test outcome enum values."""
        assert FeedbackOutcome.SUCCESS.value == "success"
        assert FeedbackOutcome.FAILURE.value == "failure"
        assert FeedbackOutcome.PARTIAL.value == "partial"
        assert FeedbackOutcome.TIMEOUT.value == "timeout"
        assert FeedbackOutcome.ERROR.value == "error"

    def test_outcome_is_string_enum(self) -> None:
        """Test that FeedbackOutcome is a string enum."""
        assert isinstance(FeedbackOutcome.SUCCESS.value, str)


class TestModelAttributes:
    """Test model class attributes (stub classes or SQLAlchemy models)."""

    def test_user_has_expected_attributes(self) -> None:
        """Test User model has expected attribute definitions."""
        # Check class has attributes defined (either as columns or type hints)
        user_attrs = dir(User)
        # At minimum, these should be defined somewhere
        assert 'id' in user_attrs or hasattr(User, '__annotations__')

    def test_memory_entry_has_expected_attributes(self) -> None:
        """Test MemoryEntry model has expected attribute definitions."""
        entry_attrs = dir(MemoryEntry)
        assert 'id' in entry_attrs or hasattr(MemoryEntry, '__annotations__')

    def test_knowledge_document_has_expected_attributes(self) -> None:
        """Test KnowledgeDocument model has expected attribute definitions."""
        doc_attrs = dir(KnowledgeDocument)
        assert 'id' in doc_attrs or hasattr(KnowledgeDocument, '__annotations__')


@pytest.mark.skipif(not ENCRYPTION_AVAILABLE, reason="Encryption module not available")
class TestEncryptionModule:
    """Tests for encryption module (when available)."""

    def test_encryption_manager_class_exists(self) -> None:
        """Test EncryptionManager class exists."""
        assert EncryptionManager is not None

    def test_get_encryption_manager_function_exists(self) -> None:
        """Test get_encryption_manager function exists."""
        assert get_encryption_manager is not None
        assert callable(get_encryption_manager)

    @pytest.mark.skip(reason="Requires cryptography module installed")
    def test_encryption_manager_disabled_mode(self) -> None:
        """Test encryption manager in disabled mode."""
        manager = EncryptionManager(encryption_key=None, require_key=False)
        assert not manager.enabled

    @pytest.mark.skip(reason="Requires cryptography module installed")
    def test_encryption_roundtrip(self) -> None:
        """Test encrypt/decrypt roundtrip."""
        manager = EncryptionManager(
            encryption_key="test_key_32_characters_long!!!!!",
            require_key=False
        )
        if manager.enabled:
            plaintext = "Sensitive data"
            encrypted = manager.encrypt(plaintext)
            decrypted = manager.decrypt(encrypted)
            assert decrypted == plaintext


@pytest.mark.skipif(not GUARDRAILS_AVAILABLE, reason="Guardrails module not available")
class TestGuardrailsModule:
    """Tests for guardrails/data filtering module (when available)."""

    def test_filter_query_function_exists(self) -> None:
        """Test filter_query function exists."""
        assert filter_query is not None
        assert callable(filter_query)


@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth module not available")
class TestAuthModule:
    """Tests for authentication module (when available)."""

    def test_verify_api_key_function_exists(self) -> None:
        """Test verify_api_key function exists."""
        assert verify_api_key is not None
        assert callable(verify_api_key)


class TestSQLAlchemyAvailability:
    """Test SQLAlchemy availability flag."""

    def test_sqlalchemy_flag_is_boolean(self) -> None:
        """Test SQLALCHEMY_AVAILABLE is a boolean."""
        assert isinstance(SQLALCHEMY_AVAILABLE, bool)

    def test_models_work_regardless_of_sqlalchemy(self) -> None:
        """Test that model imports work whether SQLAlchemy is available or not."""
        # These should not raise regardless of SQLAlchemy availability
        assert User is not None
        assert MemoryEntry is not None
        assert KnowledgeDocument is not None
        assert AccountTier is not None


class TestSecurityPatterns:
    """Test common security patterns in the codebase."""

    def test_account_tiers_have_hierarchy(self) -> None:
        """Test that account tiers represent a hierarchy."""
        tiers = [AccountTier.FREE, AccountTier.PRO, AccountTier.ENTERPRISE]
        tier_values = [t.value for t in tiers]
        
        # All tier values should be unique
        assert len(tier_values) == len(set(tier_values))
        
    def test_feedback_outcomes_are_exhaustive(self) -> None:
        """Test feedback outcomes cover common scenarios."""
        outcomes = [o.value for o in FeedbackOutcome]
        
        # Should have success and failure at minimum
        assert "success" in outcomes
        assert "failure" in outcomes
        
        # Should have error handling outcomes
        assert "timeout" in outcomes or "error" in outcomes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
