"""Security Hardening for LLMHive.

This module provides:
- Input validation and sanitization
- Prompt injection detection
- Rate limiting helpers
- Security headers
- Request validation
- Secure configuration

Usage:
    from llmhive.app.security.hardening import SecurityManager
    
    security = SecurityManager()
    
    # Validate and sanitize input
    safe_input = security.sanitize_input(user_input)
    
    # Check for prompt injection
    if security.detect_injection(prompt):
        raise SecurityError("Potential injection detected")
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

class ThreatLevel(str, Enum):
    """Threat level classification."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(str, Enum):
    """Types of security events."""
    INJECTION_ATTEMPT = "injection_attempt"
    RATE_LIMIT = "rate_limit"
    INVALID_INPUT = "invalid_input"
    AUTH_FAILURE = "auth_failure"
    FORBIDDEN_ACCESS = "forbidden_access"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass(slots=True)
class SecurityCheckResult:
    """Result of a security check."""
    passed: bool
    threat_level: ThreatLevel
    event_type: Optional[SecurityEvent] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InputValidationResult:
    """Result of input validation."""
    valid: bool
    sanitized: str
    issues: List[str] = field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NONE


# ==============================================================================
# Prompt Injection Detection
# ==============================================================================

# Known injection patterns
INJECTION_PATTERNS = [
    # Ignore instructions
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|commands?)",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"forget\s+(everything|all)\s+(you|i)\s+(said|told)",
    
    # Role manipulation
    r"you\s+are\s+(now|actually)\s+a",
    r"pretend\s+(to\s+be|you\s+are)",
    r"act\s+as\s+(if\s+you\s+(are|were)|a)",
    r"roleplay\s+as",
    r"simulate\s+being",
    
    # System prompt extraction
    r"(show|display|print|output|reveal)\s+(your|the)\s+(system|initial)\s+prompt",
    r"what\s+(is|are)\s+your\s+(initial|system|base)\s+(instructions?|prompt)",
    r"repeat\s+(your\s+)?instructions",
    
    # Jailbreak attempts
    r"dan\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"bypass\s+(safety|filter|restriction)",
    r"unlock\s+(hidden|secret)\s+(mode|features?)",
    
    # Code injection
    r"<\s*script",
    r"javascript\s*:",
    r"on(load|error|click)\s*=",
    r"\{\{\s*constructor",
    r"__proto__",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    
    # SQL injection (if applicable)
    r";\s*(drop|delete|truncate|update|insert)\s+",
    r"'\s*(or|and)\s+['\"0-9]=",
    r"union\s+(all\s+)?select",
]

# Compiled patterns
COMPILED_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for pattern in INJECTION_PATTERNS
]


class InjectionDetector:
    """Detect prompt injection attempts."""
    
    def __init__(self, patterns: Optional[List[str]] = None):
        self.patterns = patterns or INJECTION_PATTERNS
        self._compiled = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.patterns
        ]
    
    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect injection patterns in text.
        
        Returns:
            (is_injection, list of matched patterns)
        """
        matched = []
        
        for pattern in self._compiled:
            if pattern.search(text):
                matched.append(pattern.pattern)
        
        return len(matched) > 0, matched
    
    def get_threat_level(self, text: str) -> ThreatLevel:
        """Determine threat level of text."""
        is_injection, matches = self.detect(text)
        
        if not is_injection:
            return ThreatLevel.NONE
        
        # More matches = higher threat
        if len(matches) >= 3:
            return ThreatLevel.CRITICAL
        elif len(matches) >= 2:
            return ThreatLevel.HIGH
        elif len(matches) >= 1:
            return ThreatLevel.MEDIUM
        
        return ThreatLevel.LOW


# ==============================================================================
# Input Sanitization
# ==============================================================================

# Characters to strip or escape
DANGEROUS_CHARS = {
    '\x00': '',  # Null byte
    '\x0b': '',  # Vertical tab
    '\x0c': '',  # Form feed
    '\x7f': '',  # Delete
}

# HTML entities to escape
HTML_ESCAPE = {
    '<': '&lt;',
    '>': '&gt;',
    '&': '&amp;',
    '"': '&quot;',
    "'": '&#x27;',
}


def sanitize_text(
    text: str,
    max_length: int = 100000,
    strip_html: bool = True,
    strip_control: bool = True,
) -> str:
    """
    Sanitize text input.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        strip_html: Escape HTML characters
        strip_control: Remove control characters
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning("Input truncated to %d chars", max_length)
    
    # Strip control characters
    if strip_control:
        for char, replacement in DANGEROUS_CHARS.items():
            text = text.replace(char, replacement)
    
    # Escape HTML
    if strip_html:
        for char, escape in HTML_ESCAPE.items():
            text = text.replace(char, escape)
    
    # Normalize whitespace
    text = re.sub(r'[\r\n]+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()


def sanitize_json(data: Any, max_depth: int = 10) -> Any:
    """Recursively sanitize JSON-like data."""
    if max_depth <= 0:
        return "[MAX_DEPTH]"
    
    if isinstance(data, str):
        return sanitize_text(data, strip_html=False)
    
    elif isinstance(data, dict):
        return {
            sanitize_text(str(k), max_length=256): sanitize_json(v, max_depth - 1)
            for k, v in data.items()
        }
    
    elif isinstance(data, (list, tuple)):
        return [sanitize_json(item, max_depth - 1) for item in data[:1000]]
    
    elif isinstance(data, (int, float, bool, type(None))):
        return data
    
    return str(data)[:1000]


# ==============================================================================
# Security Manager
# ==============================================================================

class SecurityManager:
    """Central security manager for LLMHive.
    
    Provides:
    - Input validation and sanitization
    - Prompt injection detection
    - Security event logging
    - Rate limiting helpers
    
    Usage:
        security = SecurityManager()
        
        # Check and sanitize input
        result = security.validate_input(user_prompt)
        if not result.valid:
            raise SecurityError(result.issues)
        
        safe_prompt = result.sanitized
    """
    
    def __init__(
        self,
        max_input_length: int = 100000,
        block_injections: bool = True,
        log_events: bool = True,
    ):
        self.max_input_length = max_input_length
        self.block_injections = block_injections
        self.log_events = log_events
        
        self._injection_detector = InjectionDetector()
        self._event_log: List[Dict[str, Any]] = []
    
    def validate_input(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> InputValidationResult:
        """
        Validate and sanitize user input.
        
        Args:
            text: Input text to validate
            context: Optional context for logging
            
        Returns:
            InputValidationResult with validation status and sanitized text
        """
        issues: List[str] = []
        threat_level = ThreatLevel.NONE
        
        # Length check
        if len(text) > self.max_input_length:
            issues.append(f"Input exceeds maximum length ({self.max_input_length})")
            text = text[:self.max_input_length]
        
        # Injection detection
        if self.block_injections:
            is_injection, patterns = self._injection_detector.detect(text)
            if is_injection:
                threat_level = self._injection_detector.get_threat_level(text)
                issues.append(f"Potential prompt injection detected (threat: {threat_level.value})")
                
                self._log_event(
                    SecurityEvent.INJECTION_ATTEMPT,
                    threat_level,
                    {"patterns": patterns[:3], "context": context},
                )
        
        # Sanitize
        sanitized = sanitize_text(text, max_length=self.max_input_length)
        
        return InputValidationResult(
            valid=len(issues) == 0 or threat_level in (ThreatLevel.NONE, ThreatLevel.LOW),
            sanitized=sanitized,
            issues=issues,
            threat_level=threat_level,
        )
    
    def sanitize_input(self, text: str) -> str:
        """Quick sanitize without full validation."""
        return sanitize_text(text, max_length=self.max_input_length)
    
    def detect_injection(self, text: str) -> bool:
        """Check if text contains injection patterns."""
        is_injection, _ = self._injection_detector.detect(text)
        return is_injection
    
    def check_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[Any] = None,
    ) -> SecurityCheckResult:
        """
        Perform security checks on a request.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            body: Request body
            
        Returns:
            SecurityCheckResult
        """
        issues = []
        threat_level = ThreatLevel.NONE
        
        # Check for suspicious headers
        suspicious_headers = ["X-Forwarded-Host", "X-Original-URL"]
        for header in suspicious_headers:
            if header in headers:
                issues.append(f"Suspicious header: {header}")
        
        # Check body for injections
        if body and isinstance(body, dict):
            for key, value in body.items():
                if isinstance(value, str):
                    result = self.validate_input(value)
                    if not result.valid:
                        threat_level = max(threat_level, result.threat_level, key=lambda x: list(ThreatLevel).index(x))
                        issues.extend(result.issues)
        
        return SecurityCheckResult(
            passed=threat_level in (ThreatLevel.NONE, ThreatLevel.LOW),
            threat_level=threat_level,
            event_type=SecurityEvent.INVALID_INPUT if issues else None,
            message="; ".join(issues) if issues else None,
        )
    
    def _log_event(
        self,
        event_type: SecurityEvent,
        threat_level: ThreatLevel,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a security event."""
        if not self.log_events:
            return
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "threat_level": threat_level.value,
            "details": details or {},
        }
        
        self._event_log.append(event)
        
        # Also log to standard logger
        if threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            logger.warning("Security event: %s (threat=%s)", event_type.value, threat_level.value)
        else:
            logger.info("Security event: %s (threat=%s)", event_type.value, threat_level.value)
    
    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[SecurityEvent] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent security events."""
        events = self._event_log[-limit:]
        
        if event_type:
            events = [e for e in events if e["event_type"] == event_type.value]
        
        return events


# ==============================================================================
# Security Headers
# ==============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def apply_security_headers(response) -> None:
    """Apply security headers to a response."""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value


# ==============================================================================
# Request Signing
# ==============================================================================

def sign_request(
    data: str,
    secret: str,
    timestamp: Optional[int] = None,
) -> str:
    """Sign a request for verification."""
    timestamp = timestamp or int(time.time())
    message = f"{timestamp}:{data}"
    
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    
    return f"{timestamp}.{signature}"


def verify_signature(
    data: str,
    signature: str,
    secret: str,
    max_age: int = 300,
) -> bool:
    """Verify a request signature."""
    try:
        parts = signature.split(".")
        if len(parts) != 2:
            return False
        
        timestamp = int(parts[0])
        provided_sig = parts[1]
        
        # Check age
        if abs(time.time() - timestamp) > max_age:
            return False
        
        # Verify signature
        expected = sign_request(data, secret, timestamp).split(".")[1]
        return hmac.compare_digest(expected, provided_sig)
        
    except Exception:
        return False


# ==============================================================================
# Convenience Functions
# ==============================================================================

_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


def sanitize_input(text: str) -> str:
    """Quick sanitize input."""
    return get_security_manager().sanitize_input(text)


def validate_request(
    method: str,
    path: str,
    headers: Dict[str, str],
    body: Optional[Any] = None,
) -> SecurityCheckResult:
    """Validate a request."""
    return get_security_manager().check_request(method, path, headers, body)


# ==============================================================================
# FastAPI Middleware
# ==============================================================================

def setup_security_middleware(app):
    """Setup security middleware for FastAPI."""
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class SecurityMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Apply security headers
            response = await call_next(request)
            apply_security_headers(response)
            return response
    
    app.add_middleware(SecurityMiddleware)
    logger.info("Security middleware enabled")

