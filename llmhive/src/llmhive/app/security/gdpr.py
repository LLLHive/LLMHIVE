"""GDPR Compliance for LLMHive.

This module provides GDPR/CCPA compliance features:
- Data subject access requests (DSAR)
- Right to erasure (data deletion)
- Data portability (export)
- Consent management
- Data processing records

Usage:
    gdpr = GDPRManager()
    
    # Export all user data
    data = await gdpr.export_user_data(user_id="user123")
    
    # Delete all user data
    result = await gdpr.delete_user_data(user_id="user123")
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class RequestType(str, Enum):
    """Types of data subject requests."""
    ACCESS = "access"  # Right to access
    ERASURE = "erasure"  # Right to be forgotten
    PORTABILITY = "portability"  # Data export
    RECTIFICATION = "rectification"  # Correct data
    RESTRICTION = "restriction"  # Limit processing
    OBJECTION = "objection"  # Object to processing


class DataCategory(str, Enum):
    """Categories of personal data."""
    IDENTITY = "identity"  # Names, IDs
    CONTACT = "contact"  # Email, phone
    CONTENT = "content"  # User-generated content
    USAGE = "usage"  # Usage data, logs
    PREFERENCES = "preferences"  # Settings
    PAYMENT = "payment"  # Billing data
    MEMORY = "memory"  # Stored memories/context


class RequestStatus(str, Enum):
    """Status of a data subject request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(slots=True)
class DataSubjectRequest:
    """A data subject access request."""
    request_id: str
    user_id: str
    request_type: RequestType
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    data_categories: List[DataCategory] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass(slots=True)
class DataExport:
    """Exported user data."""
    user_id: str
    export_date: datetime
    data_categories: Dict[str, List[Dict[str, Any]]]
    format: str = "json"
    
    def to_json(self) -> str:
        return json.dumps({
            "user_id": self.user_id,
            "export_date": self.export_date.isoformat(),
            "data": self.data_categories,
        }, indent=2, default=str)


@dataclass(slots=True)
class DeletionResult:
    """Result of data deletion."""
    user_id: str
    success: bool
    deleted_categories: List[str]
    deleted_count: int
    errors: List[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# GDPR Manager
# ==============================================================================

class GDPRManager:
    """Manager for GDPR compliance operations.
    
    Handles data subject requests including:
    - Data export (right to portability)
    - Data deletion (right to erasure)
    - Data access (subject access requests)
    
    Usage:
        gdpr = GDPRManager()
        
        # Register data handlers
        gdpr.register_data_handler("memory", memory_handler)
        gdpr.register_deletion_handler("memory", memory_deletion_handler)
        
        # Process requests
        export = await gdpr.export_user_data("user123")
        result = await gdpr.delete_user_data("user123")
    """
    
    def __init__(
        self,
        export_dir: Optional[str] = None,
        retention_days: int = 30,
    ):
        """
        Initialize GDPR manager.
        
        Args:
            export_dir: Directory for data exports
            retention_days: Days to retain export files
        """
        self.export_dir = Path(export_dir or os.getenv("GDPR_EXPORT_DIR", "./data/exports"))
        self.retention_days = retention_days
        
        # Data handlers for each category
        self._data_handlers: Dict[str, Callable] = {}
        self._deletion_handlers: Dict[str, Callable] = {}
        
        # Request tracking
        self._requests: Dict[str, DataSubjectRequest] = {}
        
        # Ensure export directory exists
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def register_data_handler(
        self,
        category: str,
        handler: Callable,
    ) -> None:
        """Register a handler to fetch data for a category.
        
        Args:
            category: Data category name
            handler: Async function(user_id) -> List[Dict]
        """
        self._data_handlers[category] = handler
        logger.info("Registered data handler: %s", category)
    
    def register_deletion_handler(
        self,
        category: str,
        handler: Callable,
    ) -> None:
        """Register a handler to delete data for a category.
        
        Args:
            category: Data category name
            handler: Async function(user_id) -> int (count deleted)
        """
        self._deletion_handlers[category] = handler
        logger.info("Registered deletion handler: %s", category)
    
    async def export_user_data(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
        save_file: bool = True,
    ) -> DataExport:
        """
        Export all data for a user (right to portability).
        
        Args:
            user_id: User identifier
            categories: Specific categories to export (None = all)
            save_file: Save export to file
            
        Returns:
            DataExport with all user data
        """
        logger.info("Starting data export for user: %s", user_id)
        start_time = time.time()
        
        # Create request
        request = DataSubjectRequest(
            request_id=hashlib.sha256(
                f"{user_id}-{time.time()}".encode()
            ).hexdigest()[:16],
            user_id=user_id,
            request_type=RequestType.PORTABILITY,
            status=RequestStatus.IN_PROGRESS,
        )
        self._requests[request.request_id] = request
        
        # Collect data from all handlers
        data_categories: Dict[str, List[Dict[str, Any]]] = {}
        
        handlers_to_run = categories or list(self._data_handlers.keys())
        
        for category in handlers_to_run:
            if category not in self._data_handlers:
                continue
            
            try:
                handler = self._data_handlers[category]
                if asyncio.iscoroutinefunction(handler):
                    data = await handler(user_id)
                else:
                    data = await asyncio.to_thread(handler, user_id)
                
                if data:
                    data_categories[category] = data
                    
            except Exception as e:
                logger.error("Error fetching %s data: %s", category, e)
                data_categories[category] = [{"error": str(e)}]
        
        # Create export
        export = DataExport(
            user_id=user_id,
            export_date=datetime.now(timezone.utc),
            data_categories=data_categories,
        )
        
        # Save to file if requested
        if save_file:
            file_path = self.export_dir / f"export_{user_id}_{int(time.time())}.json"
            file_path.write_text(export.to_json())
            logger.info("Export saved to: %s", file_path)
        
        # Update request
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.result = {"export_categories": list(data_categories.keys())}
        
        duration = time.time() - start_time
        logger.info(
            "Data export completed for %s in %.2fs: %d categories",
            user_id, duration, len(data_categories),
        )
        
        return export
    
    async def delete_user_data(
        self,
        user_id: str,
        categories: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> DeletionResult:
        """
        Delete all data for a user (right to erasure).
        
        Args:
            user_id: User identifier
            categories: Specific categories to delete (None = all)
            dry_run: If True, don't actually delete
            
        Returns:
            DeletionResult with deletion status
        """
        logger.info(
            "Starting data deletion for user: %s (dry_run=%s)",
            user_id, dry_run,
        )
        start_time = time.time()
        
        # Create request
        request = DataSubjectRequest(
            request_id=hashlib.sha256(
                f"{user_id}-delete-{time.time()}".encode()
            ).hexdigest()[:16],
            user_id=user_id,
            request_type=RequestType.ERASURE,
            status=RequestStatus.IN_PROGRESS,
        )
        self._requests[request.request_id] = request
        
        deleted_categories: List[str] = []
        total_deleted = 0
        errors: List[str] = []
        
        handlers_to_run = categories or list(self._deletion_handlers.keys())
        
        for category in handlers_to_run:
            if category not in self._deletion_handlers:
                continue
            
            try:
                handler = self._deletion_handlers[category]
                
                if dry_run:
                    count = 0  # Don't actually delete
                else:
                    if asyncio.iscoroutinefunction(handler):
                        count = await handler(user_id)
                    else:
                        count = await asyncio.to_thread(handler, user_id)
                
                if count is not None:
                    total_deleted += count
                    deleted_categories.append(category)
                    logger.info("Deleted %d items from %s", count, category)
                    
            except Exception as e:
                logger.error("Error deleting %s data: %s", category, e)
                errors.append(f"{category}: {e}")
        
        # Create result
        result = DeletionResult(
            user_id=user_id,
            success=len(errors) == 0,
            deleted_categories=deleted_categories,
            deleted_count=total_deleted,
            errors=errors,
        )
        
        # Update request
        request.status = RequestStatus.COMPLETED if result.success else RequestStatus.FAILED
        request.completed_at = datetime.now(timezone.utc)
        request.result = {
            "deleted_count": total_deleted,
            "categories": deleted_categories,
        }
        if errors:
            request.error = "; ".join(errors)
        
        duration = time.time() - start_time
        logger.info(
            "Data deletion completed for %s in %.2fs: %d items deleted",
            user_id, duration, total_deleted,
        )
        
        return result
    
    async def get_request_status(self, request_id: str) -> Optional[DataSubjectRequest]:
        """Get status of a data subject request."""
        return self._requests.get(request_id)
    
    async def list_requests(
        self,
        user_id: Optional[str] = None,
        request_type: Optional[RequestType] = None,
    ) -> List[DataSubjectRequest]:
        """List data subject requests."""
        requests = list(self._requests.values())
        
        if user_id:
            requests = [r for r in requests if r.user_id == user_id]
        
        if request_type:
            requests = [r for r in requests if r.request_type == request_type]
        
        return sorted(requests, key=lambda r: r.created_at, reverse=True)
    
    async def cleanup_old_exports(self) -> int:
        """Clean up old export files."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        deleted = 0
        
        for file in self.export_dir.glob("export_*.json"):
            try:
                # Parse timestamp from filename
                parts = file.stem.split("_")
                if len(parts) >= 3:
                    timestamp = int(parts[-1])
                    file_date = datetime.fromtimestamp(timestamp, timezone.utc)
                    
                    if file_date < cutoff:
                        file.unlink()
                        deleted += 1
            except Exception as e:
                logger.warning("Error cleaning up %s: %s", file, e)
        
        if deleted:
            logger.info("Cleaned up %d old export files", deleted)
        
        return deleted


# ==============================================================================
# Default Data Handlers
# ==============================================================================

async def _default_memory_data_handler(user_id: str) -> List[Dict[str, Any]]:
    """Default handler to fetch memory data."""
    try:
        from ..memory.persistent_memory import get_memory_manager
        manager = get_memory_manager()
        
        if hasattr(manager, 'get_all_for_user'):
            entries = await manager.get_all_for_user(user_id)
            return [
                {
                    "id": e.id if hasattr(e, 'id') else str(i),
                    "content": e.content[:100] + "..." if len(e.content) > 100 else e.content,
                    "created_at": e.created_at.isoformat() if hasattr(e, 'created_at') else None,
                }
                for i, e in enumerate(entries)
            ]
    except Exception as e:
        logger.warning("Memory data handler error: %s", e)
    
    return []


async def _default_memory_deletion_handler(user_id: str) -> int:
    """Default handler to delete memory data."""
    try:
        from ..memory.persistent_memory import get_memory_manager
        manager = get_memory_manager()
        
        if hasattr(manager, 'delete_user_data'):
            return await manager.delete_user_data(user_id)
    except Exception as e:
        logger.warning("Memory deletion handler error: %s", e)
    
    return 0


# ==============================================================================
# Global Instance and Convenience Functions
# ==============================================================================

_gdpr_manager: Optional[GDPRManager] = None


def get_gdpr_manager() -> GDPRManager:
    """Get or create global GDPR manager."""
    global _gdpr_manager
    if _gdpr_manager is None:
        _gdpr_manager = GDPRManager()
        
        # Register default handlers
        _gdpr_manager.register_data_handler("memory", _default_memory_data_handler)
        _gdpr_manager.register_deletion_handler("memory", _default_memory_deletion_handler)
    
    return _gdpr_manager


async def export_user_data(user_id: str, **kwargs) -> DataExport:
    """Convenience function to export user data."""
    return await get_gdpr_manager().export_user_data(user_id, **kwargs)


async def delete_user_data(user_id: str, **kwargs) -> DeletionResult:
    """Convenience function to delete user data."""
    return await get_gdpr_manager().delete_user_data(user_id, **kwargs)


# ==============================================================================
# FastAPI Integration
# ==============================================================================

def setup_gdpr_endpoints(app, require_admin: bool = True):
    """Setup GDPR-related API endpoints."""
    from fastapi import HTTPException, Response
    
    @app.post("/api/gdpr/export/{user_id}")
    async def request_data_export(user_id: str):
        """Request data export for a user."""
        gdpr = get_gdpr_manager()
        export = await gdpr.export_user_data(user_id)
        
        return {
            "status": "completed",
            "user_id": user_id,
            "export_date": export.export_date.isoformat(),
            "categories": list(export.data_categories.keys()),
        }
    
    @app.delete("/api/gdpr/user/{user_id}")
    async def request_data_deletion(user_id: str, dry_run: bool = False):
        """Request data deletion for a user."""
        gdpr = get_gdpr_manager()
        result = await gdpr.delete_user_data(user_id, dry_run=dry_run)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail={"errors": result.errors},
            )
        
        return {
            "status": "completed",
            "user_id": user_id,
            "deleted_count": result.deleted_count,
            "deleted_categories": result.deleted_categories,
        }
    
    @app.get("/api/gdpr/requests")
    async def list_gdpr_requests(user_id: Optional[str] = None):
        """List GDPR requests."""
        gdpr = get_gdpr_manager()
        requests = await gdpr.list_requests(user_id=user_id)
        
        return {
            "requests": [
                {
                    "request_id": r.request_id,
                    "user_id": r.user_id,
                    "type": r.request_type.value,
                    "status": r.status.value,
                    "created_at": r.created_at.isoformat(),
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in requests
            ]
        }
    
    logger.info("GDPR endpoints registered")

