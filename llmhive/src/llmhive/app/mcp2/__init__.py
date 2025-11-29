"""MCP 2.0 Code-Executor System.

This module implements a production-grade Model Context Protocol 2.0 architecture
that uses code execution instead of direct tool calls, dramatically reducing token
usage while maintaining security and performance.
"""

from .filesystem import VirtualFileSystem, ToolFileSystem
from .sandbox import CodeSandbox, SandboxConfig
from .executor import CodeExecutor, ExecutionResult
from .context_optimizer import ContextOptimizer
from .tool_abstraction import ToolStubGenerator, MCPToolClient

__all__ = [
    "VirtualFileSystem",
    "ToolFileSystem",
    "CodeSandbox",
    "SandboxConfig",
    "CodeExecutor",
    "ExecutionResult",
    "ContextOptimizer",
    "ToolStubGenerator",
    "MCPToolClient",
]

