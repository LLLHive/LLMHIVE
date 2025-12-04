"""Unit tests for Live Data Feed Module."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytest

from llmhive.app.services.live_data import (
    LiveDataManager,
    LiveDataPoint,
    LiveDataTool,
    DataFeedConfig,
    DataFeedType,
    FetchMode,
    DataStatus,
    WeatherFeed,
    StockFeed,
    CryptoFeed,
    NewsFeed,
    get_live_data_manager,
)


class TestLiveDataPoint:
    """Tests for LiveDataPoint class."""
    
    def test_create_data_point(self):
        """Test creating a data point."""
        data = LiveDataPoint(
            feed_id="weather",
            data_type=DataFeedType.WEATHER,
            content={"temperature_f": 72, "conditions": "Sunny"},
            timestamp=datetime.utcnow(),
            source="weather_api",
            status=DataStatus.FRESH,
            ttl_seconds=60,
        )
        
        assert data.feed_id == "weather"
        assert data.data_type == DataFeedType.WEATHER
        assert data.status == DataStatus.FRESH
    
    def test_is_stale_fresh(self):
        """Test is_stale for fresh data."""
        data = LiveDataPoint(
            feed_id="test",
            data_type=DataFeedType.CUSTOM,
            content={},
            timestamp=datetime.utcnow(),
            source="test",
            ttl_seconds=60,
        )
        
        assert data.is_stale is False
    
    def test_is_stale_old(self):
        """Test is_stale for old data."""
        data = LiveDataPoint(
            feed_id="test",
            data_type=DataFeedType.CUSTOM,
            content={},
            timestamp=datetime.utcnow() - timedelta(seconds=120),
            source="test",
            ttl_seconds=60,
        )
        
        assert data.is_stale is True
    
    def test_age_seconds(self):
        """Test age_seconds calculation."""
        data = LiveDataPoint(
            feed_id="test",
            data_type=DataFeedType.CUSTOM,
            content={},
            timestamp=datetime.utcnow() - timedelta(seconds=30),
            source="test",
        )
        
        assert 29 <= data.age_seconds <= 31
    
    def test_to_context_string(self):
        """Test context string generation."""
        data = LiveDataPoint(
            feed_id="weather",
            data_type=DataFeedType.WEATHER,
            content={"temperature_f": 72},
            timestamp=datetime.utcnow(),
            source="test",
        )
        
        context = data.to_context_string()
        
        assert "WEATHER" in context
        assert "72" in context
    
    def test_format_content_dict(self):
        """Test format_content with dict."""
        data = LiveDataPoint(
            feed_id="test",
            data_type=DataFeedType.CUSTOM,
            content={"key": "value"},
            timestamp=datetime.utcnow(),
            source="test",
        )
        
        formatted = data.format_content()
        
        assert "key" in formatted
        assert "value" in formatted
    
    def test_format_content_string(self):
        """Test format_content with string."""
        data = LiveDataPoint(
            feed_id="test",
            data_type=DataFeedType.CUSTOM,
            content="Simple string",
            timestamp=datetime.utcnow(),
            source="test",
        )
        
        assert data.format_content() == "Simple string"


class TestDataFeedConfig:
    """Tests for DataFeedConfig class."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = DataFeedConfig(
            feed_id="test",
            feed_type=DataFeedType.CUSTOM,
        )
        
        assert config.feed_id == "test"
        assert config.fetch_mode == FetchMode.PULL
        assert config.poll_interval_seconds == 60
        assert config.enabled is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = DataFeedConfig(
            feed_id="weather",
            feed_type=DataFeedType.WEATHER,
            source_url="https://api.weather.com",
            api_key="secret",
            fetch_mode=FetchMode.POLL,
            poll_interval_seconds=300,
            ttl_seconds=300,
        )
        
        assert config.source_url == "https://api.weather.com"
        assert config.api_key == "secret"
        assert config.fetch_mode == FetchMode.POLL
        assert config.poll_interval_seconds == 300


class TestWeatherFeed:
    """Tests for WeatherFeed class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = DataFeedConfig(
            feed_id="weather",
            feed_type=DataFeedType.WEATHER,
            ttl_seconds=60,
        )
        self.feed = WeatherFeed(config)
    
    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test fetching weather data."""
        data = await self.feed.fetch(location="New York")
        
        assert data.feed_id == "weather"
        assert data.data_type == DataFeedType.WEATHER
        assert data.status == DataStatus.FRESH
        assert "location" in data.content
        assert "temperature_f" in data.content
        assert "conditions" in data.content
    
    @pytest.mark.asyncio
    async def test_get_data_caching(self):
        """Test data caching."""
        data1 = await self.feed.get_data(location="NYC")
        data2 = await self.feed.get_data(location="NYC")
        
        # Second call should return cached data
        assert data2.status == DataStatus.CACHED
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        self.feed._cached_data = MagicMock()
        
        self.feed.invalidate_cache()
        
        assert self.feed._cached_data is None


class TestStockFeed:
    """Tests for StockFeed class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = DataFeedConfig(
            feed_id="stock",
            feed_type=DataFeedType.STOCK,
            ttl_seconds=60,
        )
        self.feed = StockFeed(config)
    
    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test fetching stock data."""
        data = await self.feed.fetch(symbol="AAPL")
        
        assert data.data_type == DataFeedType.STOCK
        assert "symbol" in data.content
        assert data.content["symbol"] == "AAPL"
        assert "price" in data.content
        assert "change" in data.content
    
    @pytest.mark.asyncio
    async def test_fetch_unknown_symbol(self):
        """Test fetching with unknown symbol."""
        data = await self.feed.fetch(symbol="UNKNOWN")
        
        assert data.content["symbol"] == "UNKNOWN"
        assert "price" in data.content


class TestCryptoFeed:
    """Tests for CryptoFeed class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = DataFeedConfig(
            feed_id="crypto",
            feed_type=DataFeedType.CRYPTO,
            ttl_seconds=30,
        )
        self.feed = CryptoFeed(config)
    
    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test fetching crypto data."""
        data = await self.feed.fetch(symbol="BTC")
        
        assert data.data_type == DataFeedType.CRYPTO
        assert data.content["symbol"] == "BTC"
        assert "price_usd" in data.content
        assert "change_24h_percent" in data.content


class TestNewsFeed:
    """Tests for NewsFeed class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = DataFeedConfig(
            feed_id="news",
            feed_type=DataFeedType.NEWS,
            ttl_seconds=900,
        )
        self.feed = NewsFeed(config)
    
    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test fetching news data."""
        data = await self.feed.fetch(topic="technology")
        
        assert data.data_type == DataFeedType.NEWS
        assert data.content["topic"] == "technology"
        assert "headlines" in data.content
        assert len(data.content["headlines"]) > 0


class TestLiveDataManager:
    """Tests for LiveDataManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = LiveDataManager()
    
    def test_initialization(self):
        """Test manager initialization with default feeds."""
        assert "weather" in self.manager._feeds
        assert "stock" in self.manager._feeds
        assert "crypto" in self.manager._feeds
        assert "news" in self.manager._feeds
    
    def test_register_feed(self):
        """Test registering a new feed."""
        config = DataFeedConfig(
            feed_id="custom",
            feed_type=DataFeedType.CUSTOM,
        )
        
        class CustomFeed(WeatherFeed):
            pass
        
        feed = CustomFeed(config)
        self.manager.register_feed(feed)
        
        assert "custom" in self.manager._feeds
    
    def test_unregister_feed(self):
        """Test unregistering a feed."""
        result = self.manager.unregister_feed("weather")
        
        assert result is True
        assert "weather" not in self.manager._feeds
    
    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent feed."""
        result = self.manager.unregister_feed("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_data(self):
        """Test getting data from a feed."""
        data = await self.manager.get_data("weather", location="NYC")
        
        assert data is not None
        assert data.data_type == DataFeedType.WEATHER
    
    @pytest.mark.asyncio
    async def test_get_data_nonexistent(self):
        """Test getting data from nonexistent feed."""
        data = await self.manager.get_data("nonexistent")
        
        assert data is None
    
    @pytest.mark.asyncio
    async def test_get_multiple(self):
        """Test getting data from multiple feeds."""
        requests = [
            ("weather", {"location": "NYC"}),
            ("stock", {"symbol": "AAPL"}),
        ]
        
        results = await self.manager.get_multiple(requests)
        
        assert len(results) == 2
        assert "weather" in results
        assert "stock" in results
    
    def test_subscribe(self):
        """Test subscribing to feed updates."""
        callback = MagicMock()
        
        sub_id = self.manager.subscribe("weather", callback)
        
        assert sub_id is not None
        assert len(sub_id) == 16
        assert sub_id in self.manager._subscriptions
    
    def test_unsubscribe(self):
        """Test unsubscribing from feed updates."""
        callback = MagicMock()
        sub_id = self.manager.subscribe("weather", callback)
        
        result = self.manager.unsubscribe(sub_id)
        
        assert result is True
        assert sub_id not in self.manager._subscriptions
    
    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing nonexistent subscription."""
        result = self.manager.unsubscribe("nonexistent")
        
        assert result is False
    
    def test_list_feeds(self):
        """Test listing all feeds."""
        feeds = self.manager.list_feeds()
        
        assert len(feeds) >= 4
        
        feed_ids = [f["feed_id"] for f in feeds]
        assert "weather" in feed_ids
        assert "stock" in feed_ids
    
    @pytest.mark.asyncio
    async def test_get_context_for_query_weather(self):
        """Test getting context for weather query."""
        context = await self.manager.get_context_for_query(
            "What is the weather in New York?"
        )
        
        assert "Live Data" in context
        assert "WEATHER" in context
    
    @pytest.mark.asyncio
    async def test_get_context_for_query_stock(self):
        """Test getting context for stock query."""
        context = await self.manager.get_context_for_query(
            "What is the current AAPL stock price?"
        )
        
        assert "Live Data" in context
        assert "STOCK" in context
    
    @pytest.mark.asyncio
    async def test_get_context_for_query_crypto(self):
        """Test getting context for crypto query."""
        context = await self.manager.get_context_for_query(
            "What is the Bitcoin price today?"
        )
        
        assert "Live Data" in context
        assert "CRYPTO" in context
    
    @pytest.mark.asyncio
    async def test_get_context_for_query_no_match(self):
        """Test getting context for unrelated query."""
        context = await self.manager.get_context_for_query(
            "What is the capital of France?"
        )
        
        assert context == ""


class TestLiveDataTool:
    """Tests for LiveDataTool class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = LiveDataManager()
        self.tool = LiveDataTool(self.manager)
    
    def test_tool_properties(self):
        """Test tool properties."""
        assert self.tool.name == "live_data"
        assert "real-time" in self.tool.description.lower()
    
    @pytest.mark.asyncio
    async def test_execute_weather(self):
        """Test executing weather lookup."""
        result = await self.tool.execute("weather", location="NYC")
        
        assert "WEATHER" in result
    
    @pytest.mark.asyncio
    async def test_execute_stock(self):
        """Test executing stock lookup."""
        result = await self.tool.execute("stock", symbol="AAPL")
        
        assert "STOCK" in result
    
    @pytest.mark.asyncio
    async def test_execute_unknown_type(self):
        """Test executing with unknown feed type."""
        result = await self.tool.execute("unknown_type")
        
        assert "Unknown feed type" in result


class TestGlobalInstance:
    """Tests for global instance."""
    
    def test_get_live_data_manager(self):
        """Test getting global instance."""
        manager1 = get_live_data_manager()
        manager2 = get_live_data_manager()
        
        assert manager1 is manager2


class TestPollingIntegration:
    """Tests for polling functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = LiveDataManager()
    
    @pytest.mark.asyncio
    async def test_start_and_stop_polling(self):
        """Test starting and stopping polling."""
        await self.manager.start_polling()
        
        assert self.manager._running is True
        assert len(self.manager._polling_tasks) > 0
        
        await self.manager.stop_polling()
        
        assert self.manager._running is False
        assert len(self.manager._polling_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_subscriber_notification(self):
        """Test subscriber callback is called."""
        callback = MagicMock()
        
        self.manager.subscribe("weather", callback)
        
        # Get data which should trigger notification
        data = await self.manager.get_data("weather")
        await self.manager._notify_subscribers("weather", data)
        
        callback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

