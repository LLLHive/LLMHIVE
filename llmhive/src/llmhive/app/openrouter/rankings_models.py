"""OpenRouter Rankings Database Models.

Tables for storing rankings data synced from OpenRouter:
- Categories with hierarchy support
- Ranking snapshots for history
- Ranking entries (top models per category)

This is the canonical source of truth for OpenRouter rankings.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .models import Base


# =============================================================================
# Enums
# =============================================================================

class CategoryGroup(str, Enum):
    """Category group types."""
    USECASE = "usecase"          # Main use case categories
    LANGUAGE = "language"         # Natural language rankings
    PROGRAMMING = "programming"   # Programming language rankings


class SnapshotStatus(str, Enum):
    """Snapshot status."""
    SUCCESS = "success"
    FAIL = "fail"
    PARTIAL = "partial"


class RankingView(str, Enum):
    """Ranking time view."""
    WEEK = "week"
    MONTH = "month"
    DAY = "day"
    ALL = "all"


# =============================================================================
# OpenRouter Category
# =============================================================================

class OpenRouterCategory(Base):
    """OpenRouter ranking category.
    
    Supports nested categories (e.g., marketing/seo).
    Discovered dynamically from OpenRouter.
    """
    __tablename__ = "openrouter_categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Category identification
    slug = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    
    # Grouping
    group = Column(SQLEnum(CategoryGroup), default=CategoryGroup.USECASE, index=True)
    
    # Hierarchy (for nested categories like marketing/seo)
    parent_slug = Column(String(100), nullable=True, index=True)
    full_path = Column(String(255), nullable=True)  # e.g., "marketing/seo"
    depth = Column(Integer, default=0)  # 0 for root, 1 for nested
    
    # Source URL (for debugging)
    source_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Audit
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    snapshots = relationship("OpenRouterRankingSnapshot", back_populates="category")
    
    __table_args__ = (
        Index("ix_categories_group_active", "group", "is_active"),
        Index("ix_categories_parent", "parent_slug"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "display_name": self.display_name,
            "group": self.group.value if self.group else "usecase",
            "parent_slug": self.parent_slug,
            "full_path": self.full_path or self.slug,
            "depth": self.depth,
            "is_active": self.is_active,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


# =============================================================================
# OpenRouter Ranking Snapshot
# =============================================================================

class OpenRouterRankingSnapshot(Base):
    """Snapshot of rankings for a category at a point in time.
    
    Stores metadata about each sync attempt.
    """
    __tablename__ = "openrouter_ranking_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Category reference
    category_slug = Column(String(100), ForeignKey("openrouter_categories.slug"), nullable=False, index=True)
    
    # Grouping and view
    group = Column(SQLEnum(CategoryGroup), default=CategoryGroup.USECASE)
    view = Column(SQLEnum(RankingView), default=RankingView.WEEK)
    
    # Time period (if available from source)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    as_of_date = Column(DateTime(timezone=True), nullable=True)
    
    # Source info
    source_url = Column(String(500), nullable=True)
    
    # Fetch metadata
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    parse_version = Column(String(20), default="1.0.0")  # Bump when parser changes
    
    # Content validation
    raw_payload_hash = Column(String(64), nullable=True)  # SHA256 of raw response
    entry_count = Column(Integer, default=0)
    
    # Status
    status = Column(SQLEnum(SnapshotStatus), default=SnapshotStatus.SUCCESS)
    error = Column(Text, nullable=True)
    
    # Relationships
    category = relationship("OpenRouterCategory", back_populates="snapshots")
    entries = relationship("OpenRouterRankingEntry", back_populates="snapshot", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_snapshots_category_fetched", "category_slug", "fetched_at"),
        Index("ix_snapshots_group_view_fetched", "group", "view", "fetched_at"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category_slug": self.category_slug,
            "group": self.group.value if self.group else "usecase",
            "view": self.view.value if self.view else "week",
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "parse_version": self.parse_version,
            "entry_count": self.entry_count,
            "status": self.status.value if self.status else "unknown",
            "error": self.error,
            "entries": [e.to_dict() for e in self.entries] if self.entries else [],
        }


# =============================================================================
# OpenRouter Ranking Entry
# =============================================================================

class OpenRouterRankingEntry(Base):
    """Single ranking entry (model in a category ranking).
    
    Stores the actual ranked models with their metrics.
    """
    __tablename__ = "openrouter_ranking_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Snapshot reference
    snapshot_id = Column(Integer, ForeignKey("openrouter_ranking_snapshots.id"), nullable=False, index=True)
    
    # Rank position
    rank = Column(Integer, nullable=False)
    
    # Model identification
    model_id = Column(String(255), nullable=True, index=True)  # Canonical OpenRouter ID if resolved
    model_name = Column(String(255), nullable=False)
    author = Column(String(100), nullable=True, index=True)  # Extracted from model_id or name
    
    # Metrics from OpenRouter
    tokens = Column(Numeric(20, 0), nullable=True)  # Token count
    tokens_display = Column(String(50), nullable=True)  # e.g., "1.2B"
    share_pct = Column(Float, nullable=True)  # Percentage share
    
    # Additional metrics if available
    requests = Column(Integer, nullable=True)
    latency_avg_ms = Column(Integer, nullable=True)
    cost_per_1m = Column(Float, nullable=True)
    
    # Special flags
    is_others_bucket = Column(Boolean, default=False)  # True for "Others" row
    
    # Model link (for ID resolution)
    model_href = Column(String(500), nullable=True)  # Original href from ranking
    
    # Audit
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    snapshot = relationship("OpenRouterRankingSnapshot", back_populates="entries")
    
    __table_args__ = (
        Index("ix_entries_snapshot_rank", "snapshot_id", "rank"),
        Index("ix_entries_model", "model_id"),
        Index("ix_entries_author", "author"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "author": self.author,
            "tokens": int(self.tokens) if self.tokens else None,
            "tokens_display": self.tokens_display,
            "share_pct": self.share_pct,
            "is_others_bucket": self.is_others_bucket,
        }


# =============================================================================
# Sync Status Table
# =============================================================================

class OpenRouterSyncStatus(Base):
    """Tracks sync status for monitoring and alerting."""
    __tablename__ = "openrouter_sync_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Sync type
    sync_type = Column(String(50), nullable=False, index=True)  # "models", "rankings", "categories"
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    status = Column(String(20), nullable=False)  # "running", "success", "failed"
    items_processed = Column(Integer, default=0)
    items_added = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Duration
    duration_seconds = Column(Float, nullable=True)
    
    __table_args__ = (
        Index("ix_sync_status_type_started", "sync_type", "started_at"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sync_type": self.sync_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "items_processed": self.items_processed,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }


# =============================================================================
# Model Alert (for new model detection)
# =============================================================================

class OpenRouterModelAlert(Base):
    """Alerts for new models or significant changes."""
    __tablename__ = "openrouter_model_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Alert type
    alert_type = Column(String(50), nullable=False)  # "new_model", "ranking_change", "price_change"
    
    # Model info
    model_id = Column(String(255), nullable=True, index=True)
    model_name = Column(String(255), nullable=True)
    category_slug = Column(String(100), nullable=True)
    
    # Alert details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("ix_alerts_type_created", "alert_type", "created_at"),
        Index("ix_alerts_unread", "is_read", "created_at"),
    )

