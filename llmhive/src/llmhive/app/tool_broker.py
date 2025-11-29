"""Tool Broker: Centralized tool execution interface for LLMHive.

This module provides a simple interface for executing tools like web search
and safe Python code execution. It wraps existing services and provides
error handling and security boundaries.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .guardrails import ExecutionSandbox
from .services.web_research import WebResearchClient, WebDocument

logger = logging.getLogger(__name__)


class ToolBroker:
    """Centralized broker for tool execution with error handling and security."""

    def __init__(
        self,
        web_research: Optional[WebResearchClient] = None,
        enable_sandbox: bool = True,
    ) -> None:
        """
        Initialize the ToolBroker.
        
        Args:
            web_research: Optional WebResearchClient instance. If None, creates a new one.
            enable_sandbox: Whether to enable sandbox for Python execution (default: True)
        """
        # Initialize web research client
        if web_research is None:
            from .config import settings
            self.web_research = WebResearchClient(
                timeout=getattr(settings, "web_search_timeout", 8.0)
            )
        else:
            self.web_research = web_research
        
        # Initialize execution sandbox for safe Python execution
        self.sandbox: Optional[ExecutionSandbox] = (
            ExecutionSandbox() if enable_sandbox else None
        )
        
        # Initialize available tools
        self.tools: Dict[str, Callable[..., Any]] = {
            "web_search": self._web_search_tool,
            "python_exec": self._python_exec_tool,
        }

    async def _web_search_tool(self, query: str) -> list[Dict[str, str]]:
        """
        Web search tool: Wraps self.web_research.search.
        
        Args:
            query: Search query string
            
        Returns:
            List of dictionaries with 'title', 'url', and 'snippet' keys
        """
        try:
            results = await self.web_research.search(query)
            # Convert WebDocument objects to dictionaries
            return [
                {
                    "title": doc.title,
                    "url": doc.url,
                    "snippet": doc.snippet,
                }
                for doc in results
            ]
        except Exception as e:
            logger.error("Web search tool failed: %s", e)
            return [{"error": str(e)}]

    def _python_exec_tool(self, code: str) -> str:
        """
        Safe Python execution tool: Executes Python code in a sandbox.
        
        Args:
            code: Python code to execute
            
        Returns:
            String result of execution (stdout or error message)
        """
        if not self.sandbox:
            return "Python execution disabled: sandbox not available"
        
        try:
            output, success, error = self.sandbox.execute_python(code)
            if success:
                return output if output else "Execution completed successfully (no output)"
            else:
                error_msg = error if error else "Execution failed"
                return f"Execution error: {error_msg}"
        except Exception as e:
            logger.error("Python execution tool failed: %s", e)
            return str(e)

    def use_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """
        Execute a tool by name (synchronous interface).
        
        Note: For async tools like web_search, use use_tool_async() instead.
        
        Args:
            tool_name: Name of the tool to execute
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Tool execution result (type depends on tool)
            
        Raises:
            ValueError: If tool_name is not available
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not available")
        
        try:
            tool_func = self.tools[tool_name]
            import inspect
            
            # Check if the tool function is async
            if inspect.iscoroutinefunction(tool_func):
                # For async tools, raise an error suggesting use_tool_async
                raise ValueError(
                    f"Tool {tool_name} is async. Use use_tool_async() instead, "
                    "or await the result in an async context."
                )
            else:
                # Synchronous tool
                return tool_func(*args, **kwargs)
        except ValueError:
            # Re-raise ValueError (tool not found or async tool)
            raise
        except Exception as e:
            logger.error("Tool execution failed for %s: %s", tool_name, e)
            return str(e)

    async def use_tool_async(self, tool_name: str, *args, **kwargs) -> Any:
        """
        Async version of use_tool for use in async contexts.
        
        Args:
            tool_name: Name of the tool to execute
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Tool execution result (type depends on tool)
            
        Raises:
            ValueError: If tool_name is not available
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not available")
        
        try:
            tool_func = self.tools[tool_name]
            import inspect
            
            # Check if the tool function is async
            if inspect.iscoroutinefunction(tool_func):
                return await tool_func(*args, **kwargs)
            else:
                # Synchronous tool, run in executor if needed
                return tool_func(*args, **kwargs)
        except Exception as e:
            logger.error("Tool execution failed for %s: %s", tool_name, e)
            return str(e)

    def register_tool(self, name: str, tool_func: Callable[..., Any]) -> None:
        """
        Register a new tool.
        
        Args:
            name: Name of the tool
            tool_func: Function to execute for this tool
        """
        self.tools[name] = tool_func
        logger.info("Registered tool: %s", name)

    def list_tools(self) -> list[str]:
        """
        List all available tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())

