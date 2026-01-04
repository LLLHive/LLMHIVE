"""Concurrency and Role Management for LLMHive Stage 4.

This module implements Section 11 of Stage 4 upgrades:
- Distributed locks via Redis
- Granular access permissions
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ==============================================================================
# DISTRIBUTED LOCKING
# ==============================================================================

class LockAcquisitionError(Exception):
    """Raised when lock acquisition fails."""
    pass


class DistributedLock(ABC):
    """Abstract base for distributed locks."""
    
    @abstractmethod
    async def acquire(self, timeout: float = 10.0) -> bool:
        """Acquire the lock."""
        pass
    
    @abstractmethod
    async def release(self) -> None:
        """Release the lock."""
        pass
    
    @abstractmethod
    async def extend(self, additional_time: float) -> bool:
        """Extend the lock timeout."""
        pass
    
    @asynccontextmanager
    async def __call__(self, timeout: float = 10.0):
        """Context manager for lock acquisition."""
        acquired = await self.acquire(timeout)
        if not acquired:
            raise LockAcquisitionError(f"Failed to acquire lock within {timeout}s")
        try:
            yield self
        finally:
            await self.release()


class LocalLock(DistributedLock):
    """In-process lock for single-process deployments."""
    
    def __init__(self, name: str):
        self.name = name
        self._lock = asyncio.Lock()
        self._acquired = False
    
    async def acquire(self, timeout: float = 10.0) -> bool:
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            self._acquired = True
            logger.debug("Local lock %s acquired", self.name)
            return True
        except asyncio.TimeoutError:
            logger.warning("Local lock %s acquisition timed out", self.name)
            return False
    
    async def release(self) -> None:
        if self._acquired:
            self._lock.release()
            self._acquired = False
            logger.debug("Local lock %s released", self.name)
    
    async def extend(self, additional_time: float) -> bool:
        # Local locks don't need extension
        return self._acquired


class RedisLock(DistributedLock):
    """Redis-based distributed lock for multi-process deployments.
    
    Implements Stage 4 Section 11: Distributed locks via Redis.
    """
    
    def __init__(
        self,
        name: str,
        redis_client: Any,
        lock_ttl: float = 30.0,
        retry_interval: float = 0.1,
    ):
        self.name = name
        self._redis = redis_client
        self._ttl = lock_ttl
        self._retry_interval = retry_interval
        self._lock_key = f"llmhive:lock:{name}"
        self._lock_value: Optional[str] = None
    
    async def acquire(self, timeout: float = 10.0) -> bool:
        import uuid
        
        self._lock_value = str(uuid.uuid4())
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                # Try to set lock with NX (only if not exists)
                result = await self._redis.set(
                    self._lock_key,
                    self._lock_value,
                    nx=True,
                    ex=int(self._ttl),
                )
                
                if result:
                    logger.debug("Redis lock %s acquired", self.name)
                    return True
                
            except Exception as e:
                logger.warning("Redis lock error: %s", e)
            
            await asyncio.sleep(self._retry_interval)
        
        logger.warning("Redis lock %s acquisition timed out", self.name)
        return False
    
    async def release(self) -> None:
        if not self._lock_value:
            return
        
        try:
            # Lua script for atomic check-and-delete
            lua_script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
            """
            
            await self._redis.eval(
                lua_script,
                1,
                self._lock_key,
                self._lock_value,
            )
            logger.debug("Redis lock %s released", self.name)
            
        except Exception as e:
            logger.warning("Redis lock release error: %s", e)
        
        self._lock_value = None
    
    async def extend(self, additional_time: float) -> bool:
        if not self._lock_value:
            return False
        
        try:
            # Lua script for atomic check-and-extend
            lua_script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('expire', KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            
            result = await self._redis.eval(
                lua_script,
                1,
                self._lock_key,
                self._lock_value,
                int(additional_time),
            )
            
            return result == 1
            
        except Exception as e:
            logger.warning("Redis lock extend error: %s", e)
            return False


class LockManager:
    """Manages distributed locks with automatic backend selection.
    
    Uses Redis when available, falls back to local locks.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self._redis_client = None
        self._use_redis = False
        
        if redis_url:
            self._init_redis(redis_url)
    
    def _init_redis(self, url: str):
        """Initialize Redis client."""
        try:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(url)
            self._use_redis = True
            logger.info("Lock manager using Redis")
        except ImportError:
            logger.warning("redis package not installed, using local locks")
        except Exception as e:
            logger.warning("Redis initialization failed: %s, using local locks", e)
    
    def get_lock(self, name: str, ttl: float = 30.0) -> DistributedLock:
        """Get a lock by name."""
        if self._use_redis and self._redis_client:
            return RedisLock(name, self._redis_client, lock_ttl=ttl)
        else:
            return LocalLock(name)
    
    @asynccontextmanager
    async def lock(self, name: str, timeout: float = 10.0, ttl: float = 30.0):
        """Context manager for acquiring a lock."""
        lock = self.get_lock(name, ttl)
        async with lock(timeout):
            yield lock


# ==============================================================================
# ACCESS PERMISSIONS
# ==============================================================================

class Role(Enum):
    """User roles for access control."""
    GUEST = "guest"
    MEMBER = "member"
    EDITOR = "editor"
    ADMIN = "admin"
    OWNER = "owner"


class Permission(Enum):
    """Specific permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    SHARE = "share"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: {Permission.READ},
    Role.MEMBER: {Permission.READ, Permission.WRITE},
    Role.EDITOR: {Permission.READ, Permission.WRITE},
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN},
    Role.OWNER: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.SHARE},
}


@dataclass
class AccessControl:
    """Access control settings for a resource.
    
    Implements Stage 4 Section 11: Granular access permissions.
    """
    owner_id: str
    allowed_users: Set[str] = field(default_factory=set)
    allowed_teams: Set[str] = field(default_factory=set)
    read_only: bool = False
    user_roles: Dict[str, Role] = field(default_factory=dict)
    public: bool = False
    
    def can_read(self, user_id: str, user_teams: Optional[Set[str]] = None) -> bool:
        """Check if user can read the resource."""
        if self.public:
            return True
        if user_id == self.owner_id:
            return True
        if user_id in self.allowed_users:
            return True
        if user_teams and self.allowed_teams & user_teams:
            return True
        return False
    
    def can_write(self, user_id: str, user_teams: Optional[Set[str]] = None) -> bool:
        """Check if user can write to the resource."""
        if self.read_only and user_id != self.owner_id:
            return False
        if user_id == self.owner_id:
            return True
        
        role = self.user_roles.get(user_id, Role.GUEST)
        if Permission.WRITE in ROLE_PERMISSIONS.get(role, set()):
            return True
        
        if user_id in self.allowed_users and not self.read_only:
            return True
        
        return False
    
    def can_delete(self, user_id: str) -> bool:
        """Check if user can delete the resource."""
        if user_id == self.owner_id:
            return True
        
        role = self.user_roles.get(user_id, Role.GUEST)
        return Permission.DELETE in ROLE_PERMISSIONS.get(role, set())
    
    def can_admin(self, user_id: str) -> bool:
        """Check if user has admin access."""
        if user_id == self.owner_id:
            return True
        
        role = self.user_roles.get(user_id, Role.GUEST)
        return Permission.ADMIN in ROLE_PERMISSIONS.get(role, set())
    
    def grant_access(self, user_id: str, role: Role) -> None:
        """Grant access to a user."""
        self.allowed_users.add(user_id)
        self.user_roles[user_id] = role
        logger.info("Granted %s access to user %s", role.value, user_id)
    
    def revoke_access(self, user_id: str) -> None:
        """Revoke access from a user."""
        self.allowed_users.discard(user_id)
        self.user_roles.pop(user_id, None)
        logger.info("Revoked access from user %s", user_id)


@dataclass
class MemoryEntry:
    """A memory entry with access control."""
    entry_id: str
    content: str
    owner_id: str
    access: AccessControl = field(default_factory=lambda: AccessControl(owner_id=""))
    created_at: Optional[float] = None
    
    def __post_init__(self):
        if not self.access.owner_id:
            self.access.owner_id = self.owner_id


class PermissionChecker:
    """Checks permissions for memory operations."""
    
    def __init__(self, user_service: Optional[Any] = None):
        self._user_service = user_service
    
    async def check_read(
        self,
        entry: MemoryEntry,
        user_id: str,
    ) -> bool:
        """Check read permission."""
        user_teams = await self._get_user_teams(user_id)
        return entry.access.can_read(user_id, user_teams)
    
    async def check_write(
        self,
        entry: MemoryEntry,
        user_id: str,
    ) -> bool:
        """Check write permission."""
        user_teams = await self._get_user_teams(user_id)
        return entry.access.can_write(user_id, user_teams)
    
    async def check_delete(
        self,
        entry: MemoryEntry,
        user_id: str,
    ) -> bool:
        """Check delete permission."""
        return entry.access.can_delete(user_id)
    
    async def _get_user_teams(self, user_id: str) -> Set[str]:
        """Get teams for a user."""
        if self._user_service:
            try:
                return await self._user_service.get_teams(user_id)
            except Exception:
                pass
        return set()


# ==============================================================================
# CONCURRENT MEMORY STORE
# ==============================================================================

class ConcurrentMemoryStore:
    """Thread-safe memory store with distributed locking.
    
    Supports multi-process deployments with Redis locks.
    """
    
    def __init__(
        self,
        lock_manager: Optional[LockManager] = None,
        permission_checker: Optional[PermissionChecker] = None,
    ):
        self._lock_manager = lock_manager or LockManager()
        self._permission_checker = permission_checker or PermissionChecker()
        self._entries: Dict[str, MemoryEntry] = {}
        self._local_lock = threading.RLock()
    
    async def store(
        self,
        entry: MemoryEntry,
        user_id: str,
    ) -> bool:
        """Store an entry with locking."""
        lock_name = f"memory:{entry.entry_id}"
        
        async with self._lock_manager.lock(lock_name, timeout=5.0):
            # Check if updating existing
            if entry.entry_id in self._entries:
                existing = self._entries[entry.entry_id]
                if not await self._permission_checker.check_write(existing, user_id):
                    logger.warning("Permission denied for user %s to write %s", user_id, entry.entry_id)
                    return False
            
            with self._local_lock:
                self._entries[entry.entry_id] = entry
            
            logger.debug("Stored entry %s", entry.entry_id)
            return True
    
    async def get(
        self,
        entry_id: str,
        user_id: str,
    ) -> Optional[MemoryEntry]:
        """Get an entry with permission check."""
        with self._local_lock:
            entry = self._entries.get(entry_id)
        
        if not entry:
            return None
        
        if not await self._permission_checker.check_read(entry, user_id):
            logger.warning("Permission denied for user %s to read %s", user_id, entry_id)
            return None
        
        return entry
    
    async def delete(
        self,
        entry_id: str,
        user_id: str,
    ) -> bool:
        """Delete an entry with locking and permission check."""
        lock_name = f"memory:{entry_id}"
        
        async with self._lock_manager.lock(lock_name, timeout=5.0):
            with self._local_lock:
                entry = self._entries.get(entry_id)
            
            if not entry:
                return False
            
            if not await self._permission_checker.check_delete(entry, user_id):
                logger.warning("Permission denied for user %s to delete %s", user_id, entry_id)
                return False
            
            with self._local_lock:
                del self._entries[entry_id]
            
            logger.debug("Deleted entry %s", entry_id)
            return True
    
    async def list_for_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """List entries accessible by user."""
        results = []
        
        with self._local_lock:
            entries = list(self._entries.values())
        
        for entry in entries:
            if await self._permission_checker.check_read(entry, user_id):
                results.append(entry)
                if len(results) >= limit:
                    break
        
        return results


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================

def create_lock_manager(redis_url: Optional[str] = None) -> LockManager:
    """Create a lock manager."""
    return LockManager(redis_url)


def create_access_control(owner_id: str, public: bool = False) -> AccessControl:
    """Create access control settings."""
    return AccessControl(owner_id=owner_id, public=public)


def create_permission_checker() -> PermissionChecker:
    """Create a permission checker."""
    return PermissionChecker()


def create_concurrent_memory_store(
    redis_url: Optional[str] = None,
) -> ConcurrentMemoryStore:
    """Create a concurrent memory store."""
    lock_manager = create_lock_manager(redis_url)
    return ConcurrentMemoryStore(lock_manager=lock_manager)

