"""Built-in LLMHive Plugins.

This module contains ready-to-use plugins that ship with LLMHive:
- WikiPlugin: Wikipedia search and information retrieval
- NewsPlugin: Latest news from RSS feeds
- MathPlugin: Advanced mathematical computations
- WeatherPlugin: Weather information and forecasts

These plugins serve as examples and provide useful functionality
out of the box.
"""
from __future__ import annotations

# Built-in plugins are loaded dynamically by the plugin manager
# from their respective directories. This __init__ just provides
# imports for programmatic use.

try:
    from .wiki_plugin import WikiPlugin
    WIKI_AVAILABLE = True
except ImportError:
    WIKI_AVAILABLE = False
    WikiPlugin = None  # type: ignore

try:
    from .news_plugin import NewsPlugin
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False
    NewsPlugin = None  # type: ignore

try:
    from .math_plugin import MathPlugin
    MATH_AVAILABLE = True
except ImportError:
    MATH_AVAILABLE = False
    MathPlugin = None  # type: ignore

try:
    from .weather_plugin import WeatherPlugin
    WEATHER_AVAILABLE = True
except ImportError:
    WEATHER_AVAILABLE = False
    WeatherPlugin = None  # type: ignore


__all__ = []

if WIKI_AVAILABLE:
    __all__.append("WikiPlugin")
if NEWS_AVAILABLE:
    __all__.append("NewsPlugin")
if MATH_AVAILABLE:
    __all__.append("MathPlugin")
if WEATHER_AVAILABLE:
    __all__.append("WeatherPlugin")

