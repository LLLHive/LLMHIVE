"""Secure memory management with encryption, retention policy, and user isolation.

This module extends the memory manager with:
- Retention policy enforcement (max entries per user, max age)
- User isolation (filter by user_id)
- Encryption of sensitive content
- Optimized indexing for fast retrieval
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import List, Optional, Sequence

from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import Session

from ..config import settings
from ..encryption import get_encryption_manager
from ..models import Conversation, MemoryEntry

logger = logging.getLogger(__name__)


class SecureMemoryManager:
    """Secure memory manager with encryption, retention policy, and user isolation.
    
    Features:
    - Retention Policy: Enforces max entries per user and max age
    - User Isolation: Ensures users can only access their own memory
    - Encryption: Encrypts sensitive content before storage
    - Indexing: Uses database indexes for efficient queries
    """

    def __init__(self, session: Session):
        """Initialize secure memory manager.
        
        Args:
            session: Database session
        """
        self.session = session
        self.encryption_manager = None
        
        # Initialize encryption if enabled
        if settings.memory_enable_encryption:
            try:
                # In production, require key. In development, allow graceful degradation
                require_key = settings.environment.lower() == "production"
                self.encryption_manager = get_encryption_manager(require_key=require_key)
                if self.encryption_manager.enabled:
                    logger.info("Secure Memory: Encryption enabled for memory entries")
                else:
                    logger.warning("Secure Memory: Encryption disabled (no key available)")
            except ValueError as exc:
                if settings.environment.lower() == "production":
                    raise  # Fail fast in production
                logger.warning("Secure Memory: Encryption initialization failed: %s", exc)

    def _encrypt_content(self, content: str) -> tuple[str, bool]:
        """Encrypt content if encryption is enabled.
        
        Args:
            content: Plaintext content to encrypt
            
        Returns:
            Tuple of (encrypted_content, is_encrypted)
        """
        if self.encryption_manager and self.encryption_manager.enabled:
            encrypted = self.encryption_manager.encrypt(content)
            return encrypted, True
        return content, False

    def _decrypt_content(self, content: str, is_encrypted: bool) -> str:
        """Decrypt content if it was encrypted.
        
        Args:
            content: Encrypted or plaintext content
            is_encrypted: Whether content is encrypted
            
        Returns:
            Decrypted plaintext content
        """
        if is_encrypted and self.encryption_manager and self.encryption_manager.enabled:
            return self.encryption_manager.decrypt(content)
        return content

    def append_entry(
        self,
        conversation: Conversation,
        *,
        role: str,
        content: str,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> MemoryEntry:
        """Append a memory entry with encryption and user isolation.
        
        Args:
            conversation: Conversation object
            role: Role of the message (user, assistant)
            content: Content to store (will be encrypted if enabled)
            metadata: Optional metadata dictionary
            user_id: User ID for isolation (defaults to conversation.user_id)
            
        Returns:
            Created MemoryEntry
        """
        # User Isolation: Use provided user_id or conversation's user_id
        entry_user_id = user_id or conversation.user_id
        
        # Encryption: Encrypt content before storage
        encrypted_content, is_encrypted = self._encrypt_content(content)
        
        entry = MemoryEntry(
            conversation_id=conversation.id,
            user_id=entry_user_id,  # User Isolation: Store user_id
            role=role,
            content=encrypted_content,  # Encryption: Store encrypted content
            content_encrypted=is_encrypted,  # Encryption: Flag for decryption
            payload=metadata or {},
            created_at=dt.datetime.utcnow(),
        )
        self.session.add(entry)
        self.session.flush()  # Flush to get the ID
        
        # Retention Policy: Enforce limits after adding entry
        self._enforce_retention_policy(entry_user_id)
        
        logger.debug(
            "Secure Memory: Added entry for user %s (conversation %d, encrypted=%s)",
            entry_user_id,
            conversation.id,
            is_encrypted,
        )
        
        return entry

    def _enforce_retention_policy(self, user_id: str | None) -> None:
        """Enforce retention policy by pruning old entries.
        
        Retention Policy: Removes entries that exceed:
        - Max entries per user (keeps most recent N entries)
        - Max age (removes entries older than M days)
        
        Args:
            user_id: User ID to enforce policy for (None = global)
        """
        try:
            max_entries = settings.memory_max_entries_per_user
            max_age_days = settings.memory_max_age_days
            cutoff_date = dt.datetime.utcnow() - dt.timedelta(days=max_age_days)
            
            # Retention Policy: Build query to find entries to prune
            query = select(MemoryEntry)
            
            # User Isolation: Filter by user_id if provided
            if user_id:
                query = query.where(MemoryEntry.user_id == user_id)
            
            # Retention Policy: Filter by age (entries older than cutoff)
            query = query.where(MemoryEntry.created_at < cutoff_date)
            
            # Delete old entries
            old_entries = list(self.session.scalars(query))
            if old_entries:
                for entry in old_entries:
                    self.session.delete(entry)
                logger.info(
                    "Retention Policy: Pruned %d entries older than %d days for user %s",
                    len(old_entries),
                    max_age_days,
                    user_id or "all",
                )
            
            # Retention Policy: Enforce max entries per user (keep most recent N)
            if user_id and max_entries > 0:
                # Count entries for this user
                count_query = select(func.count(MemoryEntry.id)).where(
                    MemoryEntry.user_id == user_id
                )
                total_count = self.session.scalar(count_query) or 0
                
                if total_count > max_entries:
                    # Find entries to delete (oldest ones beyond limit)
                    excess = total_count - max_entries
                    delete_query = (
                        select(MemoryEntry.id)
                        .where(MemoryEntry.user_id == user_id)
                        .order_by(MemoryEntry.created_at.asc())
                        .limit(excess)
                    )
                    ids_to_delete = list(self.session.scalars(delete_query))
                    
                    if ids_to_delete:
                        delete_stmt = delete(MemoryEntry).where(MemoryEntry.id.in_(ids_to_delete))
                        self.session.execute(delete_stmt)
                        logger.info(
                            "Retention Policy: Pruned %d excess entries for user %s (kept %d most recent)",
                            len(ids_to_delete),
                            user_id,
                            max_entries,
                        )
            
            self.session.flush()
        except Exception as exc:
            logger.error("Retention Policy: Failed to enforce retention policy: %s", exc)
            # Don't raise - retention policy failure shouldn't break memory insertion

    def fetch_recent_context(
        self,
        conversation: Conversation,
        *,
        limit: int = 6,
        user_id: str | None = None,
        query: str | None = None,
    ) -> "MemoryContext":
        """Fetch recent context with user isolation and decryption.
        
        User Isolation: Only returns entries for the specified user_id.
        Encryption: Decrypts content before returning.
        
        Args:
            conversation: Conversation object
            limit: Maximum number of entries to return
            user_id: User ID for isolation (defaults to conversation.user_id)
            query: Optional query string for relevance filtering
            
        Returns:
            MemoryContext with decrypted content
        """
        from ..memory import MemoryContext
        
        # User Isolation: Use provided user_id or conversation's user_id
        entry_user_id = user_id or conversation.user_id
        
        # User Isolation: Build query with user_id filter
        stmt = (
            select(MemoryEntry)
            .where(
                and_(
                    MemoryEntry.conversation_id == conversation.id,
                    MemoryEntry.user_id == entry_user_id,  # User Isolation: Filter by user_id
                )
            )
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        
        rows = list(self.session.scalars(stmt))
        
        # Encryption: Decrypt content before returning
        recent = []
        for entry in reversed(rows):
            decrypted_content = self._decrypt_content(entry.content, entry.content_encrypted)
            recent.append(f"{entry.role.capitalize()}: {decrypted_content}")
        
        summary = conversation.summary or "No long-term summary recorded yet."
        
        return MemoryContext(
            conversation_id=conversation.id,
            summary=summary,
            recent_messages=recent,
        )

    def get_user_memory_count(self, user_id: str) -> int:
        """Get the number of memory entries for a user.
        
        User Isolation: Only counts entries for the specified user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of memory entries for the user
        """
        stmt = select(func.count(MemoryEntry.id)).where(MemoryEntry.user_id == user_id)
        return self.session.scalar(stmt) or 0

    def prune_user_memory(self, user_id: str, max_entries: int | None = None) -> int:
        """Manually prune memory entries for a user.
        
        Args:
            user_id: User ID
            max_entries: Maximum entries to keep (uses config default if None)
            
        Returns:
            Number of entries pruned
        """
        max_entries = max_entries or settings.memory_max_entries_per_user
        
        count_query = select(func.count(MemoryEntry.id)).where(MemoryEntry.user_id == user_id)
        total_count = self.session.scalar(count_query) or 0
        
        if total_count <= max_entries:
            return 0
        
        excess = total_count - max_entries
        delete_query = (
            select(MemoryEntry.id)
            .where(MemoryEntry.user_id == user_id)
            .order_by(MemoryEntry.created_at.asc())
            .limit(excess)
        )
        ids_to_delete = list(self.session.scalars(delete_query))
        
        if ids_to_delete:
            delete_stmt = delete(MemoryEntry).where(MemoryEntry.id.in_(ids_to_delete))
            self.session.execute(delete_stmt)
            self.session.flush()
            logger.info(
                "Retention Policy: Manually pruned %d entries for user %s",
                len(ids_to_delete),
                user_id,
            )
        
        return len(ids_to_delete)

