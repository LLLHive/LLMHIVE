"""Shared Memory Module for Cross-Session and Multi-Agent Memory.

This module provides persistent memory storage that can be shared:
1. Across different sessions for the same user (conversation continuity)
2. Across different agents within the same query (inter-agent communication)
3. Across different users with proper access controls (shared knowledge)

Features:
- Multi-tenant isolation with configurable sharing levels
- Cross-session memory persistence
- Conversation context and insights sharing
- Access control lists (ACLs) for fine-grained permissions
- Tagging and categorization system
- Expiration and retention policies
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class AccessLevel(str, Enum):
    """Access level for shared memory entries."""
    PRIVATE = "private"           # Only owner can access
    SESSION = "session"           # Accessible within same session
    USER = "user"                 # Accessible by same user across sessions
    TEAM = "team"                 # Accessible by team/organization
    PUBLIC = "public"             # Globally accessible (read-only to others)


class MemoryCategory(str, Enum):
    """Category of memory entry."""
    FACT = "fact"                 # Verified factual information
    PREFERENCE = "preference"     # User preferences
    CONTEXT = "context"           # Conversation context
    INSIGHT = "insight"           # Derived insights
    INTERMEDIATE = "intermediate" # Intermediate computation results
    KNOWLEDGE = "knowledge"       # General knowledge
    HISTORY = "history"           # Historical interaction


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class AccessControl:
    """Access control settings for a memory entry."""
    owner_id: str
    access_level: AccessLevel = AccessLevel.PRIVATE
    allowed_users: Set[str] = field(default_factory=set)
    allowed_teams: Set[str] = field(default_factory=set)
    read_only: bool = False
    expires_at: Optional[datetime] = None
    
    def can_read(self, user_id: str, team_id: Optional[str] = None) -> bool:
        """Check if user can read this entry."""
        if user_id == self.owner_id:
            return True
        if self.access_level == AccessLevel.PRIVATE:
            return False
        if self.access_level == AccessLevel.PUBLIC:
            return True
        if user_id in self.allowed_users:
            return True
        if team_id and team_id in self.allowed_teams:
            return True
        if self.access_level == AccessLevel.TEAM and team_id:
            return True
        return False
    
    def can_write(self, user_id: str) -> bool:
        """Check if user can write to this entry."""
        if self.read_only:
            return user_id == self.owner_id
        if user_id == self.owner_id:
            return True
        if user_id in self.allowed_users and not self.read_only:
            return True
        return False
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        exp = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return now > exp


@dataclass(slots=True)
class SharedMemoryEntry:
    """A shared memory entry."""
    id: str
    content: str
    owner_id: str
    access_control: AccessControl
    category: MemoryCategory = MemoryCategory.CONTEXT
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    embedding: Optional[List[float]] = None
    
    @property
    def session_id(self) -> Optional[str]:
        return self.metadata.get("session_id")
    
    @property
    def is_verified(self) -> bool:
        return self.metadata.get("verified", False)


@dataclass(slots=True)
class SharedMemoryQuery:
    """Query parameters for shared memory."""
    query_text: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    session_id: Optional[str] = None
    categories: Optional[List[MemoryCategory]] = None
    tags: Optional[List[str]] = None
    include_public: bool = True
    include_team: bool = True
    min_score: float = 0.0
    max_age_hours: Optional[int] = None
    limit: int = 10


@dataclass(slots=True)
class SharedMemoryResult:
    """Result of a shared memory query."""
    entries: List[SharedMemoryEntry]
    total_found: int
    query_time_ms: float
    source_breakdown: Dict[str, int] = field(default_factory=dict)


# ==============================================================================
# Shared Memory Store Interface
# ==============================================================================

class SharedMemoryStore(ABC):
    """Abstract base class for shared memory storage backends."""
    
    @abstractmethod
    async def store(self, entry: SharedMemoryEntry) -> str:
        """Store a memory entry."""
        pass
    
    @abstractmethod
    async def get(self, entry_id: str, user_id: str) -> Optional[SharedMemoryEntry]:
        """Get a memory entry by ID."""
        pass
    
    @abstractmethod
    async def query(self, query: SharedMemoryQuery) -> SharedMemoryResult:
        """Query memory entries."""
        pass
    
    @abstractmethod
    async def update(self, entry_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str, user_id: str) -> bool:
        """Delete a memory entry."""
        pass
    
    @abstractmethod
    async def share(self, entry_id: str, owner_id: str, share_with: List[str]) -> bool:
        """Share an entry with other users."""
        pass


class InMemorySharedStore(SharedMemoryStore):
    """In-memory implementation of shared memory store."""
    
    def __init__(self):
        self._entries: Dict[str, SharedMemoryEntry] = {}
        self._user_index: Dict[str, Set[str]] = defaultdict(set)
        self._session_index: Dict[str, Set[str]] = defaultdict(set)
        self._category_index: Dict[MemoryCategory, Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
    
    async def store(self, entry: SharedMemoryEntry) -> str:
        """Store a memory entry."""
        with self._lock:
            self._entries[entry.id] = entry
            self._user_index[entry.owner_id].add(entry.id)
            
            if entry.session_id:
                self._session_index[entry.session_id].add(entry.id)
            
            self._category_index[entry.category].add(entry.id)
            
            for tag in entry.tags:
                self._tag_index[tag].add(entry.id)
            
            logger.debug("Stored shared memory entry: %s", entry.id[:8])
            return entry.id
    
    async def get(self, entry_id: str, user_id: str) -> Optional[SharedMemoryEntry]:
        """Get a memory entry by ID with access check."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return None
            
            # Check access
            if not entry.access_control.can_read(user_id):
                logger.warning(
                    "Access denied: user %s cannot read entry %s",
                    user_id, entry_id[:8]
                )
                return None
            
            # Check expiration
            if entry.access_control.is_expired():
                logger.debug("Entry %s has expired", entry_id[:8])
                return None
            
            # Increment access count
            entry.access_count += 1
            return entry
    
    async def query(self, query: SharedMemoryQuery) -> SharedMemoryResult:
        """Query memory entries with filtering."""
        start_time = time.time()
        
        with self._lock:
            candidate_ids: Set[str] = set(self._entries.keys())
            
            # Filter by user
            if query.user_id:
                user_entries = self._user_index.get(query.user_id, set())
                candidate_ids &= user_entries
            
            # Filter by session
            if query.session_id:
                session_entries = self._session_index.get(query.session_id, set())
                candidate_ids &= session_entries
            
            # Filter by categories
            if query.categories:
                category_entries: Set[str] = set()
                for cat in query.categories:
                    category_entries |= self._category_index.get(cat, set())
                candidate_ids &= category_entries
            
            # Filter by tags
            if query.tags:
                tag_entries: Set[str] = set()
                for tag in query.tags:
                    tag_entries |= self._tag_index.get(tag, set())
                candidate_ids &= tag_entries
            
            # Collect and filter entries
            results: List[SharedMemoryEntry] = []
            source_breakdown: Dict[str, int] = defaultdict(int)
            
            for entry_id in candidate_ids:
                entry = self._entries.get(entry_id)
                if entry is None:
                    continue
                
                # Check access
                if not entry.access_control.can_read(
                    query.user_id or "", query.team_id
                ):
                    if not (query.include_public and entry.access_control.access_level == AccessLevel.PUBLIC):
                        continue
                
                # Check expiration
                if entry.access_control.is_expired():
                    continue
                
                # Check age
                if query.max_age_hours:
                    max_age = timedelta(hours=query.max_age_hours)
                    created = entry.created_at if entry.created_at.tzinfo else entry.created_at.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - created > max_age:
                        continue
                
                results.append(entry)
                source_breakdown[entry.access_control.access_level.value] += 1
            
            # Sort by recency and limit
            results.sort(key=lambda e: e.updated_at, reverse=True)
            total_found = len(results)
            results = results[:query.limit]
            
            query_time = (time.time() - start_time) * 1000
            
            return SharedMemoryResult(
                entries=results,
                total_found=total_found,
                query_time_ms=query_time,
                source_breakdown=dict(source_breakdown),
            )
    
    async def update(self, entry_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return False
            
            if not entry.access_control.can_write(user_id):
                logger.warning("Access denied: user %s cannot write entry %s", user_id, entry_id[:8])
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(entry, key) and key not in ('id', 'owner_id'):
                    setattr(entry, key, value)
            
            entry.updated_at = datetime.now(timezone.utc)
            return True
    
    async def delete(self, entry_id: str, user_id: str) -> bool:
        """Delete a memory entry."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return False
            
            if entry.owner_id != user_id:
                logger.warning("Access denied: only owner can delete entry %s", entry_id[:8])
                return False
            
            # Remove from all indices
            self._user_index[entry.owner_id].discard(entry_id)
            if entry.session_id:
                self._session_index[entry.session_id].discard(entry_id)
            self._category_index[entry.category].discard(entry_id)
            for tag in entry.tags:
                self._tag_index[tag].discard(entry_id)
            
            del self._entries[entry_id]
            return True
    
    async def share(self, entry_id: str, owner_id: str, share_with: List[str]) -> bool:
        """Share an entry with other users."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.owner_id != owner_id:
                return False
            
            entry.access_control.allowed_users.update(share_with)
            if entry.access_control.access_level == AccessLevel.PRIVATE:
                entry.access_control.access_level = AccessLevel.USER
            
            entry.updated_at = datetime.now(timezone.utc)
            return True


# ==============================================================================
# Shared Memory Manager
# ==============================================================================

class SharedMemoryManager:
    """Manager for shared memory operations with multi-tenant support.
    
    Features:
    - Cross-session memory for user continuity
    - Inter-agent communication within queries
    - Team/organization sharing with ACLs
    - Category-based organization
    - Retention policies
    """
    
    def __init__(
        self,
        store: Optional[SharedMemoryStore] = None,
        embedding_service: Optional[Any] = None,
        default_ttl_hours: int = 24 * 7,  # 1 week default
        max_entries_per_user: int = 1000,
    ):
        """
        Initialize shared memory manager.
        
        Args:
            store: Backend storage implementation
            embedding_service: Optional embedding service for semantic search
            default_ttl_hours: Default TTL for entries in hours
            max_entries_per_user: Maximum entries per user
        """
        self._store = store or InMemorySharedStore()
        self._embedding_service = embedding_service
        self._default_ttl_hours = default_ttl_hours
        self._max_entries_per_user = max_entries_per_user
        
        logger.info("SharedMemoryManager initialized")
    
    def _generate_id(self, owner_id: str, content: str) -> str:
        """Generate unique ID for an entry."""
        combined = f"{owner_id}|{content}|{time.time()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    async def store_memory(
        self,
        content: str,
        owner_id: str,
        *,
        session_id: Optional[str] = None,
        category: MemoryCategory = MemoryCategory.CONTEXT,
        access_level: AccessLevel = AccessLevel.USER,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_hours: Optional[int] = None,
        share_with: Optional[List[str]] = None,
    ) -> str:
        """
        Store a memory entry.
        
        Args:
            content: Content to store
            owner_id: Owner user ID
            session_id: Optional session ID
            category: Memory category
            access_level: Access level
            tags: Optional tags
            metadata: Optional metadata
            ttl_hours: TTL in hours (None = use default)
            share_with: List of user IDs to share with
            
        Returns:
            Entry ID
        """
        if not content or not content.strip():
            return ""
        
        # Generate entry ID
        entry_id = self._generate_id(owner_id, content)
        
        # Calculate expiration
        ttl = ttl_hours if ttl_hours is not None else self._default_ttl_hours
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl) if ttl > 0 else None
        
        # Build access control
        access_control = AccessControl(
            owner_id=owner_id,
            access_level=access_level,
            allowed_users=set(share_with or []),
            expires_at=expires_at,
        )
        
        # Build metadata
        entry_metadata = metadata or {}
        if session_id:
            entry_metadata["session_id"] = session_id
        
        # Generate embedding if service available
        embedding = None
        if self._embedding_service:
            try:
                embedding = self._embedding_service.get_embedding(content)
            except Exception as e:
                logger.debug("Failed to generate embedding: %s", e)
        
        # Create entry
        entry = SharedMemoryEntry(
            id=entry_id,
            content=content,
            owner_id=owner_id,
            access_control=access_control,
            category=category,
            tags=list(tags or []),
            metadata=entry_metadata,
            embedding=embedding,
        )
        
        # Store
        await self._store.store(entry)
        
        logger.info(
            "Stored shared memory: id=%s, owner=%s, category=%s, access=%s",
            entry_id[:8], owner_id, category.value, access_level.value
        )
        
        return entry_id
    
    async def query_memory(
        self,
        user_id: str,
        *,
        query_text: Optional[str] = None,
        session_id: Optional[str] = None,
        team_id: Optional[str] = None,
        categories: Optional[List[MemoryCategory]] = None,
        tags: Optional[List[str]] = None,
        include_public: bool = True,
        max_age_hours: Optional[int] = None,
        limit: int = 10,
    ) -> SharedMemoryResult:
        """
        Query shared memory.
        
        Args:
            user_id: User ID for access control
            query_text: Optional semantic query
            session_id: Filter by session
            team_id: Team ID for team-level access
            categories: Filter by categories
            tags: Filter by tags
            include_public: Include public entries
            max_age_hours: Maximum age filter
            limit: Maximum results
            
        Returns:
            SharedMemoryResult with matching entries
        """
        query = SharedMemoryQuery(
            query_text=query_text,
            user_id=user_id,
            team_id=team_id,
            session_id=session_id,
            categories=categories,
            tags=tags,
            include_public=include_public,
            max_age_hours=max_age_hours,
            limit=limit,
        )
        
        return await self._store.query(query)
    
    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
        *,
        max_entries: int = 10,
    ) -> List[SharedMemoryEntry]:
        """
        Get memory context for a specific session.
        
        Args:
            user_id: User ID
            session_id: Session ID
            max_entries: Maximum entries to return
            
        Returns:
            List of session memory entries
        """
        result = await self.query_memory(
            user_id=user_id,
            session_id=session_id,
            categories=[MemoryCategory.CONTEXT, MemoryCategory.INTERMEDIATE],
            limit=max_entries,
        )
        return result.entries
    
    async def get_user_history(
        self,
        user_id: str,
        *,
        categories: Optional[List[MemoryCategory]] = None,
        max_age_hours: int = 24 * 30,  # 30 days
        limit: int = 50,
    ) -> List[SharedMemoryEntry]:
        """
        Get user's memory history across sessions.
        
        Args:
            user_id: User ID
            categories: Filter by categories
            max_age_hours: Maximum age
            limit: Maximum entries
            
        Returns:
            List of user's memory entries
        """
        result = await self.query_memory(
            user_id=user_id,
            categories=categories,
            include_public=False,
            max_age_hours=max_age_hours,
            limit=limit,
        )
        return result.entries
    
    async def share_memory(
        self,
        entry_id: str,
        owner_id: str,
        share_with: List[str],
    ) -> bool:
        """
        Share a memory entry with other users.
        
        Args:
            entry_id: Entry ID
            owner_id: Owner ID (must be the owner)
            share_with: List of user IDs to share with
            
        Returns:
            True if successful
        """
        return await self._store.share(entry_id, owner_id, share_with)
    
    async def store_conversation_insight(
        self,
        user_id: str,
        session_id: str,
        insight: str,
        *,
        verified: bool = False,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store a conversation insight for future reference.
        
        Args:
            user_id: User ID
            session_id: Session ID
            insight: Insight content
            verified: Whether the insight is verified
            tags: Optional tags
            
        Returns:
            Entry ID
        """
        return await self.store_memory(
            content=insight,
            owner_id=user_id,
            session_id=session_id,
            category=MemoryCategory.INSIGHT,
            access_level=AccessLevel.USER,
            tags=tags or ["insight"],
            metadata={"verified": verified},
            ttl_hours=24 * 30,  # 30 days
        )
    
    async def store_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: str,
    ) -> str:
        """
        Store a user preference.
        
        Args:
            user_id: User ID
            preference_key: Preference key (e.g., "response_style")
            preference_value: Preference value
            
        Returns:
            Entry ID
        """
        content = f"{preference_key}: {preference_value}"
        return await self.store_memory(
            content=content,
            owner_id=user_id,
            category=MemoryCategory.PREFERENCE,
            access_level=AccessLevel.USER,
            tags=["preference", preference_key],
            metadata={"preference_key": preference_key, "preference_value": preference_value},
            ttl_hours=0,  # No expiration for preferences
        )
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, str]:
        """
        Get all user preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict of preference key -> value
        """
        result = await self.query_memory(
            user_id=user_id,
            categories=[MemoryCategory.PREFERENCE],
            include_public=False,
            limit=100,
        )
        
        preferences = {}
        for entry in result.entries:
            key = entry.metadata.get("preference_key")
            value = entry.metadata.get("preference_value")
            if key and value:
                preferences[key] = value
        
        return preferences
    
    async def build_context_string(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        *,
        max_length: int = 2000,
    ) -> str:
        """
        Build a context string from shared memory for prompt augmentation.
        
        Args:
            user_id: User ID
            session_id: Optional session ID
            max_length: Maximum context length
            
        Returns:
            Formatted context string
        """
        parts = []
        total_length = 0
        
        # Get session context if available
        if session_id:
            session_entries = await self.get_session_context(
                user_id, session_id, max_entries=5
            )
            if session_entries:
                parts.append("--- Recent Session Context ---")
                for entry in session_entries[:3]:
                    text = f"[{entry.category.value}] {entry.content[:200]}"
                    if total_length + len(text) > max_length:
                        break
                    parts.append(text)
                    total_length += len(text)
        
        # Get user history
        history_entries = await self.get_user_history(
            user_id,
            categories=[MemoryCategory.INSIGHT, MemoryCategory.FACT],
            limit=5,
        )
        
        if history_entries:
            parts.append("--- Relevant Past Knowledge ---")
            for entry in history_entries[:3]:
                text = f"[{entry.category.value}] {entry.content[:200]}"
                if total_length + len(text) > max_length:
                    break
                parts.append(text)
                total_length += len(text)
        
        if not parts:
            return ""
        
        return "\n".join(parts) + "\n"


# ==============================================================================
# Global Instance
# ==============================================================================

_shared_memory_manager: Optional[SharedMemoryManager] = None


def get_shared_memory_manager() -> SharedMemoryManager:
    """Get the global shared memory manager."""
    global _shared_memory_manager
    if _shared_memory_manager is None:
        _shared_memory_manager = SharedMemoryManager()
    return _shared_memory_manager

