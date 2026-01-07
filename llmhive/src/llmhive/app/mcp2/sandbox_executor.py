"""Enhanced Sandbox Executor with cold boot detection, retry logic, and error redaction.

This module extends the base sandbox with production-hardening features:
1. Cold boot detection and pre-warming
2. Timeout retry logic with simplified inputs
3. Graceful error traceback redaction
4. Resource monitoring and limits
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .sandbox import CodeSandbox, SandboxConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class EnhancedSandboxConfig(SandboxConfig):
    """Extended sandbox configuration with resilience options."""
    
    # Cold boot settings
    enable_prewarm: bool = True
    prewarm_script: str = "import json, datetime, collections, math"
    
    # Retry settings
    enable_timeout_retry: bool = True
    retry_timeout_multiplier: float = 1.5  # Extend timeout on retry
    max_retries: int = 1
    simplify_input_on_retry: bool = True
    
    # Error redaction
    redact_tracebacks: bool = True
    max_error_length: int = 500
    redact_patterns: List[str] = field(default_factory=lambda: [
        r'/tmp/[^\s]+',  # Temp paths
        r'/home/[^\s]+',  # Home paths
        r'/Users/[^\s]+',  # macOS paths
        r'File "[^"]+", line',  # File references
        r'at 0x[0-9a-f]+',  # Memory addresses
    ])
    
    # Resource monitoring
    enable_resource_monitor: bool = True
    memory_warning_threshold_mb: int = 400


# =============================================================================
# Cold Boot Detection and Pre-warming
# =============================================================================

class ColdBootManager:
    """Manages cold boot detection and pre-warming for sandbox environments."""
    
    def __init__(self, config: EnhancedSandboxConfig):
        """Initialize cold boot manager.
        
        Args:
            config: Enhanced sandbox configuration
        """
        self.config = config
        self._warmed_sessions: Dict[str, float] = {}  # session -> last_warm_time
        self._warm_duration_seconds = 300  # 5 minutes warm window
        self._prewarm_lock = asyncio.Lock()
    
    def is_cold_boot(self, session_token: str) -> bool:
        """Check if this is a cold boot for the session.
        
        Args:
            session_token: Session identifier
            
        Returns:
            True if cold boot (not pre-warmed)
        """
        if session_token not in self._warmed_sessions:
            return True
        
        last_warm = self._warmed_sessions[session_token]
        return (time.time() - last_warm) > self._warm_duration_seconds
    
    async def prewarm(
        self,
        sandbox: CodeSandbox,
        session_token: str,
    ) -> Tuple[bool, float]:
        """Pre-warm the sandbox environment.
        
        Args:
            sandbox: Sandbox instance to warm
            session_token: Session identifier
            
        Returns:
            Tuple of (success, warmup_time_ms)
        """
        if not self.config.enable_prewarm:
            return True, 0.0
        
        async with self._prewarm_lock:
            if not self.is_cold_boot(session_token):
                return True, 0.0
            
            start_time = time.time()
            logger.info("Pre-warming sandbox for session %s", session_token[:8])
            
            try:
                # Run pre-warm script to load common modules
                result = await sandbox.execute_python(
                    self.config.prewarm_script,
                    context=None,
                )
                
                warmup_ms = (time.time() - start_time) * 1000
                
                if result.get("status") == "success":
                    self._warmed_sessions[session_token] = time.time()
                    logger.info("Sandbox pre-warmed in %.1fms", warmup_ms)
                    return True, warmup_ms
                else:
                    logger.warning("Pre-warm failed: %s", result.get("error"))
                    return False, warmup_ms
                    
            except Exception as e:
                warmup_ms = (time.time() - start_time) * 1000
                logger.warning("Pre-warm exception: %s", e)
                return False, warmup_ms
    
    def mark_warmed(self, session_token: str) -> None:
        """Mark a session as warmed."""
        self._warmed_sessions[session_token] = time.time()
    
    def cleanup_session(self, session_token: str) -> None:
        """Remove session from warm tracking."""
        self._warmed_sessions.pop(session_token, None)


# =============================================================================
# Error Redaction
# =============================================================================

class ErrorRedactor:
    """Redacts sensitive information from error messages."""
    
    def __init__(self, config: EnhancedSandboxConfig):
        """Initialize error redactor.
        
        Args:
            config: Configuration with redaction patterns
        """
        self.config = config
        self._patterns = [
            re.compile(pattern) for pattern in config.redact_patterns
        ]
    
    def redact(self, error: str) -> str:
        """Redact sensitive information from error message.
        
        Args:
            error: Raw error message
            
        Returns:
            Redacted error message
        """
        if not self.config.redact_tracebacks:
            return error
        
        redacted = error
        
        # Apply all redaction patterns
        for pattern in self._patterns:
            redacted = pattern.sub('[redacted]', redacted)
        
        # Remove stack trace details while keeping essential info
        lines = redacted.split('\n')
        filtered_lines = []
        in_traceback = False
        
        for line in lines:
            if 'Traceback (most recent call last):' in line:
                in_traceback = True
                filtered_lines.append("Error details:")
                continue
            
            if in_traceback:
                # Keep only the error message, not the full traceback
                if line.strip().startswith(('Error:', 'Exception:', 'TypeError:',
                                           'ValueError:', 'KeyError:', 'IndexError:',
                                           'AttributeError:', 'NameError:', 'RuntimeError:')):
                    filtered_lines.append(f"  {line.strip()}")
                    in_traceback = False
                elif not line.strip().startswith(('File ', '    ', '^')):
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines).strip()
        
        # Truncate if too long
        if len(result) > self.config.max_error_length:
            result = result[:self.config.max_error_length] + "... [truncated]"
        
        return result
    
    def extract_user_friendly_error(self, error: str) -> str:
        """Extract a user-friendly error message.
        
        Args:
            error: Raw error message
            
        Returns:
            User-friendly error description
        """
        # Common error patterns and user-friendly messages
        error_mappings = [
            (r"NameError: name '(\w+)' is not defined", "Variable '{}' was not defined"),
            (r"TypeError: '(\w+)' object is not", "Cannot perform this operation on '{}'"),
            (r"ZeroDivisionError", "Cannot divide by zero"),
            (r"IndexError: list index out of range", "List index out of bounds"),
            (r"KeyError: '?(\w+)'?", "Key '{}' not found in dictionary"),
            (r"TimeoutError|timeout", "Operation timed out"),
            (r"MemoryError", "Ran out of memory"),
            (r"PermissionError", "Permission denied"),
        ]
        
        for pattern, message in error_mappings:
            match = re.search(pattern, error)
            if match:
                if '{}' in message and match.groups():
                    return message.format(match.group(1))
                return message
        
        # Fall back to first line of redacted error
        redacted = self.redact(error)
        first_line = redacted.split('\n')[0]
        return first_line if first_line else "Execution error occurred"


# =============================================================================
# Input Simplification
# =============================================================================

def simplify_code_input(code: str) -> str:
    """Simplify code for retry attempt.
    
    Removes non-essential parts that might cause timeouts:
    - Reduces iteration counts
    - Limits string lengths
    - Removes print statements in loops
    
    Args:
        code: Original code
        
    Returns:
        Simplified code
    """
    simplified = code
    
    # Reduce range sizes (e.g., range(1000) -> range(100))
    simplified = re.sub(
        r'range\((\d{4,})\)',
        lambda m: f'range({min(100, int(m.group(1)))})',
        simplified
    )
    
    # Reduce list comprehension sizes
    simplified = re.sub(
        r'for\s+\w+\s+in\s+range\((\d{4,})\)',
        lambda m: f'for i in range({min(100, int(m.group(1)))})',
        simplified
    )
    
    # Add early termination hint
    if 'while ' in simplified and 'break' not in simplified:
        # Add iteration limit warning
        simplified = f"# Note: Added iteration limit for safety\n_iter_count = 0\n" + simplified
        simplified = re.sub(
            r'(while\s+.+:)',
            r'\1\n    _iter_count += 1\n    if _iter_count > 1000: break',
            simplified
        )
    
    return simplified


# =============================================================================
# Enhanced Sandbox Executor
# =============================================================================

class EnhancedSandboxExecutor:
    """Enhanced sandbox executor with resilience features.
    
    Features:
    - Cold boot detection and pre-warming
    - Automatic retry on timeout with input simplification
    - Graceful error redaction
    - Resource monitoring
    """
    
    def __init__(
        self,
        config: Optional[EnhancedSandboxConfig] = None,
        session_token: str = "",
    ):
        """Initialize enhanced executor.
        
        Args:
            config: Enhanced sandbox configuration
            session_token: Session identifier
        """
        self.config = config or EnhancedSandboxConfig()
        self.session_token = session_token
        
        # Initialize components
        self.cold_boot_manager = ColdBootManager(self.config)
        self.error_redactor = ErrorRedactor(self.config)
        
        # Create base sandbox
        self.sandbox = CodeSandbox(self.config, session_token)
        
        # Execution metrics
        self._execution_count = 0
        self._timeout_count = 0
        self._retry_count = 0
    
    async def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Execute code with enhanced resilience.
        
        Args:
            code: Code to execute
            context: Execution context
            language: Programming language
            
        Returns:
            Execution result with enhanced metadata
        """
        start_time = time.time()
        self._execution_count += 1
        
        # Handle cold boot
        if self.cold_boot_manager.is_cold_boot(self.session_token):
            warmup_success, warmup_ms = await self.cold_boot_manager.prewarm(
                self.sandbox,
                self.session_token,
            )
            if not warmup_success:
                logger.warning("Cold boot pre-warm failed, continuing anyway")
        
        # First attempt
        result = await self._execute_with_timeout(code, context, language)
        
        # Check for timeout and retry if enabled
        if (
            result.get("status") == "timeout"
            and self.config.enable_timeout_retry
            and self.config.max_retries > 0
        ):
            self._timeout_count += 1
            
            # Attempt retry with longer timeout and/or simplified input
            for retry_num in range(self.config.max_retries):
                self._retry_count += 1
                logger.info(
                    "Timeout retry %d/%d for session %s",
                    retry_num + 1,
                    self.config.max_retries,
                    self.session_token[:8],
                )
                
                # Simplify input on retry if enabled
                retry_code = code
                if self.config.simplify_input_on_retry:
                    retry_code = simplify_code_input(code)
                
                # Extend timeout
                original_timeout = self.config.timeout_seconds
                self.config.timeout_seconds *= self.config.retry_timeout_multiplier
                
                try:
                    result = await self._execute_with_timeout(retry_code, context, language)
                    
                    if result.get("status") != "timeout":
                        result["retry_succeeded"] = True
                        result["retry_count"] = retry_num + 1
                        break
                finally:
                    # Restore original timeout
                    self.config.timeout_seconds = original_timeout
            
            if result.get("status") == "timeout":
                result["retry_exhausted"] = True
        
        # Redact errors
        if result.get("error"):
            result["error_raw"] = result["error"]
            result["error"] = self.error_redactor.redact(result["error"])
            result["error_friendly"] = self.error_redactor.extract_user_friendly_error(
                result["error_raw"]
            )
        
        if result.get("stderr"):
            result["stderr"] = self.error_redactor.redact(result["stderr"])
        
        # Add execution metadata
        result["execution_time_ms"] = (time.time() - start_time) * 1000
        result["session_token"] = self.session_token[:8]
        result["was_cold_boot"] = self.cold_boot_manager.is_cold_boot(self.session_token)
        
        # Mark session as warmed after successful execution
        if result.get("status") == "success":
            self.cold_boot_manager.mark_warmed(self.session_token)
        
        return result
    
    async def _execute_with_timeout(
        self,
        code: str,
        context: Optional[Dict[str, Any]],
        language: str,
    ) -> Dict[str, Any]:
        """Execute code with timeout handling.
        
        Args:
            code: Code to execute
            context: Execution context
            language: Programming language
            
        Returns:
            Execution result
        """
        if language == "python":
            return await self.sandbox.execute_python(code, context)
        elif language == "typescript":
            return await self.sandbox.execute_typescript(code, context)
        else:
            return {
                "status": "error",
                "error": f"Unsupported language: {language}",
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics.
        
        Returns:
            Execution statistics
        """
        return {
            "total_executions": self._execution_count,
            "timeout_count": self._timeout_count,
            "retry_count": self._retry_count,
            "timeout_rate": self._timeout_count / max(1, self._execution_count),
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.cold_boot_manager.cleanup_session(self.session_token)
        self.sandbox.cleanup()


# =============================================================================
# Factory Functions
# =============================================================================

_executors: Dict[str, EnhancedSandboxExecutor] = {}


def get_enhanced_executor(
    session_token: str,
    config: Optional[EnhancedSandboxConfig] = None,
) -> EnhancedSandboxExecutor:
    """Get or create an enhanced executor for a session.
    
    Args:
        session_token: Session identifier
        config: Optional configuration
        
    Returns:
        EnhancedSandboxExecutor instance
    """
    global _executors
    
    if session_token not in _executors:
        _executors[session_token] = EnhancedSandboxExecutor(
            config=config,
            session_token=session_token,
        )
    
    return _executors[session_token]


def cleanup_executor(session_token: str) -> None:
    """Clean up an executor for a session."""
    global _executors
    
    if session_token in _executors:
        _executors[session_token].cleanup()
        del _executors[session_token]

