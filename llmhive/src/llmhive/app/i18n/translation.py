"""Translation Service for LLMHive.

Provides translation capabilities using multiple backends:
1. Google Translate API
2. DeepL API
3. LibreTranslate (open source)
4. LLM-based translation (fallback)

Usage:
    service = get_translation_service()
    
    # Translate text
    result = await service.translate(
        "Hello, how are you?",
        source_lang="en",
        target_lang="es",
    )
    print(result.translated)  # "Hola, ¿cómo estás?"
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .detection import detect_language, LanguageInfo

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class TranslationProvider(str, Enum):
    """Available translation providers."""
    GOOGLE = "google"
    DEEPL = "deepl"
    LIBRE = "libre"
    LLM = "llm"
    MOCK = "mock"  # For testing


@dataclass(slots=True)
class TranslationResult:
    """Result of a translation."""
    original: str
    translated: str
    source_lang: str
    target_lang: str
    provider: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "translated": self.translated,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "provider": self.provider,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class TranslationError:
    """Translation error information."""
    message: str
    provider: str
    code: Optional[str] = None


# ==============================================================================
# Translation Backends
# ==============================================================================

class TranslationBackend(ABC):
    """Base class for translation backends."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate text."""
        pass


class GoogleTranslateBackend(TranslationBackend):
    """Google Translate API backend."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
    
    @property
    def name(self) -> str:
        return "google"
    
    @property
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate using Google Translate API."""
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp required for Google Translate")
        
        url = "https://translation.googleapis.com/language/translate/v2"
        
        async with aiohttp.ClientSession() as session:
            params = {
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "key": self.api_key,
                "format": "text",
            }
            
            async with session.post(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated = data["data"]["translations"][0]["translatedText"]
                    
                    return TranslationResult(
                        original=text,
                        translated=translated,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        provider=self.name,
                    )
                else:
                    error = await resp.text()
                    raise RuntimeError(f"Google Translate error: {error}")


class DeepLBackend(TranslationBackend):
    """DeepL API backend."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")
        self.base_url = "https://api-free.deepl.com/v2" if self.api_key and ":fx" in self.api_key else "https://api.deepl.com/v2"
    
    @property
    def name(self) -> str:
        return "deepl"
    
    @property
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate using DeepL API."""
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp required for DeepL")
        
        # DeepL uses uppercase language codes
        source = source_lang.upper()
        target = target_lang.upper()
        
        # Handle language variants
        if target == "EN":
            target = "EN-US"
        if target == "PT":
            target = "PT-BR"
        
        url = f"{self.base_url}/translate"
        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
        
        async with aiohttp.ClientSession() as session:
            data = {
                "text": [text],
                "source_lang": source,
                "target_lang": target,
            }
            
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    translated = result["translations"][0]["text"]
                    
                    return TranslationResult(
                        original=text,
                        translated=translated,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        provider=self.name,
                    )
                else:
                    error = await resp.text()
                    raise RuntimeError(f"DeepL error: {error}")


class LibreTranslateBackend(TranslationBackend):
    """LibreTranslate (open source) backend."""
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.api_url = api_url or os.getenv(
            "LIBRETRANSLATE_URL",
            "https://libretranslate.com"
        )
        self.api_key = api_key or os.getenv("LIBRETRANSLATE_API_KEY")
    
    @property
    def name(self) -> str:
        return "libre"
    
    @property
    def is_available(self) -> bool:
        return bool(self.api_url)
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate using LibreTranslate."""
        try:
            import aiohttp
        except ImportError:
            raise RuntimeError("aiohttp required for LibreTranslate")
        
        url = f"{self.api_url}/translate"
        
        async with aiohttp.ClientSession() as session:
            data = {
                "q": text,
                "source": source_lang,
                "target": target_lang,
            }
            if self.api_key:
                data["api_key"] = self.api_key
            
            async with session.post(url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    translated = result.get("translatedText", "")
                    
                    return TranslationResult(
                        original=text,
                        translated=translated,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        provider=self.name,
                    )
                else:
                    error = await resp.text()
                    raise RuntimeError(f"LibreTranslate error: {error}")


class LLMTranslationBackend(TranslationBackend):
    """LLM-based translation fallback."""
    
    def __init__(self, llm_provider: Optional[Any] = None):
        self.llm_provider = llm_provider
    
    @property
    def name(self) -> str:
        return "llm"
    
    @property
    def is_available(self) -> bool:
        return self.llm_provider is not None
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate using LLM."""
        if not self.llm_provider:
            raise RuntimeError("LLM provider not configured")
        
        from .detection import SUPPORTED_LANGUAGES
        
        source_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
        target_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        
        prompt = f"""Translate the following text from {source_name} to {target_name}.
Only output the translation, nothing else.

Text: {text}

Translation:"""
        
        response = await self.llm_provider.generate(prompt)
        translated = response.strip()
        
        return TranslationResult(
            original=text,
            translated=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            provider=self.name,
            confidence=0.8,  # Lower confidence for LLM translation
        )


class MockTranslationBackend(TranslationBackend):
    """Mock backend for testing."""
    
    MOCK_TRANSLATIONS = {
        ("en", "es"): {
            "hello": "hola",
            "world": "mundo",
            "how are you": "cómo estás",
            "thank you": "gracias",
        },
        ("en", "fr"): {
            "hello": "bonjour",
            "world": "monde",
            "how are you": "comment allez-vous",
            "thank you": "merci",
        },
        ("es", "en"): {
            "hola": "hello",
            "mundo": "world",
            "gracias": "thank you",
        },
    }
    
    @property
    def name(self) -> str:
        return "mock"
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Mock translation for testing."""
        key = (source_lang, target_lang)
        translations = self.MOCK_TRANSLATIONS.get(key, {})
        
        text_lower = text.lower().strip()
        translated = translations.get(text_lower, f"[{target_lang}:{text}]")
        
        return TranslationResult(
            original=text,
            translated=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            provider=self.name,
            confidence=1.0 if text_lower in translations else 0.5,
        )


# ==============================================================================
# Translation Service
# ==============================================================================

class TranslationService:
    """Multi-provider translation service.
    
    Automatically selects the best available translation provider.
    Supports caching for efficiency.
    
    Usage:
        service = TranslationService()
        
        result = await service.translate(
            "Hello, world!",
            target_lang="es",
        )
        print(result.translated)  # "¡Hola, mundo!"
    """
    
    def __init__(
        self,
        preferred_provider: Optional[TranslationProvider] = None,
        llm_provider: Optional[Any] = None,
        enable_cache: bool = True,
    ):
        self.preferred_provider = preferred_provider
        self.enable_cache = enable_cache
        self._cache: Dict[str, TranslationResult] = {}
        
        # Initialize backends
        self._backends: Dict[str, TranslationBackend] = {
            "google": GoogleTranslateBackend(),
            "deepl": DeepLBackend(),
            "libre": LibreTranslateBackend(),
            "llm": LLMTranslationBackend(llm_provider),
            "mock": MockTranslationBackend(),
        }
    
    def _get_cache_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Generate cache key."""
        return f"{source_lang}:{target_lang}:{hash(text)}"
    
    def _get_backend(
        self,
        provider: Optional[TranslationProvider] = None,
    ) -> TranslationBackend:
        """Get the best available backend."""
        # Use specified provider if available
        if provider:
            backend = self._backends.get(provider.value)
            if backend and backend.is_available:
                return backend
        
        # Use preferred provider if set
        if self.preferred_provider:
            backend = self._backends.get(self.preferred_provider.value)
            if backend and backend.is_available:
                return backend
        
        # Try providers in order of quality
        for name in ["deepl", "google", "libre", "llm", "mock"]:
            backend = self._backends.get(name)
            if backend and backend.is_available:
                return backend
        
        # Return mock as ultimate fallback
        return self._backends["mock"]
    
    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
        provider: Optional[TranslationProvider] = None,
    ) -> TranslationResult:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code (e.g., "es")
            source_lang: Source language code (auto-detect if None)
            provider: Specific provider to use
            
        Returns:
            TranslationResult
        """
        if not text or not text.strip():
            return TranslationResult(
                original=text,
                translated=text,
                source_lang=source_lang or "en",
                target_lang=target_lang,
                provider="none",
            )
        
        # Auto-detect source language if not specified
        if not source_lang:
            detected = await detect_language(text)
            source_lang = detected.code
        
        # Skip translation if source == target
        if source_lang == target_lang:
            return TranslationResult(
                original=text,
                translated=text,
                source_lang=source_lang,
                target_lang=target_lang,
                provider="none",
            )
        
        # Check cache
        if self.enable_cache:
            cache_key = self._get_cache_key(text, source_lang, target_lang)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Get backend and translate
        backend = self._get_backend(provider)
        
        try:
            result = await backend.translate(text, source_lang, target_lang)
            
            # Cache result
            if self.enable_cache:
                self._cache[cache_key] = result
            
            logger.debug(
                "Translated [%s->%s] via %s: %s -> %s",
                source_lang, target_lang, backend.name,
                text[:50], result.translated[:50],
            )
            
            return result
            
        except Exception as e:
            logger.error("Translation failed with %s: %s", backend.name, e)
            
            # Try fallback to mock
            if backend.name != "mock":
                return await self._backends["mock"].translate(
                    text, source_lang, target_lang
                )
            raise
    
    async def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts."""
        tasks = [
            self.translate(text, target_lang, source_lang)
            for text in texts
        ]
        return await asyncio.gather(*tasks)
    
    async def detect_and_translate(
        self,
        text: str,
        target_lang: str,
    ) -> Tuple[LanguageInfo, TranslationResult]:
        """Detect language and translate in one call."""
        detected = await detect_language(text)
        
        result = await self.translate(
            text,
            target_lang=target_lang,
            source_lang=detected.code,
        )
        
        return detected, result
    
    def clear_cache(self) -> None:
        """Clear translation cache."""
        self._cache.clear()
    
    def get_available_providers(self) -> List[str]:
        """Get list of available translation providers."""
        return [
            name for name, backend in self._backends.items()
            if backend.is_available
        ]


# ==============================================================================
# Global Instance
# ==============================================================================

_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create global translation service."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


async def translate_text(
    text: str,
    target_lang: str,
    source_lang: Optional[str] = None,
) -> str:
    """Quick helper to translate text."""
    service = get_translation_service()
    result = await service.translate(text, target_lang, source_lang)
    return result.translated

