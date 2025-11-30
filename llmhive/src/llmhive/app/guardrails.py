"""Comprehensive security guardrails for LLMHive.

This module provides:
- Data redaction (PII, sensitive information)
- Content filtering (profanity, hate speech, harmful content)
- Output policy enforcement
- Tier-based access control
- Query risk assessment
- Execution sandboxing
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Sensitive Data Patterns for Redaction
# ==============================================================================

class SensitiveDataType(str, Enum):
    """Types of sensitive data that can be redacted."""
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    PASSWORD = "password"
    ADDRESS = "address"
    DATE_OF_BIRTH = "dob"
    BANK_ACCOUNT = "bank_account"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"


# Regex patterns for sensitive data detection
SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str, SensitiveDataType]] = [
    # Social Security Number (XXX-XX-XXXX or XXXXXXXXX)
    (re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'), "[REDACTED_SSN]", SensitiveDataType.SSN),
    
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[REDACTED_EMAIL]", SensitiveDataType.EMAIL),
    
    # Phone numbers (various formats)
    (re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'), "[REDACTED_PHONE]", SensitiveDataType.PHONE),
    
    # Credit card numbers (major formats)
    (re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'), "[REDACTED_CC]", SensitiveDataType.CREDIT_CARD),
    (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), "[REDACTED_CC]", SensitiveDataType.CREDIT_CARD),
    
    # IP addresses (IPv4)
    (re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'), "[REDACTED_IP]", SensitiveDataType.IP_ADDRESS),
    
    # API keys (common patterns)
    (re.compile(r'\b(?:sk|pk|api|key|token)[-_]?[A-Za-z0-9]{20,}\b', re.IGNORECASE), "[REDACTED_API_KEY]", SensitiveDataType.API_KEY),
    (re.compile(r'\b[A-Za-z0-9]{32,64}\b(?=.*(?:api|key|token|secret))', re.IGNORECASE), "[REDACTED_API_KEY]", SensitiveDataType.API_KEY),
    
    # Passwords in common formats
    (re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*[\'"]?([^\s\'"]+)[\'"]?', re.IGNORECASE), "[REDACTED_PASSWORD]", SensitiveDataType.PASSWORD),
    
    # Date of birth patterns
    (re.compile(r'\b(?:DOB|Date of Birth|Birthday)\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', re.IGNORECASE), "[REDACTED_DOB]", SensitiveDataType.DATE_OF_BIRTH),
    
    # Bank account numbers (basic pattern)
    (re.compile(r'\b(?:account|acct)[-\s]?(?:number|no|#)?[-\s]?:?\s*\d{8,17}\b', re.IGNORECASE), "[REDACTED_BANK]", SensitiveDataType.BANK_ACCOUNT),
    
    # Passport numbers (US format)
    (re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'), "[REDACTED_PASSPORT]", SensitiveDataType.PASSPORT),
    
    # Driver's license (various state formats)
    (re.compile(r'\b(?:DL|Driver[\'s]* License)\s*[:=]?\s*[A-Z0-9]{5,15}\b', re.IGNORECASE), "[REDACTED_DL]", SensitiveDataType.DRIVER_LICENSE),
]


# ==============================================================================
# Content Policy Definitions
# ==============================================================================

class ContentSeverity(str, Enum):
    """Severity levels for content policy violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Disallowed content patterns with severity
DISALLOWED_CONTENT: List[Tuple[str, ContentSeverity, str]] = [
    # Critical: Harmful instructions
    ("how to make a bomb", ContentSeverity.CRITICAL, "harmful_instructions"),
    ("how to make explosives", ContentSeverity.CRITICAL, "harmful_instructions"),
    ("how to synthesize drugs", ContentSeverity.CRITICAL, "harmful_instructions"),
    ("how to hack into", ContentSeverity.CRITICAL, "harmful_instructions"),
    ("how to steal", ContentSeverity.CRITICAL, "harmful_instructions"),
    
    # High: Hate speech and slurs
    ("hate speech", ContentSeverity.HIGH, "hate_speech"),
    ("racial slur", ContentSeverity.HIGH, "hate_speech"),
    ("kill all", ContentSeverity.HIGH, "violence"),
    ("murder", ContentSeverity.HIGH, "violence"),
    
    # Medium: Profanity (sample - expand as needed)
    ("fuck", ContentSeverity.MEDIUM, "profanity"),
    ("shit", ContentSeverity.MEDIUM, "profanity"),
    ("asshole", ContentSeverity.MEDIUM, "profanity"),
    ("bitch", ContentSeverity.MEDIUM, "profanity"),
    
    # Low: Mildly inappropriate
    ("damn", ContentSeverity.LOW, "mild_profanity"),
    ("crap", ContentSeverity.LOW, "mild_profanity"),
]

# Safe alternatives for profanity
PROFANITY_REPLACEMENTS: Dict[str, str] = {
    "fuck": "[expletive]",
    "shit": "[expletive]",
    "asshole": "[insult]",
    "bitch": "[insult]",
    "damn": "darn",
    "crap": "crud",
}


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class RedactionResult:
    """Result of redacting sensitive information."""
    original_text: str
    redacted_text: str
    redactions: List[Tuple[str, str, SensitiveDataType]]  # (original, replacement, type)
    redaction_count: int = 0
    
    def __post_init__(self):
        self.redaction_count = len(self.redactions)


@dataclass(slots=True)
class PolicyViolation:
    """Represents a content policy violation."""
    content: str
    violation_type: str
    severity: ContentSeverity
    position: int = 0
    replacement: Optional[str] = None


@dataclass(slots=True)
class PolicyCheckResult:
    """Result of checking content against policies."""
    is_allowed: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    severity_score: float = 0.0  # 0.0 = clean, 1.0 = critical violation
    requires_rejection: bool = False
    sanitized_content: Optional[str] = None
    
    def __post_init__(self):
        if self.violations:
            # Calculate severity score
            severity_weights = {
                ContentSeverity.LOW: 0.1,
                ContentSeverity.MEDIUM: 0.4,
                ContentSeverity.HIGH: 0.7,
                ContentSeverity.CRITICAL: 1.0,
            }
            max_severity = max(
                severity_weights.get(v.severity, 0) for v in self.violations
            )
            self.severity_score = max_severity
            self.requires_rejection = max_severity >= 0.9


@dataclass(slots=True)
class RiskAssessment:
    """Assessment of query risk level."""
    risk_level: str  # "low", "medium", "high", "critical"
    risk_score: float  # 0.0-1.0
    risk_factors: List[str] = field(default_factory=list)
    requires_review: bool = False
    blocked: bool = False
    block_reason: Optional[str] = None


@dataclass(slots=True)
class SafetyReport:
    """Comprehensive safety report for content."""
    original_content: str
    sanitized_content: str
    is_safe: bool
    redaction_result: Optional[RedactionResult] = None
    policy_result: Optional[PolicyCheckResult] = None
    risk_assessment: Optional[RiskAssessment] = None


# ==============================================================================
# Core Functions
# ==============================================================================

def redact_sensitive_info(
    text: str,
    *,
    exclude_types: Optional[Set[SensitiveDataType]] = None,
    custom_patterns: Optional[List[Tuple[re.Pattern, str]]] = None,
    user_disallowed: Optional[List[str]] = None,
) -> RedactionResult:
    """
    Redact sensitive information from text.
    
    Detects and masks PII including:
    - Social Security Numbers
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - IP addresses
    - API keys
    - Passwords
    
    Args:
        text: Text to redact
        exclude_types: Set of SensitiveDataType to skip
        custom_patterns: Additional custom patterns [(pattern, replacement), ...]
        user_disallowed: List of user-specific strings to redact
        
    Returns:
        RedactionResult with original and redacted text
    """
    if not text:
        return RedactionResult(
            original_text=text,
            redacted_text=text,
            redactions=[],
        )
    
    exclude_types = exclude_types or set()
    redacted = text
    all_redactions: List[Tuple[str, str, SensitiveDataType]] = []
    
    # Apply standard patterns
    for pattern, replacement, data_type in SENSITIVE_PATTERNS:
        if data_type in exclude_types:
            continue
        
        matches = pattern.findall(redacted)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]  # Handle groups
            if match and match != replacement:
                all_redactions.append((match, replacement, data_type))
                redacted = redacted.replace(match, replacement)
    
    # Apply custom patterns
    if custom_patterns:
        for pattern, replacement in custom_patterns:
            matches = pattern.findall(redacted)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match:
                    all_redactions.append((match, replacement, SensitiveDataType.API_KEY))  # Generic type
                    redacted = redacted.replace(match, replacement)
    
    # Apply user-specific disallowed strings
    if user_disallowed:
        for disallowed in user_disallowed:
            if disallowed in redacted:
                all_redactions.append((disallowed, "[REDACTED_CUSTOM]", SensitiveDataType.API_KEY))
                redacted = redacted.replace(disallowed, "[REDACTED_CUSTOM]")
    
    result = RedactionResult(
        original_text=text,
        redacted_text=redacted,
        redactions=all_redactions,
    )
    
    if all_redactions:
        logger.info(
            "Redacted %d sensitive items: %s",
            len(all_redactions),
            [r[2].value for r in all_redactions],
        )
    
    return result


def check_output_policy(
    text: str,
    *,
    severity_threshold: ContentSeverity = ContentSeverity.MEDIUM,
    custom_disallowed: Optional[List[str]] = None,
) -> PolicyCheckResult:
    """
    Check if output content complies with policies.
    
    Checks for:
    - Profanity
    - Hate speech
    - Harmful instructions
    - Violence
    - Custom disallowed content
    
    Args:
        text: Text to check
        severity_threshold: Minimum severity to flag
        custom_disallowed: Additional disallowed phrases
        
    Returns:
        PolicyCheckResult with violations and recommendations
    """
    if not text:
        return PolicyCheckResult(is_allowed=True, violations=[])
    
    violations: List[PolicyViolation] = []
    text_lower = text.lower()
    
    severity_order = {
        ContentSeverity.LOW: 0,
        ContentSeverity.MEDIUM: 1,
        ContentSeverity.HIGH: 2,
        ContentSeverity.CRITICAL: 3,
    }
    threshold_level = severity_order.get(severity_threshold, 1)
    
    # Check standard disallowed content
    for phrase, severity, violation_type in DISALLOWED_CONTENT:
        if severity_order.get(severity, 0) >= threshold_level:
            if phrase.lower() in text_lower:
                position = text_lower.find(phrase.lower())
                replacement = PROFANITY_REPLACEMENTS.get(phrase.lower(), "[REMOVED]")
                violations.append(PolicyViolation(
                    content=phrase,
                    violation_type=violation_type,
                    severity=severity,
                    position=position,
                    replacement=replacement,
                ))
    
    # Check custom disallowed phrases
    if custom_disallowed:
        for phrase in custom_disallowed:
            if phrase.lower() in text_lower:
                position = text_lower.find(phrase.lower())
                violations.append(PolicyViolation(
                    content=phrase,
                    violation_type="custom_policy",
                    severity=ContentSeverity.HIGH,
                    position=position,
                    replacement="[REMOVED]",
                ))
    
    is_allowed = len(violations) == 0
    
    result = PolicyCheckResult(
        is_allowed=is_allowed,
        violations=violations,
    )
    
    if violations:
        logger.warning(
            "Content policy violations: %d (severity: %.2f, rejection: %s)",
            len(violations),
            result.severity_score,
            result.requires_rejection,
        )
    
    return result


def enforce_output_policy(
    text: str,
    *,
    severity_threshold: ContentSeverity = ContentSeverity.MEDIUM,
    reject_critical: bool = True,
) -> Tuple[str, bool, List[str]]:
    """
    Enforce output policy by sanitizing content.
    
    Args:
        text: Text to sanitize
        severity_threshold: Minimum severity to filter
        reject_critical: Whether to reject critical violations entirely
        
    Returns:
        Tuple of (sanitized_text, content_removed, issues)
    """
    result = check_output_policy(text, severity_threshold=severity_threshold)
    
    if result.is_allowed:
        return text, False, []
    
    # Check if we should reject entirely
    if reject_critical and result.requires_rejection:
        return (
            "I apologize, but I cannot provide a response to this request as it may "
            "involve content that violates our safety policies.",
            True,
            [f"Critical violation: {v.violation_type}" for v in result.violations],
        )
    
    # Sanitize by replacing violations
    sanitized = text
    issues = []
    
    for violation in result.violations:
        if violation.replacement:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(violation.content), re.IGNORECASE)
            sanitized = pattern.sub(violation.replacement, sanitized)
            issues.append(f"Replaced '{violation.content}' ({violation.violation_type})")
    
    return sanitized, len(issues) > 0, issues


def assess_query_risk(
    query: str,
    *,
    user_tier: str = "free",
    check_harmful: bool = True,
) -> RiskAssessment:
    """
    Assess the risk level of a query.
    
    Args:
        query: Query to assess
        user_tier: User's account tier
        check_harmful: Whether to check for harmful content
        
    Returns:
        RiskAssessment with risk level and factors
    """
    risk_factors: List[str] = []
    risk_score = 0.0
    blocked = False
    block_reason = None
    
    query_lower = query.lower()
    
    # Check for harmful query patterns
    harmful_patterns = [
        ("how to make a bomb", 1.0, "harmful_instructions"),
        ("how to make explosives", 1.0, "harmful_instructions"),
        ("how to hack", 0.8, "potential_illegal_activity"),
        ("how to steal", 0.9, "illegal_activity"),
        ("how to kill", 1.0, "violence"),
        ("hack into", 0.7, "potential_illegal_activity"),
        ("bypass security", 0.5, "security_concern"),
        ("credit card generator", 0.9, "fraud"),
        ("fake id", 0.8, "fraud"),
    ]
    
    for pattern, score, factor in harmful_patterns:
        if pattern in query_lower:
            risk_score = max(risk_score, score)
            risk_factors.append(factor)
            if score >= 0.9:
                blocked = True
                block_reason = f"Query blocked: {factor}"
    
    # Check for PII in query (might indicate privacy concern)
    redaction = redact_sensitive_info(query)
    if redaction.redaction_count > 0:
        risk_score = max(risk_score, 0.3)
        risk_factors.append("contains_pii")
    
    # Tier-based restrictions
    if user_tier == "free":
        restricted_keywords = ["medical diagnosis", "legal advice", "financial advice"]
        for keyword in restricted_keywords:
            if keyword in query_lower:
                risk_score = max(risk_score, 0.4)
                risk_factors.append(f"tier_restricted:{keyword}")
    
    # Determine risk level
    if risk_score >= 0.9:
        risk_level = "critical"
    elif risk_score >= 0.6:
        risk_level = "high"
    elif risk_score >= 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return RiskAssessment(
        risk_level=risk_level,
        risk_score=risk_score,
        risk_factors=risk_factors,
        requires_review=risk_score >= 0.6,
        blocked=blocked,
        block_reason=block_reason,
    )


# ==============================================================================
# Query and Output Filters (for secure_executor.py compatibility)
# ==============================================================================

def filter_query(
    query: str,
    *,
    is_external: bool = True,
    user_disallowed: Optional[List[str]] = None,
) -> str:
    """
    Filter a query before sending to models.
    
    For external models, redacts sensitive information.
    For internal models, applies minimal filtering.
    
    Args:
        query: Query to filter
        is_external: Whether the target model is external
        user_disallowed: User-specific disallowed strings
        
    Returns:
        Filtered query
    """
    if is_external:
        result = redact_sensitive_info(query, user_disallowed=user_disallowed)
        return result.redacted_text
    
    # Internal models: minimal filtering (just check for harmful content)
    risk = assess_query_risk(query)
    if risk.blocked:
        logger.warning("Query blocked: %s", risk.block_reason)
        return "[Query blocked due to policy violation]"
    
    return query


def filter_output(
    output: str,
    *,
    severity_threshold: str = "medium",
    reject_critical: bool = True,
) -> Tuple[str, bool, List[str]]:
    """
    Filter model output for policy compliance.
    
    Args:
        output: Output to filter
        severity_threshold: "low", "medium", "high"
        reject_critical: Whether to reject critical violations
        
    Returns:
        Tuple of (filtered_output, content_removed, issues)
    """
    threshold_map = {
        "low": ContentSeverity.LOW,
        "medium": ContentSeverity.MEDIUM,
        "high": ContentSeverity.HIGH,
    }
    threshold = threshold_map.get(severity_threshold.lower(), ContentSeverity.MEDIUM)
    
    return enforce_output_policy(
        output,
        severity_threshold=threshold,
        reject_critical=reject_critical,
    )


# ==============================================================================
# Safety Validator Class
# ==============================================================================

class SafetyValidator:
    """Comprehensive safety validator for content.
    
    Combines redaction, policy checking, and risk assessment.
    """
    
    def __init__(
        self,
        severity_threshold: ContentSeverity = ContentSeverity.MEDIUM,
        reject_critical: bool = True,
        custom_disallowed: Optional[List[str]] = None,
    ):
        """
        Initialize safety validator.
        
        Args:
            severity_threshold: Minimum severity to flag
            reject_critical: Reject content with critical violations
            custom_disallowed: Custom disallowed phrases
        """
        self.severity_threshold = severity_threshold
        self.reject_critical = reject_critical
        self.custom_disallowed = custom_disallowed or []
    
    def inspect(self, content: str) -> SafetyReport:
        """
        Inspect content for safety issues.
        
        Args:
            content: Content to inspect
            
        Returns:
            SafetyReport with full analysis
        """
        # Step 1: Redact sensitive info
        redaction_result = redact_sensitive_info(content)
        working_content = redaction_result.redacted_text
        
        # Step 2: Check output policy
        policy_result = check_output_policy(
            working_content,
            severity_threshold=self.severity_threshold,
            custom_disallowed=self.custom_disallowed,
        )
        
        # Step 3: Sanitize if needed
        if not policy_result.is_allowed:
            sanitized, _, _ = enforce_output_policy(
                working_content,
                severity_threshold=self.severity_threshold,
                reject_critical=self.reject_critical,
            )
            working_content = sanitized
        
        is_safe = (
            policy_result.is_allowed or
            (not policy_result.requires_rejection)
        )
        
        return SafetyReport(
            original_content=content,
            sanitized_content=working_content,
            is_safe=is_safe,
            redaction_result=redaction_result,
            policy_result=policy_result,
        )
    
    def validate_input(self, query: str, *, user_tier: str = "free") -> Tuple[str, bool, Optional[str]]:
        """
        Validate and sanitize input query.
        
        Args:
            query: Input query
            user_tier: User's account tier
            
        Returns:
            Tuple of (sanitized_query, is_allowed, rejection_reason)
        """
        # Check risk
        risk = assess_query_risk(query, user_tier=user_tier)
        
        if risk.blocked:
            return "", False, risk.block_reason
        
        # Redact sensitive info
        redaction = redact_sensitive_info(query)
        
        return redaction.redacted_text, True, None
    
    def validate_output(self, output: str) -> Tuple[str, bool]:
        """
        Validate and sanitize output.
        
        Args:
            output: Model output
            
        Returns:
            Tuple of (sanitized_output, is_safe)
        """
        report = self.inspect(output)
        return report.sanitized_content, report.is_safe


# ==============================================================================
# Execution Sandbox
# ==============================================================================

class ExecutionSandbox:
    """Sandbox for safe code execution.
    
    Provides a restricted environment for executing code snippets
    with limited access to system resources.
    """
    
    ALLOWED_MODULES = frozenset({
        "math", "json", "re", "datetime", "collections", "itertools",
        "functools", "operator", "string", "random", "statistics",
    })
    
    FORBIDDEN_BUILTINS = frozenset({
        "open", "exec", "eval", "compile", "__import__",
        "getattr", "setattr", "delattr", "globals", "locals",
        "input", "breakpoint",
    })
    
    def __init__(self, timeout_seconds: float = 5.0):
        """
        Initialize execution sandbox.
        
        Args:
            timeout_seconds: Maximum execution time
        """
        self.timeout = timeout_seconds
    
    def execute_python(self, code: str) -> Tuple[str, bool, Optional[str]]:
        """
        Execute Python code in sandbox.
        
        Args:
            code: Python code to execute
            
        Returns:
            Tuple of (output, success, error_message)
        """
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        
        # Validate code first
        is_safe, violations = self._validate_code(code)
        if not is_safe:
            return "", False, f"Code validation failed: {', '.join(violations)}"
        
        # Create restricted builtins
        safe_builtins = {
            k: v for k, v in __builtins__.__dict__.items()
            if k not in self.FORBIDDEN_BUILTINS
        } if isinstance(__builtins__, dict) else {
            k: getattr(__builtins__, k)
            for k in dir(__builtins__)
            if k not in self.FORBIDDEN_BUILTINS and not k.startswith('_')
        }
        
        # Create restricted globals
        sandbox_globals = {
            "__builtins__": safe_builtins,
            "__name__": "__sandbox__",
        }
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, sandbox_globals)
            
            output = stdout_capture.getvalue()
            return output, True, None
            
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"
            return "", False, error
    
    def _validate_code(self, code: str) -> Tuple[bool, List[str]]:
        """Validate code for dangerous patterns."""
        violations = []
        
        dangerous_patterns = [
            (r'import\s+os\b', "os module import"),
            (r'import\s+subprocess\b', "subprocess module import"),
            (r'import\s+sys\b', "sys module import"),
            (r'import\s+shutil\b', "shutil module import"),
            (r'__import__\s*\(', "__import__ usage"),
            (r'exec\s*\(', "exec usage"),
            (r'eval\s*\(', "eval usage"),
            (r'open\s*\(', "file open"),
            (r'os\.system', "os.system call"),
            (r'subprocess\.', "subprocess usage"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(description)
        
        return len(violations) == 0, violations


# ==============================================================================
# Tier-Based Access Control
# ==============================================================================

class TierAccessController:
    """Controls access to features based on user tier."""
    
    TIER_FEATURES: Dict[str, Set[str]] = {
        "free": {
            "basic_orchestration",
            "standard_models",
        },
        "pro": {
            "basic_orchestration",
            "standard_models",
            "advanced_orchestration",
            "deep_verification",
            "enhanced_memory",
        },
        "enterprise": {
            "basic_orchestration",
            "standard_models",
            "advanced_orchestration",
            "deep_verification",
            "enhanced_memory",
            "custom_models",
            "priority_support",
            "medical_domain",
            "legal_domain",
        },
    }
    
    TIER_RATE_LIMITS: Dict[str, Dict[str, int]] = {
        "free": {"requests_per_minute": 5, "requests_per_day": 100},
        "pro": {"requests_per_minute": 20, "requests_per_day": 1000},
        "enterprise": {"requests_per_minute": 60, "requests_per_day": -1},  # -1 = unlimited
    }
    
    def __init__(self):
        """Initialize tier access controller."""
        self._usage_counters: Dict[str, Dict[str, int]] = {}
    
    def check_feature_access(
        self,
        user_tier: str,
        feature: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user tier has access to feature.
        
        Args:
            user_tier: User's tier
            feature: Feature to check
            
        Returns:
            Tuple of (allowed, rejection_reason)
        """
        tier = user_tier.lower()
        allowed_features = self.TIER_FEATURES.get(tier, self.TIER_FEATURES["free"])
        
        if feature in allowed_features:
            return True, None
        
        return False, f"Feature '{feature}' not available for tier '{tier}'"
    
    def check_rate_limit(
        self,
        user_id: str,
        user_tier: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits.
        
        Args:
            user_id: User ID
            user_tier: User's tier
            
        Returns:
            Tuple of (allowed, rejection_reason)
        """
        tier = user_tier.lower()
        limits = self.TIER_RATE_LIMITS.get(tier, self.TIER_RATE_LIMITS["free"])
        
        # For now, just return True (rate limiting implemented elsewhere)
        return True, None
    
    def enforce_tier_restrictions(
        self,
        query: str,
        user_tier: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Enforce tier-based query restrictions.
        
        Args:
            query: User query
            user_tier: User's tier
            
        Returns:
            Tuple of (allowed, rejection_reason)
        """
        query_lower = query.lower()
        tier = user_tier.lower()
        
        # Domain restrictions for free tier
        if tier == "free":
            restricted_domains = [
                ("medical diagnosis", "medical_domain"),
                ("legal advice", "legal_domain"),
                ("investment advice", "financial_domain"),
            ]
            
            for keyword, domain in restricted_domains:
                if keyword in query_lower:
                    return False, (
                        f"Query involves {domain} which requires Pro or Enterprise tier. "
                        "Please upgrade to access this feature."
                    )
        
        return True, None


# ==============================================================================
# Security Check Pipeline
# ==============================================================================

async def security_check(
    content: str,
    *,
    content_type: str = "output",
    user_tier: str = "free",
    is_external: bool = True,
) -> Tuple[str, bool, List[str]]:
    """
    Run comprehensive security check on content.
    
    This is the main entry point for security checks at the end of the pipeline.
    
    Args:
        content: Content to check
        content_type: "input" or "output"
        user_tier: User's account tier
        is_external: Whether content is going to/from external model
        
    Returns:
        Tuple of (sanitized_content, passed, issues)
    """
    issues: List[str] = []
    
    # Step 1: Redact sensitive info (for external models)
    if is_external and content_type == "input":
        redaction = redact_sensitive_info(content)
        content = redaction.redacted_text
        if redaction.redaction_count > 0:
            issues.append(f"Redacted {redaction.redaction_count} sensitive items")
    
    # Step 2: Check content policy
    policy_result = check_output_policy(content)
    if not policy_result.is_allowed:
        # Step 3: Enforce policy
        content, removed, policy_issues = enforce_output_policy(content)
        issues.extend(policy_issues)
        
        if policy_result.requires_rejection:
            return content, False, issues
    
    # Step 4: Risk assessment for inputs
    if content_type == "input":
        risk = assess_query_risk(content, user_tier=user_tier)
        if risk.blocked:
            return "", False, [risk.block_reason or "Query blocked"]
        if risk.requires_review:
            issues.append(f"Risk level: {risk.risk_level}")
    
    return content, True, issues


# Global instances
_safety_validator: Optional[SafetyValidator] = None
_tier_controller: Optional[TierAccessController] = None


def get_safety_validator() -> SafetyValidator:
    """Get global safety validator instance."""
    global _safety_validator
    if _safety_validator is None:
        _safety_validator = SafetyValidator()
    return _safety_validator


def get_tier_controller() -> TierAccessController:
    """Get global tier access controller instance."""
    global _tier_controller
    if _tier_controller is None:
        _tier_controller = TierAccessController()
    return _tier_controller

