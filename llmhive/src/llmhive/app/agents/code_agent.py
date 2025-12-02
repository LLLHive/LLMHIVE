"""Code Execution Agent for LLMHive.

This on-demand agent handles code execution tasks.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


class CodeExecutionAgent(BaseAgent):
    """Agent that executes code and returns results.
    
    Responsibilities:
    - Execute code snippets safely
    - Run tests on generated code
    - Generate visualizations
    - Handle computation tasks
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="code_agent",
                agent_type=AgentType.ON_DEMAND,
                priority=AgentPriority.HIGH,
                max_tokens_per_run=5000,
                max_runtime_seconds=30,  # Short timeout for code
                allowed_tools=["code_sandbox", "linter"],
                memory_namespace="code",
            )
        super().__init__(config)
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute code."""
        # TODO: Integrate with secure_executor.py
        if not task:
            return AgentResult(success=False, error="No task provided")
        
        return AgentResult(
            success=True,
            output={"status": "Code execution completed (stub)"},
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Code Execution Agent",
            "type": "on_demand",
            "purpose": "Execute code and return results",
            "languages": ["Python", "JavaScript"],
        }

