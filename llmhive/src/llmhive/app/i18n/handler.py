"""Multilingual Handler for LLMHive.

Central handler for multilingual query processing:
- Language detection on incoming queries
- Prompt adaptation for different languages
- Response translation when needed
- Context management across languages

Usage:
    handler = get_multilingual_handler()
    
    # Process multilingual query
    context = await handler.prepare_query(
        query="¿Cuál es la capital de Francia?",
        user_id="user123",
    )
    # context.detected_lang = "es"
    # context.system_instruction = "Respond in Spanish"
    
    # Translate response if needed
    response = await handler.process_response(
        response="The capital of France is Paris.",
        context=context,
    )
    # Returns: "La capital de Francia es París."
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .detection import (
    LanguageDetector,
    LanguageInfo,
    detect_language,
    get_language_detector,
    SUPPORTED_LANGUAGES,
)
from .translation import (
    TranslationService,
    TranslationResult,
    get_translation_service,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Prompt Templates by Language
# ==============================================================================

SYSTEM_INSTRUCTIONS: Dict[str, str] = {
    "en": "Respond in English.",
    "es": "Responde en español.",
    "fr": "Réponds en français.",
    "de": "Antworte auf Deutsch.",
    "it": "Rispondi in italiano.",
    "pt": "Responda em português.",
    "nl": "Antwoord in het Nederlands.",
    "ru": "Отвечай на русском языке.",
    "zh": "请用中文回答。",
    "ja": "日本語で回答してください。",
    "ko": "한국어로 대답해 주세요.",
    "ar": "أجب باللغة العربية.",
    "hi": "हिंदी में जवाब दें।",
    "tr": "Türkçe cevap ver.",
    "pl": "Odpowiedz po polsku.",
    "vi": "Trả lời bằng tiếng Việt.",
    "th": "ตอบเป็นภาษาไทย",
}

MULTILINGUAL_SYSTEM_PROMPT = """You are a helpful multilingual AI assistant.
The user's language has been detected as {language_name} ({language_code}).
{language_instruction}
Maintain the same language throughout the conversation unless the user switches languages.
If you need to use technical terms, you may include the English term in parentheses for clarity."""


# ==============================================================================
# Types
# ==============================================================================

@dataclass(slots=True)
class MultilingualContext:
    """Context for multilingual query processing."""
    original_query: str
    detected_language: LanguageInfo
    working_language: str  # Language for processing (may be English)
    response_language: str  # Language for final response
    
    # Processed query (may be translated)
    processed_query: str
    
    # System instruction for the model
    system_instruction: str
    
    # Whether translation was applied
    query_translated: bool = False
    translation_confidence: float = 1.0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_language": self.detected_language.to_dict(),
            "working_language": self.working_language,
            "response_language": self.response_language,
            "query_translated": self.query_translated,
            "system_instruction": self.system_instruction,
        }


@dataclass(slots=True)
class MultilingualResponse:
    """Processed multilingual response."""
    original_response: str
    final_response: str
    response_language: str
    was_translated: bool
    confidence: float = 1.0


# ==============================================================================
# Multilingual Handler
# ==============================================================================

class MultilingualHandler:
    """Central handler for multilingual processing.
    
    Handles the complete flow:
    1. Detect query language
    2. Translate to working language if needed (for knowledge lookup)
    3. Generate system instructions for target language
    4. Translate response back to user's language
    
    Usage:
        handler = MultilingualHandler()
        
        # Prepare query
        context = await handler.prepare_query("¿Cómo está el tiempo?")
        
        # Use context.processed_query for processing
        # Use context.system_instruction in prompt
        
        # Process response
        response = await handler.process_response(
            "The weather is sunny.",
            context,
        )
    """
    
    def __init__(
        self,
        detector: Optional[LanguageDetector] = None,
        translator: Optional[TranslationService] = None,
        working_language: str = "en",
        translate_queries: bool = True,
        translate_responses: bool = True,
    ):
        self.detector = detector or get_language_detector()
        self.translator = translator or get_translation_service()
        self.working_language = working_language
        self.translate_queries = translate_queries
        self.translate_responses = translate_responses
    
    async def prepare_query(
        self,
        query: str,
        user_language: Optional[str] = None,
        translate_to_working: bool = True,
    ) -> MultilingualContext:
        """
        Prepare a query for multilingual processing.
        
        Args:
            query: User's query
            user_language: Override detected language
            translate_to_working: Whether to translate to working language
            
        Returns:
            MultilingualContext with processed query and instructions
        """
        # Detect language if not provided
        if user_language:
            detected = LanguageInfo(
                code=user_language,
                name=SUPPORTED_LANGUAGES.get(user_language, "Unknown"),
                confidence=1.0,
            )
        else:
            detected = await self.detector.detect(query)
        
        response_language = detected.code
        query_translated = False
        translation_confidence = 1.0
        processed_query = query
        
        # Translate to working language if needed
        if (
            translate_to_working 
            and self.translate_queries 
            and detected.code != self.working_language
        ):
            try:
                result = await self.translator.translate(
                    query,
                    target_lang=self.working_language,
                    source_lang=detected.code,
                )
                processed_query = result.translated
                query_translated = True
                translation_confidence = result.confidence
                
                logger.debug(
                    "Translated query [%s->%s]: %s -> %s",
                    detected.code, self.working_language,
                    query[:50], processed_query[:50],
                )
            except Exception as e:
                logger.warning("Query translation failed: %s", e)
                processed_query = query
        
        # Generate system instruction
        system_instruction = self._get_system_instruction(response_language)
        
        return MultilingualContext(
            original_query=query,
            detected_language=detected,
            working_language=self.working_language if query_translated else detected.code,
            response_language=response_language,
            processed_query=processed_query,
            system_instruction=system_instruction,
            query_translated=query_translated,
            translation_confidence=translation_confidence,
        )
    
    async def process_response(
        self,
        response: str,
        context: MultilingualContext,
    ) -> MultilingualResponse:
        """
        Process response for the user's language.
        
        Args:
            response: Model's response (may be in working language)
            context: Multilingual context from prepare_query
            
        Returns:
            MultilingualResponse with potentially translated text
        """
        # If response is already in user's language, return as-is
        if not context.query_translated or not self.translate_responses:
            return MultilingualResponse(
                original_response=response,
                final_response=response,
                response_language=context.response_language,
                was_translated=False,
            )
        
        # Detect response language
        response_lang = await self.detector.detect(response)
        
        # Translate if response is in working language but user expects different
        if response_lang.code != context.response_language:
            try:
                result = await self.translator.translate(
                    response,
                    target_lang=context.response_language,
                    source_lang=response_lang.code,
                )
                
                logger.debug(
                    "Translated response [%s->%s]",
                    response_lang.code, context.response_language,
                )
                
                return MultilingualResponse(
                    original_response=response,
                    final_response=result.translated,
                    response_language=context.response_language,
                    was_translated=True,
                    confidence=result.confidence,
                )
            except Exception as e:
                logger.warning("Response translation failed: %s", e)
        
        return MultilingualResponse(
            original_response=response,
            final_response=response,
            response_language=response_lang.code,
            was_translated=False,
        )
    
    def _get_system_instruction(self, language: str) -> str:
        """Get system instruction for target language."""
        lang_instruction = SYSTEM_INSTRUCTIONS.get(
            language,
            f"Respond in {SUPPORTED_LANGUAGES.get(language, language)}."
        )
        
        return MULTILINGUAL_SYSTEM_PROMPT.format(
            language_name=SUPPORTED_LANGUAGES.get(language, language),
            language_code=language,
            language_instruction=lang_instruction,
        )
    
    def get_prompt_prefix(
        self,
        language: str,
        include_instruction: bool = True,
    ) -> str:
        """
        Get prompt prefix for a language.
        
        Args:
            language: Language code
            include_instruction: Whether to include response instruction
            
        Returns:
            Prompt prefix string
        """
        lang_name = SUPPORTED_LANGUAGES.get(language, language)
        
        if include_instruction:
            instruction = SYSTEM_INSTRUCTIONS.get(
                language,
                f"Respond in {lang_name}."
            )
            return f"[Language: {lang_name}]\n{instruction}\n\n"
        
        return f"[Language: {lang_name}]\n\n"
    
    async def translate_for_knowledge_lookup(
        self,
        query: str,
        query_lang: str,
    ) -> Tuple[str, bool]:
        """
        Translate query to English for knowledge base lookup.
        
        Args:
            query: User query
            query_lang: Detected query language
            
        Returns:
            (translated_query, was_translated)
        """
        if query_lang == "en":
            return query, False
        
        try:
            result = await self.translator.translate(
                query,
                target_lang="en",
                source_lang=query_lang,
            )
            return result.translated, True
        except Exception as e:
            logger.warning("Knowledge lookup translation failed: %s", e)
            return query, False
    
    async def translate_knowledge_results(
        self,
        results: List[str],
        target_lang: str,
    ) -> List[str]:
        """
        Translate knowledge lookup results to user's language.
        
        Args:
            results: List of knowledge results (likely in English)
            target_lang: User's language
            
        Returns:
            Translated results
        """
        if target_lang == "en":
            return results
        
        translated = []
        for result in results:
            try:
                tr = await self.translator.translate(
                    result,
                    target_lang=target_lang,
                    source_lang="en",
                )
                translated.append(tr.translated)
            except Exception:
                translated.append(result)  # Keep original on failure
        
        return translated


# ==============================================================================
# Conversation Language Tracking
# ==============================================================================

class ConversationLanguageTracker:
    """Tracks language across conversation turns.
    
    Handles:
    - Initial language detection
    - Language switches mid-conversation
    - Preferred language persistence
    """
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self._conversation_languages: Dict[str, str] = {}
        self._user_preferences: Dict[str, str] = {}
    
    def set_user_preference(self, user_id: str, language: str) -> None:
        """Set user's preferred language."""
        self._user_preferences[user_id] = language
    
    def get_user_preference(self, user_id: str) -> Optional[str]:
        """Get user's preferred language."""
        return self._user_preferences.get(user_id)
    
    def update_conversation_language(
        self,
        session_id: str,
        detected_language: str,
    ) -> str:
        """
        Update and return the conversation language.
        
        Args:
            session_id: Conversation session ID
            detected_language: Detected language of current message
            
        Returns:
            Current conversation language
        """
        current = self._conversation_languages.get(session_id)
        
        if current is None:
            # First message - set language
            self._conversation_languages[session_id] = detected_language
            return detected_language
        
        if current != detected_language:
            # Language switch detected
            logger.info(
                "Language switch in session %s: %s -> %s",
                session_id, current, detected_language,
            )
            self._conversation_languages[session_id] = detected_language
        
        return detected_language
    
    def get_conversation_language(self, session_id: str) -> str:
        """Get current conversation language."""
        return self._conversation_languages.get(session_id, self.default_language)
    
    def end_conversation(self, session_id: str) -> None:
        """Clean up conversation language tracking."""
        self._conversation_languages.pop(session_id, None)


# ==============================================================================
# Global Instance
# ==============================================================================

_multilingual_handler: Optional[MultilingualHandler] = None
_language_tracker: Optional[ConversationLanguageTracker] = None


def get_multilingual_handler() -> MultilingualHandler:
    """Get or create global multilingual handler."""
    global _multilingual_handler
    if _multilingual_handler is None:
        _multilingual_handler = MultilingualHandler()
    return _multilingual_handler


def get_language_tracker() -> ConversationLanguageTracker:
    """Get or create global language tracker."""
    global _language_tracker
    if _language_tracker is None:
        _language_tracker = ConversationLanguageTracker()
    return _language_tracker

