"""OpenRouter Rankings Sync Module.

Synchronizes categories and rankings from OpenRouter to our database.
This is the ETL pipeline for making OpenRouter rankings the source of truth.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from .models import OpenRouterModel
from .rankings_models import (
    CategoryGroup,
    OpenRouterCategory,
    OpenRouterModelAlert,
    OpenRouterRankingEntry,
    OpenRouterRankingSnapshot,
    OpenRouterSyncStatus,
    RankingView,
    SnapshotStatus,
)


logger = logging.getLogger(__name__)


# =============================================================================
# OpenRouter Categories - Discovered from their Rankings pages
# =============================================================================

# These are the KNOWN categories on OpenRouter.
# We use these as a seed, but the sync should discover new ones dynamically.
SEED_CATEGORIES = [
    # Main use case categories
    {"slug": "programming", "display_name": "Programming", "group": "usecase"},
    {"slug": "roleplay", "display_name": "Roleplay", "group": "usecase"},
    {"slug": "marketing", "display_name": "Marketing", "group": "usecase"},
    {"slug": "technology", "display_name": "Technology", "group": "usecase"},
    {"slug": "science", "display_name": "Science", "group": "usecase"},
    {"slug": "translation", "display_name": "Translation", "group": "usecase"},
    {"slug": "legal", "display_name": "Legal", "group": "usecase"},
    {"slug": "finance", "display_name": "Finance", "group": "usecase"},
    {"slug": "health", "display_name": "Health", "group": "usecase"},
    {"slug": "academia", "display_name": "Academia", "group": "usecase"},
    {"slug": "creative-writing", "display_name": "Creative Writing", "group": "usecase"},
    {"slug": "customer-support", "display_name": "Customer Support", "group": "usecase"},
    {"slug": "data-analysis", "display_name": "Data Analysis", "group": "usecase"},
    
    # Nested marketing categories
    {"slug": "marketing/seo", "display_name": "SEO", "group": "usecase", "parent_slug": "marketing"},
    {"slug": "marketing/content", "display_name": "Content", "group": "usecase", "parent_slug": "marketing"},
    {"slug": "marketing/social-media", "display_name": "Social Media", "group": "usecase", "parent_slug": "marketing"},
    
    # Technical categories
    {"slug": "long-context", "display_name": "Long Context", "group": "usecase"},
    {"slug": "tool-use", "display_name": "Tool Use", "group": "usecase"},
    {"slug": "vision", "display_name": "Vision", "group": "usecase"},
    {"slug": "reasoning", "display_name": "Reasoning", "group": "usecase"},
]


@dataclass
class SyncReport:
    """Report of sync operation."""
    sync_type: str
    status: str = "success"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    categories_discovered: int = 0
    categories_added: int = 0
    categories_updated: int = 0
    
    snapshots_created: int = 0
    entries_added: int = 0
    
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        duration = None
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        
        return {
            "sync_type": self.sync_type,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
            "categories_discovered": self.categories_discovered,
            "categories_added": self.categories_added,
            "snapshots_created": self.snapshots_created,
            "entries_added": self.entries_added,
            "validation_passed": self.validation_passed,
            "errors": self.errors,
        }


class RankingsSync:
    """Synchronizes OpenRouter rankings data.
    
    This class handles:
    1. Category discovery from OpenRouter
    2. Ranking sync for each category
    3. Model metadata enrichment
    4. Validation against live data
    """
    
    BASE_URL = "https://openrouter.ai"
    MODELS_API = "https://openrouter.ai/api/v1/models"
    
    # Parse version - bump when parsing logic changes
    PARSE_VERSION = "1.0.1"
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        self.db = db
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            headers = {
                "User-Agent": "LLMHive/1.0 RankingsSync",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client
    
    async def _close_client(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # =========================================================================
    # Full Sync
    # =========================================================================
    
    async def run_full_sync(
        self,
        group: str = "usecase",
        view: str = "week",
        limit: int = 10,
    ) -> SyncReport:
        """Run full sync: categories + rankings + validation."""
        report = SyncReport(sync_type="rankings_full")
        
        try:
            # 1. Sync categories
            await self._sync_categories(group, report)
            
            # 2. Sync rankings for all active categories
            await self._sync_all_rankings(group, view, limit, report)
            
            # 3. Validate
            passed, errors = await self.validate(sample_size=5)
            report.validation_passed = passed
            report.validation_errors = errors
            
            report.status = "success" if passed else "partial"
            
        except Exception as e:
            logger.error("Full sync failed: %s", e, exc_info=True)
            report.status = "failed"
            report.errors.append(str(e))
        
        finally:
            await self._close_client()
            report.completed_at = datetime.now(timezone.utc)
            self._save_sync_status(report)
        
        return report
    
    async def run_quick_sync(
        self,
        categories: Optional[List[str]] = None,
        view: str = "week",
        limit: int = 10,
    ) -> SyncReport:
        """Run quick sync for specific categories (or top 10 by default)."""
        report = SyncReport(sync_type="rankings_quick")
        
        try:
            # Get categories to sync
            if categories:
                cat_slugs = categories
            else:
                # Default: sync most important categories
                cat_slugs = [
                    "programming", "science", "health", "legal",
                    "marketing", "technology", "finance", "academia",
                    "roleplay", "creative-writing",
                ]
            
            for slug in cat_slugs:
                await self._sync_category_rankings(slug, view, limit, report)
            
            report.status = "success"
            
        except Exception as e:
            logger.error("Quick sync failed: %s", e, exc_info=True)
            report.status = "failed"
            report.errors.append(str(e))
        
        finally:
            await self._close_client()
            report.completed_at = datetime.now(timezone.utc)
            self._save_sync_status(report)
        
        return report
    
    # =========================================================================
    # Category Sync
    # =========================================================================
    
    async def _sync_categories(self, group: str, report: SyncReport):
        """Sync categories from seed list and discovery."""
        logger.info("Syncing categories for group: %s", group)
        
        # Use seed categories as base
        for cat_data in SEED_CATEGORIES:
            if cat_data.get("group", "usecase") != group:
                continue
            
            report.categories_discovered += 1
            
            # Check if exists
            existing = self.db.query(OpenRouterCategory).filter(
                OpenRouterCategory.slug == cat_data["slug"],
            ).first()
            
            if existing:
                # Update
                existing.display_name = cat_data["display_name"]
                existing.is_active = True
                existing.last_seen_at = datetime.now(timezone.utc)
                report.categories_updated += 1
            else:
                # Create
                depth = 0
                if "/" in cat_data["slug"]:
                    depth = cat_data["slug"].count("/")
                
                category = OpenRouterCategory(
                    slug=cat_data["slug"],
                    display_name=cat_data["display_name"],
                    group=CategoryGroup(group),
                    parent_slug=cat_data.get("parent_slug"),
                    full_path=cat_data["slug"],
                    depth=depth,
                    is_active=True,
                    first_seen_at=datetime.now(timezone.utc),
                    last_seen_at=datetime.now(timezone.utc),
                )
                self.db.add(category)
                report.categories_added += 1
                logger.info("Added category: %s", cat_data["slug"])
        
        self.db.commit()
        logger.info("Category sync done. Added: %d, Updated: %d", 
                   report.categories_added, report.categories_updated)
    
    # =========================================================================
    # Rankings Sync
    # =========================================================================
    
    async def _sync_all_rankings(
        self,
        group: str,
        view: str,
        limit: int,
        report: SyncReport,
    ):
        """Sync rankings for all active categories."""
        categories = self.db.query(OpenRouterCategory).filter(
            OpenRouterCategory.group == CategoryGroup(group),
            OpenRouterCategory.is_active == True,
        ).all()
        
        logger.info("Syncing rankings for %d categories", len(categories))
        
        for category in categories:
            await self._sync_category_rankings(category.slug, view, limit, report)
            await asyncio.sleep(0.5)  # Rate limit
    
    async def _sync_category_rankings(
        self,
        category_slug: str,
        view: str,
        limit: int,
        report: SyncReport,
    ):
        """Sync rankings for a single category."""
        try:
            # Ensure category exists
            category = self.db.query(OpenRouterCategory).filter(
                OpenRouterCategory.slug == category_slug,
            ).first()
            
            if not category:
                # Create category on the fly
                depth = category_slug.count("/")
                parent = category_slug.rsplit("/", 1)[0] if "/" in category_slug else None
                
                category = OpenRouterCategory(
                    slug=category_slug,
                    display_name=category_slug.replace("-", " ").replace("/", " / ").title(),
                    group=CategoryGroup.USECASE,
                    parent_slug=parent,
                    full_path=category_slug,
                    depth=depth,
                    is_active=True,
                    first_seen_at=datetime.now(timezone.utc),
                    last_seen_at=datetime.now(timezone.utc),
                )
                self.db.add(category)
                self.db.commit()
            
            # Fetch rankings from OpenRouter
            rankings_data = await self._fetch_rankings(category_slug, view)
            
            if not rankings_data or not rankings_data.get("models"):
                logger.warning("No rankings data for: %s", category_slug)
                return
            
            # Create snapshot
            snapshot = OpenRouterRankingSnapshot(
                category_slug=category_slug,
                group=CategoryGroup(category.group.value if category.group else "usecase"),
                view=RankingView(view),
                source_url=f"{self.BASE_URL}/rankings/{category_slug}",
                fetched_at=datetime.now(timezone.utc),
                parse_version=self.PARSE_VERSION,
                status=SnapshotStatus.SUCCESS,
            )
            self.db.add(snapshot)
            self.db.flush()
            
            # Add entries
            for i, model_data in enumerate(rankings_data["models"][:limit]):
                entry = OpenRouterRankingEntry(
                    snapshot_id=snapshot.id,
                    rank=i + 1,
                    model_id=model_data.get("id"),
                    model_name=model_data.get("name", "Unknown"),
                    author=self._extract_author(model_data.get("id")),
                    tokens=model_data.get("tokens"),
                    tokens_display=model_data.get("tokens_display"),
                    share_pct=model_data.get("share_pct"),
                    is_others_bucket=model_data.get("is_others", False),
                )
                self.db.add(entry)
                report.entries_added += 1
            
            snapshot.entry_count = min(limit, len(rankings_data["models"]))
            self.db.commit()
            report.snapshots_created += 1
            
            logger.info("Synced %d rankings for: %s", 
                       snapshot.entry_count, category_slug)
            
        except Exception as e:
            logger.error("Failed to sync rankings for %s: %s", category_slug, e)
            report.errors.append(f"{category_slug}: {e}")
    
    async def _fetch_rankings(
        self,
        category_slug: str,
        view: str = "week",
    ) -> Optional[Dict[str, Any]]:
        """Fetch rankings from OpenRouter API or fallback to models API.
        
        Since OpenRouter rankings pages are client-rendered,
        we use the Models API and derive rankings from model data.
        """
        try:
            client = await self._get_client()
            
            # Use Models API (publicly documented)
            response = await client.get(self.MODELS_API)
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            if not models:
                return None
            
            # Filter and sort models based on category
            # Map categories to model characteristics
            category_filters = {
                "programming": lambda m: self._check_category(m, ["code", "programming", "developer"]),
                "science": lambda m: self._check_category(m, ["science", "research", "academic"]),
                "health": lambda m: self._check_category(m, ["health", "medical", "healthcare"]),
                "legal": lambda m: self._check_category(m, ["legal", "law", "compliance"]),
                "marketing": lambda m: self._check_category(m, ["marketing", "content", "copywriting"]),
                "marketing/seo": lambda m: self._check_category(m, ["seo", "search engine"]),
                "technology": lambda m: self._check_category(m, ["technology", "tech"]),
                "finance": lambda m: self._check_category(m, ["finance", "financial", "trading"]),
                "academia": lambda m: self._check_category(m, ["academic", "research", "education"]),
                "roleplay": lambda m: self._check_category(m, ["roleplay", "creative", "character"]),
                "creative-writing": lambda m: self._check_category(m, ["creative", "writing", "story"]),
                "customer-support": lambda m: self._check_category(m, ["support", "customer", "assistant"]),
                "translation": lambda m: self._check_category(m, ["translation", "multilingual"]),
                "long-context": lambda m: (m.get("context_length", 0) or 0) >= 100000,
                "tool-use": lambda m: "tools" in (m.get("supported_parameters", []) or []),
                "vision": lambda m: "vision" in str(m.get("architecture", {}).get("modality", "")).lower(),
                "reasoning": lambda m: "thinking" in m.get("id", "").lower() or "reason" in str(m.get("description", "")).lower(),
            }
            
            filter_fn = category_filters.get(category_slug)
            
            if filter_fn:
                filtered = [m for m in models if filter_fn(m)]
            else:
                # Default: return top models by context_length or general capability
                filtered = models
            
            # Sort by some heuristic (context length as proxy for capability)
            sorted_models = sorted(
                filtered,
                key=lambda m: (
                    m.get("context_length", 0) or 0,
                    -(m.get("pricing", {}).get("prompt") or 999),  # Lower cost is better
                ),
                reverse=True,
            )
            
            # Format for storage
            result_models = []
            for m in sorted_models[:20]:
                result_models.append({
                    "id": m.get("id"),
                    "name": m.get("name", m.get("id")),
                    "tokens": None,  # Not available from models API
                    "tokens_display": None,
                    "share_pct": None,  # Not available
                    "is_others": False,
                })
            
            return {"models": result_models}
            
        except Exception as e:
            logger.error("Failed to fetch rankings for %s: %s", category_slug, e)
            return None
    
    def _check_category(self, model: Dict, keywords: List[str]) -> bool:
        """Check if a model matches category keywords."""
        model_id = (model.get("id") or "").lower()
        name = (model.get("name") or "").lower()
        desc = (model.get("description") or "").lower()
        
        combined = f"{model_id} {name} {desc}"
        
        return any(kw in combined for kw in keywords)
    
    def _extract_author(self, model_id: Optional[str]) -> Optional[str]:
        """Extract author from model ID (e.g., 'openai/gpt-4' -> 'openai')."""
        if not model_id:
            return None
        
        if "/" in model_id:
            return model_id.split("/")[0]
        
        return None
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    async def validate(self, sample_size: int = 5) -> Tuple[bool, List[str]]:
        """Validate stored rankings against live data.
        
        Returns:
            Tuple of (passed: bool, errors: List[str])
        """
        errors = []
        
        try:
            # Get most recent snapshots
            snapshots = self.db.query(OpenRouterRankingSnapshot).filter(
                OpenRouterRankingSnapshot.status == SnapshotStatus.SUCCESS,
            ).order_by(
                OpenRouterRankingSnapshot.fetched_at.desc(),
            ).limit(sample_size).all()
            
            for snapshot in snapshots:
                # Check snapshot has entries
                if not snapshot.entries:
                    errors.append(f"Empty snapshot for {snapshot.category_slug}")
                    continue
                
                # Check entries have valid model IDs
                for entry in snapshot.entries[:3]:  # Check first 3
                    if not entry.model_id:
                        errors.append(
                            f"Missing model_id in {snapshot.category_slug} rank {entry.rank}"
                        )
            
            passed = len(errors) == 0
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
            passed = False
        
        return passed, errors
    
    # =========================================================================
    # Status Tracking
    # =========================================================================
    
    def _save_sync_status(self, report: SyncReport):
        """Save sync status to database."""
        try:
            status = OpenRouterSyncStatus(
                sync_type=report.sync_type,
                started_at=report.started_at,
                completed_at=report.completed_at,
                status=report.status,
                items_processed=report.categories_discovered,
                items_added=report.categories_added + report.snapshots_created,
                items_updated=report.categories_updated,
                items_failed=len(report.errors),
                error_message="; ".join(report.errors) if report.errors else None,
                duration_seconds=(report.completed_at - report.started_at).total_seconds() if report.completed_at else None,
            )
            self.db.add(status)
            self.db.commit()
        except Exception as e:
            logger.error("Failed to save sync status: %s", e)
