"""Data Retention Policies for LLMHive.

This module manages data retention:
- Configurable retention periods by data category
- Automatic cleanup of expired data
- Retention policy enforcement
- Compliance reporting

Usage:
    manager = get_retention_manager()
    
    # Configure retention
    manager.set_policy(DataCategory.MEMORY, days=90)
    
    # Run cleanup
    deleted = await manager.cleanup_expired()
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class DataCategory(str, Enum):
    """Categories of data with retention policies."""
    MEMORY = "memory"  # Persistent memories
    CONVERSATIONS = "conversations"  # Chat history
    USAGE_LOGS = "usage_logs"  # Request logs
    AUDIT_LOGS = "audit_logs"  # Security audit logs
    EXPORTS = "exports"  # Data exports
    CACHE = "cache"  # Cached data
    TEMP = "temp"  # Temporary data


@dataclass(slots=True)
class RetentionPolicy:
    """Retention policy for a data category."""
    category: DataCategory
    retention_days: int  # -1 = forever
    description: Optional[str] = None
    requires_consent: bool = False
    can_extend: bool = True
    
    @property
    def expires_after(self) -> Optional[timedelta]:
        if self.retention_days < 0:
            return None
        return timedelta(days=self.retention_days)


@dataclass(slots=True)
class CleanupResult:
    """Result of retention cleanup."""
    category: DataCategory
    items_deleted: int
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


# Default retention policies
DEFAULT_POLICIES = {
    DataCategory.MEMORY: RetentionPolicy(
        category=DataCategory.MEMORY,
        retention_days=365,  # 1 year
        description="User persistent memories",
        requires_consent=True,
    ),
    DataCategory.CONVERSATIONS: RetentionPolicy(
        category=DataCategory.CONVERSATIONS,
        retention_days=90,  # 90 days
        description="Chat conversation history",
    ),
    DataCategory.USAGE_LOGS: RetentionPolicy(
        category=DataCategory.USAGE_LOGS,
        retention_days=30,  # 30 days
        description="API usage and request logs",
    ),
    DataCategory.AUDIT_LOGS: RetentionPolicy(
        category=DataCategory.AUDIT_LOGS,
        retention_days=365 * 7,  # 7 years for compliance
        description="Security and compliance audit logs",
        can_extend=False,
    ),
    DataCategory.EXPORTS: RetentionPolicy(
        category=DataCategory.EXPORTS,
        retention_days=30,
        description="User data export files",
    ),
    DataCategory.CACHE: RetentionPolicy(
        category=DataCategory.CACHE,
        retention_days=7,
        description="Cached API responses",
    ),
    DataCategory.TEMP: RetentionPolicy(
        category=DataCategory.TEMP,
        retention_days=1,
        description="Temporary processing data",
    ),
}


# ==============================================================================
# Data Retention Manager
# ==============================================================================

class DataRetentionManager:
    """Manager for data retention policies.
    
    Features:
    - Configurable retention periods
    - Automatic cleanup scheduling
    - Category-specific handlers
    - Compliance reporting
    
    Usage:
        manager = DataRetentionManager()
        
        # Set custom policy
        manager.set_policy(DataCategory.MEMORY, days=180)
        
        # Register cleanup handler
        manager.register_cleanup_handler(DataCategory.MEMORY, cleanup_memories)
        
        # Run cleanup
        results = await manager.cleanup_expired()
    """
    
    def __init__(
        self,
        policies: Optional[Dict[DataCategory, RetentionPolicy]] = None,
    ):
        self.policies = policies or dict(DEFAULT_POLICIES)
        self._cleanup_handlers: Dict[DataCategory, Callable] = {}
        self._last_cleanup: Optional[datetime] = None
    
    def get_policy(self, category: DataCategory) -> RetentionPolicy:
        """Get retention policy for a category."""
        return self.policies.get(category, DEFAULT_POLICIES.get(category))
    
    def set_policy(
        self,
        category: DataCategory,
        days: int,
        **kwargs,
    ) -> None:
        """Set retention policy for a category."""
        self.policies[category] = RetentionPolicy(
            category=category,
            retention_days=days,
            **kwargs,
        )
        logger.info("Set retention policy: %s = %d days", category.value, days)
    
    def register_cleanup_handler(
        self,
        category: DataCategory,
        handler: Callable,
    ) -> None:
        """Register a cleanup handler for a category.
        
        Handler signature: async (cutoff_date: datetime) -> int (items deleted)
        """
        self._cleanup_handlers[category] = handler
        logger.debug("Registered cleanup handler: %s", category.value)
    
    async def cleanup_expired(
        self,
        categories: Optional[List[DataCategory]] = None,
        dry_run: bool = False,
    ) -> List[CleanupResult]:
        """
        Clean up expired data across categories.
        
        Args:
            categories: Specific categories to clean (None = all)
            dry_run: If True, don't actually delete
            
        Returns:
            List of CleanupResult for each category
        """
        logger.info("Starting retention cleanup (dry_run=%s)", dry_run)
        start_time = time.time()
        
        results: List[CleanupResult] = []
        categories_to_clean = categories or list(self.policies.keys())
        
        for category in categories_to_clean:
            policy = self.get_policy(category)
            if not policy or policy.retention_days < 0:
                continue  # No expiration
            
            handler = self._cleanup_handlers.get(category)
            if not handler:
                continue  # No handler registered
            
            cutoff = datetime.now(timezone.utc) - policy.expires_after
            result = CleanupResult(category=category, items_deleted=0)
            
            try:
                step_start = time.time()
                
                if dry_run:
                    # Just count, don't delete
                    count = 0
                else:
                    if asyncio.iscoroutinefunction(handler):
                        count = await handler(cutoff)
                    else:
                        count = await asyncio.to_thread(handler, cutoff)
                
                result.items_deleted = count or 0
                result.duration_ms = (time.time() - step_start) * 1000
                
                if count:
                    logger.info(
                        "Cleaned %d items from %s (cutoff: %s)",
                        count, category.value, cutoff.isoformat(),
                    )
                    
            except Exception as e:
                result.errors.append(str(e))
                logger.error("Cleanup error for %s: %s", category.value, e)
            
            results.append(result)
        
        self._last_cleanup = datetime.now(timezone.utc)
        total_deleted = sum(r.items_deleted for r in results)
        total_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Retention cleanup completed: %d items deleted in %.1fms",
            total_deleted, total_time,
        )
        
        return results
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report for data retention."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "last_cleanup": self._last_cleanup.isoformat() if self._last_cleanup else None,
            "policies": {},
        }
        
        for category, policy in self.policies.items():
            report["policies"][category.value] = {
                "retention_days": policy.retention_days,
                "description": policy.description,
                "requires_consent": policy.requires_consent,
                "has_handler": category in self._cleanup_handlers,
            }
        
        return report


# ==============================================================================
# Default Cleanup Handlers
# ==============================================================================

async def _cleanup_temp_files(cutoff: datetime) -> int:
    """Clean up temporary files older than cutoff."""
    import os
    from pathlib import Path
    
    temp_dir = Path(os.getenv("LLMHIVE_TEMP_DIR", "/tmp/llmhive"))
    if not temp_dir.exists():
        return 0
    
    deleted = 0
    cutoff_ts = cutoff.timestamp()
    
    for file in temp_dir.iterdir():
        try:
            if file.stat().st_mtime < cutoff_ts:
                file.unlink()
                deleted += 1
        except Exception:
            pass
    
    return deleted


async def _cleanup_cache(cutoff: datetime) -> int:
    """Clean up cache entries older than cutoff."""
    # Placeholder - implement based on your cache backend
    return 0


# ==============================================================================
# Global Instance
# ==============================================================================

_retention_manager: Optional[DataRetentionManager] = None


def get_retention_manager() -> DataRetentionManager:
    """Get or create global retention manager."""
    global _retention_manager
    if _retention_manager is None:
        _retention_manager = DataRetentionManager()
        
        # Register default handlers
        _retention_manager.register_cleanup_handler(
            DataCategory.TEMP, _cleanup_temp_files
        )
        _retention_manager.register_cleanup_handler(
            DataCategory.CACHE, _cleanup_cache
        )
    
    return _retention_manager


# ==============================================================================
# Scheduled Cleanup
# ==============================================================================

async def run_scheduled_cleanup(
    interval_hours: int = 24,
    categories: Optional[List[DataCategory]] = None,
):
    """Run cleanup on a schedule."""
    logger.info("Starting scheduled cleanup (interval=%d hours)", interval_hours)
    
    while True:
        try:
            manager = get_retention_manager()
            await manager.cleanup_expired(categories=categories)
        except Exception as e:
            logger.error("Scheduled cleanup error: %s", e)
        
        await asyncio.sleep(interval_hours * 3600)

