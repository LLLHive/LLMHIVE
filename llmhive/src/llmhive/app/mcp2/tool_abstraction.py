"""MCP tool abstraction and client.

This module provides the interface between the agent's code and actual MCP tools,
handling authentication and credential security.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MCPToolClient:
    """Client for calling MCP tools with credential security.
    
    Handles authentication internally, ensuring the agent's code never sees
    raw credentials or sensitive data.
    """

    def __init__(self, mcp_client: Any, session_token: str):
        """Initialize MCP tool client.
        
        Args:
            mcp_client: Underlying MCP client instance
            session_token: Session token for scoping tool access
        """
        self.mcp_client = mcp_client
        self.session_token = session_token
        self._sanitize_patterns = [
            r'password["\']?\s*[:=]\s*["\']?[^"\']+',
            r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\']+',
            r'token["\']?\s*[:=]\s*["\']?[^"\']+',
        ]
    
    async def call_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool with sanitized output.
        
        Args:
            tool_name: Name of the tool to call
            params: Tool parameters
            
        Returns:
            Tool result with sensitive data sanitized
        """
        try:
            # Call the actual MCP tool
            if self.mcp_client:
                result = await self.mcp_client.call_tool(tool_name, params)
            else:
                # Fallback for testing
                result = {"status": "success", "data": "Tool called successfully"}
            
            # Sanitize sensitive data in response
            sanitized = self._sanitize_output(result)
            
            logger.debug(
                "MCP tool called: %s (session: %s)",
                tool_name,
                self.session_token[:8]
            )
            
            return sanitized
            
        except Exception as exc:
            logger.error("Error calling MCP tool %s: %s", tool_name, exc)
            return {
                "status": "error",
                "error": str(exc),
                "tool": tool_name
            }
    
    def _sanitize_output(self, data: Any) -> Any:
        """Sanitize sensitive data in tool output.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data
        """
        import re
        
        if isinstance(data, str):
            # Replace sensitive patterns with [REDACTED]
            sanitized = data
            for pattern in self._sanitize_patterns:
                sanitized = re.sub(pattern, r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
            return sanitized
        elif isinstance(data, dict):
            return {k: self._sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_output(item) for item in data]
        else:
            return data


class ToolStubGenerator:
    """Generates tool stub code for the file system.
    
    Creates TypeScript/Python stubs that the agent can use to call MCP tools.
    """

    @staticmethod
    def generate_typescript_stub(tool: Dict[str, Any]) -> str:
        """Generate TypeScript stub for a tool.
        
        Args:
            tool: Tool definition
            
        Returns:
            TypeScript code string
        """
        tool_name = tool["name"]
        description = tool.get("description", "")
        input_schema = tool.get("inputSchema", {})
        
        # Generate parameter types
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        param_defs = []
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "any")
            ts_type = ToolStubGenerator._map_type_to_ts(prop_type)
            optional = "" if prop_name in required else "?"
            param_defs.append(f"  {prop_name}{optional}: {ts_type}")
        
        params_type = "{\n" + ",\n".join(param_defs) + "\n}"
        
        stub = f"""/**
 * {description}
 */
export async function {tool_name}(params: {params_type}): Promise<any> {{
  return await callMCPTool('{tool_name}', params);
}}
"""
        return stub
    
    @staticmethod
    def generate_python_stub(tool: Dict[str, Any]) -> str:
        """Generate Python stub for a tool.
        
        Args:
            tool: Tool definition
            
        Returns:
            Python code string
        """
        tool_name = tool["name"]
        description = tool.get("description", "")
        input_schema = tool.get("inputSchema", {})
        
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        # Generate function signature
        params = []
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "any")
            py_type = ToolStubGenerator._map_type_to_py(prop_type)
            default = "None" if prop_name not in required else ""
            params.append(f"{prop_name}: {py_type}{' = ' + default if default else ''}")
        
        params_str = ", ".join(params) if params else ""
        
        stub = f'''"""
{description}
"""
async def {tool_name}({params_str}) -> Any:
    """Call MCP tool {tool_name}."""
    return await call_mcp_tool("{tool_name}", {{
        {", ".join([f'"{k}": {k}' for k in properties.keys()]) if properties else ""}
    }})
'''
        return stub
    
    @staticmethod
    def _map_type_to_ts(python_type: str) -> str:
        """Map Python/JSON type to TypeScript type."""
        mapping = {
            "string": "string",
            "number": "number",
            "integer": "number",
            "boolean": "boolean",
            "array": "any[]",
            "object": "Record<string, any>",
        }
        return mapping.get(python_type, "any")
    
    @staticmethod
    def _map_type_to_py(json_type: str) -> str:
        """Map JSON type to Python type hint."""
        mapping = {
            "string": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return mapping.get(json_type, "Any")

