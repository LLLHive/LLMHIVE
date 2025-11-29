"""Secure code execution sandbox for MCP 2.0.

This module implements a secure sandbox environment for executing agent-generated
code with strong isolation, resource limits, and security controls.
"""
from __future__ import annotations

import ast
import asyncio
import logging
import os
import resource
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for code execution sandbox."""
    
    timeout_seconds: float = 5.0
    memory_limit_mb: int = 512
    cpu_limit_percent: float = 50.0
    allow_network: bool = False
    allowed_hosts: List[str] = None  # type: ignore
    allowed_modules: List[str] = None  # type: ignore
    workspace_size_mb: int = 100
    max_file_size_mb: int = 10
    
    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = []
        if self.allowed_modules is None:
            # Default allowed modules for safe execution
            self.allowed_modules = [
                "json",
                "os",
                "pathlib",
                "datetime",
                "collections",
                "itertools",
                "functools",
                "operator",
            ]


class CodeSandbox:
    """Secure sandbox for executing agent-generated code.
    
    Provides isolation, resource limits, and security controls to safely
    execute untrusted code from the AI agent.
    """

    def __init__(self, config: SandboxConfig, session_token: str):
        """Initialize code sandbox.
        
        Args:
            config: Sandbox configuration
            session_token: Session token for scoping
        """
        self.config = config
        self.session_token = session_token
        self.workspace_path: Optional[Path] = None
        self._setup_workspace()
    
    def _setup_workspace(self) -> None:
        """Set up isolated workspace directory."""
        temp_dir = tempfile.gettempdir()
        workspace_name = f"mcp2_sandbox_{self.session_token[:8]}"
        self.workspace_path = Path(temp_dir) / workspace_name
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Set workspace permissions (read/write for owner only)
        os.chmod(self.workspace_path, 0o700)
    
    def _validate_code_ast(self, code: str) -> Dict[str, Any]:
        """Validate code using AST analysis before execution.
        
        Args:
            code: Code to validate
            
        Returns:
            Dictionary with 'safe' boolean and 'reason' string
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Syntax errors are handled by Python interpreter
            return {"safe": True, "reason": ""}
        
        # Unsafe patterns to detect
        unsafe_patterns = []
        
        class UnsafePatternVisitor(ast.NodeVisitor):
            def __init__(self):
                self.unsafe = []
            
            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name in ["os", "subprocess", "sys", "shutil", "socket", "urllib", "requests"]:
                        self.unsafe.append(f"Import of restricted module: {alias.name}")
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module in ["os", "subprocess", "sys", "shutil"]:
                    self.unsafe.append(f"Import from restricted module: {node.module}")
                self.generic_visit(node)
            
            def visit_Call(self, node):
                # Check for eval, exec, __import__
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec", "__import__"]:
                        self.unsafe.append(f"Unsafe function call: {node.func.id}")
                # Check for os.system, subprocess calls
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ["os", "subprocess"]:
                            self.unsafe.append(f"Unsafe method call: {node.func.attr}")
                self.generic_visit(node)
            
            def visit_Attribute(self, node):
                # Check for __dict__, __class__, __builtins__ access
                if isinstance(node.attr, str) and node.attr.startswith("__"):
                    if node.attr in ["__dict__", "__class__", "__builtins__", "__import__"]:
                        self.unsafe.append(f"Unsafe attribute access: {node.attr}")
                self.generic_visit(node)
        
        visitor = UnsafePatternVisitor()
        visitor.visit(tree)
        
        if visitor.unsafe:
            return {
                "safe": False,
                "reason": "; ".join(visitor.unsafe)
            }
        
        return {"safe": True, "reason": ""}
    
    async def execute_python(
        self, code: str, context: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Execute Python code in the sandbox.
        
        Args:
            code: Python code to execute
            context: Additional context variables to inject
            
        Returns:
            Execution result with output, errors, and metadata
        """
        # Security: Pre-execution AST analysis
        ast_validation_result = self._validate_code_ast(code)
        if not ast_validation_result["safe"]:
            return {
                "status": "error",
                "error": f"Security violation: {ast_validation_result['reason']}",
                "stdout": "",
                "stderr": ast_validation_result["reason"],
            }
        
        # Create isolated execution script
        script_path = self.workspace_path / "execute.py"
        
        # Wrap code with safety checks
        wrapped_code = self._wrap_code(code, context)
        script_path.write_text(wrapped_code, encoding="utf-8")
        
        # Security: Set OS resource limits
        try:
            # CPU time limit (in seconds)
            cpu_limit = int(self.config.timeout_seconds) + 1  # Slightly more than timeout
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
            # Memory limit (address space in bytes)
            memory_bytes = self.config.memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        except (ValueError, OSError) as exc:
            logger.warning("Failed to set resource limits: %s", exc)
        
        try:
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                "python3",
                "-u",  # Unbuffered output
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
                env=self._get_safe_env(),
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "status": "timeout",
                    "error": f"Execution exceeded timeout of {self.config.timeout_seconds}s",
                    "stdout": "",
                    "stderr": "",
                }
            
            return_code = process.returncode
            
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            
            return {
                "status": "success" if return_code == 0 else "error",
                "stdout": stdout_text,
                "stderr": stderr_text,
                "return_code": return_code,
            }
            
        except Exception as exc:
            logger.error("Sandbox execution error: %s", exc, exc_info=True)
            return {
                "status": "error",
                "error": str(exc),
                "stdout": "",
                "stderr": "",
            }
        finally:
            # Cleanup script
            if script_path.exists():
                script_path.unlink()
    
    async def execute_typescript(
        self, code: str, context: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Execute TypeScript code in the sandbox.
        
        Args:
            code: TypeScript code to execute
            context: Additional context variables to inject
            
        Returns:
            Execution result
        """
        # For TypeScript, we'd need to compile first
        # For now, return a placeholder indicating TS support needs Node.js setup
        return {
            "status": "error",
            "error": "TypeScript execution requires Node.js setup. Use Python for now.",
        }
    
    def _wrap_code(self, code: str, context: Dict[str, Any] | None = None) -> str:
        """Wrap code with safety checks and context injection.
        
        Args:
            code: Original code
            context: Context variables to inject
            
        Returns:
            Wrapped code with safety checks
        """
        # Import restrictions
        restricted_imports = [
            "subprocess",
            "sys",
            "os.system",
            "eval",
            "exec",
            "__import__",
        ]
        
        # Check for restricted imports
        for restricted in restricted_imports:
            if restricted in code:
                code = f"# Security: Restricted import '{restricted}' detected\n# {code}"
        
        # Inject context
        context_code = ""
        if context:
            for key, value in context.items():
                if isinstance(value, str):
                    context_code += f'{key} = "{value}"\n'
                elif isinstance(value, (int, float, bool)):
                    context_code += f"{key} = {value}\n"
                else:
                    context_code += f"{key} = {repr(value)}\n"
        
        # Remove restricted modules from sys.modules
        restricted_modules = [
            "os", "subprocess", "sys", "shutil", "socket",
            "urllib", "requests", "http", "ftplib", "telnetlib",
        ]
        restricted_modules_str = ", ".join([f'"{m}"' for m in restricted_modules])
        
        wrapped = f"""# Sandboxed execution environment
import json
from pathlib import Path

# Security: Remove dangerous modules
import sys
_restricted_modules = [{restricted_modules_str}]
for mod in _restricted_modules:
    if mod in sys.modules:
        del sys.modules[mod]

# Security: Restrict builtins
_original_builtins = __builtins__
_safe_builtins = {{}}
_allowed_builtins = ['print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed', 'min', 'max', 'sum', 'abs', 'round', 'divmod', 'pow', 'all', 'any', 'isinstance', 'type', 'hasattr', 'getattr', 'setattr', 'delattr', 'callable', 'iter', 'next', 'open']
for name in _allowed_builtins:
    if hasattr(_original_builtins, name):
        _safe_builtins[name] = getattr(_original_builtins, name)
__builtins__ = type(__builtins__)(_safe_builtins)

# Security: Override open() to restrict file access
_original_open = open
def open(file, mode='r', *args, **kwargs):
    '''Restricted open() that only allows workspace access.'''
    from pathlib import Path
    file_path = Path(file).resolve()
    workspace = Path("{self.workspace_path}").resolve()
    try:
        file_path.relative_to(workspace)
    except ValueError:
        raise PermissionError(f"File access outside workspace denied: {{file}}")
    return _original_open(file, mode, *args, **kwargs)

# Workspace path
WORKSPACE = Path("{self.workspace_path}")

# Context variables
{context_code}

# User code
try:
{self._indent_code(code)}
except Exception as e:
    # Clean error reporting (no internal paths)
    error_msg = str(e)
    # Remove file paths from error messages
    import re
    error_msg = re.sub(r'/tmp/[^\\s]+', '[sandbox]', error_msg)
    error_msg = re.sub(r'File "[^"]+", line', 'Line', error_msg)
    print(f"Error: {{error_msg}}", file=sys.stderr)
    sys.exit(1)
"""
        return wrapped
    
    def _indent_code(self, code: str) -> str:
        """Indent code for inclusion in wrapper."""
        lines = code.split("\n")
        return "\n".join(f"    {line}" if line.strip() else line for line in lines)
    
    def _get_safe_env(self) -> Dict[str, str]:
        """Get safe environment variables for execution."""
        env = os.environ.copy()
        
        # Remove dangerous environment variables
        dangerous_vars = [
            "PATH",
            "LD_LIBRARY_PATH",
            "PYTHONPATH",
            "HOME",
        ]
        
        for var in dangerous_vars:
            env.pop(var, None)
        
        # Set safe defaults
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        
        return env
    
    def reset(self) -> None:
        """Reset sandbox state (clean workspace and clear any in-memory state).
        
        This should be called between execution sessions to prevent
        data contamination.
        """
        if self.workspace_path and self.workspace_path.exists():
            import shutil
            try:
                # Remove all files in workspace
                for item in self.workspace_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                logger.debug("Sandbox workspace reset: %s", self.workspace_path)
            except Exception as exc:
                logger.warning("Failed to reset sandbox workspace: %s", exc)
    
    def cleanup(self) -> None:
        """Clean up sandbox workspace (removes entire directory)."""
        if self.workspace_path and self.workspace_path.exists():
            import shutil
            try:
                shutil.rmtree(self.workspace_path)
                logger.debug("Sandbox workspace cleaned up: %s", self.workspace_path)
            except Exception as exc:
                logger.warning("Failed to cleanup sandbox workspace: %s", exc)

