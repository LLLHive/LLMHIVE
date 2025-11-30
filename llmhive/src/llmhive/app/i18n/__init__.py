"""Internationalization (i18n) and Multilingual Support for LLMHive.

This module provides:
- Language detection for incoming queries
- Translation services integration
- Multilingual prompt templates
- Locale-aware formatting
- Language-specific model routing

Usage:
    from llmhive.app.i18n import (
        detect_language,
        translate_text,
        get_multilingual_handler,
    )
    
    # Detect language
    lang = await detect_language("Bonjour, comment ça va?")
    # Returns: LanguageInfo(code="fr", name="French", confidence=0.95)
    
    # Translate text
    translated = await translate_text(
        "Hello world",
        source_lang="en",
        target_lang="es",
    )
    # Returns: "Hola mundo"
"""
from __future__ import annotations

# Language detection
try:
    from .detection import (
        LanguageDetector,
        LanguageInfo,
        detect_language,
        get_language_detector,
        SUPPORTED_LANGUAGES,
    )
    DETECTION_AVAILABLE = True
except ImportError:
    DETECTION_AVAILABLE = False
    LanguageDetector = None  # type: ignore

# Translation
try:
    from .translation import (
        TranslationService,
        TranslationResult,
        translate_text,
        get_translation_service,
    )
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    TranslationService = None  # type: ignore

# Multilingual handler
try:
    from .handler import (
        MultilingualHandler,
        MultilingualContext,
        get_multilingual_handler,
    )
    HANDLER_AVAILABLE = True
except ImportError:
    HANDLER_AVAILABLE = False
    MultilingualHandler = None  # type: ignore

# Localization
try:
    from .localization import (
        LocaleFormatter,
        format_number,
        format_date,
        format_currency,
        get_locale_formatter,
    )
    LOCALIZATION_AVAILABLE = True
except ImportError:
    LOCALIZATION_AVAILABLE = False
    LocaleFormatter = None  # type: ignore


__all__ = []

if DETECTION_AVAILABLE:
    __all__.extend([
        "LanguageDetector",
        "LanguageInfo",
        "detect_language",
        "get_language_detector",
        "SUPPORTED_LANGUAGES",
    ])

if TRANSLATION_AVAILABLE:
    __all__.extend([
        "TranslationService",
        "TranslationResult",
        "translate_text",
        "get_translation_service",
    ])

if HANDLER_AVAILABLE:
    __all__.extend([
        "MultilingualHandler",
        "MultilingualContext",
        "get_multilingual_handler",
    ])

if LOCALIZATION_AVAILABLE:
    __all__.extend([
        "LocaleFormatter",
        "format_number",
        "format_date",
        "format_currency",
        "get_locale_formatter",
    ])

