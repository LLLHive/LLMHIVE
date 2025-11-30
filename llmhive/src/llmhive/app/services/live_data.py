"""Live Data Feed Integration Framework for LLMHive.

This module provides a plugin-like system for subscribing to live data sources:
- Financial market data (stocks, crypto)
- News feeds
- Weather data
- Custom domain-specific data sources

Features:
- Push/pull data fetching modes
- Periodic polling with configurable intervals
- Event-driven updates via callbacks
- Data caching with TTL
- Rate limiting and error handling
- Integration with orchestrator for mid-conversation updates
"""
from __future__ import annotations

import asyncio
import logging
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict
import json
import hashlib

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class DataFeedType(str, Enum):
    """Type of data feed."""
    WEATHER = "weather"
    STOCK = "stock"
    CRYPTO = "crypto"
    NEWS = "news"
    SPORTS = "sports"
    CUSTOM = "custom"


class FetchMode(str, Enum):
    """Data fetching mode."""
    PULL = "pull"       # On-demand fetching
    PUSH = "push"       # Server-sent events / WebSocket
    POLL = "poll"       # Periodic polling


class DataStatus(str, Enum):
    """Status of data."""
    FRESH = "fresh"     # Recently fetched
    CACHED = "cached"   # From cache
    STALE = "stale"     # Past TTL but available
    ERROR = "error"     # Fetch error
    UNAVAILABLE = "unavailable"  # Not available


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class LiveDataPoint:
    """A single data point from a live feed."""
    feed_id: str
    data_type: DataFeedType
    content: Any
    timestamp: datetime
    source: str
    status: DataStatus = DataStatus.FRESH
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: int = 60
    
    @property
    def is_stale(self) -> bool:
        """Check if data is stale."""
        age = datetime.utcnow() - self.timestamp
        return age.total_seconds() > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()
    
    def to_context_string(self) -> str:
        """Convert to context string for prompt augmentation."""
        age = int(self.age_seconds)
        status = "live" if age < 60 else f"{age}s ago"
        return f"[{self.data_type.value.upper()} {status}] {self.format_content()}"
    
    def format_content(self) -> str:
        """Format content as string."""
        if isinstance(self.content, dict):
            return json.dumps(self.content, indent=2)
        return str(self.content)


@dataclass(slots=True)
class DataFeedConfig:
    """Configuration for a data feed."""
    feed_id: str
    feed_type: DataFeedType
    source_url: str = ""
    api_key: Optional[str] = None
    fetch_mode: FetchMode = FetchMode.PULL
    poll_interval_seconds: int = 60
    ttl_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 5
    enabled: bool = True
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LiveDataSubscription:
    """A subscription to live data updates."""
    subscription_id: str
    feed_id: str
    callback: Callable[[LiveDataPoint], None]
    filter_params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True


# ==============================================================================
# Data Feed Interface
# ==============================================================================

class DataFeed(ABC):
    """Abstract base class for live data feeds."""
    
    def __init__(self, config: DataFeedConfig):
        self.config = config
        self._last_fetch: Optional[datetime] = None
        self._cached_data: Optional[LiveDataPoint] = None
        self._error_count: int = 0
    
    @property
    def feed_id(self) -> str:
        return self.config.feed_id
    
    @property
    def feed_type(self) -> DataFeedType:
        return self.config.feed_type
    
    @abstractmethod
    async def fetch(self, **params) -> LiveDataPoint:
        """Fetch data from the source."""
        pass
    
    async def get_data(self, **params) -> LiveDataPoint:
        """Get data with caching."""
        # Check cache
        if self._cached_data and not self._cached_data.is_stale:
            cached = self._cached_data
            cached.status = DataStatus.CACHED
            return cached
        
        # Fetch new data
        try:
            data = await self.fetch(**params)
            self._cached_data = data
            self._last_fetch = datetime.utcnow()
            self._error_count = 0
            return data
        except Exception as e:
            logger.error("Feed %s fetch error: %s", self.feed_id, e)
            self._error_count += 1
            
            # Return stale data if available
            if self._cached_data:
                stale = self._cached_data
                stale.status = DataStatus.STALE
                return stale
            
            # Return error data point
            return LiveDataPoint(
                feed_id=self.feed_id,
                data_type=self.feed_type,
                content={"error": str(e)},
                timestamp=datetime.utcnow(),
                source=self.config.source_url,
                status=DataStatus.ERROR,
                confidence=0.0,
            )
    
    def invalidate_cache(self) -> None:
        """Invalidate cached data."""
        self._cached_data = None


# ==============================================================================
# Built-in Data Feeds
# ==============================================================================

class WeatherFeed(DataFeed):
    """Weather data feed (demo implementation)."""
    
    async def fetch(self, location: str = "New York", **params) -> LiveDataPoint:
        """Fetch weather data."""
        # Demo implementation - in production, call real API
        import random
        
        temp = random.randint(50, 85)
        conditions = random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy"])
        humidity = random.randint(30, 80)
        
        content = {
            "location": location,
            "temperature_f": temp,
            "temperature_c": round((temp - 32) * 5/9, 1),
            "conditions": conditions,
            "humidity": humidity,
            "wind_mph": random.randint(0, 20),
            "updated": datetime.utcnow().isoformat(),
        }
        
        return LiveDataPoint(
            feed_id=self.feed_id,
            data_type=DataFeedType.WEATHER,
            content=content,
            timestamp=datetime.utcnow(),
            source="weather_api",
            status=DataStatus.FRESH,
            ttl_seconds=self.config.ttl_seconds,
            metadata={"location": location},
        )


class StockFeed(DataFeed):
    """Stock market data feed (demo implementation)."""
    
    async def fetch(self, symbol: str = "AAPL", **params) -> LiveDataPoint:
        """Fetch stock data."""
        # Demo implementation - in production, call real API
        import random
        
        base_prices = {
            "AAPL": 175.0,
            "GOOGL": 140.0,
            "MSFT": 375.0,
            "AMZN": 180.0,
            "TSLA": 250.0,
        }
        
        base = base_prices.get(symbol.upper(), 100.0)
        price = round(base + random.uniform(-5, 5), 2)
        change = round(random.uniform(-3, 3), 2)
        change_pct = round(change / base * 100, 2)
        
        content = {
            "symbol": symbol.upper(),
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "high": round(price + random.uniform(0, 2), 2),
            "low": round(price - random.uniform(0, 2), 2),
            "volume": random.randint(1000000, 50000000),
            "updated": datetime.utcnow().isoformat(),
        }
        
        return LiveDataPoint(
            feed_id=self.feed_id,
            data_type=DataFeedType.STOCK,
            content=content,
            timestamp=datetime.utcnow(),
            source="stock_api",
            status=DataStatus.FRESH,
            ttl_seconds=self.config.ttl_seconds,
            metadata={"symbol": symbol.upper()},
        )


class CryptoFeed(DataFeed):
    """Cryptocurrency data feed (demo implementation)."""
    
    async def fetch(self, symbol: str = "BTC", **params) -> LiveDataPoint:
        """Fetch crypto data."""
        # Demo implementation
        import random
        
        base_prices = {
            "BTC": 65000.0,
            "ETH": 3500.0,
            "SOL": 150.0,
            "ADA": 0.45,
            "DOT": 7.0,
        }
        
        base = base_prices.get(symbol.upper(), 1.0)
        price = round(base + random.uniform(-base * 0.05, base * 0.05), 2)
        change_24h = round(random.uniform(-5, 5), 2)
        
        content = {
            "symbol": symbol.upper(),
            "price_usd": price,
            "change_24h_percent": change_24h,
            "market_cap": round(price * random.randint(1000000, 100000000)),
            "volume_24h": round(random.uniform(1000000, 50000000)),
            "updated": datetime.utcnow().isoformat(),
        }
        
        return LiveDataPoint(
            feed_id=self.feed_id,
            data_type=DataFeedType.CRYPTO,
            content=content,
            timestamp=datetime.utcnow(),
            source="crypto_api",
            status=DataStatus.FRESH,
            ttl_seconds=self.config.ttl_seconds,
            metadata={"symbol": symbol.upper()},
        )


class NewsFeed(DataFeed):
    """News feed (demo implementation)."""
    
    async def fetch(self, topic: str = "technology", **params) -> LiveDataPoint:
        """Fetch news data."""
        # Demo implementation
        import random
        
        headlines = [
            f"Breaking: Major developments in {topic} sector",
            f"Analysis: What's next for {topic} industry",
            f"Report: {topic} trends to watch in 2024",
            f"Update: Latest {topic} innovations announced",
        ]
        
        content = {
            "topic": topic,
            "headlines": random.sample(headlines, min(3, len(headlines))),
            "article_count": random.randint(10, 50),
            "trending": random.choice([True, False]),
            "updated": datetime.utcnow().isoformat(),
        }
        
        return LiveDataPoint(
            feed_id=self.feed_id,
            data_type=DataFeedType.NEWS,
            content=content,
            timestamp=datetime.utcnow(),
            source="news_api",
            status=DataStatus.FRESH,
            ttl_seconds=self.config.ttl_seconds,
            metadata={"topic": topic},
        )


# ==============================================================================
# Live Data Manager
# ==============================================================================

class LiveDataManager:
    """Manages live data feeds and subscriptions.
    
    Features:
    - Register and manage multiple data feeds
    - Subscribe to data updates
    - Periodic polling for poll-mode feeds
    - Event-driven callbacks
    - Integration with orchestrator
    """
    
    def __init__(self):
        self._feeds: Dict[str, DataFeed] = {}
        self._subscriptions: Dict[str, LiveDataSubscription] = {}
        self._polling_tasks: Dict[str, asyncio.Task] = {}
        self._lock = threading.RLock()
        self._running = False
        
        # Initialize default feeds
        self._init_default_feeds()
    
    def _init_default_feeds(self) -> None:
        """Initialize default data feeds."""
        # Weather feed
        weather_config = DataFeedConfig(
            feed_id="weather",
            feed_type=DataFeedType.WEATHER,
            poll_interval_seconds=300,  # 5 minutes
            ttl_seconds=300,
        )
        self._feeds["weather"] = WeatherFeed(weather_config)
        
        # Stock feed
        stock_config = DataFeedConfig(
            feed_id="stock",
            feed_type=DataFeedType.STOCK,
            poll_interval_seconds=60,
            ttl_seconds=60,
        )
        self._feeds["stock"] = StockFeed(stock_config)
        
        # Crypto feed
        crypto_config = DataFeedConfig(
            feed_id="crypto",
            feed_type=DataFeedType.CRYPTO,
            poll_interval_seconds=30,
            ttl_seconds=30,
        )
        self._feeds["crypto"] = CryptoFeed(crypto_config)
        
        # News feed
        news_config = DataFeedConfig(
            feed_id="news",
            feed_type=DataFeedType.NEWS,
            poll_interval_seconds=900,  # 15 minutes
            ttl_seconds=900,
        )
        self._feeds["news"] = NewsFeed(news_config)
        
        logger.info("Initialized %d default data feeds", len(self._feeds))
    
    def register_feed(self, feed: DataFeed) -> None:
        """Register a data feed."""
        with self._lock:
            self._feeds[feed.feed_id] = feed
            logger.info("Registered feed: %s (%s)", feed.feed_id, feed.feed_type.value)
    
    def unregister_feed(self, feed_id: str) -> bool:
        """Unregister a data feed."""
        with self._lock:
            if feed_id in self._feeds:
                # Stop polling if running
                if feed_id in self._polling_tasks:
                    self._polling_tasks[feed_id].cancel()
                    del self._polling_tasks[feed_id]
                
                del self._feeds[feed_id]
                logger.info("Unregistered feed: %s", feed_id)
                return True
            return False
    
    async def get_data(
        self,
        feed_id: str,
        **params,
    ) -> Optional[LiveDataPoint]:
        """
        Get data from a feed.
        
        Args:
            feed_id: Feed identifier
            **params: Feed-specific parameters
            
        Returns:
            LiveDataPoint or None
        """
        feed = self._feeds.get(feed_id)
        if feed is None:
            logger.warning("Feed not found: %s", feed_id)
            return None
        
        return await feed.get_data(**params)
    
    async def get_multiple(
        self,
        requests: List[Tuple[str, Dict[str, Any]]],
    ) -> Dict[str, LiveDataPoint]:
        """
        Get data from multiple feeds in parallel.
        
        Args:
            requests: List of (feed_id, params) tuples
            
        Returns:
            Dict of feed_id -> LiveDataPoint
        """
        tasks = []
        feed_ids = []
        
        for feed_id, params in requests:
            feed = self._feeds.get(feed_id)
            if feed:
                tasks.append(feed.get_data(**params))
                feed_ids.append(feed_id)
        
        if not tasks:
            return {}
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            feed_id: result
            for feed_id, result in zip(feed_ids, results)
            if isinstance(result, LiveDataPoint)
        }
    
    def subscribe(
        self,
        feed_id: str,
        callback: Callable[[LiveDataPoint], None],
        *,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Subscribe to feed updates.
        
        Args:
            feed_id: Feed to subscribe to
            callback: Callback function for updates
            filter_params: Optional filter parameters
            
        Returns:
            Subscription ID
        """
        sub_id = hashlib.sha256(
            f"{feed_id}|{time.time()}|{id(callback)}".encode()
        ).hexdigest()[:16]
        
        subscription = LiveDataSubscription(
            subscription_id=sub_id,
            feed_id=feed_id,
            callback=callback,
            filter_params=filter_params or {},
        )
        
        with self._lock:
            self._subscriptions[sub_id] = subscription
        
        logger.info("Created subscription %s for feed %s", sub_id, feed_id)
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from feed updates."""
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                logger.info("Removed subscription: %s", subscription_id)
                return True
            return False
    
    async def start_polling(self) -> None:
        """Start polling for all poll-mode feeds."""
        self._running = True
        
        for feed_id, feed in self._feeds.items():
            if feed.config.fetch_mode == FetchMode.POLL and feed.config.enabled:
                task = asyncio.create_task(self._poll_feed(feed_id))
                self._polling_tasks[feed_id] = task
        
        logger.info("Started polling for %d feeds", len(self._polling_tasks))
    
    async def stop_polling(self) -> None:
        """Stop all polling tasks."""
        self._running = False
        
        for task in self._polling_tasks.values():
            task.cancel()
        
        self._polling_tasks.clear()
        logger.info("Stopped all polling tasks")
    
    async def _poll_feed(self, feed_id: str) -> None:
        """Poll a feed periodically."""
        feed = self._feeds.get(feed_id)
        if not feed:
            return
        
        while self._running:
            try:
                data = await feed.get_data()
                
                # Notify subscribers
                await self._notify_subscribers(feed_id, data)
                
                await asyncio.sleep(feed.config.poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Poll error for feed %s: %s", feed_id, e)
                await asyncio.sleep(feed.config.retry_delay_seconds)
    
    async def _notify_subscribers(
        self,
        feed_id: str,
        data: LiveDataPoint,
    ) -> None:
        """Notify all subscribers of a feed update."""
        with self._lock:
            subscribers = [
                sub for sub in self._subscriptions.values()
                if sub.feed_id == feed_id and sub.active
            ]
        
        for sub in subscribers:
            try:
                # Check filters
                if self._matches_filter(data, sub.filter_params):
                    sub.callback(data)
            except Exception as e:
                logger.error("Subscriber callback error: %s", e)
    
    def _matches_filter(
        self,
        data: LiveDataPoint,
        filters: Dict[str, Any],
    ) -> bool:
        """Check if data matches filter criteria."""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key in data.metadata:
                if data.metadata[key] != value:
                    return False
            elif hasattr(data, key):
                if getattr(data, key) != value:
                    return False
        
        return True
    
    def list_feeds(self) -> List[Dict[str, Any]]:
        """List all registered feeds."""
        return [
            {
                "feed_id": feed.feed_id,
                "feed_type": feed.feed_type.value,
                "enabled": feed.config.enabled,
                "poll_interval": feed.config.poll_interval_seconds,
                "ttl": feed.config.ttl_seconds,
            }
            for feed in self._feeds.values()
        ]
    
    async def get_context_for_query(
        self,
        query: str,
        *,
        max_feeds: int = 3,
    ) -> str:
        """
        Get relevant live data context for a query.
        
        Args:
            query: User query
            max_feeds: Maximum number of feeds to query
            
        Returns:
            Context string with live data
        """
        query_lower = query.lower()
        relevant_feeds: List[Tuple[str, Dict[str, Any]]] = []
        
        # Detect relevant feeds based on query
        if any(w in query_lower for w in ["weather", "temperature", "rain", "sunny", "forecast"]):
            # Extract location if mentioned
            relevant_feeds.append(("weather", {}))
        
        if any(w in query_lower for w in ["stock", "price", "market", "share", "trading"]):
            # Try to extract stock symbol
            symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
            for sym in symbols:
                if sym.lower() in query_lower:
                    relevant_feeds.append(("stock", {"symbol": sym}))
                    break
            else:
                relevant_feeds.append(("stock", {"symbol": "AAPL"}))
        
        if any(w in query_lower for w in ["bitcoin", "crypto", "ethereum", "btc", "eth"]):
            symbol = "BTC"
            if "ethereum" in query_lower or "eth" in query_lower:
                symbol = "ETH"
            relevant_feeds.append(("crypto", {"symbol": symbol}))
        
        if any(w in query_lower for w in ["news", "headlines", "breaking", "latest"]):
            relevant_feeds.append(("news", {"topic": "technology"}))
        
        if not relevant_feeds:
            return ""
        
        # Fetch data from relevant feeds
        relevant_feeds = relevant_feeds[:max_feeds]
        data_points = await self.get_multiple(relevant_feeds)
        
        if not data_points:
            return ""
        
        # Build context string
        context_parts = ["--- Live Data ---"]
        for feed_id, data in data_points.items():
            if data.status != DataStatus.ERROR:
                context_parts.append(data.to_context_string())
        
        if len(context_parts) == 1:
            return ""
        
        context_parts.append("--- End Live Data ---\n")
        return "\n".join(context_parts)


# ==============================================================================
# Integration Tool
# ==============================================================================

class LiveDataTool:
    """Tool interface for orchestrator integration."""
    
    def __init__(self, manager: Optional[LiveDataManager] = None):
        self.manager = manager or get_live_data_manager()
        self.name = "live_data"
        self.description = "Get real-time data from live feeds (weather, stocks, crypto, news)"
    
    async def execute(
        self,
        feed_type: str,
        **params,
    ) -> str:
        """
        Execute live data lookup.
        
        Args:
            feed_type: Type of feed (weather, stock, crypto, news)
            **params: Feed-specific parameters
            
        Returns:
            Formatted data string
        """
        feed_map = {
            "weather": "weather",
            "stock": "stock",
            "crypto": "crypto",
            "news": "news",
        }
        
        feed_id = feed_map.get(feed_type.lower())
        if not feed_id:
            return f"Unknown feed type: {feed_type}. Available: {', '.join(feed_map.keys())}"
        
        data = await self.manager.get_data(feed_id, **params)
        
        if data is None:
            return f"No data available for {feed_type}"
        
        if data.status == DataStatus.ERROR:
            return f"Error fetching {feed_type} data: {data.content.get('error', 'Unknown error')}"
        
        return data.to_context_string()


# ==============================================================================
# Global Instance
# ==============================================================================

_live_data_manager: Optional[LiveDataManager] = None


def get_live_data_manager() -> LiveDataManager:
    """Get the global live data manager."""
    global _live_data_manager
    if _live_data_manager is None:
        _live_data_manager = LiveDataManager()
    return _live_data_manager

