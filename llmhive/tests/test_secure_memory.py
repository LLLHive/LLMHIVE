"""Unit tests for secure memory management with encryption, retention policy, and user isolation."""
from __future__ import annotations

import datetime as dt
import os
import pytest
from sqlalchemy.orm import Session

from llmhive.app.memory.secure_memory import SecureMemoryManager
from llmhive.app.models import Conversation, MemoryEntry, User, AccountTier
from llmhive.app.encryption import EncryptionManager, get_encryption_manager


@pytest.fixture
def db_session(test_db_session: Session) -> Session:
    """Provide a database session for tests."""
    return test_db_session


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(user_id="test_user_1", account_tier=AccountTier.FREE)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_2(db_session: Session) -> User:
    """Create a second test user."""
    user = User(user_id="test_user_2", account_tier=AccountTier.FREE)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_conversation(db_session: Session, test_user: User) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(user_id=test_user.user_id, topic="test")
    db_session.add(conversation)
    db_session.commit()
    return conversation


@pytest.fixture
def encryption_key() -> str:
    """Generate a test encryption key."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


@pytest.fixture
def secure_memory_manager(db_session: Session, encryption_key: str, monkeypatch) -> SecureMemoryManager:
    """Create a secure memory manager with encryption enabled."""
    monkeypatch.setenv("ENCRYPTION_KEY", encryption_key)
    # Reset global encryption manager
    import llmhive.app.encryption
    llmhive.app.encryption._encryption_manager = None
    return SecureMemoryManager(db_session)


def test_retention_policy_max_entries(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User, monkeypatch):
    """Test that retention policy prunes entries beyond max_entries_per_user."""
    # Set max entries to 5 for testing
    monkeypatch.setattr("llmhive.app.config.settings.memory_max_entries_per_user", 5)
    
    # Add 7 entries (should keep only 5 most recent)
    for i in range(7):
        secure_memory_manager.append_entry(
            test_conversation,
            role="user",
            content=f"Message {i}",
            user_id=test_user.user_id,
        )
    
    db_session = secure_memory_manager.session
    db_session.commit()
    
    # Check that only 5 entries remain
    from sqlalchemy import select, func
    count = db_session.scalar(
        select(func.count(MemoryEntry.id)).where(MemoryEntry.user_id == test_user.user_id)
    )
    assert count == 5, f"Expected 5 entries, got {count}"
    
    # Verify the oldest entries were removed (should have messages 2-6, not 0-1)
    entries = db_session.scalars(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == test_user.user_id)
        .order_by(MemoryEntry.created_at.asc())
    ).all()
    
    # Check that oldest entries are gone
    content_list = [secure_memory_manager._decrypt_content(e.content, e.content_encrypted) for e in entries]
    assert "Message 0" not in content_list
    assert "Message 1" not in content_list
    assert "Message 2" in content_list or "Message 3" in content_list  # At least one of the kept messages


def test_retention_policy_max_age(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User, monkeypatch):
    """Test that retention policy prunes entries older than max_age_days."""
    # Set max age to 1 day for testing
    monkeypatch.setattr("llmhive.app.config.settings.memory_max_age_days", 1)
    
    # Add an old entry (2 days ago)
    old_entry = MemoryEntry(
        conversation_id=test_conversation.id,
        user_id=test_user.user_id,
        role="user",
        content="Old message",
        content_encrypted=False,
        created_at=dt.datetime.utcnow() - dt.timedelta(days=2),
    )
    secure_memory_manager.session.add(old_entry)
    secure_memory_manager.session.flush()
    
    # Add a new entry (should trigger retention policy)
    secure_memory_manager.append_entry(
        test_conversation,
        role="user",
        content="New message",
        user_id=test_user.user_id,
    )
    
    secure_memory_manager.session.commit()
    
    # Check that old entry was removed
    from sqlalchemy import select
    entries = secure_memory_manager.session.scalars(
        select(MemoryEntry).where(MemoryEntry.user_id == test_user.user_id)
    ).all()
    
    content_list = [secure_memory_manager._decrypt_content(e.content, e.content_encrypted) for e in entries]
    assert "Old message" not in content_list
    assert "New message" in content_list


def test_user_isolation(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User, test_user_2: User):
    """Test that users can only access their own memory entries."""
    # Add entries for user 1
    secure_memory_manager.append_entry(
        test_conversation,
        role="user",
        content="User 1 message",
        user_id=test_user.user_id,
    )
    
    # Add entries for user 2
    secure_memory_manager.append_entry(
        test_conversation,
        role="user",
        content="User 2 message",
        user_id=test_user_2.user_id,
    )
    
    secure_memory_manager.session.commit()
    
    # Fetch context for user 1 - should only see user 1's messages
    context_1 = secure_memory_manager.fetch_recent_context(
        test_conversation,
        user_id=test_user.user_id,
    )
    
    assert "User 1 message" in " ".join(context_1.recent_messages)
    assert "User 2 message" not in " ".join(context_1.recent_messages)
    
    # Fetch context for user 2 - should only see user 2's messages
    context_2 = secure_memory_manager.fetch_recent_context(
        test_conversation,
        user_id=test_user_2.user_id,
    )
    
    assert "User 2 message" in " ".join(context_2.recent_messages)
    assert "User 1 message" not in " ".join(context_2.recent_messages)


def test_encryption_roundtrip(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User):
    """Test that encryption/decryption works correctly."""
    sensitive_content = "This is a sensitive message with PII: john.doe@example.com"
    
    # Add entry with encryption
    entry = secure_memory_manager.append_entry(
        test_conversation,
        role="user",
        content=sensitive_content,
        user_id=test_user.user_id,
    )
    
    secure_memory_manager.session.commit()
    secure_memory_manager.session.refresh(entry)
    
    # Verify content is encrypted in database
    assert entry.content_encrypted is True
    assert entry.content != sensitive_content  # Encrypted content should be different
    assert len(entry.content) > len(sensitive_content)  # Encrypted content is typically longer
    
    # Verify decryption works
    decrypted = secure_memory_manager._decrypt_content(entry.content, entry.content_encrypted)
    assert decrypted == sensitive_content
    
    # Verify fetch_recent_context returns decrypted content
    context = secure_memory_manager.fetch_recent_context(
        test_conversation,
        user_id=test_user.user_id,
    )
    
    assert sensitive_content in " ".join(context.recent_messages)


def test_encryption_backwards_compatibility(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User):
    """Test that unencrypted entries (backwards compatibility) still work."""
    # Create an entry without encryption (simulating old data)
    old_entry = MemoryEntry(
        conversation_id=test_conversation.id,
        user_id=test_user.user_id,
        role="user",
        content="Unencrypted message",
        content_encrypted=False,
        created_at=dt.datetime.utcnow(),
    )
    secure_memory_manager.session.add(old_entry)
    secure_memory_manager.session.commit()
    
    # Fetch context - should handle unencrypted entry gracefully
    context = secure_memory_manager.fetch_recent_context(
        test_conversation,
        user_id=test_user.user_id,
    )
    
    assert "Unencrypted message" in " ".join(context.recent_messages)


def test_get_user_memory_count(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User, test_user_2: User):
    """Test getting memory count for a user."""
    # Add entries for user 1
    for i in range(3):
        secure_memory_manager.append_entry(
            test_conversation,
            role="user",
            content=f"Message {i}",
            user_id=test_user.user_id,
        )
    
    # Add entries for user 2
    for i in range(2):
        secure_memory_manager.append_entry(
            test_conversation,
            role="user",
            content=f"Message {i}",
            user_id=test_user_2.user_id,
        )
    
    secure_memory_manager.session.commit()
    
    # Check counts
    count_1 = secure_memory_manager.get_user_memory_count(test_user.user_id)
    count_2 = secure_memory_manager.get_user_memory_count(test_user_2.user_id)
    
    assert count_1 == 3
    assert count_2 == 2


def test_prune_user_memory(secure_memory_manager: SecureMemoryManager, test_conversation: Conversation, test_user: User):
    """Test manual pruning of user memory."""
    # Add 10 entries
    for i in range(10):
        secure_memory_manager.append_entry(
            test_conversation,
            role="user",
            content=f"Message {i}",
            user_id=test_user.user_id,
        )
    
    secure_memory_manager.session.commit()
    
    # Manually prune to 5 entries
    pruned = secure_memory_manager.prune_user_memory(test_user.user_id, max_entries=5)
    
    assert pruned == 5  # Should have pruned 5 entries
    
    # Verify only 5 remain
    count = secure_memory_manager.get_user_memory_count(test_user.user_id)
    assert count == 5


def test_encryption_manager_initialization(encryption_key: str, monkeypatch):
    """Test encryption manager initialization."""
    monkeypatch.setenv("ENCRYPTION_KEY", encryption_key)
    
    # Reset global encryption manager
    import llmhive.app.encryption
    llmhive.app.encryption._encryption_manager = None
    
    manager = get_encryption_manager(require_key=True)
    assert manager.enabled is True
    
    # Test encryption/decryption
    plaintext = "Test message"
    encrypted = manager.encrypt(plaintext)
    assert encrypted != plaintext
    assert manager.is_encrypted(encrypted) is True
    
    decrypted = manager.decrypt(encrypted)
    assert decrypted == plaintext


def test_encryption_manager_missing_key(monkeypatch):
    """Test encryption manager behavior when key is missing."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    
    # Reset global encryption manager
    import llmhive.app.encryption
    llmhive.app.encryption._encryption_manager = None
    
    # In production mode, should raise error
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        get_encryption_manager(require_key=True)
    
    # In development mode, should allow graceful degradation
    manager = get_encryption_manager(require_key=False)
    assert manager.enabled is False
    
    # Encryption should return plaintext when disabled
    plaintext = "Test message"
    encrypted = manager.encrypt(plaintext)
    assert encrypted == plaintext  # No encryption when disabled

