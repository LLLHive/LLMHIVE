"""Weather Plugin for LLMHive.

Provides weather information and forecasts.

Features:
- Current weather conditions
- Multi-day forecasts
- Weather alerts
- Location-based queries

Usage:
    plugin = WeatherPlugin()
    await plugin.activate()
    
    # Get current weather
    weather = await plugin.get_weather("New York")
    
    # Get forecast
    forecast = await plugin.get_forecast("London", days=5)
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..base import (
    Plugin,
    PluginConfig,
    PluginTool,
    PluginKnowledgeBase,
    PluginCapability,
    PluginTier,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass
class WeatherData:
    """Weather information."""
    location: str
    country: str
    temperature_c: float
    temperature_f: float
    feels_like_c: float
    feels_like_f: float
    condition: str
    humidity: int
    wind_kph: float
    wind_mph: float
    wind_direction: str
    pressure_mb: float
    visibility_km: float
    uv_index: float
    last_updated: str


@dataclass
class ForecastDay:
    """Forecast for a single day."""
    date: str
    max_temp_c: float
    min_temp_c: float
    max_temp_f: float
    min_temp_f: float
    condition: str
    chance_of_rain: int
    humidity: int


# ==============================================================================
# Weather API Client
# ==============================================================================

class WeatherAPIClient:
    """Client for weather API (WeatherAPI.com or Open-Meteo)."""
    
    OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
    GEOCODING_BASE = "https://geocoding-api.open-meteo.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize client with optional API key."""
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
    
    async def _geocode(self, location: str) -> Optional[Dict[str, Any]]:
        """Get coordinates for a location."""
        try:
            import aiohttp
        except ImportError:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.GEOCODING_BASE}/search"
                params = {"name": location, "count": 1}
                
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        if results:
                            return results[0]
        except Exception as e:
            logger.warning("Geocoding failed: %s", e)
        
        return None
    
    async def get_current_weather(
        self,
        location: str,
    ) -> Optional[WeatherData]:
        """Get current weather for a location."""
        try:
            import aiohttp
        except ImportError:
            return None
        
        # Get coordinates
        geo = await self._geocode(location)
        if not geo:
            return None
        
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        location_name = geo.get("name", location)
        country = geo.get("country", "")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.OPEN_METEO_BASE}/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure",
                    "timezone": "auto",
                }
                
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current = data.get("current", {})
                        
                        temp_c = current.get("temperature_2m", 0)
                        feels_c = current.get("apparent_temperature", temp_c)
                        
                        return WeatherData(
                            location=location_name,
                            country=country,
                            temperature_c=temp_c,
                            temperature_f=temp_c * 9/5 + 32,
                            feels_like_c=feels_c,
                            feels_like_f=feels_c * 9/5 + 32,
                            condition=self._decode_weather_code(
                                current.get("weather_code", 0)
                            ),
                            humidity=current.get("relative_humidity_2m", 0),
                            wind_kph=current.get("wind_speed_10m", 0),
                            wind_mph=current.get("wind_speed_10m", 0) * 0.621371,
                            wind_direction=self._wind_direction(
                                current.get("wind_direction_10m", 0)
                            ),
                            pressure_mb=current.get("surface_pressure", 0),
                            visibility_km=10.0,  # Not available in free API
                            uv_index=0,  # Not available in current
                            last_updated=data.get("current", {}).get("time", ""),
                        )
        except Exception as e:
            logger.error("Weather fetch failed: %s", e)
        
        return None
    
    async def get_forecast(
        self,
        location: str,
        days: int = 5,
    ) -> List[ForecastDay]:
        """Get weather forecast."""
        try:
            import aiohttp
        except ImportError:
            return []
        
        geo = await self._geocode(location)
        if not geo:
            return []
        
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.OPEN_METEO_BASE}/forecast"
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,relative_humidity_2m_max",
                    "forecast_days": days,
                    "timezone": "auto",
                }
                
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        daily = data.get("daily", {})
                        
                        forecasts = []
                        dates = daily.get("time", [])
                        max_temps = daily.get("temperature_2m_max", [])
                        min_temps = daily.get("temperature_2m_min", [])
                        codes = daily.get("weather_code", [])
                        rain_probs = daily.get("precipitation_probability_max", [])
                        humidity = daily.get("relative_humidity_2m_max", [])
                        
                        for i in range(min(len(dates), days)):
                            max_c = max_temps[i] if i < len(max_temps) else 0
                            min_c = min_temps[i] if i < len(min_temps) else 0
                            
                            forecasts.append(ForecastDay(
                                date=dates[i],
                                max_temp_c=max_c,
                                min_temp_c=min_c,
                                max_temp_f=max_c * 9/5 + 32,
                                min_temp_f=min_c * 9/5 + 32,
                                condition=self._decode_weather_code(
                                    codes[i] if i < len(codes) else 0
                                ),
                                chance_of_rain=rain_probs[i] if i < len(rain_probs) else 0,
                                humidity=humidity[i] if i < len(humidity) else 0,
                            ))
                        
                        return forecasts
        except Exception as e:
            logger.error("Forecast fetch failed: %s", e)
        
        return []
    
    def _decode_weather_code(self, code: int) -> str:
        """Decode WMO weather code to description."""
        codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return codes.get(code, "Unknown")
    
    def _wind_direction(self, degrees: float) -> str:
        """Convert wind degrees to direction."""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(degrees / 22.5) % 16
        return directions[idx]


# ==============================================================================
# Weather Plugin
# ==============================================================================

class WeatherPlugin(Plugin):
    """Weather Plugin for LLMHive.
    
    Provides weather information and forecasts.
    
    Tools:
    - weather_current: Get current weather conditions
    - weather_forecast: Get multi-day forecast
    """
    
    def __init__(self):
        config = PluginConfig(
            name="weather",
            display_name="Weather",
            version="1.0.0",
            description="Get weather information and forecasts",
            author="LLMHive",
            domains=["weather", "climate", "forecast"],
            keywords=[
                "weather", "temperature", "forecast", "rain", "snow",
                "sunny", "cloudy", "humidity", "wind", "climate",
            ],
            min_tier=PluginTier.FREE,
            capabilities=[PluginCapability.TOOLS, PluginCapability.KNOWLEDGE],
            enabled=True,
            auto_activate=True,
            priority=35,
        )
        super().__init__(config)
        
        self.client = WeatherAPIClient()
    
    async def initialize(self) -> bool:
        """Initialize Weather plugin."""
        logger.info("Initializing Weather plugin")
        return True
    
    def get_tools(self) -> List[PluginTool]:
        """Get weather tools."""
        return [
            PluginTool(
                name="weather_current",
                description="Get current weather conditions for a location.",
                handler=self._tool_current,
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location (city name, e.g., 'New York', 'London')",
                        },
                    },
                    "required": ["location"],
                },
                domains=["weather"],
                trigger_keywords=["weather", "temperature", "current weather"],
            ),
            PluginTool(
                name="weather_forecast",
                description="Get weather forecast for upcoming days.",
                handler=self._tool_forecast,
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location (city name)",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days (1-7)",
                            "default": 5,
                        },
                    },
                    "required": ["location"],
                },
                domains=["weather", "forecast"],
                trigger_keywords=["forecast", "weather forecast", "upcoming weather"],
            ),
        ]
    
    def get_knowledge_bases(self) -> List[PluginKnowledgeBase]:
        """Weather provides dynamic knowledge."""
        return [
            PluginKnowledgeBase(
                name="weather_info",
                description="Current weather conditions",
                kb_type="api",
                domains=["weather"],
                query_handler=self._query_knowledge,
            )
        ]
    
    async def _query_knowledge(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Extract weather info from query."""
        # Try to extract location from query
        # Simple extraction - look for common patterns
        import re
        
        patterns = [
            r"weather (?:in|for|at) ([A-Za-z\s]+?)(?:\?|$|,)",
            r"(?:in|at) ([A-Za-z\s]+?) (?:weather|temperature)",
            r"([A-Za-z\s]+?) weather",
        ]
        
        location = None
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                break
        
        if not location:
            return []
        
        weather = await self.client.get_current_weather(location)
        if weather:
            return [{
                "content": f"Current weather in {weather.location}, {weather.country}: "
                          f"{weather.condition}, {weather.temperature_c}°C ({weather.temperature_f}°F), "
                          f"Humidity: {weather.humidity}%, Wind: {weather.wind_kph} km/h {weather.wind_direction}",
                "source": "Weather API",
                "confidence": 0.95,
            }]
        
        return []
    
    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------
    
    async def _tool_current(
        self,
        location: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle weather_current tool call."""
        weather = await self.client.get_current_weather(location)
        
        if weather:
            return {
                "success": True,
                "location": f"{weather.location}, {weather.country}",
                "temperature": {
                    "celsius": round(weather.temperature_c, 1),
                    "fahrenheit": round(weather.temperature_f, 1),
                },
                "feels_like": {
                    "celsius": round(weather.feels_like_c, 1),
                    "fahrenheit": round(weather.feels_like_f, 1),
                },
                "condition": weather.condition,
                "humidity": weather.humidity,
                "wind": {
                    "speed_kph": round(weather.wind_kph, 1),
                    "speed_mph": round(weather.wind_mph, 1),
                    "direction": weather.wind_direction,
                },
                "pressure_mb": round(weather.pressure_mb, 1),
                "last_updated": weather.last_updated,
            }
        
        return {
            "success": False,
            "error": f"Could not get weather for: {location}",
        }
    
    async def _tool_forecast(
        self,
        location: str,
        days: int = 5,
        **kwargs,
    ) -> Dict[str, Any]:
        """Handle weather_forecast tool call."""
        days = min(max(days, 1), 7)
        forecasts = await self.client.get_forecast(location, days)
        
        if forecasts:
            return {
                "success": True,
                "location": location,
                "days": len(forecasts),
                "forecast": [
                    {
                        "date": f.date,
                        "high": {
                            "celsius": round(f.max_temp_c, 1),
                            "fahrenheit": round(f.max_temp_f, 1),
                        },
                        "low": {
                            "celsius": round(f.min_temp_c, 1),
                            "fahrenheit": round(f.min_temp_f, 1),
                        },
                        "condition": f.condition,
                        "chance_of_rain": f.chance_of_rain,
                        "humidity": f.humidity,
                    }
                    for f in forecasts
                ],
            }
        
        return {
            "success": False,
            "error": f"Could not get forecast for: {location}",
        }


# Plugin manifest
PLUGIN_MANIFEST = {
    "name": "weather",
    "display_name": "Weather",
    "version": "1.0.0",
    "description": "Get weather information and forecasts",
    "author": "LLMHive",
    "domains": ["weather", "climate", "forecast"],
    "keywords": ["weather", "temperature", "forecast", "rain", "climate"],
    "min_tier": "free",
    "capabilities": ["tools", "knowledge"],
    "entry_point": "weather_plugin.py",
    "plugin_class": "WeatherPlugin",
    "enabled": True,
    "auto_activate": True,
    "priority": 35,
}

