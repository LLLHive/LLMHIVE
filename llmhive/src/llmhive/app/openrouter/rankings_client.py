"""OpenRouter Rankings Client.

Fetches real rankings data from OpenRouter.ai for:
- Category discovery (all use case categories)
- Top-N models per category with exact ordering
- Model ID resolution and validation

Strategy:
1. First check for OpenRouter API endpoints for rankings
2. If no API, parse the rankings pages (structured data from Next.js)
3. Validate model IDs against OpenRouter Models API

COMPLIANCE NOTE: This fetches publicly available data from openrouter.ai
for the purpose of providing accurate rankings to our users.
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
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

OPENROUTER_BASE = "https://openrouter.ai"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
RANKINGS_PAGE_URL = "https://openrouter.ai/rankings"

# Parser version - bump when parsing logic changes
PARSE_VERSION = "1.1.0"

# Known category groups
CATEGORY_GROUPS = {
    "usecase": "Use Case",
    "language": "Language",
    "programming_language": "Programming Language",
}

# Default categories to always check (even if discovery fails)
FALLBACK_CATEGORIES = [
    "programming",
    "roleplay",
    "marketing",
    "marketing/seo",
    "technology",
    "science",
    "translation",
    "legal",
    "finance",
    "health",
    "academia",
    "writing",
    "education",
    "business",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DiscoveredCategory:
    """Category discovered from OpenRouter."""
    slug: str
    display_name: str
    group: str = "usecase"
    parent_slug: Optional[str] = None
    full_path: str = ""
    depth: int = 0
    source_url: Optional[str] = None
    
    def __post_init__(self):
        if not self.full_path:
            self.full_path = self.slug
        if "/" in self.slug and not self.parent_slug:
            parts = self.slug.rsplit("/", 1)
            self.parent_slug = parts[0]
            self.depth = self.slug.count("/")


@dataclass
class RankedModelEntry:
    """A model entry in a ranking."""
    rank: int
    model_name: str
    author: Optional[str] = None
    model_id: Optional[str] = None
    tokens: Optional[int] = None
    tokens_display: Optional[str] = None
    share_pct: Optional[float] = None
    model_href: Optional[str] = None
    is_others_bucket: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "model_name": self.model_name,
            "author": self.author,
            "model_id": self.model_id,
            "tokens": self.tokens,
            "tokens_display": self.tokens_display,
            "share_pct": self.share_pct,
            "is_others_bucket": self.is_others_bucket,
        }


@dataclass
class RankingSnapshot:
    """Complete ranking for a category."""
    category_slug: str
    entries: List[RankedModelEntry]
    group: str = "usecase"
    view: str = "week"
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: Optional[str] = None
    raw_payload_hash: Optional[str] = None
    parse_version: str = PARSE_VERSION
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.error is None and len(self.entries) > 0


# =============================================================================
# OpenRouter Rankings Client
# =============================================================================

class OpenRouterRankingsClient:
    """Client for fetching rankings from OpenRouter.
    
    Usage:
        async with OpenRouterRankingsClient() as client:
            # Discover all categories
            categories = await client.discover_categories()
            
            # Get top 10 for a category
            ranking = await client.get_category_ranking("programming", limit=10)
            
            # Validate model IDs
            valid = await client.validate_model_id("openai/gpt-4o")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize client.
        
        Args:
            api_key: OpenRouter API key (for model validation)
            timeout: Request timeout in seconds
            max_retries: Max retry attempts for failed requests
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._models_cache: Dict[str, Any] = {}
    
    async def __aenter__(self) -> "OpenRouterRankingsClient":
        headers = {
            "User-Agent": "LLMHive/1.0 (https://llmhive.com)",
            "Accept": "application/json, text/html",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # =========================================================================
    # Category Discovery
    # =========================================================================
    
    async def discover_categories(
        self,
        group: str = "usecase",
    ) -> List[DiscoveredCategory]:
        """Discover all categories from OpenRouter.
        
        Args:
            group: Category group (usecase, language, programming_language)
            
        Returns:
            List of discovered categories
        """
        categories: List[DiscoveredCategory] = []
        
        try:
            # First, try to get categories from the rankings page structure
            page_categories = await self._extract_categories_from_rankings_page()
            categories.extend(page_categories)
            
            logger.info("Discovered %d categories from rankings page", len(categories))
            
        except Exception as e:
            logger.warning("Failed to discover categories from page: %s", e)
        
        # Ensure fallback categories are included
        existing_slugs = {c.slug for c in categories}
        for slug in FALLBACK_CATEGORIES:
            if slug not in existing_slugs:
                display_name = slug.replace("/", " > ").replace("_", " ").title()
                categories.append(DiscoveredCategory(
                    slug=slug,
                    display_name=display_name,
                    group=group,
                ))
        
        return sorted(categories, key=lambda c: (c.depth, c.slug))
    
    async def _extract_categories_from_rankings_page(self) -> List[DiscoveredCategory]:
        """Extract categories from the rankings page."""
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        response = await self._fetch_with_retry(RANKINGS_PAGE_URL)
        if not response:
            return []
        
        categories = []
        content = response.text
        
        # Try to find __NEXT_DATA__ JSON
        next_data = self._extract_next_data(content)
        if next_data:
            categories.extend(self._parse_categories_from_next_data(next_data))
        
        # Also try to extract from dropdown/menu HTML
        html_categories = self._extract_categories_from_html(content)
        
        # Merge, preferring next_data
        existing = {c.slug for c in categories}
        for cat in html_categories:
            if cat.slug not in existing:
                categories.append(cat)
        
        return categories
    
    def _extract_next_data(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract __NEXT_DATA__ JSON from HTML."""
        match = re.search(
            r'<script\s+id="__NEXT_DATA__"\s+type="application/json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
    
    def _parse_categories_from_next_data(self, data: Dict[str, Any]) -> List[DiscoveredCategory]:
        """Parse categories from Next.js page data."""
        categories = []
        
        # Navigate to props.pageProps or similar
        props = data.get("props", {}).get("pageProps", {})
        
        # Look for categories in various possible locations
        for key in ["categories", "categoryOptions", "useCases", "rankingCategories"]:
            if key in props:
                cat_data = props[key]
                if isinstance(cat_data, list):
                    for item in cat_data:
                        if isinstance(item, dict):
                            slug = item.get("slug") or item.get("id") or item.get("value")
                            name = item.get("name") or item.get("label") or item.get("display_name")
                            if slug and name:
                                categories.append(DiscoveredCategory(
                                    slug=slug,
                                    display_name=name,
                                    source_url=RANKINGS_PAGE_URL,
                                ))
                        elif isinstance(item, str):
                            categories.append(DiscoveredCategory(
                                slug=item,
                                display_name=item.replace("_", " ").title(),
                                source_url=RANKINGS_PAGE_URL,
                            ))
        
        return categories
    
    def _extract_categories_from_html(self, html: str) -> List[DiscoveredCategory]:
        """Extract categories from HTML (dropdown menus, links)."""
        categories = []
        
        # Look for links to /rankings/<category>
        pattern = r'href="/rankings/([a-z0-9_/-]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for slug, display_name in matches:
            slug = slug.strip("/").lower()
            if slug and len(slug) < 100:  # Sanity check
                categories.append(DiscoveredCategory(
                    slug=slug,
                    display_name=display_name.strip(),
                    source_url=RANKINGS_PAGE_URL,
                ))
        
        # Look for data attributes
        pattern2 = r'data-category="([^"]+)"'
        for slug in re.findall(pattern2, html):
            if slug not in {c.slug for c in categories}:
                categories.append(DiscoveredCategory(
                    slug=slug,
                    display_name=slug.replace("_", " ").title(),
                ))
        
        return categories
    
    # =========================================================================
    # Ranking Fetch
    # =========================================================================
    
    async def get_category_ranking(
        self,
        category_slug: str,
        view: str = "week",
        limit: int = 10,
    ) -> RankingSnapshot:
        """Get ranking for a category.
        
        Args:
            category_slug: Category slug (e.g., "programming", "marketing/seo")
            view: Time view (week, month, day, all)
            limit: Max entries to return
            
        Returns:
            RankingSnapshot with entries
        """
        url = f"{RANKINGS_PAGE_URL}/{category_slug}"
        if view and view != "week":
            url += f"?view={view}"
        
        snapshot = RankingSnapshot(
            category_slug=category_slug,
            entries=[],
            view=view,
            source_url=url,
        )
        
        try:
            response = await self._fetch_with_retry(url)
            if not response:
                snapshot.error = "Failed to fetch page"
                return snapshot
            
            content = response.text
            snapshot.raw_payload_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Try Next.js data first
            next_data = self._extract_next_data(content)
            if next_data:
                entries = self._parse_ranking_from_next_data(next_data, limit)
                if entries:
                    snapshot.entries = entries
                    return snapshot
            
            # Fallback to HTML parsing
            entries = self._parse_ranking_from_html(content, limit)
            snapshot.entries = entries
            
            if not entries:
                snapshot.error = "No ranking entries found"
            
        except Exception as e:
            logger.error("Failed to get ranking for %s: %s", category_slug, e)
            snapshot.error = str(e)
        
        return snapshot
    
    def _parse_ranking_from_next_data(
        self,
        data: Dict[str, Any],
        limit: int,
    ) -> List[RankedModelEntry]:
        """Parse ranking entries from Next.js data."""
        entries = []
        
        props = data.get("props", {}).get("pageProps", {})
        
        # Look for ranking data in various possible locations
        for key in ["ranking", "rankings", "models", "topModels", "data"]:
            if key in props:
                ranking_data = props[key]
                if isinstance(ranking_data, list):
                    for i, item in enumerate(ranking_data[:limit]):
                        entry = self._parse_ranking_item(item, i + 1)
                        if entry:
                            entries.append(entry)
                    break
        
        return entries
    
    def _parse_ranking_item(self, item: Dict[str, Any], rank: int) -> Optional[RankedModelEntry]:
        """Parse a single ranking item."""
        if not isinstance(item, dict):
            return None
        
        # Extract model name
        model_name = (
            item.get("name") or
            item.get("model_name") or
            item.get("model") or
            item.get("id", "").split("/")[-1]
        )
        
        if not model_name:
            return None
        
        # Extract model ID
        model_id = item.get("id") or item.get("model_id")
        
        # Extract author
        author = item.get("author") or item.get("provider")
        if not author and model_id and "/" in model_id:
            author = model_id.split("/")[0]
        
        # Extract metrics
        tokens = item.get("tokens") or item.get("token_count")
        if isinstance(tokens, str):
            tokens = self._parse_token_string(tokens)
        
        share = item.get("share") or item.get("share_pct") or item.get("percentage")
        if isinstance(share, str):
            share = float(share.replace("%", ""))
        
        return RankedModelEntry(
            rank=rank,
            model_name=model_name,
            author=author,
            model_id=model_id,
            tokens=tokens,
            tokens_display=item.get("tokens_display"),
            share_pct=share,
            model_href=item.get("href") or item.get("url"),
            is_others_bucket=item.get("is_others", False) or "other" in model_name.lower(),
        )
    
    def _parse_ranking_from_html(
        self,
        html: str,
        limit: int,
    ) -> List[RankedModelEntry]:
        """Parse ranking entries from HTML (fallback)."""
        entries = []
        
        # Look for table rows or list items with ranking data
        # Pattern for ranked model entries
        patterns = [
            # Table row pattern
            r'<tr[^>]*>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>.*?href="/([^"]+)"[^>]*>([^<]+)</a>.*?<td[^>]*>([^<]+)</td>.*?<td[^>]*>([^<]+)</td>.*?</tr>',
            # List item pattern
            r'<li[^>]*data-rank="(\d+)"[^>]*>.*?<a[^>]*href="/([^"]+)"[^>]*>([^<]+)</a>.*?<span[^>]*>([^<]+)</span>.*?</li>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                for match in matches[:limit]:
                    try:
                        rank = int(match[0])
                        href = match[1]
                        name = match[2].strip()
                        tokens_str = match[3].strip() if len(match) > 3 else ""
                        share_str = match[4].strip() if len(match) > 4 else ""
                        
                        # Extract model ID from href
                        model_id = None
                        if "/models/" in href or "/" in href:
                            parts = href.split("/")
                            if len(parts) >= 2:
                                model_id = "/".join(parts[-2:])
                        
                        entries.append(RankedModelEntry(
                            rank=rank,
                            model_name=name,
                            model_id=model_id,
                            tokens=self._parse_token_string(tokens_str),
                            tokens_display=tokens_str,
                            share_pct=self._parse_share_string(share_str),
                            model_href=href,
                        ))
                    except (ValueError, IndexError):
                        continue
                break
        
        return entries
    
    def _parse_token_string(self, s: str) -> Optional[int]:
        """Parse token string like '1.2B' or '500M' to int."""
        if not s:
            return None
        
        s = s.upper().replace(",", "").strip()
        
        multipliers = {
            "K": 1_000,
            "M": 1_000_000,
            "B": 1_000_000_000,
            "T": 1_000_000_000_000,
        }
        
        for suffix, mult in multipliers.items():
            if suffix in s:
                try:
                    num = float(s.replace(suffix, ""))
                    return int(num * mult)
                except ValueError:
                    pass
        
        try:
            return int(float(s))
        except ValueError:
            return None
    
    def _parse_share_string(self, s: str) -> Optional[float]:
        """Parse share string like '12.5%' to float."""
        if not s:
            return None
        
        s = s.replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return None
    
    # =========================================================================
    # Model Validation
    # =========================================================================
    
    async def validate_model_id(self, model_id: str) -> bool:
        """Validate that a model ID exists in OpenRouter.
        
        Args:
            model_id: Model ID to validate
            
        Returns:
            True if model exists
        """
        if model_id in self._models_cache:
            return self._models_cache[model_id] is not None
        
        # Fetch models if cache is empty
        if not self._models_cache:
            await self._load_models_cache()
        
        return model_id in self._models_cache
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model info from OpenRouter API.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model info dict or None
        """
        if not self._models_cache:
            await self._load_models_cache()
        
        return self._models_cache.get(model_id)
    
    async def _load_models_cache(self) -> None:
        """Load all models from OpenRouter API."""
        if not self._client:
            return
        
        try:
            response = await self._fetch_with_retry(f"{OPENROUTER_API_BASE}/models")
            if response and response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                for model in models:
                    model_id = model.get("id")
                    if model_id:
                        self._models_cache[model_id] = model
                
                logger.info("Loaded %d models into cache", len(self._models_cache))
        except Exception as e:
            logger.error("Failed to load models: %s", e)
    
    async def resolve_model_id(
        self,
        entry: RankedModelEntry,
    ) -> Optional[str]:
        """Try to resolve/validate model ID for a ranking entry.
        
        Args:
            entry: Ranking entry
            
        Returns:
            Resolved model ID or None
        """
        # If we have an ID, validate it
        if entry.model_id:
            if await self.validate_model_id(entry.model_id):
                return entry.model_id
        
        # Try to construct from author and name
        if entry.author and entry.model_name:
            candidates = [
                f"{entry.author}/{entry.model_name}",
                f"{entry.author}/{entry.model_name.lower().replace(' ', '-')}",
            ]
            for candidate in candidates:
                if await self.validate_model_id(candidate):
                    return candidate
        
        # Try to extract from href
        if entry.model_href:
            parts = entry.model_href.strip("/").split("/")
            if len(parts) >= 2:
                candidate = f"{parts[-2]}/{parts[-1]}"
                if await self.validate_model_id(candidate):
                    return candidate
        
        return None
    
    # =========================================================================
    # HTTP Helpers
    # =========================================================================
    
    async def _fetch_with_retry(
        self,
        url: str,
        method: str = "GET",
    ) -> Optional[httpx.Response]:
        """Fetch URL with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(method, url)
                
                if response.status_code == 429:
                    # Rate limited
                    wait_time = 2 ** attempt
                    logger.warning("Rate limited, waiting %ds", wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                
                if response.status_code >= 400:
                    logger.warning("HTTP %d for %s", response.status_code, url)
                    if response.status_code >= 500:
                        await asyncio.sleep(1)
                        continue
                    return None
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d failed for %s: %s", attempt + 1, url, e)
                await asyncio.sleep(1)
        
        logger.error("All retries failed for %s: %s", url, last_error)
        return None

