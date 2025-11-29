"""Code executor for MCP 2.0 system.

This module coordinates code execution, tool calls, and result processing.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .sandbox import CodeSandbox, SandboxConfig
from .tool_abstraction import MCPToolClient

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution."""
    
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tokens_saved: int = 0
    tools_called: List[str] = None  # type: ignore
    data_processed_size: int = 0
    
    def __post_init__(self):
        if self.tools_called is None:
            self.tools_called = []


class CodeExecutor:
    """Executor for agent-generated code with MCP tool integration.
    
    Coordinates code execution in a sandbox, handles tool calls, and
    manages context optimization.
    """

    def __init__(
        self,
        sandbox_config: SandboxConfig,
        mcp_tool_client: MCPToolClient,
        session_token: str,
    ):
        """Initialize code executor.
        
        Args:
            sandbox_config: Sandbox configuration
            mcp_tool_client: MCP tool client for tool calls
            session_token: Session token
        """
        self.sandbox_config = sandbox_config
        self.mcp_tool_client = mcp_tool_client
        self.session_token = session_token
        self.sandbox: Optional[CodeSandbox] = None
    
    async def execute(
        self, code: str, language: str = "python"
    ) -> ExecutionResult:
        """Execute agent-generated code.
        
        Args:
            code: Code to execute
            language: Programming language ("python" or "typescript")
            
        Returns:
            Execution result with output and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        # Create sandbox for this execution
        self.sandbox = CodeSandbox(self.sandbox_config, self.session_token)
        
        try:
            # Inject tool calling function into context
            context = {
                "callMCPTool": self._create_tool_caller(),
                "call_mcp_tool": self._create_tool_caller(),  # Python alias
            }
            
            # Execute code
            if language == "python":
                result = await self.sandbox.execute_python(code, context)
            elif language == "typescript":
                result = await self.sandbox.execute_typescript(code, context)
            else:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Unsupported language: {language}",
                )
            
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Parse result
            success = result.get("status") == "success"
            output = result.get("stdout", "")
            error = result.get("stderr") or result.get("error")
            
            return ExecutionResult(
                success=success,
                output=output,
                error=error,
                execution_time_ms=execution_time,
                tools_called=self._extract_tools_called(code),
            )
            
        except Exception as exc:
            logger.error("Code execution error: %s", exc, exc_info=True)
            return ExecutionResult(
                success=False,
                output="",
                error=str(exc),
            )
        finally:
            if self.sandbox:
                self.sandbox.cleanup()
    
    def _create_tool_caller(self) -> Any:
        """Create a tool calling function for injection into code context.
        
        Returns:
            Callable function for tool calls
        """
        async def call_tool(tool_name: str, params: Dict[str, Any]) -> Any:
            """Call an MCP tool from within executed code."""
            try:
                result = await self.mcp_tool_client.call_tool(tool_name, params)
                return result
            except Exception as exc:
                logger.error("Tool call error in sandbox: %s", exc)
                return {"status": "error", "error": str(exc)}
        
        return call_tool
    
    def _extract_tools_called(self, code: str) -> List[str]:
        """Extract list of tools called in code.
        
        Args:
            code: Code string
            
        Returns:
            List of tool names called
        """
        # Simple regex-based extraction
        import re
        pattern = r'callMCPTool\(["\']([^"\']+)["\']'
        matches = re.findall(pattern, code)
        return list(set(matches))

