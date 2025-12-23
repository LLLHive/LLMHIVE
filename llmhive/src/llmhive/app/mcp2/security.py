"""Security hardening for MCP 2.0 sandbox.

This module provides additional security layers beyond basic sandboxing.
"""
from __future__ import annotations

import logging
import re
from typing import List, Set, Any

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validates code and operations for security violations.
    
    Checks for dangerous patterns, restricted operations, and potential exploits.
    """

    def __init__(self):
        """Initialize security validator."""
        self.dangerous_patterns = [
            # System operations
            r'os\.system\s*\(',
            r'subprocess\.',
            r'exec\s*\(',
            r'eval\s*\(',
            r'__import__\s*\(',
            r'compile\s*\(',
            
            # File system escapes
            r'\.\./',
            r'/etc/',
            r'/proc/',
            r'/sys/',
            r'/dev/',
            
            # Network operations
            r'socket\.',
            r'urllib\.',
            r'requests\.',
            r'http\.',
            
            # Credential access attempts
            r'password\s*[:=]',
            r'api[_-]?key\s*[:=]',
            r'token\s*[:=]',
            r'secret\s*[:=]',
            
            # Dangerous imports
            r'import\s+subprocess',
            r'import\s+sys',
            r'from\s+os\s+import\s+system',
            r'import\s+shutil',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns]
    
    def validate_code(self, code: str) -> tuple[bool, List[str]]:
        """Validate code for security violations.
        
        Args:
            code: Code to validate
            
        Returns:
            Tuple of (is_safe, violations)
        """
        violations: List[str] = []
        
        for pattern in self.compiled_patterns:
            matches = pattern.findall(code)
            if matches:
                violations.append(f"Dangerous pattern detected: {pattern.pattern}")
        
        is_safe = len(violations) == 0
        
        if not is_safe:
            logger.warning(
                "Security validation failed: %d violations detected",
                len(violations)
            )
        
        return is_safe, violations
    
    def sanitize_path(self, path: str) -> str:
        """Sanitize file path to prevent directory traversal.
        
        Args:
            path: File path
            
        Returns:
            Sanitized path
        """
        # Remove directory traversal attempts
        sanitized = path.replace("../", "").replace("..\\", "")
        
        # Remove absolute paths
        if sanitized.startswith("/"):
            sanitized = sanitized.lstrip("/")
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"|?*]', "", sanitized)
        
        return sanitized
    
    def validate_tool_call(self, tool_name: str, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a tool call for security.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for path traversal in file paths
        for key, value in params.items():
            if "path" in key.lower() and isinstance(value, str):
                if ".." in value or value.startswith("/"):
                    return False, f"Invalid path in parameter {key}: {value}"
        
        # Check for injection attempts in string parameters
        for key, value in params.items():
            if isinstance(value, str):
                if any(char in value for char in [";", "|", "&", "$", "`"]):
                    return False, f"Potentially dangerous characters in parameter {key}"
        
        return True, None


class SecurityAuditor:
    """Audits security events and violations.
    
    Tracks security-related events for analysis and alerting.
    """

    def __init__(self):
        """Initialize security auditor."""
        self.violations: List[Dict[str, Any]] = []
        self.blocked_operations: List[Dict[str, Any]] = []
    
    def record_violation(
        self,
        violation_type: str,
        details: str,
        session_token: str,
        code_snippet: str = "",
        tool_name: str = "",
    ) -> None:
        """Record a security violation.
        
        Args:
            violation_type: Type of violation
            details: Violation details
            session_token: Session token
            code_snippet: Code snippet that caused violation
            tool_name: Name of tool that triggered violation (if applicable)
        """
        violation = {
            "type": violation_type,
            "details": details,
            "session_token": session_token[:8],
            "code_snippet": code_snippet[:200],  # Limit snippet size
            "tool_name": tool_name,
            "timestamp": time.time(),
        }
        
        self.violations.append(violation)
        logger.warning(
            "Security violation: type=%s, session=%s, tool=%s, details=%s",
            violation_type,
            session_token[:8],
            tool_name or "N/A",
            details
        )
        
        # Keep only recent violations (last 1000)
        if len(self.violations) > 1000:
            self.violations = self.violations[-1000:]
    
    def record_blocked_operation(
        self,
        operation: str,
        reason: str,
        session_token: str,
    ) -> None:
        """Record a blocked operation.
        
        Args:
            operation: Blocked operation
            reason: Reason for blocking
            session_token: Session token
        """
        blocked = {
            "operation": operation,
            "reason": reason,
            "session_token": session_token[:8],
            "timestamp": time.time(),
        }
        
        self.blocked_operations.append(blocked)
        logger.info(
            "Blocked operation: %s (reason: %s, session: %s)",
            operation,
            reason,
            session_token[:8]
        )
    
    def get_security_report(self) -> Dict[str, Any]:
        """Get security audit report.
        
        Returns:
            Security report dictionary
        """
        return {
            "total_violations": len(self.violations),
            "total_blocked_operations": len(self.blocked_operations),
            "recent_violations": self.violations[-20:],
            "recent_blocked_operations": self.blocked_operations[-20:],
        }


# Import time for timestamps
import time

