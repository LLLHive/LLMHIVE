"""Edge case and fault injection tests for MCP 2.0 sandbox security.

These tests verify that the sandbox handles misuse, malicious code,
and extreme conditions safely.
"""
from __future__ import annotations

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from llmhive.app.mcp2.sandbox import CodeSandbox, SandboxConfig
from llmhive.app.mcp2.security import SecurityValidator, SecurityAuditor
from llmhive.app.mcp2.executor import CodeExecutor
from llmhive.app.mcp2.tool_abstraction import MCPToolClient


class TestSandboxEscapeAttempts:
    """Tests for sandbox escape attempts."""
    
    @pytest.mark.asyncio
    async def test_import_os_via_import(self):
        """Test that importing os via __import__ is blocked."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
import __builtins__
os = __import__('os')
print(os.system('echo hacked'))
"""
        result = await sandbox.execute_python(code)
        
        # Should fail with security error or import error
        assert result["status"] != "success"
        assert "os" in result.get("stderr", "").lower() or "security" in result.get("stderr", "").lower()
    
    @pytest.mark.asyncio
    async def test_access_builtins(self):
        """Test that accessing __builtins__ is restricted."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
import builtins
builtins.__import__('subprocess')
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
    
    @pytest.mark.asyncio
    async def test_read_etc_passwd(self):
        """Test that reading /etc/passwd is blocked."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
with open('/etc/passwd', 'r') as f:
    print(f.read())
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
        assert "permission" in result.get("stderr", "").lower() or "error" in result.get("stderr", "").lower()
    
    @pytest.mark.asyncio
    async def test_directory_traversal(self):
        """Test that directory traversal (../) is blocked."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
with open('../../secret.txt', 'r') as f:
    print(f.read())
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
    
    @pytest.mark.asyncio
    async def test_subprocess_spawn(self):
        """Test that subprocess spawning is blocked."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
import subprocess
subprocess.call(['rm', '-rf', '/'])
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
        assert "subprocess" in result.get("stderr", "").lower() or "security" in result.get("stderr", "").lower()
    
    @pytest.mark.asyncio
    async def test_eval_exec_usage(self):
        """Test that eval and exec are blocked."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
eval("__import__('os').system('echo hacked')")
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
    
    @pytest.mark.asyncio
    async def test_sneaky_import_attempts(self):
        """Test various sneaky import methods."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        # Try different import methods
        sneaky_imports = [
            "import os",
            "from os import system",
            "__import__('os')",
            "getattr(__builtins__, '__import__')('os')",
        ]
        
        for import_code in sneaky_imports:
            code = f"{import_code}\nprint('success')"
            result = await sandbox.execute_python(code)
            
            # All should fail
            assert result["status"] != "success", f"Import method {import_code} should be blocked"


class TestMaliciousCodeInjection:
    """Tests for malicious code injection attempts."""
    
    @pytest.mark.asyncio
    async def test_recover_builtins(self):
        """Test attempts to recover builtins."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
# Try to recover builtins
import types
builtins = types.__dict__['__builtins__']
os = builtins['__import__']('os')
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
    
    @pytest.mark.asyncio
    async def test_sys_module_access(self):
        """Test that sys module access is restricted."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
import sys
sys.exit(0)
"""
        result = await sandbox.execute_python(code)
        
        # Should either fail or sys should not be available
        assert "sys" in result.get("stderr", "").lower() or result["status"] != "success"
    
    @pytest.mark.asyncio
    async def test_file_system_manipulation(self):
        """Test file system manipulation attempts."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
import shutil
shutil.rmtree('/')
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"


class TestStressTests:
    """Stress tests for resource limits."""
    
    @pytest.mark.asyncio
    async def test_infinite_loop_timeout(self):
        """Test that infinite loops are terminated by timeout."""
        config = SandboxConfig(timeout_seconds=1.0)  # Short timeout
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
while True:
    pass
"""
        start_time = time.time()
        result = await sandbox.execute_python(code)
        execution_time = time.time() - start_time
        
        # Should timeout within reasonable time (timeout + overhead)
        assert execution_time < 3.0, "Execution should timeout quickly"
        assert result["status"] == "timeout" or "timeout" in result.get("error", "").lower()
    
    @pytest.mark.asyncio
    async def test_heavy_recursion(self):
        """Test that heavy recursion hits resource limits."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
def recurse(n):
    if n <= 0:
        return 0
    return recurse(n - 1) + recurse(n - 1)

recurse(1000)
"""
        result = await sandbox.execute_python(code)
        
        # Should timeout or hit recursion limit
        assert result["status"] != "success"
    
    @pytest.mark.asyncio
    async def test_memory_exhaustion(self):
        """Test that memory exhaustion is handled."""
        config = SandboxConfig(timeout_seconds=5.0, memory_limit_mb=10)  # Very small limit
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
# Try to allocate huge list
data = [0] * (10 * 1024 * 1024)  # 10MB
print(len(data))
"""
        result = await sandbox.execute_python(code)
        
        # Should fail with memory error or timeout
        assert result["status"] != "success"
        assert "memory" in result.get("stderr", "").lower() or result["status"] == "timeout"
    
    @pytest.mark.asyncio
    async def test_cpu_intensive_task(self):
        """Test that CPU-intensive tasks are limited."""
        config = SandboxConfig(timeout_seconds=1.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
# CPU-intensive computation
total = 0
for i in range(10000000):
    total += i * i
print(total)
"""
        start_time = time.time()
        result = await sandbox.execute_python(code)
        execution_time = time.time() - start_time
        
        # Should timeout before completing
        assert execution_time < 2.0
        assert result["status"] == "timeout" or "timeout" in result.get("error", "").lower()


class TestConcurrentExecution:
    """Tests for concurrent execution isolation."""
    
    @pytest.mark.asyncio
    async def test_parallel_sandbox_isolation(self):
        """Test that parallel sandboxes are isolated."""
        config = SandboxConfig(timeout_seconds=5.0)
        
        async def run_in_sandbox(session_id, filename):
            sandbox = CodeSandbox(config, f"session-{session_id}")
            code = f"""
with open('{filename}', 'w') as f:
    f.write('session-{session_id}')
"""
            result = await sandbox.execute_python(code)
            sandbox.cleanup()
            return result, session_id
        
        # Run multiple sandboxes in parallel
        tasks = [
            run_in_sandbox(i, f"file_{i}.txt")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for result, session_id in results:
            assert result["status"] == "success", f"Session {session_id} should succeed"
    
    @pytest.mark.asyncio
    async def test_state_isolation(self):
        """Test that state doesn't leak between executions."""
        config = SandboxConfig(timeout_seconds=5.0)
        
        # First execution sets a variable
        sandbox1 = CodeSandbox(config, "session-1")
        code1 = """
x = "secret_value"
with open('state.txt', 'w') as f:
    f.write(x)
"""
        result1 = await sandbox1.execute_python(code1)
        sandbox1.cleanup()
        
        # Second execution should not see it
        sandbox2 = CodeSandbox(config, "session-2")
        code2 = """
try:
    with open('state.txt', 'r') as f:
        content = f.read()
    print(f"Found: {content}")
except FileNotFoundError:
    print("File not found (good - isolated)")
"""
        result2 = await sandbox2.execute_python(code2)
        sandbox2.cleanup()
        
        assert result1["status"] == "success"
        assert result2["status"] == "success"
        # Second execution should not find the file
        assert "not found" in result2["stdout"].lower() or "isolated" in result2["stdout"].lower()


class TestMultiToolWorkflow:
    """Tests for multi-tool integration workflows."""
    
    @pytest.mark.asyncio
    async def test_tool_chain_isolation(self):
        """Test that tool chains maintain proper isolation."""
        config = SandboxConfig(timeout_seconds=5.0)
        mcp_client = Mock()
        tool_client = MCPToolClient(mcp_client, "test-session")
        
        executor = CodeExecutor(config, tool_client, "test-session")
        
        # Simulate a multi-tool workflow
        code = """
# Step 1: Fetch data (simulated)
data = {"items": [1, 2, 3, 4, 5]}

# Step 2: Process in sandbox
summary = f"Found {len(data['items'])} items"

# Step 3: Return concise result
print(summary)
"""
        result = await executor.execute(code, language="python")
        
        assert result.success
        assert "5 items" in result.output or "Found" in result.output


class TestErrorHandling:
    """Tests for error handling and reporting."""
    
    @pytest.mark.asyncio
    async def test_syntax_error_handling(self):
        """Test that syntax errors are caught and reported cleanly."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
def broken_function(
    # Missing closing parenthesis
print("test")
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
        # Error should be user-friendly, no internal paths
        assert "/tmp" not in result.get("stderr", "")
        assert "SyntaxError" in result.get("stderr", "") or "syntax" in result.get("stderr", "").lower()
    
    @pytest.mark.asyncio
    async def test_runtime_exception_handling(self):
        """Test that runtime exceptions are handled cleanly."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
# NameError
print(undefined_variable)
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
        # Should contain error message but not full stack trace with paths
        stderr = result.get("stderr", "")
        assert "NameError" in stderr or "name" in stderr.lower()
        # Should not expose internal file paths
        assert "/tmp/mcp2" not in stderr
    
    @pytest.mark.asyncio
    async def test_file_not_found_handling(self):
        """Test that file not found errors are handled."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
with open('nonexistent.txt', 'r') as f:
    content = f.read()
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
        assert "FileNotFoundError" in result.get("stderr", "") or "not found" in result.get("stderr", "").lower()
    
    @pytest.mark.asyncio
    async def test_clean_error_messages(self):
        """Test that error messages don't leak internal details."""
        config = SandboxConfig(timeout_seconds=2.0)
        sandbox = CodeSandbox(config, "test-session")
        
        code = """
raise ValueError("User-facing error")
"""
        result = await sandbox.execute_python(code)
        
        assert result["status"] != "success"
        stderr = result.get("stderr", "")
        # Should contain the error message
        assert "ValueError" in stderr or "User-facing error" in stderr
        # Should not contain internal Python paths
        assert "site-packages" not in stderr
        assert "/usr/lib" not in stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

