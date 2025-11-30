"""Tests for Internationalization (i18n) System.

These tests verify:
1. Language detection accuracy
2. Translation service integration
3. Multilingual handler flow
4. Locale formatting (numbers, dates, currencies)
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, date, timezone
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import modules under test
from llmhive.src.llmhive.app.i18n.detection import (
    LanguageDetector,
    LanguageInfo,
    HeuristicDetector,
    detect_language,
    SUPPORTED_LANGUAGES,
)
from llmhive.src.llmhive.app.i18n.translation import (
    TranslationService,
    TranslationResult,
    MockTranslationBackend,
    translate_text,
)
from llmhive.src.llmhive.app.i18n.handler import (
    MultilingualHandler,
    MultilingualContext,
    ConversationLanguageTracker,
    SYSTEM_INSTRUCTIONS,
)
from llmhive.src.llmhive.app.i18n.localization import (
    LocaleFormatter,
    LocaleConfig,
    format_number,
    format_date,
    format_currency,
    LOCALE_CONFIGS,
)


# ==============================================================================
# Language Detection Tests
# ==============================================================================

class TestHeuristicDetector:
    """Tests for HeuristicDetector."""
    
    @pytest.fixture
    def detector(self):
        return HeuristicDetector()
    
    def test_detect_chinese(self, detector):
        """Test detecting Chinese."""
        result = detector.detect("你好世界")
        
        assert result is not None
        assert result.code == "zh"
        assert result.confidence > 0.5
    
    def test_detect_japanese(self, detector):
        """Test detecting Japanese."""
        result = detector.detect("こんにちは世界")
        
        assert result is not None
        assert result.code == "ja"
    
    def test_detect_korean(self, detector):
        """Test detecting Korean."""
        result = detector.detect("안녕하세요 세계")
        
        assert result is not None
        assert result.code == "ko"
    
    def test_detect_arabic(self, detector):
        """Test detecting Arabic."""
        result = detector.detect("مرحبا بالعالم")
        
        assert result is not None
        assert result.code == "ar"
    
    def test_detect_russian(self, detector):
        """Test detecting Russian (Cyrillic)."""
        result = detector.detect("Привет мир")
        
        assert result is not None
        assert result.code == "ru"
    
    def test_detect_english_by_words(self, detector):
        """Test detecting English by common words."""
        result = detector.detect("The quick brown fox jumps over the lazy dog.")
        
        assert result is not None
        assert result.code == "en"
    
    def test_detect_spanish_by_words(self, detector):
        """Test detecting Spanish by common words."""
        result = detector.detect("El gato está en la casa con un libro.")
        
        assert result is not None
        assert result.code == "es"
    
    def test_detect_french_by_words(self, detector):
        """Test detecting French by common words."""
        result = detector.detect("Le chat est dans la maison avec un livre pour lire.")
        
        assert result is not None
        assert result.code == "fr"


class TestLanguageDetector:
    """Tests for LanguageDetector."""
    
    @pytest.fixture
    def detector(self):
        return LanguageDetector()
    
    @pytest.mark.asyncio
    async def test_detect_english(self, detector):
        """Test detecting English."""
        result = await detector.detect("Hello, how are you today?")
        
        assert result.code == "en"
        assert result.name == "English"
    
    @pytest.mark.asyncio
    async def test_detect_short_text(self, detector):
        """Test short text returns default."""
        result = await detector.detect("Hi")
        
        # Short text should return default
        assert result.code == "en"
    
    @pytest.mark.asyncio
    async def test_detect_empty_text(self, detector):
        """Test empty text returns default."""
        result = await detector.detect("")
        
        assert result.code == "en"
        assert result.confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_detect_with_alternatives(self, detector):
        """Test detection with alternatives."""
        result = await detector.detect_with_alternatives(
            "The weather is beautiful today.",
            max_alternatives=3,
        )
        
        assert result.primary.code == "en"
        assert result.method in ["langdetect", "heuristic", "default"]
    
    def test_is_right_to_left(self, detector):
        """Test RTL detection."""
        assert detector.is_right_to_left("ar") is True
        assert detector.is_right_to_left("he") is True
        assert detector.is_right_to_left("en") is False
        assert detector.is_right_to_left("es") is False


# ==============================================================================
# Translation Tests
# ==============================================================================

class TestMockTranslationBackend:
    """Tests for MockTranslationBackend."""
    
    @pytest.fixture
    def backend(self):
        return MockTranslationBackend()
    
    @pytest.mark.asyncio
    async def test_translate_known(self, backend):
        """Test translating known phrase."""
        result = await backend.translate("hello", "en", "es")
        
        assert result.translated == "hola"
        assert result.confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_translate_unknown(self, backend):
        """Test translating unknown phrase."""
        result = await backend.translate("unknown phrase", "en", "es")
        
        assert result.translated == "[es:unknown phrase]"
        assert result.confidence == 0.5


class TestTranslationService:
    """Tests for TranslationService."""
    
    @pytest.fixture
    def service(self):
        return TranslationService(enable_cache=True)
    
    @pytest.mark.asyncio
    async def test_translate_same_language(self, service):
        """Test translating to same language returns original."""
        result = await service.translate(
            "Hello world",
            target_lang="en",
            source_lang="en",
        )
        
        assert result.translated == "Hello world"
        assert result.provider == "none"
    
    @pytest.mark.asyncio
    async def test_translate_empty(self, service):
        """Test translating empty text."""
        result = await service.translate("", target_lang="es")
        
        assert result.translated == ""
        assert result.provider == "none"
    
    @pytest.mark.asyncio
    async def test_translate_with_cache(self, service):
        """Test translation caching."""
        # First call
        result1 = await service.translate("hello", target_lang="es", source_lang="en")
        
        # Second call (should use cache)
        result2 = await service.translate("hello", target_lang="es", source_lang="en")
        
        assert result1.translated == result2.translated
    
    def test_get_available_providers(self, service):
        """Test getting available providers."""
        providers = service.get_available_providers()
        
        # Mock should always be available
        assert "mock" in providers
    
    @pytest.mark.asyncio
    async def test_detect_and_translate(self, service):
        """Test combined detection and translation."""
        # This will detect as English and translate to Spanish
        detected, result = await service.detect_and_translate(
            "Hello world",
            target_lang="es",
        )
        
        assert detected.code == "en"
        assert result.source_lang == "en"
        assert result.target_lang == "es"


# ==============================================================================
# Multilingual Handler Tests
# ==============================================================================

class TestMultilingualHandler:
    """Tests for MultilingualHandler."""
    
    @pytest.fixture
    def handler(self):
        return MultilingualHandler()
    
    @pytest.mark.asyncio
    async def test_prepare_english_query(self, handler):
        """Test preparing English query."""
        context = await handler.prepare_query(
            "What is the capital of France?"
        )
        
        assert context.detected_language.code == "en"
        assert context.response_language == "en"
        assert not context.query_translated
    
    @pytest.mark.asyncio
    async def test_prepare_with_override(self, handler):
        """Test preparing with language override."""
        context = await handler.prepare_query(
            "What is the capital of France?",
            user_language="es",
        )
        
        assert context.detected_language.code == "es"
        assert context.response_language == "es"
    
    @pytest.mark.asyncio
    async def test_system_instruction_generation(self, handler):
        """Test system instruction for different languages."""
        context = await handler.prepare_query(
            "Test query",
            user_language="es",
        )
        
        assert "Spanish" in context.system_instruction
        assert "español" in context.system_instruction.lower()
    
    def test_get_prompt_prefix(self, handler):
        """Test getting prompt prefix."""
        prefix = handler.get_prompt_prefix("es")
        
        assert "Spanish" in prefix
        assert "español" in prefix.lower()
    
    @pytest.mark.asyncio
    async def test_process_response_no_translation(self, handler):
        """Test processing response without translation."""
        # Create context for English
        context = await handler.prepare_query(
            "What is AI?",
            user_language="en",
        )
        
        response = await handler.process_response(
            "AI is artificial intelligence.",
            context,
        )
        
        assert not response.was_translated
        assert response.final_response == "AI is artificial intelligence."


class TestConversationLanguageTracker:
    """Tests for ConversationLanguageTracker."""
    
    @pytest.fixture
    def tracker(self):
        return ConversationLanguageTracker()
    
    def test_set_user_preference(self, tracker):
        """Test setting user language preference."""
        tracker.set_user_preference("user1", "es")
        
        assert tracker.get_user_preference("user1") == "es"
    
    def test_update_conversation_language(self, tracker):
        """Test updating conversation language."""
        # First message
        lang = tracker.update_conversation_language("session1", "en")
        assert lang == "en"
        
        # Same language
        lang = tracker.update_conversation_language("session1", "en")
        assert lang == "en"
        
        # Language switch
        lang = tracker.update_conversation_language("session1", "es")
        assert lang == "es"
    
    def test_get_conversation_language(self, tracker):
        """Test getting conversation language."""
        tracker.update_conversation_language("session1", "fr")
        
        assert tracker.get_conversation_language("session1") == "fr"
        assert tracker.get_conversation_language("unknown") == "en"  # Default
    
    def test_end_conversation(self, tracker):
        """Test ending conversation cleans up."""
        tracker.update_conversation_language("session1", "es")
        tracker.end_conversation("session1")
        
        assert tracker.get_conversation_language("session1") == "en"  # Default


# ==============================================================================
# Localization Tests
# ==============================================================================

class TestLocaleFormatter:
    """Tests for LocaleFormatter."""
    
    def test_english_number_format(self):
        """Test English number formatting."""
        formatter = LocaleFormatter("en")
        
        assert formatter.format_number(1234567.89) == "1,234,567.89"
        assert formatter.format_number(1000) == "1,000.00"
    
    def test_spanish_number_format(self):
        """Test Spanish number formatting."""
        formatter = LocaleFormatter("es")
        
        assert formatter.format_number(1234567.89) == "1.234.567,89"
        assert formatter.format_number(1000) == "1.000,00"
    
    def test_german_number_format(self):
        """Test German number formatting."""
        formatter = LocaleFormatter("de")
        
        assert formatter.format_number(1234567.89) == "1.234.567,89"
    
    def test_french_number_format(self):
        """Test French number formatting (space separator)."""
        formatter = LocaleFormatter("fr")
        
        assert formatter.format_number(1234567.89) == "1 234 567,89"
    
    def test_negative_number(self):
        """Test negative number formatting."""
        formatter = LocaleFormatter("en")
        
        assert formatter.format_number(-1234.56) == "-1,234.56"
    
    def test_integer_format(self):
        """Test integer formatting."""
        formatter = LocaleFormatter("en")
        
        assert formatter.format_integer(1000000) == "1,000,000"
    
    def test_percentage_format(self):
        """Test percentage formatting."""
        formatter = LocaleFormatter("en")
        
        assert formatter.format_percentage(0.1234) == "12.3%"
    
    def test_date_format_english(self):
        """Test English date formatting."""
        formatter = LocaleFormatter("en")
        dt = datetime(2025, 1, 15, 14, 30)
        
        formatted = formatter.format_date(dt)
        assert "January" in formatted
        assert "15" in formatted
        assert "2025" in formatted
    
    def test_date_format_spanish(self):
        """Test Spanish date formatting."""
        formatter = LocaleFormatter("es")
        dt = datetime(2025, 1, 15, 14, 30)
        
        formatted = formatter.format_date(dt)
        assert "enero" in formatted
        assert "15" in formatted
        assert "2025" in formatted
    
    def test_date_format_short(self):
        """Test short date format."""
        formatter = LocaleFormatter("en")
        dt = datetime(2025, 1, 15)
        
        formatted = formatter.format_date(dt, format_type="short")
        assert "/" in formatted
    
    def test_currency_english(self):
        """Test English currency formatting."""
        formatter = LocaleFormatter("en")
        
        assert formatter.format_currency(99.99) == "$99.99"
    
    def test_currency_spanish(self):
        """Test Spanish currency formatting (symbol after)."""
        formatter = LocaleFormatter("es")
        
        assert formatter.format_currency(99.99) == "99,99 €"
    
    def test_currency_japanese(self):
        """Test Japanese currency formatting."""
        formatter = LocaleFormatter("ja")
        
        assert formatter.format_currency(1000) == "¥1,000.00"
    
    def test_get_month_name(self):
        """Test getting localized month name."""
        formatter_en = LocaleFormatter("en")
        formatter_es = LocaleFormatter("es")
        
        assert formatter_en.get_month_name(1) == "January"
        assert formatter_es.get_month_name(1) == "enero"
    
    def test_get_day_name(self):
        """Test getting localized day name."""
        formatter_en = LocaleFormatter("en")
        formatter_es = LocaleFormatter("es")
        
        assert formatter_en.get_day_name(0) == "Monday"
        assert formatter_es.get_day_name(0) == "lunes"


class TestLocaleConfigs:
    """Tests for predefined locale configs."""
    
    def test_all_configs_valid(self):
        """Test all locale configs have required fields."""
        for code, config in LOCALE_CONFIGS.items():
            assert config.code == code
            assert config.decimal_separator
            assert config.thousands_separator is not None  # Can be empty
            assert config.date_format
            assert config.currency_symbol
    
    def test_all_month_names(self):
        """Test all configs have 12 month names."""
        for code, config in LOCALE_CONFIGS.items():
            if config.month_names:
                assert len(config.month_names) == 12, f"{code} missing month names"
    
    def test_rtl_languages(self):
        """Test RTL languages are marked."""
        assert LOCALE_CONFIGS["ar"].rtl is True
        assert LOCALE_CONFIGS["en"].rtl is False


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestMultilingualIntegration:
    """Integration tests for multilingual system."""
    
    @pytest.mark.asyncio
    async def test_full_flow_spanish(self):
        """Test full multilingual flow for Spanish."""
        handler = MultilingualHandler()
        
        # Spanish query
        context = await handler.prepare_query(
            "¿Cuál es la capital de Francia?",
        )
        
        # Should detect Spanish
        assert context.detected_language.code == "es"
        
        # Should generate Spanish instructions
        assert "español" in context.system_instruction.lower()
        
        # Process English response back to Spanish
        response = await handler.process_response(
            "The capital of France is Paris.",
            context,
        )
        
        # Response should be for Spanish user
        assert context.response_language == "es"
    
    @pytest.mark.asyncio
    async def test_language_switch_tracking(self):
        """Test tracking language switches in conversation."""
        tracker = ConversationLanguageTracker()
        handler = MultilingualHandler()
        
        session = "test_session"
        
        # First message in English
        ctx1 = await handler.prepare_query("Hello, how are you?")
        tracker.update_conversation_language(session, ctx1.detected_language.code)
        assert tracker.get_conversation_language(session) == "en"
        
        # Second message in Spanish (switch)
        ctx2 = await handler.prepare_query(
            "Ahora voy a hablar en español por favor.",
            user_language="es",  # Override for test
        )
        tracker.update_conversation_language(session, ctx2.detected_language.code)
        assert tracker.get_conversation_language(session) == "es"
    
    def test_format_across_locales(self):
        """Test formatting the same data across locales."""
        value = 1234567.89
        dt = datetime(2025, 6, 15, 14, 30)
        
        locales = ["en", "es", "fr", "de", "ja"]
        
        for locale in locales:
            formatter = LocaleFormatter(locale)
            
            # All should succeed
            formatted_num = formatter.format_number(value)
            formatted_date = formatter.format_date(dt)
            formatted_currency = formatter.format_currency(value)
            
            assert len(formatted_num) > 0
            assert len(formatted_date) > 0
            assert len(formatted_currency) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

