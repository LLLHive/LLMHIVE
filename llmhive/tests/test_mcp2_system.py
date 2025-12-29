"""Tests for MCP 2.0 Code-Executor System."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from llmhive.app.mcp2.filesystem import VirtualFileSystem, ToolFileSystem
from llmhive.app.mcp2.sandbox import CodeSandbox, SandboxConfig
from llmhive.app.mcp2.executor import CodeExecutor, ExecutionResult
from llmhive.app.mcp2.context_optimizer import ContextOptimizer
from llmhive.app.mcp2.tool_abstraction import MCPToolClient
from llmhive.app.mcp2.security import SecurityValidator, SecurityAuditor
from llmhive.app.mcp2.monitoring import MCP2Monitor


class TestVirtualFileSystem:
    """Tests for virtual file system."""
    
    def test_read_write_file(self, tmp_path):
        """Test reading and writing files."""
        vfs = VirtualFileSystem(tmp_path)
        
        vfs.write_file("test.txt", "Hello, World!")
        content = vfs.read_file("test.txt")
        
        assert content == "Hello, World!"
    
    def test_list_directory(self, tmp_path):
        """Test listing directory contents."""
        vfs = VirtualFileSystem(tmp_path)
        
        vfs.write_file("file1.txt", "content1")
        vfs.write_file("file2.txt", "content2")
        
        files = vfs.list_directory(".")
        assert "file1.txt" in files
        assert "file2.txt" in files
    
    def test_path_traversal_protection(self, tmp_path):
        """Test that path traversal is blocked."""
        vfs = VirtualFileSystem(tmp_path)
        
        with pytest.raises(PermissionError):
            vfs.read_file("../../../etc/passwd")


class TestToolFileSystem:
    """Tests for tool file system."""
    
    def test_register_server(self, tmp_path):
        """Test registering an MCP server."""
        vfs = VirtualFileSystem(tmp_path)
        tool_fs = ToolFileSystem(vfs)
        
        tools = [
            {
                "name": "getDocument",
                "description": "Get a document",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "documentId": {"type": "string"}
                    },
                    "required": ["documentId"]
                }
            }
        ]
        
        tool_fs.register_server("google-drive", tools)
        
        servers = tool_fs.list_servers()
        assert "google-drive" in servers
        
        server_tools = tool_fs.list_tools("google-drive")
        assert "getDocument" in server_tools
    
    def test_get_tool_code(self, tmp_path):
        """Test retrieving tool code."""
        vfs = VirtualFileSystem(tmp_path)
        tool_fs = ToolFileSystem(vfs)
        
        tools = [
            {
                "name": "getDocument",
                "description": "Get a document",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "documentId": {"type": "string"}
                    }
                }
            }
        ]
        
        tool_fs.register_server("google-drive", tools)
        code = tool_fs.get_tool_code("google-drive", "getDocument")
        
        assert "getDocument" in code
        assert "callMCPTool" in code


class TestContextOptimizer:
    """Tests for context optimizer."""
    
    def test_filter_large_output(self):
        """Test filtering large output."""
        optimizer = ContextOptimizer(max_output_tokens=100)
        
        large_data = {"items": [f"item_{i}" for i in range(1000)]}
        filtered = optimizer.filter_large_output(large_data, strategy="summarize")
        
        assert len(filtered) < len(str(large_data))
        # The data is a dict with 1 key containing a list
        assert "Dictionary with 1 keys" in filtered or "items" in filtered
    
    def test_calculate_token_savings(self):
        """Test token savings calculation."""
        optimizer = ContextOptimizer()
        
        original_size = 10000
        filtered_size = 500
        
        savings = optimizer.calculate_token_savings(original_size, filtered_size)
        
        assert savings["tokens_saved"] > 0
        assert savings["savings_percent"] > 90


class TestSecurityValidator:
    """Tests for security validator."""
    
    def test_validate_code_safe(self):
        """Test validation of safe code."""
        validator = SecurityValidator()
        
        safe_code = """
result = callMCPTool('getDocument', {'documentId': '123'})
print(result)
"""
        is_safe, violations = validator.validate_code(safe_code)
        
        assert is_safe
        assert len(violations) == 0
    
    def test_validate_code_dangerous(self):
        """Test validation of dangerous code."""
        validator = SecurityValidator()
        
        dangerous_code = "import subprocess; subprocess.call(['rm', '-rf', '/'])"
        is_safe, violations = validator.validate_code(dangerous_code)
        
        assert not is_safe
        assert len(violations) > 0
    
    def test_sanitize_path(self):
        """Test path sanitization removes directory traversal."""
        validator = SecurityValidator()
        
        dangerous_path = "../../../etc/passwd"
        sanitized = validator.sanitize_path(dangerous_path)
        
        # Should remove path traversal sequences
        assert "../" not in sanitized
        # The remaining path after removing traversal is "etc/passwd"
        assert sanitized == "etc/passwd"


class TestMCP2Monitor:
    """Tests for monitoring system."""
    
    def test_log_execution(self):
        """Test logging an execution."""
        monitor = MCP2Monitor()
        
        result = Mock()
        result.success = True
        result.tools_called = ["getDocument"]
        result.error = None
        
        monitor.log_execution(
            session_token="test-session",
            execution_id="exec-1",
            code="test code",
            language="python",
            result=result,
            execution_time_ms=100.0,
            tokens_saved=500,
        )
        
        assert monitor.metrics["total_executions"] == 1
        assert monitor.metrics["total_tokens_saved"] == 500
    
    def test_get_metrics(self):
        """Test getting metrics."""
        monitor = MCP2Monitor()
        
        result = Mock()
        result.success = True
        result.tools_called = []
        result.error = None
        
        monitor.log_execution(
            session_token="test",
            execution_id="exec-1",
            code="code",
            language="python",
            result=result,
            execution_time_ms=100.0,
            tokens_saved=100,
        )
        
        metrics = monitor.get_metrics()
        assert metrics["total_executions"] == 1
        assert metrics["success_rate"] == 1.0


@pytest.mark.asyncio
class TestCodeExecutor:
    """Tests for code executor."""
    
    async def test_execute_python_success(self):
        """Test successful Python execution."""
        config = SandboxConfig(timeout_seconds=5.0)
        mcp_client = Mock()
        tool_client = MCPToolClient(mcp_client, "test-session")
        
        executor = CodeExecutor(config, tool_client, "test-session")
        
        code = """
result = 2 + 2
print(result)
"""
        result = await executor.execute(code, language="python")
        
        assert result.success
        assert "4" in result.output
    
    async def test_execute_python_with_tool_call(self):
        """Test Python execution with tool call."""
        config = SandboxConfig(timeout_seconds=5.0)
        mcp_client = AsyncMock()
        mcp_client.call_tool = AsyncMock(return_value={"status": "success", "data": "test"})
        
        tool_client = MCPToolClient(mcp_client, "test-session")
        
        executor = CodeExecutor(config, tool_client, "test-session")
        
        # Note: Actual tool calling in sandbox requires more setup
        # This is a simplified test
        code = "print('Hello')"
        result = await executor.execute(code, language="python")
        
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

