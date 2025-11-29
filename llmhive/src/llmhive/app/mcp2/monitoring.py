"""Monitoring and logging for MCP 2.0 system.

This module provides comprehensive logging, monitoring, and metrics collection
for the code-executor system.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionLog:
    """Log entry for code execution."""
    
    session_token: str
    execution_id: str
    code_length: int
    language: str
    success: bool
    execution_time_ms: float
    tokens_saved: int
    tools_called: List[str]
    error: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class MCP2Monitor:
    """Monitoring and logging for MCP 2.0 system.
    
    Tracks executions, metrics, and provides alerts for anomalies.
    """

    def __init__(self, enable_debug: bool = False):
        """Initialize monitor.
        
        Args:
            enable_debug: Enable debug mode (logs full code and outputs)
        """
        self.enable_debug = enable_debug
        self.execution_logs: List[ExecutionLog] = []
        self.metrics: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_tokens_saved": 0,
            "avg_execution_time_ms": 0.0,
            "total_tools_called": 0,
        }
        self._max_logs = 1000  # Keep last 1000 executions
    
    def log_execution(
        self,
        session_token: str,
        execution_id: str,
        code: str,
        language: str,
        result: Any,
        execution_time_ms: float,
        tokens_saved: int = 0,
    ) -> None:
        """Log a code execution.
        
        Args:
            session_token: Session token
            execution_id: Unique execution ID
            code: Executed code (may be sanitized)
            language: Programming language
            result: Execution result
            execution_time_ms: Execution time in milliseconds
            tokens_saved: Tokens saved through optimization
        """
        log_entry = ExecutionLog(
            session_token=session_token[:8],  # Truncate for privacy
            execution_id=execution_id,
            code_length=len(code),
            language=language,
            success=getattr(result, "success", False),
            execution_time_ms=execution_time_ms,
            tokens_saved=tokens_saved,
            tools_called=getattr(result, "tools_called", []),
            error=getattr(result, "error", None),
        )
        
        # Add to logs
        self.execution_logs.append(log_entry)
        
        # Trim logs if too large
        if len(self.execution_logs) > self._max_logs:
            self.execution_logs = self.execution_logs[-self._max_logs:]
        
        # Update metrics
        self.metrics["total_executions"] += 1
        if log_entry.success:
            self.metrics["successful_executions"] += 1
        else:
            self.metrics["failed_executions"] += 1
        
        self.metrics["total_tokens_saved"] += tokens_saved
        self.metrics["total_tools_called"] += len(log_entry.tools_called)
        
        # Update average execution time
        total_time = sum(e.execution_time_ms for e in self.execution_logs)
        self.metrics["avg_execution_time_ms"] = total_time / len(self.execution_logs)
        
        # Log to logger
        if self.enable_debug:
            logger.debug(
                "MCP 2.0 Execution: session=%s, success=%s, time=%.2fms, tokens_saved=%d",
                session_token[:8],
                log_entry.success,
                execution_time_ms,
                tokens_saved
            )
        else:
            logger.info(
                "MCP 2.0 Execution: session=%s, success=%s, time=%.2fms, tokens_saved=%d",
                session_token[:8],
                log_entry.success,
                execution_time_ms,
                tokens_saved
            )
        
        # Check for anomalies
        self._check_anomalies(log_entry)
    
    def _check_anomalies(self, log_entry: ExecutionLog) -> None:
        """Check for anomalous execution patterns.
        
        Args:
            log_entry: Execution log entry
        """
        # Check for timeout patterns
        if log_entry.execution_time_ms > 4000:  # 4 seconds
            logger.warning(
                "MCP 2.0: Slow execution detected: %.2fms (session: %s)",
                log_entry.execution_time_ms,
                log_entry.session_token
            )
        
        # Check for repeated failures
        recent_failures = [
            e for e in self.execution_logs[-10:]
            if not e.success and e.session_token == log_entry.session_token
        ]
        if len(recent_failures) >= 5:
            logger.warning(
                "MCP 2.0: Multiple failures detected for session %s (%d failures)",
                log_entry.session_token,
                len(recent_failures)
            )
        
        # Check for token usage regression
        if log_entry.tokens_saved < 0:
            logger.warning(
                "MCP 2.0: Token usage increased (saved: %d) for session %s",
                log_entry.tokens_saved,
                log_entry.session_token
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics.
        
        Returns:
            Dictionary with metrics
        """
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_executions"] / self.metrics["total_executions"]
                if self.metrics["total_executions"] > 0
                else 0.0
            ),
            "avg_tokens_saved_per_execution": (
                self.metrics["total_tokens_saved"] / self.metrics["total_executions"]
                if self.metrics["total_executions"] > 0
                else 0
            ),
        }
    
    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of log entries as dictionaries
        """
        recent = self.execution_logs[-limit:]
        return [asdict(log) for log in recent]
    
    def export_logs(self, file_path: str) -> None:
        """Export logs to a file.
        
        Args:
            file_path: Path to export file
        """
        logs_data = {
            "metrics": self.get_metrics(),
            "logs": self.get_recent_logs(limit=1000),
        }
        
        with open(file_path, "w") as f:
            json.dump(logs_data, f, indent=2)
        
        logger.info("Exported %d execution logs to %s", len(logs_data["logs"]), file_path)

