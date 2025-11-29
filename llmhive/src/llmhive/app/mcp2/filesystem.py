"""Virtual file system for MCP tool abstraction.

This module implements a file-system-based interface for MCP tools, allowing
the AI agent to discover and use tools by reading files instead of loading
all tool definitions into context.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VirtualFileSystem:
    """Emulated file system for sandboxed code execution.
    
    Provides a secure, isolated file system that the agent's code can access.
    Includes a workspace/ directory for temporary files and state persistence.
    """

    def __init__(self, root_path: str | Path, workspace_name: str = "workspace"):
        """Initialize virtual file system.
        
        Args:
            root_path: Root directory for the virtual file system
            workspace_name: Name of the workspace subdirectory
        """
        self.root_path = Path(root_path)
        self.workspace_path = self.root_path / workspace_name
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    def read_file(self, path: str) -> str:
        """Read a file from the virtual file system.
        
        Args:
            path: File path relative to root
            
        Returns:
            File contents as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If path is outside sandbox
        """
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return file_path.read_text(encoding="utf-8")
    
    def write_file(self, path: str, content: str) -> None:
        """Write a file to the virtual file system.
        
        Args:
            path: File path relative to root
            content: Content to write
            
        Raises:
            PermissionError: If path is outside sandbox
        """
        file_path = self._resolve_path(path)
        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    
    def list_directory(self, path: str = ".") -> List[str]:
        """List files and directories in a path.
        
        Args:
            path: Directory path relative to root
            
        Returns:
            List of file and directory names
        """
        dir_path = self._resolve_path(path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return [item.name for item in dir_path.iterdir()]
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists.
        
        Args:
            path: File path relative to root
            
        Returns:
            True if file exists, False otherwise
        """
        file_path = self._resolve_path(path)
        return file_path.exists()
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path to an absolute path within the sandbox.
        
        Args:
            path: Relative path
            
        Returns:
            Absolute path
            
        Raises:
            PermissionError: If path escapes the sandbox
        """
        # Normalize path
        normalized = Path(path).resolve()
        
        # If absolute, check it's within root
        if normalized.is_absolute():
            try:
                normalized.relative_to(self.root_path.resolve())
            except ValueError:
                raise PermissionError(f"Path outside sandbox: {path}")
            return normalized
        
        # Resolve relative to root
        resolved = (self.root_path / normalized).resolve()
        
        # Ensure it's within root
        try:
            resolved.relative_to(self.root_path.resolve())
        except ValueError:
            raise PermissionError(f"Path outside sandbox: {path}")
        
        return resolved


class ToolFileSystem:
    """File system abstraction for MCP tools.
    
    Represents MCP servers as directories and tools as files, allowing
    the agent to discover tools by browsing the file system.
    """

    def __init__(self, vfs: VirtualFileSystem, servers_path: str = "servers"):
        """Initialize tool file system.
        
        Args:
            vfs: Virtual file system instance
            servers_path: Path to servers directory
        """
        self.vfs = vfs
        self.servers_path = servers_path
        self._servers: Dict[str, Dict[str, Any]] = {}
    
    def register_server(self, server_name: str, tools: List[Dict[str, Any]]) -> None:
        """Register an MCP server and its tools.
        
        Args:
            server_name: Name of the MCP server (e.g., "google-drive")
            tools: List of tool definitions with name, description, inputSchema
        """
        server_dir = f"{self.servers_path}/{server_name}"
        
        # Create server directory structure
        self.vfs.write_file(f"{server_dir}/.server.json", json.dumps({
            "name": server_name,
            "tools": [tool["name"] for tool in tools]
        }, indent=2))
        
        # Create tool files
        for tool in tools:
            tool_file = f"{server_dir}/{tool['name']}.ts"
            stub_code = self._generate_tool_stub(tool)
            self.vfs.write_file(tool_file, stub_code)
        
        self._servers[server_name] = {"tools": tools}
        logger.info("Registered MCP server '%s' with %d tools", server_name, len(tools))
    
    def list_servers(self) -> List[str]:
        """List available MCP servers.
        
        Returns:
            List of server names
        """
        try:
            return self.vfs.list_directory(self.servers_path)
        except (FileNotFoundError, NotADirectoryError):
            return []
    
    def list_tools(self, server_name: str) -> List[str]:
        """List tools for a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of tool names (file names without extension)
        """
        server_dir = f"{self.servers_path}/{server_name}"
        try:
            files = self.vfs.list_directory(server_dir)
            return [f.replace(".ts", "") for f in files if f.endswith(".ts")]
        except (FileNotFoundError, NotADirectoryError):
            return []
    
    def get_tool_code(self, server_name: str, tool_name: str) -> str:
        """Get the code for a specific tool.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool
            
        Returns:
            Tool stub code as string
        """
        tool_file = f"{self.servers_path}/{server_name}/{tool_name}.ts"
        return self.vfs.read_file(tool_file)
    
    def _generate_tool_stub(self, tool: Dict[str, Any]) -> str:
        """Generate TypeScript stub code for a tool.
        
        Args:
            tool: Tool definition with name, description, inputSchema
            
        Returns:
            TypeScript code string
        """
        tool_name = tool["name"]
        description = tool.get("description", "")
        input_schema = tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        
        # Generate TypeScript interface for inputs
        param_types = []
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "any")
            if prop_type == "string":
                ts_type = "string"
            elif prop_type == "number":
                ts_type = "number"
            elif prop_type == "boolean":
                ts_type = "boolean"
            elif prop_type == "array":
                ts_type = "any[]"
            elif prop_type == "object":
                ts_type = "Record<string, any>"
            else:
                ts_type = "any"
            
            optional = "" if prop_name in input_schema.get("required", []) else "?"
            param_types.append(f"  {prop_name}{optional}: {ts_type}")
        
        params_interface = "{\n" + ",\n".join(param_types) + "\n}"
        
        # Generate function stub
        stub = f"""/**
 * {description}
 * 
 * Tool: {tool_name}
 * Server: MCP Server
 * 
 * @param params - Tool parameters
 * @returns Tool execution result
 */
export async function {tool_name}(params: {params_interface}): Promise<any> {{
  // Call the MCP tool via the executor
  return await callMCPTool('{tool_name}', params);
}}
"""
        return stub

