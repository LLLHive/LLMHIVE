"""Spell Check Tool for LLMHive.

Provides spell checking and correction capabilities:
- Check text for spelling errors
- Suggest corrections
- Auto-correct common mistakes
- Support for custom dictionaries

Usage:
    checker = SpellChecker()
    result = checker.check("Ths is a tset")
    # result.corrected = "This is a test"
    # result.errors = [("Ths", "This"), ("tset", "test")]
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SpellCheckMode(str, Enum):
    """Spell check modes."""
    SUGGEST = "suggest"  # Only suggest corrections
    AUTO_CORRECT = "auto_correct"  # Automatically correct
    HIGHLIGHT = "highlight"  # Highlight errors without correcting


@dataclass
class SpellError:
    """A spelling error with suggestions."""
    word: str
    position: int
    suggestions: List[str]
    context: str = ""
    
    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "position": self.position,
            "suggestions": self.suggestions[:5],  # Top 5 suggestions
            "context": self.context,
        }


@dataclass
class SpellCheckResult:
    """Result of spell checking."""
    original: str
    corrected: str
    errors: List[SpellError]
    error_count: int
    was_corrected: bool
    
    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "corrected": self.corrected,
            "errors": [e.to_dict() for e in self.errors],
            "error_count": self.error_count,
            "was_corrected": self.was_corrected,
        }


# Common misspellings dictionary (fast lookup)
COMMON_MISSPELLINGS: Dict[str, str] = {
    # Common typos
    "teh": "the",
    "taht": "that",
    "adn": "and",
    "wiht": "with",
    "thier": "their",
    "recieve": "receive",
    "occured": "occurred",
    "seperate": "separate",
    "definately": "definitely",
    "accomodate": "accommodate",
    "occurence": "occurrence",
    "untill": "until",
    "becuase": "because",
    "beleive": "believe",
    "freind": "friend",
    "goverment": "government",
    "happend": "happened",
    "immediatly": "immediately",
    "independant": "independent",
    "knowlege": "knowledge",
    "liason": "liaison",
    "mispell": "misspell",
    "neccessary": "necessary",
    "noticable": "noticeable",
    "occassion": "occasion",
    "paralell": "parallel",
    "persistant": "persistent",
    "privelege": "privilege",
    "publically": "publicly",
    "recomend": "recommend",
    "refering": "referring",
    "relevent": "relevant",
    "rember": "remember",
    "resistence": "resistance",
    "responsable": "responsible",
    "sucessful": "successful",
    "suprise": "surprise",
    "tommorow": "tomorrow",
    "truely": "truly",
    "unforseen": "unforeseen",
    "usualy": "usually",
    "wether": "whether",
    "wierd": "weird",
    # Tech-specific
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "github": "GitHub",
    "gitlab": "GitLab",
    "openai": "OpenAI",
    "chatgpt": "ChatGPT",
    "gpt": "GPT",
    "api": "API",
    "http": "HTTP",
    "https": "HTTPS",
    "json": "JSON",
    "xml": "XML",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "nosql": "NoSQL",
    "mongodb": "MongoDB",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    # Common query typos
    "waht": "what",
    "hwo": "how",
    "whta": "what",
    "cna": "can",
    "dont": "don't",
    "cant": "can't",
    "wont": "won't",
    "isnt": "isn't",
    "doesnt": "doesn't",
    "didnt": "didn't",
    "wouldnt": "wouldn't",
    "couldnt": "couldn't",
    "shouldnt": "shouldn't",
    "hasnt": "hasn't",
    "havent": "haven't",
    "hadnt": "hadn't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "arent": "aren't",
    "aint": "ain't",
    "im": "I'm",
    "ive": "I've",
    "id": "I'd",
    "ill": "I'll",
    "youre": "you're",
    "youve": "you've",
    "youd": "you'd",
    "youll": "you'll",
    "theyre": "they're",
    "theyve": "they've",
    "theyd": "they'd",
    "theyll": "they'll",
    "weve": "we've",
    "wed": "we'd",
    "well": "we'll",
    "hes": "he's",
    "shes": "she's",
    "its": "it's",  # Note: context-dependent
    "lets": "let's",
    "thats": "that's",
    "whats": "what's",
    "whos": "who's",
    "wheres": "where's",
    "heres": "here's",
    "theres": "there's",
}

# Words to skip (technical terms, proper nouns, etc.)
SKIP_WORDS: Set[str] = {
    "llmhive", "openai", "gpt", "llm", "ai", "ml", "nlp", "api", "url",
    "http", "https", "json", "xml", "html", "css", "js", "ts", "py",
    "sql", "nosql", "mongodb", "redis", "kafka", "nginx", "docker",
    "kubernetes", "k8s", "aws", "gcp", "azure", "ci", "cd", "devops",
    "frontend", "backend", "fullstack", "sdk", "cli", "gui", "ui", "ux",
    "regex", "oauth", "jwt", "cors", "csrf", "xss", "ddos", "ssl", "tls",
    "tcp", "udp", "ip", "dns", "cdn", "vpc", "ec2", "s3", "rds", "lambda",
    "fastapi", "flask", "django", "express", "nextjs", "react", "vue",
    "angular", "svelte", "nodejs", "npm", "yarn", "pnpm", "pip", "conda",
    "pytorch", "tensorflow", "keras", "scikit", "pandas", "numpy",
    "matplotlib", "seaborn", "plotly", "jupyter", "colab", "vscode",
    "github", "gitlab", "bitbucket", "jira", "confluence", "slack",
    "webhook", "websocket", "graphql", "grpc", "protobuf", "avro",
    "elasticsearch", "kibana", "grafana", "prometheus", "datadog",
    "sentry", "newrelic", "splunk", "logstash", "fluentd", "ansible",
    "terraform", "pulumi", "cloudformation", "helm", "istio", "envoy",
    "pinecone", "weaviate", "milvus", "qdrant", "chroma", "faiss",
    "langchain", "llamaindex", "autogen", "crewai", "anthropic", "claude",
    "gemini", "mistral", "llama", "ollama", "huggingface", "transformers",
    "tokenizer", "embeddings", "rag", "finetuning", "lora", "qlora",
    "peft", "rlhf", "dpo", "sft", "ppo", "chatbot", "copilot",
}


class SpellChecker:
    """Spell checker with multiple correction strategies."""
    
    def __init__(
        self,
        custom_dictionary: Optional[Set[str]] = None,
        use_common_misspellings: bool = True,
        case_sensitive: bool = False,
    ):
        """
        Initialize spell checker.
        
        Args:
            custom_dictionary: Additional words to consider correct
            use_common_misspellings: Use built-in common misspellings
            case_sensitive: Whether to be case-sensitive
        """
        self.custom_dictionary = custom_dictionary or set()
        self.use_common_misspellings = use_common_misspellings
        self.case_sensitive = case_sensitive
        
        # Try to import spellchecker library
        self._spellchecker = None
        try:
            from spellchecker import SpellChecker as PySpellChecker
            self._spellchecker = PySpellChecker()
            # Add custom words
            self._spellchecker.word_frequency.load_words(SKIP_WORDS)
            if custom_dictionary:
                self._spellchecker.word_frequency.load_words(custom_dictionary)
            logger.info("PySpellChecker initialized")
        except ImportError:
            logger.warning("pyspellchecker not installed, using basic spell checking")
    
    def check(
        self,
        text: str,
        mode: SpellCheckMode = SpellCheckMode.AUTO_CORRECT,
        context_window: int = 20,
    ) -> SpellCheckResult:
        """
        Check text for spelling errors.
        
        Args:
            text: Text to check
            mode: How to handle errors
            context_window: Characters of context around errors
            
        Returns:
            SpellCheckResult with errors and corrections
        """
        if not text or not text.strip():
            return SpellCheckResult(
                original=text,
                corrected=text,
                errors=[],
                error_count=0,
                was_corrected=False,
            )
        
        errors: List[SpellError] = []
        corrected_text = text
        
        # Extract words with positions
        word_pattern = re.compile(r'\b([a-zA-Z]+)\b')
        
        for match in word_pattern.finditer(text):
            word = match.group(1)
            position = match.start()
            
            # Skip short words
            if len(word) <= 2:
                continue
            
            # Check for error
            error = self._check_word(word, position, text, context_window)
            if error:
                errors.append(error)
        
        # Apply corrections if mode is auto-correct
        if mode == SpellCheckMode.AUTO_CORRECT and errors:
            corrected_text = self._apply_corrections(text, errors)
        
        return SpellCheckResult(
            original=text,
            corrected=corrected_text,
            errors=errors,
            error_count=len(errors),
            was_corrected=corrected_text != text,
        )
    
    def _check_word(
        self,
        word: str,
        position: int,
        full_text: str,
        context_window: int,
    ) -> Optional[SpellError]:
        """Check if a word is misspelled."""
        word_lower = word.lower()
        
        # Skip known technical terms
        if word_lower in SKIP_WORDS:
            return None
        
        # Skip custom dictionary words
        if word_lower in self.custom_dictionary:
            return None
        
        # Check common misspellings first (fast)
        if self.use_common_misspellings and word_lower in COMMON_MISSPELLINGS:
            correction = COMMON_MISSPELLINGS[word_lower]
            # Preserve original case
            if word[0].isupper():
                correction = correction[0].upper() + correction[1:]
            
            context = self._get_context(full_text, position, context_window)
            return SpellError(
                word=word,
                position=position,
                suggestions=[correction],
                context=context,
            )
        
        # Use spellchecker library if available
        if self._spellchecker:
            if word_lower not in self._spellchecker:
                suggestions = list(self._spellchecker.candidates(word_lower) or [])
                if suggestions:
                    # Sort by edit distance
                    suggestions = sorted(
                        suggestions,
                        key=lambda x: self._edit_distance(word_lower, x)
                    )[:5]
                    
                    # Preserve case
                    if word[0].isupper():
                        suggestions = [s[0].upper() + s[1:] for s in suggestions]
                    
                    context = self._get_context(full_text, position, context_window)
                    return SpellError(
                        word=word,
                        position=position,
                        suggestions=suggestions,
                        context=context,
                    )
        
        return None
    
    def _get_context(self, text: str, position: int, window: int) -> str:
        """Get context around a word."""
        start = max(0, position - window)
        end = min(len(text), position + window + 10)
        context = text[start:end]
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        return context
    
    def _apply_corrections(self, text: str, errors: List[SpellError]) -> str:
        """Apply corrections to text."""
        # Sort by position in reverse to avoid offset issues
        sorted_errors = sorted(errors, key=lambda e: e.position, reverse=True)
        
        result = text
        for error in sorted_errors:
            if error.suggestions:
                correction = error.suggestions[0]
                # Find the word at the position and replace it
                pattern = re.compile(r'\b' + re.escape(error.word) + r'\b')
                # Replace only the specific occurrence
                before = result[:error.position]
                after = result[error.position:]
                after = pattern.sub(correction, after, count=1)
                result = before + after
        
        return result
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance."""
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def add_words(self, words: List[str]) -> None:
        """Add words to custom dictionary."""
        self.custom_dictionary.update(w.lower() for w in words)
        if self._spellchecker:
            self._spellchecker.word_frequency.load_words(words)
    
    def get_suggestions(self, word: str, max_suggestions: int = 5) -> List[str]:
        """Get spelling suggestions for a word."""
        word_lower = word.lower()
        
        # Check common misspellings
        if word_lower in COMMON_MISSPELLINGS:
            return [COMMON_MISSPELLINGS[word_lower]]
        
        # Use spellchecker
        if self._spellchecker:
            candidates = self._spellchecker.candidates(word_lower)
            if candidates:
                suggestions = sorted(
                    candidates,
                    key=lambda x: self._edit_distance(word_lower, x)
                )[:max_suggestions]
                return suggestions
        
        return []


# Singleton instance
_spell_checker: Optional[SpellChecker] = None


def get_spell_checker() -> SpellChecker:
    """Get or create spell checker instance."""
    global _spell_checker
    if _spell_checker is None:
        _spell_checker = SpellChecker()
    return _spell_checker


# ==============================================================================
# Tool Interface for LLMHive
# ==============================================================================

def spell_check_tool(text: str, mode: str = "auto_correct") -> dict:
    """
    Spell check tool for LLMHive orchestration.
    
    Args:
        text: Text to check
        mode: "suggest", "auto_correct", or "highlight"
        
    Returns:
        Dictionary with spell check results
    """
    checker = get_spell_checker()
    
    try:
        check_mode = SpellCheckMode(mode)
    except ValueError:
        check_mode = SpellCheckMode.AUTO_CORRECT
    
    result = checker.check(text, mode=check_mode)
    return result.to_dict()


def correct_text(text: str) -> str:
    """
    Simple function to auto-correct text.
    
    Args:
        text: Text to correct
        
    Returns:
        Corrected text
    """
    checker = get_spell_checker()
    result = checker.check(text, mode=SpellCheckMode.AUTO_CORRECT)
    return result.corrected


def get_suggestions_for_word(word: str) -> List[str]:
    """
    Get spelling suggestions for a single word.
    
    Args:
        word: Word to get suggestions for
        
    Returns:
        List of suggestions
    """
    checker = get_spell_checker()
    return checker.get_suggestions(word)


# ==============================================================================
# FastAPI Router for Spell Check API
# ==============================================================================

def create_spell_check_router():
    """Create FastAPI router for spell check endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel, Field
    
    router = APIRouter()
    
    class SpellCheckRequest(BaseModel):
        text: str = Field(..., description="Text to spell check")
        mode: str = Field("auto_correct", description="Mode: suggest, auto_correct, highlight")
    
    class SpellCheckResponse(BaseModel):
        original: str
        corrected: str
        errors: List[dict]
        error_count: int
        was_corrected: bool
    
    class SuggestionsRequest(BaseModel):
        word: str = Field(..., description="Word to get suggestions for")
    
    class SuggestionsResponse(BaseModel):
        word: str
        suggestions: List[str]
    
    @router.post("/check", response_model=SpellCheckResponse)
    async def check_spelling(request: SpellCheckRequest):
        """Check text for spelling errors."""
        try:
            result = spell_check_tool(request.text, request.mode)
            return SpellCheckResponse(**result)
        except Exception as e:
            logger.error(f"Spell check error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/suggest", response_model=SuggestionsResponse)
    async def get_suggestions(request: SuggestionsRequest):
        """Get spelling suggestions for a word."""
        suggestions = get_suggestions_for_word(request.word)
        return SuggestionsResponse(word=request.word, suggestions=suggestions)
    
    @router.post("/correct")
    async def auto_correct(request: SpellCheckRequest):
        """Auto-correct text and return corrected version."""
        corrected = correct_text(request.text)
        return {"original": request.text, "corrected": corrected}
    
    return router

