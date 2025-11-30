"""Language Detection for LLMHive.

Provides language identification for incoming queries using multiple methods:
1. Character-based heuristics (fast, no dependencies)
2. langdetect library (if available)
3. fasttext language ID (most accurate, if available)

Usage:
    detector = get_language_detector()
    
    # Detect language
    lang = await detector.detect("Bonjour, comment ça va?")
    print(lang.code)  # "fr"
    print(lang.name)  # "French"
    print(lang.confidence)  # 0.95
"""
from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Supported Languages
# ==============================================================================

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "vi": "Vietnamese",
    "th": "Thai",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "id": "Indonesian",
    "ms": "Malay",
    "ro": "Romanian",
    "hu": "Hungarian",
    "uk": "Ukrainian",
    "bg": "Bulgarian",
}

# Language-specific character patterns
LANGUAGE_PATTERNS: Dict[str, List[str]] = {
    "zh": [r"[\u4e00-\u9fff]"],  # Chinese characters
    "ja": [r"[\u3040-\u309f\u30a0-\u30ff]"],  # Hiragana/Katakana
    "ko": [r"[\uac00-\ud7af\u1100-\u11ff]"],  # Korean Hangul
    "ar": [r"[\u0600-\u06ff]"],  # Arabic
    "he": [r"[\u0590-\u05ff]"],  # Hebrew
    "ru": [r"[\u0400-\u04ff]"],  # Cyrillic
    "el": [r"[\u0370-\u03ff]"],  # Greek
    "th": [r"[\u0e00-\u0e7f]"],  # Thai
    "hi": [r"[\u0900-\u097f]"],  # Devanagari (Hindi)
}

# Common words for European languages
LANGUAGE_WORDS: Dict[str, List[str]] = {
    "en": ["the", "is", "and", "to", "of", "in", "that", "it", "for", "you", "was", "with", "are", "be", "this"],
    "es": ["el", "la", "de", "que", "en", "es", "los", "las", "un", "una", "por", "con", "para", "como", "más"],
    "fr": ["le", "la", "les", "de", "et", "est", "un", "une", "que", "en", "du", "des", "pour", "dans", "ce"],
    "de": ["der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich", "des", "auf", "für", "ist", "im"],
    "it": ["il", "la", "di", "che", "è", "in", "un", "una", "per", "non", "sono", "da", "come", "con", "più"],
    "pt": ["de", "que", "e", "em", "um", "uma", "para", "é", "com", "não", "os", "se", "na", "por", "mais"],
    "nl": ["de", "het", "een", "van", "en", "in", "is", "op", "te", "dat", "die", "voor", "met", "zijn", "er"],
}


# ==============================================================================
# Types
# ==============================================================================

@dataclass(slots=True)
class LanguageInfo:
    """Information about detected language."""
    code: str  # ISO 639-1 code (e.g., "en", "fr")
    name: str  # Full name (e.g., "English", "French")
    confidence: float  # 0-1 confidence score
    script: Optional[str] = None  # e.g., "Latin", "Cyrillic"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "confidence": round(self.confidence, 3),
            "script": self.script,
        }


@dataclass(slots=True)
class DetectionResult:
    """Result of language detection with alternatives."""
    primary: LanguageInfo
    alternatives: List[LanguageInfo] = field(default_factory=list)
    method: str = "unknown"


# ==============================================================================
# Heuristic Detector
# ==============================================================================

class HeuristicDetector:
    """Rule-based language detection using character patterns and word frequency.
    
    Fast and requires no external dependencies.
    Good for scripts with distinct characters (CJK, Arabic, Cyrillic).
    """
    
    def __init__(self):
        self._compiled_patterns = {
            lang: [re.compile(p) for p in patterns]
            for lang, patterns in LANGUAGE_PATTERNS.items()
        }
    
    def detect(self, text: str) -> Optional[LanguageInfo]:
        """Detect language using heuristics."""
        if not text or len(text.strip()) < 3:
            return None
        
        text = text.strip()
        
        # First, check for script-specific languages
        for lang, patterns in self._compiled_patterns.items():
            matches = sum(len(p.findall(text)) for p in patterns)
            if matches > len(text) * 0.3:  # 30% of chars match
                return LanguageInfo(
                    code=lang,
                    name=SUPPORTED_LANGUAGES.get(lang, "Unknown"),
                    confidence=min(matches / len(text), 0.95),
                    script=self._get_script(lang),
                )
        
        # For Latin-script languages, use word frequency
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)
        
        if not words:
            return None
        
        best_lang = None
        best_score = 0.0
        
        for lang, common_words in LANGUAGE_WORDS.items():
            matches = sum(1 for w in words if w in common_words)
            score = matches / len(words) if words else 0
            
            if score > best_score:
                best_score = score
                best_lang = lang
        
        if best_lang and best_score > 0.1:
            return LanguageInfo(
                code=best_lang,
                name=SUPPORTED_LANGUAGES.get(best_lang, "Unknown"),
                confidence=min(best_score * 2, 0.85),  # Scale up, cap at 0.85
                script="Latin",
            )
        
        return None
    
    def _get_script(self, lang: str) -> str:
        """Get script name for a language."""
        scripts = {
            "zh": "Han",
            "ja": "Japanese",
            "ko": "Hangul",
            "ar": "Arabic",
            "he": "Hebrew",
            "ru": "Cyrillic",
            "el": "Greek",
            "th": "Thai",
            "hi": "Devanagari",
        }
        return scripts.get(lang, "Latin")


# ==============================================================================
# Language Detector
# ==============================================================================

class LanguageDetector:
    """Multi-method language detector.
    
    Uses multiple detection methods in order of accuracy:
    1. fasttext (most accurate)
    2. langdetect library
    3. Heuristic fallback
    
    Usage:
        detector = LanguageDetector()
        
        lang = await detector.detect("Bonjour!")
        print(lang.code)  # "fr"
    """
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self._heuristic = HeuristicDetector()
        self._langdetect_available = False
        self._fasttext_model = None
        
        # Try to import langdetect
        try:
            import langdetect
            self._langdetect = langdetect
            self._langdetect_available = True
        except ImportError:
            self._langdetect = None
    
    async def detect(
        self,
        text: str,
        min_confidence: float = 0.5,
    ) -> LanguageInfo:
        """
        Detect the language of text.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            LanguageInfo with detected language
        """
        if not text or len(text.strip()) < 3:
            return LanguageInfo(
                code=self.default_language,
                name=SUPPORTED_LANGUAGES.get(self.default_language, "Unknown"),
                confidence=1.0,
            )
        
        # Run detection
        result = await asyncio.to_thread(self._detect_sync, text)
        
        # Return default if confidence too low
        if result.confidence < min_confidence:
            return LanguageInfo(
                code=self.default_language,
                name=SUPPORTED_LANGUAGES.get(self.default_language, "Unknown"),
                confidence=0.5,
            )
        
        return result
    
    def _detect_sync(self, text: str) -> LanguageInfo:
        """Synchronous detection using available methods."""
        # Try langdetect first (good balance of speed/accuracy)
        if self._langdetect_available:
            try:
                from langdetect import detect_langs
                results = detect_langs(text)
                if results:
                    top = results[0]
                    return LanguageInfo(
                        code=top.lang,
                        name=SUPPORTED_LANGUAGES.get(top.lang, "Unknown"),
                        confidence=top.prob,
                    )
            except Exception as e:
                logger.debug("langdetect failed: %s", e)
        
        # Fall back to heuristic
        result = self._heuristic.detect(text)
        if result:
            return result
        
        # Default to configured language
        return LanguageInfo(
            code=self.default_language,
            name=SUPPORTED_LANGUAGES.get(self.default_language, "Unknown"),
            confidence=0.3,
        )
    
    async def detect_with_alternatives(
        self,
        text: str,
        max_alternatives: int = 3,
    ) -> DetectionResult:
        """
        Detect language with alternative possibilities.
        
        Args:
            text: Text to analyze
            max_alternatives: Maximum alternatives to return
            
        Returns:
            DetectionResult with primary and alternatives
        """
        if not text or len(text.strip()) < 3:
            primary = LanguageInfo(
                code=self.default_language,
                name=SUPPORTED_LANGUAGES.get(self.default_language, "Unknown"),
                confidence=1.0,
            )
            return DetectionResult(primary=primary, method="default")
        
        def _detect():
            alternatives = []
            method = "heuristic"
            
            if self._langdetect_available:
                try:
                    from langdetect import detect_langs
                    results = detect_langs(text)
                    if results:
                        method = "langdetect"
                        primary = LanguageInfo(
                            code=results[0].lang,
                            name=SUPPORTED_LANGUAGES.get(results[0].lang, "Unknown"),
                            confidence=results[0].prob,
                        )
                        alternatives = [
                            LanguageInfo(
                                code=r.lang,
                                name=SUPPORTED_LANGUAGES.get(r.lang, "Unknown"),
                                confidence=r.prob,
                            )
                            for r in results[1:max_alternatives+1]
                        ]
                        return DetectionResult(
                            primary=primary,
                            alternatives=alternatives,
                            method=method,
                        )
                except Exception:
                    pass
            
            # Heuristic fallback
            result = self._heuristic.detect(text)
            if result:
                return DetectionResult(primary=result, method="heuristic")
            
            # Default
            return DetectionResult(
                primary=LanguageInfo(
                    code=self.default_language,
                    name=SUPPORTED_LANGUAGES.get(self.default_language, "Unknown"),
                    confidence=0.3,
                ),
                method="default",
            )
        
        return await asyncio.to_thread(_detect)
    
    def is_right_to_left(self, lang_code: str) -> bool:
        """Check if a language is right-to-left."""
        rtl_languages = {"ar", "he", "fa", "ur", "yi"}
        return lang_code in rtl_languages
    
    def get_language_name(self, code: str) -> str:
        """Get full language name from code."""
        return SUPPORTED_LANGUAGES.get(code, "Unknown")


# ==============================================================================
# Global Instance
# ==============================================================================

_detector: Optional[LanguageDetector] = None


def get_language_detector() -> LanguageDetector:
    """Get or create global language detector."""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector


async def detect_language(text: str) -> LanguageInfo:
    """Quick helper to detect language."""
    detector = get_language_detector()
    return await detector.detect(text)

