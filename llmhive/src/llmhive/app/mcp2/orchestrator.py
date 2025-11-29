"""MCP 2.0 orchestrator integration.

This module integrates the MCP 2.0 code-executor system with the main orchestrator,
allowing the agent to write and execute code instead of making direct tool calls.
"""
from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Any, Dict, List, Optional

from .executor import CodeExecutor, ExecutionResult
from .filesystem import ToolFileSystem, VirtualFileSystem
from .context_optimizer import ContextOptimizer
from .sandbox import SandboxConfig
from .tool_abstraction import MCPToolClient

logger = logging.getLogger(__name__)


class MCP2Orchestrator:
    """Orchestrator for MCP 2.0 code-executor system.
    
    Manages the file system abstraction, code execution, and context optimization
    to enable efficient tool usage via code execution.
    """

    def __init__(
        self,
        mcp_client: Any,
        sandbox_config: Optional[SandboxConfig] = None,
        max_output_tokens: int = 500,
    ):
        """Initialize MCP 2.0 orchestrator.
        
        Args:
            mcp_client: MCP client instance
            sandbox_config: Sandbox configuration (uses defaults if None)
            max_output_tokens: Maximum tokens to return to LLM
        """
        self.mcp_client = mcp_client
        self.sandbox_config = sandbox_config or SandboxConfig()
        self.context_optimizer = ContextOptimizer(max_output_tokens=max_output_tokens)
        
        # Initialize file system
        self.vfs = VirtualFileSystem("/tmp/mcp2_vfs")
        self.tool_fs = ToolFileSystem(self.vfs)
        
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self) -> str:
        """Create a new execution session.
        
        Returns:
            Session token
        """
        session_token = secrets.token_urlsafe(16)
        self._sessions[session_token] = {
            "created_at": asyncio.get_event_loop().time(),
            "executions": [],
        }
        logger.info("Created MCP 2.0 session: %s", session_token[:8])
        return session_token
    
    async def initialize_tools(self) -> None:
        """Initialize and register MCP tools in the file system."""
        if not self.mcp_client:
            logger.warning("MCP client not available, skipping tool initialization")
            return
        
        try:
            # Discover tools from MCP client
            tools = await self.mcp_client.list_tools()
            
            # Group tools by server
            servers: Dict[str, List[Dict[str, Any]]] = {}
            for tool in tools:
                # Extract server name from tool name (e.g., "google_drive__get_document")
                server_name = tool.get("server", "default")
                if "__" in tool.get("name", ""):
                    server_name = tool["name"].split("__")[0].replace("_", "-")
                
                if server_name not in servers:
                    servers[server_name] = []
                servers[server_name].append(tool)
            
            # Register each server
            for server_name, server_tools in servers.items():
                self.tool_fs.register_server(server_name, server_tools)
            
            logger.info(
                "Initialized %d MCP servers with %d total tools",
                len(servers),
                len(tools)
            )
            
        except Exception as exc:
            logger.error("Failed to initialize MCP tools: %s", exc, exc_info=True)
    
    async def execute_agent_code(
        self,
        code: str,
        session_token: str,
        language: str = "python",
    ) -> ExecutionResult:
        """Execute agent-generated code.
        
        Args:
            code: Code to execute
            session_token: Session token
            language: Programming language
            
        Returns:
            Execution result
        """
        # Create tool client for this session
        tool_client = MCPToolClient(self.mcp_client, session_token)
        
        # Create executor
        executor = CodeExecutor(
            sandbox_config=self.sandbox_config,
            mcp_tool_client=tool_client,
            session_token=session_token,
        )
        
        # Execute code
        result = await executor.execute(code, language=language)
        
        # Optimize output if needed
        if result.output and len(result.output) > self.context_optimizer.max_output_chars:
            original_size = len(result.output)
            result.output = self.context_optimizer.filter_large_output(
                result.output,
                strategy="summarize"
            )
            savings = self.context_optimizer.calculate_token_savings(
                original_size,
                len(result.output)
            )
            result.tokens_saved = savings["tokens_saved"]
            logger.info(
                "Optimized output: saved %d tokens (%.1f%%)",
                savings["tokens_saved"],
                savings["savings_percent"]
            )
        
        # Track execution
        if session_token in self._sessions:
            self._sessions[session_token]["executions"].append({
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "tokens_saved": result.tokens_saved,
            })
        
        return result
    
    def get_file_system_info(self) -> Dict[str, Any]:
        """Get information about the tool file system.
        
        Returns:
            Dictionary with server and tool information
        """
        servers = self.tool_fs.list_servers()
        server_info = {}
        
        for server in servers:
            tools = self.tool_fs.list_tools(server)
            server_info[server] = {
                "tool_count": len(tools),
                "tools": tools,
            }
        
        return {
            "servers": server_info,
            "total_servers": len(servers),
            "workspace_path": str(self.vfs.workspace_path),
        }
    
    def get_session_stats(self, session_token: str) -> Dict[str, Any]:
        """Get statistics for a session.
        
        Args:
            session_token: Session token
            
        Returns:
            Session statistics
        """
        if session_token not in self._sessions:
            return {"error": "Session not found"}
        
        session = self._sessions[session_token]
        executions = session["executions"]
        
        if not executions:
            return {
                "session_token": session_token[:8],
                "executions": 0,
            }
        
        total_tokens_saved = sum(e.get("tokens_saved", 0) for e in executions)
        avg_execution_time = sum(e.get("execution_time_ms", 0) for e in executions) / len(executions)
        success_count = sum(1 for e in executions if e.get("success", False))
        
        return {
            "session_token": session_token[:8],
            "executions": len(executions),
            "successful_executions": success_count,
            "total_tokens_saved": total_tokens_saved,
            "avg_execution_time_ms": round(avg_execution_time, 2),
        }
    
    def cleanup_session(self, session_token: str) -> None:
        """Clean up a session and its resources.
        
        Args:
            session_token: Session token
        """
        if session_token in self._sessions:
            del self._sessions[session_token]
            logger.info("Cleaned up session: %s", session_token[:8])

