"""Agent Blackboard - Shared memory for inter-agent communication.

The blackboard is a thread-safe shared data structure where agents can:
- Post findings, results, and recommendations
- Read other agents' contributions
- Coordinate on complex tasks

Design Pattern: Blackboard Architecture
- Multiple agents contribute to a shared knowledge space
- Agents can read from and write to the blackboard
- Enables emergent cooperation without direct coupling
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from threading import RLock
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BlackboardEntry:
    """An entry on the blackboard."""
    key: str
    value: Any
    source_agent: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 3600  # Default 1 hour
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    priority: int = 0  # Higher = more important
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        age_seconds = (datetime.now() - self.created_at).total_seconds()
        return age_seconds > self.ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "source_agent": self.source_agent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
            "tags": self.tags,
            "priority": self.priority,
        }


class AgentBlackboard:
    """Thread-safe shared memory space for agent communication.
    
    Features:
    - Key-value storage with TTL
    - Topic-based subscriptions
    - Query by agent, tag, or time
    - Automatic expiration cleanup
    """
    
    def __init__(self, cleanup_interval_seconds: int = 300):
        """Initialize the blackboard.
        
        Args:
            cleanup_interval_seconds: How often to run cleanup
        """
        self._entries: Dict[str, BlackboardEntry] = {}
        self._lock = RLock()
        self._subscribers: Dict[str, List[callable]] = defaultdict(list)
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("AgentBlackboard initialized")
    
    async def start(self) -> None:
        """Start the blackboard background tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Blackboard cleanup task started")
    
    async def stop(self) -> None:
        """Stop the blackboard background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Blackboard cleanup task stopped")
    
    async def write(
        self,
        key: str,
        value: Any,
        source_agent: str,
        ttl_seconds: int = 3600,
        tags: Optional[List[str]] = None,
        priority: int = 0,
    ) -> bool:
        """Write a value to the blackboard.
        
        Args:
            key: Unique key for the entry
            value: Value to store
            source_agent: Name of agent writing
            ttl_seconds: Time-to-live
            tags: Optional categorization tags
            priority: Priority level (higher = more important)
            
        Returns:
            True if successful
        """
        with self._lock:
            entry = BlackboardEntry(
                key=key,
                value=value,
                source_agent=source_agent,
                ttl_seconds=ttl_seconds,
                tags=tags or [],
                priority=priority,
            )
            
            is_update = key in self._entries
            self._entries[key] = entry
            
            logger.debug(
                f"Blackboard: {'Updated' if is_update else 'Created'} "
                f"'{key}' from {source_agent}"
            )
        
        # Notify subscribers
        await self._notify_subscribers(key, entry)
        
        return True
    
    async def read(self, key: str) -> Optional[Any]:
        """Read a value from the blackboard.
        
        Args:
            key: Key to read
            
        Returns:
            Value if found and not expired, None otherwise
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            
            if entry.is_expired:
                del self._entries[key]
                return None
            
            entry.access_count += 1
            return entry.value
    
    async def read_entry(self, key: str) -> Optional[BlackboardEntry]:
        """Read full entry (including metadata) from the blackboard.
        
        Args:
            key: Key to read
            
        Returns:
            Full BlackboardEntry if found
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.is_expired:
                return None
            entry.access_count += 1
            return entry
    
    async def delete(self, key: str) -> bool:
        """Delete an entry from the blackboard.
        
        Args:
            key: Key to delete
            
        Returns:
            True if entry was deleted
        """
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                logger.debug(f"Blackboard: Deleted '{key}'")
                return True
            return False
    
    async def query_by_agent(self, agent_name: str) -> List[BlackboardEntry]:
        """Get all entries from a specific agent.
        
        Args:
            agent_name: Name of agent
            
        Returns:
            List of entries from that agent
        """
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.source_agent == agent_name and not e.is_expired
            ]
    
    async def query_by_tag(self, tag: str) -> List[BlackboardEntry]:
        """Get all entries with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of entries with that tag
        """
        with self._lock:
            return [
                e for e in self._entries.values()
                if tag in e.tags and not e.is_expired
            ]
    
    async def query_by_prefix(self, prefix: str) -> List[BlackboardEntry]:
        """Get all entries with keys starting with prefix.
        
        Args:
            prefix: Key prefix
            
        Returns:
            List of matching entries
        """
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.key.startswith(prefix) and not e.is_expired
            ]
    
    async def query_recent(
        self,
        max_age_seconds: int = 3600,
        limit: int = 100
    ) -> List[BlackboardEntry]:
        """Get recent entries.
        
        Args:
            max_age_seconds: Maximum age of entries
            limit: Maximum number to return
            
        Returns:
            List of recent entries, newest first
        """
        cutoff = datetime.now()
        with self._lock:
            recent = [
                e for e in self._entries.values()
                if (cutoff - e.created_at).total_seconds() <= max_age_seconds
                and not e.is_expired
            ]
            recent.sort(key=lambda x: x.created_at, reverse=True)
            return recent[:limit]
    
    def subscribe(self, key_pattern: str, callback: callable) -> None:
        """Subscribe to updates matching a key pattern.
        
        Args:
            key_pattern: Key or prefix to watch (* for all)
            callback: Async function to call on updates
        """
        self._subscribers[key_pattern].append(callback)
        logger.debug(f"Blackboard: New subscriber for '{key_pattern}'")
    
    def unsubscribe(self, key_pattern: str, callback: callable) -> None:
        """Unsubscribe from updates.
        
        Args:
            key_pattern: Pattern that was subscribed to
            callback: Callback to remove
        """
        if key_pattern in self._subscribers:
            self._subscribers[key_pattern] = [
                c for c in self._subscribers[key_pattern] if c != callback
            ]
    
    async def _notify_subscribers(self, key: str, entry: BlackboardEntry) -> None:
        """Notify subscribers of an update."""
        callbacks_to_run = []
        
        # Exact match subscribers
        if key in self._subscribers:
            callbacks_to_run.extend(self._subscribers[key])
        
        # Prefix match subscribers
        for pattern, callbacks in self._subscribers.items():
            if pattern.endswith("*") and key.startswith(pattern[:-1]):
                callbacks_to_run.extend(callbacks)
        
        # Global subscribers
        if "*" in self._subscribers:
            callbacks_to_run.extend(self._subscribers["*"])
        
        for callback in callbacks_to_run:
            try:
                await callback(key, entry)
            except Exception as e:
                logger.error(f"Subscriber callback error: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Blackboard cleanup error: {e}")
    
    async def _cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                k for k, v in self._entries.items() if v.is_expired
            ]
            for key in expired_keys:
                del self._entries[key]
            
            if expired_keys:
                logger.debug(f"Blackboard: Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get blackboard statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            entries_by_agent = defaultdict(int)
            for entry in self._entries.values():
                entries_by_agent[entry.source_agent] += 1
            
            return {
                "total_entries": len(self._entries),
                "entries_by_agent": dict(entries_by_agent),
                "total_subscribers": sum(
                    len(cbs) for cbs in self._subscribers.values()
                ),
                "cleanup_interval_seconds": self._cleanup_interval,
            }


# Global blackboard instance
_global_blackboard: Optional[AgentBlackboard] = None


def get_global_blackboard() -> AgentBlackboard:
    """Get or create the global blackboard instance.
    
    Returns:
        The global AgentBlackboard
    """
    global _global_blackboard
    if _global_blackboard is None:
        _global_blackboard = AgentBlackboard()
    return _global_blackboard

