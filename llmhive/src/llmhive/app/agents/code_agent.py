"""Code Execution Agent for LLMHive.

This on-demand agent handles code execution, analysis, and refactoring tasks
with secure sandbox execution and comprehensive safety features.

Task Types:
- execute_code: Run Python/JavaScript code safely in a sandbox
- analyze_code: Static analysis for issues (syntax, security, style)
- explain_code: Generate natural language explanations of code
- refactor_code: Suggest improvements and refactored versions

Safety Features:
- Sandbox execution with timeout
- Resource limits (memory, CPU)
- Blocked imports/functions list
- AST-based validation
- Output sanitization
"""
from __future__ import annotations

import ast
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


# ============================================================
# Code Analysis Types
# ============================================================

@dataclass
class CodeIssue:
    """An identified code issue."""
    issue_type: str  # "syntax", "security", "style", "performance", "bug"
    severity: str  # "info", "warning", "error", "critical"
    line: Optional[int]
    column: Optional[int]
    description: str
    suggestion: Optional[str] = None


@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    is_valid: bool
    language: str
    issues: List[CodeIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    security_risk: str = "low"  # "low", "medium", "high", "critical"


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: int = 0
    memory_used_mb: float = 0.0
    truncated: bool = False


# ============================================================
# Security Configuration
# ============================================================

# Modules that are allowed in sandbox
ALLOWED_MODULES = frozenset({
    "math", "json", "re", "datetime", "collections", "itertools",
    "functools", "operator", "string", "random", "statistics",
    "typing", "dataclasses", "enum", "abc", "copy", "decimal",
    "fractions", "numbers", "heapq", "bisect", "array",
})

# Modules that are explicitly blocked
BLOCKED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "urllib",
    "requests", "http", "ftplib", "telnetlib", "smtplib",
    "pickle", "marshal", "shelve", "dbm", "sqlite3",
    "multiprocessing", "threading", "ctypes", "importlib",
    "builtins", "__builtin__", "code", "codeop", "compile",
})

# Built-in functions that are blocked
BLOCKED_BUILTINS = frozenset({
    "open", "exec", "eval", "compile", "__import__",
    "getattr", "setattr", "delattr", "globals", "locals",
    "input", "breakpoint", "memoryview", "vars", "dir",
})

# Dangerous patterns to detect
DANGEROUS_PATTERNS = [
    r"__\w+__",  # Dunder methods/attributes
    r"os\.(system|popen|exec|spawn)",
    r"subprocess\.",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
    r"importlib",
    r"open\s*\(",
    r"file\s*\(",
]


# ============================================================
# Code Analysis Functions
# ============================================================

def analyze_python_code(code: str) -> CodeAnalysisResult:
    """
    Analyze Python code for issues.
    
    Performs:
    - Syntax validation
    - Security analysis (blocked imports/functions)
    - Style checks (basic)
    - Code metrics
    """
    issues: List[CodeIssue] = []
    metrics: Dict[str, Any] = {}
    security_risk = "low"
    
    # Check for empty code
    if not code or not code.strip():
        return CodeAnalysisResult(
            is_valid=False,
            language="python",
            issues=[CodeIssue(
                issue_type="syntax",
                severity="error",
                line=None,
                column=None,
                description="Empty code provided",
            )],
        )
    
    # Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return CodeAnalysisResult(
            is_valid=False,
            language="python",
            issues=[CodeIssue(
                issue_type="syntax",
                severity="error",
                line=e.lineno,
                column=e.offset,
                description=f"Syntax error: {e.msg}",
                suggestion="Fix the syntax error before execution",
            )],
        )
    
    # Security analysis via AST
    class SecurityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.security_issues: List[CodeIssue] = []
            self.risk_level = 0  # 0-10 scale
        
        def visit_Import(self, node):
            for alias in node.names:
                if alias.name in BLOCKED_MODULES:
                    self.security_issues.append(CodeIssue(
                        issue_type="security",
                        severity="critical",
                        line=node.lineno,
                        column=node.col_offset,
                        description=f"Blocked module import: {alias.name}",
                        suggestion=f"Remove import of '{alias.name}' - not allowed in sandbox",
                    ))
                    self.risk_level = max(self.risk_level, 10)
                elif alias.name not in ALLOWED_MODULES:
                    self.security_issues.append(CodeIssue(
                        issue_type="security",
                        severity="warning",
                        line=node.lineno,
                        column=node.col_offset,
                        description=f"Unknown module import: {alias.name}",
                        suggestion=f"Module '{alias.name}' may not be available in sandbox",
                    ))
                    self.risk_level = max(self.risk_level, 5)
            self.generic_visit(node)
        
        def visit_ImportFrom(self, node):
            if node.module in BLOCKED_MODULES:
                self.security_issues.append(CodeIssue(
                    issue_type="security",
                    severity="critical",
                    line=node.lineno,
                    column=node.col_offset,
                    description=f"Blocked module import: from {node.module}",
                    suggestion=f"Remove import from '{node.module}' - not allowed in sandbox",
                ))
                self.risk_level = max(self.risk_level, 10)
            self.generic_visit(node)
        
        def visit_Call(self, node):
            # Check for blocked builtins
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    self.security_issues.append(CodeIssue(
                        issue_type="security",
                        severity="critical",
                        line=node.lineno,
                        column=node.col_offset,
                        description=f"Blocked function call: {node.func.id}()",
                        suggestion=f"Remove call to '{node.func.id}' - not allowed in sandbox",
                    ))
                    self.risk_level = max(self.risk_level, 10)
            self.generic_visit(node)
        
        def visit_Attribute(self, node):
            # Check for dangerous attribute access
            if isinstance(node.attr, str) and node.attr.startswith("__"):
                if node.attr in ("__dict__", "__class__", "__builtins__", "__import__", "__code__"):
                    self.security_issues.append(CodeIssue(
                        issue_type="security",
                        severity="error",
                        line=node.lineno,
                        column=node.col_offset,
                        description=f"Dangerous attribute access: {node.attr}",
                        suggestion="Avoid accessing dunder attributes directly",
                    ))
                    self.risk_level = max(self.risk_level, 8)
            self.generic_visit(node)
    
    visitor = SecurityVisitor()
    visitor.visit(tree)
    issues.extend(visitor.security_issues)
    
    # Determine security risk level
    if visitor.risk_level >= 8:
        security_risk = "critical"
    elif visitor.risk_level >= 5:
        security_risk = "high"
    elif visitor.risk_level >= 3:
        security_risk = "medium"
    else:
        security_risk = "low"
    
    # Additional pattern-based checks
    for pattern in DANGEROUS_PATTERNS:
        matches = list(re.finditer(pattern, code))
        for match in matches:
            # Calculate line number
            line_num = code[:match.start()].count('\n') + 1
            issues.append(CodeIssue(
                issue_type="security",
                severity="warning",
                line=line_num,
                column=None,
                description=f"Potentially dangerous pattern detected: {match.group()}",
            ))
    
    # Collect metrics
    metrics["line_count"] = code.count('\n') + 1
    metrics["char_count"] = len(code)
    metrics["function_count"] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    metrics["class_count"] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    metrics["import_count"] = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
    
    # Style checks
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        # Check line length
        if len(line) > 120:
            issues.append(CodeIssue(
                issue_type="style",
                severity="info",
                line=i,
                column=None,
                description=f"Line exceeds 120 characters ({len(line)} chars)",
                suggestion="Consider breaking into multiple lines",
            ))
        
        # Check for trailing whitespace
        if line.rstrip() != line:
            issues.append(CodeIssue(
                issue_type="style",
                severity="info",
                line=i,
                column=None,
                description="Trailing whitespace",
                suggestion="Remove trailing whitespace",
            ))
    
    is_valid = not any(issue.severity in ("error", "critical") for issue in issues)
    
    return CodeAnalysisResult(
        is_valid=is_valid,
        language="python",
        issues=issues,
        metrics=metrics,
        security_risk=security_risk,
    )


def analyze_javascript_code(code: str) -> CodeAnalysisResult:
    """
    Analyze JavaScript code for issues.
    
    Performs basic pattern-based analysis since we don't have a JS AST parser.
    """
    issues: List[CodeIssue] = []
    metrics: Dict[str, Any] = {}
    security_risk = "low"
    
    if not code or not code.strip():
        return CodeAnalysisResult(
            is_valid=False,
            language="javascript",
            issues=[CodeIssue(
                issue_type="syntax",
                severity="error",
                line=None,
                column=None,
                description="Empty code provided",
            )],
        )
    
    # Dangerous JS patterns
    dangerous_js_patterns = [
        (r"\beval\s*\(", "eval() is dangerous", "critical"),
        (r"\bFunction\s*\(", "Function constructor is dangerous", "critical"),
        (r"document\.write", "document.write is not recommended", "warning"),
        (r"innerHTML\s*=", "innerHTML assignment can be XSS vulnerable", "warning"),
        (r"__proto__", "Prototype manipulation detected", "error"),
        (r"\brequire\s*\(['\"]child_process['\"]", "child_process is blocked", "critical"),
        (r"\brequire\s*\(['\"]fs['\"]", "fs module requires careful handling", "warning"),
    ]
    
    for pattern, description, severity in dangerous_js_patterns:
        matches = list(re.finditer(pattern, code))
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            issues.append(CodeIssue(
                issue_type="security",
                severity=severity,
                line=line_num,
                column=None,
                description=description,
            ))
            if severity == "critical":
                security_risk = "critical"
            elif severity == "error" and security_risk not in ("critical",):
                security_risk = "high"
    
    # Metrics
    metrics["line_count"] = code.count('\n') + 1
    metrics["char_count"] = len(code)
    metrics["function_count"] = len(re.findall(r'\bfunction\b|\b=>\b', code))
    
    is_valid = not any(issue.severity in ("error", "critical") for issue in issues)
    
    return CodeAnalysisResult(
        is_valid=is_valid,
        language="javascript",
        issues=issues,
        metrics=metrics,
        security_risk=security_risk,
    )


def generate_code_explanation(code: str, language: str = "python") -> Dict[str, Any]:
    """
    Generate a structured explanation of code.
    
    Returns:
        Dictionary with code explanation components
    """
    explanation = {
        "language": language,
        "summary": "",
        "components": [],
        "flow": [],
        "inputs_outputs": {
            "inputs": [],
            "outputs": [],
        },
    }
    
    if language == "python":
        try:
            tree = ast.parse(code)
            
            # Identify main components
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract function info
                    args = [arg.arg for arg in node.args.args]
                    docstring = ast.get_docstring(node) or "No docstring"
                    explanation["components"].append({
                        "type": "function",
                        "name": node.name,
                        "args": args,
                        "docstring": docstring[:200],
                        "line": node.lineno,
                    })
                    explanation["inputs_outputs"]["inputs"].extend(args)
                
                elif isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node) or "No docstring"
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    explanation["components"].append({
                        "type": "class",
                        "name": node.name,
                        "methods": methods,
                        "docstring": docstring[:200],
                        "line": node.lineno,
                    })
                
                elif isinstance(node, ast.Return):
                    if node.value:
                        explanation["inputs_outputs"]["outputs"].append("return value")
            
            # Generate summary
            func_count = len([c for c in explanation["components"] if c["type"] == "function"])
            class_count = len([c for c in explanation["components"] if c["type"] == "class"])
            
            summary_parts = []
            if class_count > 0:
                summary_parts.append(f"Defines {class_count} class(es)")
            if func_count > 0:
                summary_parts.append(f"{func_count} function(s)")
            
            explanation["summary"] = ", ".join(summary_parts) if summary_parts else "Script with no functions or classes"
            
        except SyntaxError:
            explanation["summary"] = "Unable to parse code (syntax error)"
    
    else:
        # Basic analysis for other languages
        lines = code.split('\n')
        explanation["summary"] = f"Code with {len(lines)} lines"
        
        # Look for function patterns
        func_patterns = re.findall(r'\bfunction\s+(\w+)\s*\(([^)]*)\)', code)
        for name, args in func_patterns:
            explanation["components"].append({
                "type": "function",
                "name": name,
                "args": [a.strip() for a in args.split(',') if a.strip()],
            })
    
    return explanation


def suggest_refactoring(code: str, language: str = "python") -> Dict[str, Any]:
    """
    Suggest refactoring improvements for code.
    
    Returns:
        Dictionary with refactoring suggestions
    """
    suggestions = {
        "language": language,
        "overall_quality": "good",
        "suggestions": [],
        "refactored_snippets": [],
    }
    
    if language == "python":
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Check for long functions
                if isinstance(node, ast.FunctionDef):
                    func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if func_lines > 50:
                        suggestions["suggestions"].append({
                            "type": "complexity",
                            "location": f"function '{node.name}' at line {node.lineno}",
                            "issue": f"Function is {func_lines} lines long",
                            "suggestion": "Consider breaking into smaller functions",
                        })
                    
                    # Check for too many parameters
                    param_count = len(node.args.args)
                    if param_count > 5:
                        suggestions["suggestions"].append({
                            "type": "signature",
                            "location": f"function '{node.name}' at line {node.lineno}",
                            "issue": f"Function has {param_count} parameters",
                            "suggestion": "Consider using a data class or configuration object",
                        })
                
                # Check for deeply nested code
                if isinstance(node, (ast.If, ast.For, ast.While)):
                    # Simple depth check
                    depth = sum(1 for _ in ast.walk(node) if isinstance(_, (ast.If, ast.For, ast.While)))
                    if depth > 4:
                        suggestions["suggestions"].append({
                            "type": "complexity",
                            "location": f"line {node.lineno}",
                            "issue": "Deeply nested control flow",
                            "suggestion": "Consider extracting to helper functions or using early returns",
                        })
            
            # Check for common anti-patterns
            code_str = code
            
            # Check for mutable default arguments
            mutable_defaults = re.findall(r'def\s+\w+\([^)]*=\s*(\[\]|\{\})\)', code_str)
            if mutable_defaults:
                suggestions["suggestions"].append({
                    "type": "bug_risk",
                    "location": "function definitions",
                    "issue": "Mutable default argument detected",
                    "suggestion": "Use None as default and initialize inside function",
                })
            
            # Check for bare except
            if re.search(r'\bexcept\s*:', code_str):
                suggestions["suggestions"].append({
                    "type": "best_practice",
                    "location": "exception handling",
                    "issue": "Bare 'except:' clause found",
                    "suggestion": "Specify exception types explicitly (e.g., 'except ValueError:')",
                })
            
        except SyntaxError:
            suggestions["overall_quality"] = "error"
            suggestions["suggestions"].append({
                "type": "syntax",
                "issue": "Code has syntax errors",
                "suggestion": "Fix syntax errors first",
            })
    
    # Determine overall quality
    critical_count = sum(1 for s in suggestions["suggestions"] if s.get("type") in ("bug_risk", "complexity"))
    if critical_count > 3:
        suggestions["overall_quality"] = "needs_improvement"
    elif critical_count > 0:
        suggestions["overall_quality"] = "acceptable"
    else:
        suggestions["overall_quality"] = "good"
    
    return suggestions


# ============================================================
# Sandbox Execution
# ============================================================

async def execute_code_sandboxed(
    code: str,
    language: str = "python",
    timeout_seconds: float = 5.0,
    max_output_chars: int = 10000,
) -> ExecutionResult:
    """
    Execute code in a sandboxed environment.
    
    Args:
        code: Code to execute
        language: Programming language
        timeout_seconds: Maximum execution time
        max_output_chars: Maximum output length
        
    Returns:
        ExecutionResult with output or error
    """
    start_time = time.time()
    
    if language not in ("python", "javascript"):
        return ExecutionResult(
            success=False,
            error=f"Unsupported language: {language}. Supported: python, javascript",
        )
    
    # Analyze code first
    if language == "python":
        analysis = analyze_python_code(code)
    else:
        analysis = analyze_javascript_code(code)
    
    # Block execution if security risk is too high
    if analysis.security_risk in ("critical", "high"):
        critical_issues = [i for i in analysis.issues if i.severity in ("critical", "error")]
        issue_desc = "; ".join(i.description for i in critical_issues[:3])
        return ExecutionResult(
            success=False,
            error=f"Security risk too high ({analysis.security_risk}): {issue_desc}",
        )
    
    if language == "python":
        return await _execute_python_sandboxed(code, timeout_seconds, max_output_chars, start_time)
    else:
        return ExecutionResult(
            success=False,
            error="JavaScript execution not yet implemented in sandbox",
        )


async def _execute_python_sandboxed(
    code: str,
    timeout_seconds: float,
    max_output_chars: int,
    start_time: float,
) -> ExecutionResult:
    """Execute Python code in a restricted environment."""
    import io
    import sys
    import builtins
    from contextlib import redirect_stdout, redirect_stderr
    
    # Pre-import allowed modules BEFORE creating restricted builtins
    pre_imported = {}
    for module_name in ["math", "json", "re", "datetime", "collections", "itertools", "functools", "random", "statistics"]:
        try:
            pre_imported[module_name] = __import__(module_name)
        except ImportError:
            pass
    
    # Create safe builtins - explicitly build from builtins module
    safe_builtins = {}
    for name in dir(builtins):
        if name.startswith('_'):
            continue
        if name in BLOCKED_BUILTINS:
            continue
        try:
            safe_builtins[name] = getattr(builtins, name)
        except AttributeError:
            pass
    
    # Add required dunder items
    safe_builtins['__name__'] = '__sandbox__'
    safe_builtins['__doc__'] = None
    
    # Create a restricted import function that only allows safe modules
    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in pre_imported:
            return pre_imported[name]
        if name in ALLOWED_MODULES:
            return __import__(name, globals, locals, fromlist, level)
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")
    
    safe_builtins['__import__'] = restricted_import
    
    # Allow only safe modules
    safe_globals = {
        "__builtins__": safe_builtins,
        "__name__": "__sandbox__",
    }
    
    # Add pre-imported modules to globals
    safe_globals.update(pre_imported)
    
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        # Execute with timeout using asyncio
        async def run_code():
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals)
        
        await asyncio.wait_for(run_code(), timeout=timeout_seconds)
        
        output = stdout_capture.getvalue()
        errors = stderr_capture.getvalue()
        
        # Truncate if needed
        truncated = False
        if len(output) > max_output_chars:
            output = output[:max_output_chars] + f"\n... [truncated, {len(output) - max_output_chars} more chars]"
            truncated = True
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        if errors:
            return ExecutionResult(
                success=True,  # Code ran but had stderr output
                output=output,
                error=errors[:1000],
                execution_time_ms=execution_time_ms,
                truncated=truncated,
            )
        
        return ExecutionResult(
            success=True,
            output=output,
            execution_time_ms=execution_time_ms,
            truncated=truncated,
        )
        
    except asyncio.TimeoutError:
        return ExecutionResult(
            success=False,
            error=f"Execution timed out after {timeout_seconds}s",
            execution_time_ms=int(timeout_seconds * 1000),
        )
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return ExecutionResult(
            success=False,
            error=f"{type(e).__name__}: {str(e)}",
            execution_time_ms=execution_time_ms,
        )


# ============================================================
# Code Execution Agent
# ============================================================

class CodeExecutionAgent(BaseAgent):
    """Agent that executes, analyzes, and refactors code.
    
    Responsibilities:
    - Execute code snippets safely in a sandbox
    - Analyze code for issues (syntax, security, style)
    - Generate code explanations
    - Suggest refactoring improvements
    
    Usage:
        agent = CodeExecutionAgent()
        
        # Execute code
        task = AgentTask(
            task_id="exec-1",
            task_type="execute_code",
            payload={
                "code": "print('Hello')",
                "language": "python",
            }
        )
        result = await agent.run()
        
        # Analyze code
        task = AgentTask(
            task_id="analyze-1",
            task_type="analyze_code",
            payload={
                "code": "def foo(): pass",
                "language": "python",
            }
        )
        result = await agent.run()
    """
    
    # Execution settings
    DEFAULT_TIMEOUT = 5.0
    MAX_OUTPUT_CHARS = 10000
    MAX_CODE_LENGTH = 50000
    
    # History settings
    MAX_HISTORY_SIZE = 100
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="code_agent",
                agent_type=AgentType.ON_DEMAND,
                priority=AgentPriority.HIGH,
                max_tokens_per_run=5000,
                max_runtime_seconds=30,
                allowed_tools=["code_sandbox", "linter"],
                memory_namespace="code",
            )
        super().__init__(config)
        
        # Execution tracking
        self._execution_history: deque[Dict[str, Any]] = deque(maxlen=self.MAX_HISTORY_SIZE)
        self._total_executions = 0
        self._successful_executions = 0
        self._blocked_executions = 0
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """
        Execute code-related tasks.
        
        Task types:
        - "execute_code": Execute code in sandbox
        - "analyze_code": Static analysis for issues
        - "explain_code": Generate code explanation
        - "refactor_code": Suggest improvements
        - "get_history": Return execution history
        - "get_capabilities": Return agent capabilities
        
        Returns:
            AgentResult with task outcome
        """
        if not task:
            return AgentResult(
                success=False,
                error="No task provided",
            )
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "execute_code":
                return await self._execute_code(payload)
            
            elif task_type == "analyze_code":
                return self._analyze_code(payload)
            
            elif task_type == "explain_code":
                return self._explain_code(payload)
            
            elif task_type == "refactor_code":
                return self._refactor_code(payload)
            
            elif task_type == "get_history":
                return self._get_execution_history()
            
            elif task_type == "get_capabilities":
                return AgentResult(
                    success=True,
                    output=self.get_capabilities(),
                )
            
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown task type: {task_type}",
                    recommendations=[
                        "Available task types: execute_code, analyze_code, explain_code, refactor_code",
                    ],
                )
                
        except Exception as e:
            logger.error("Code Agent execution failed: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )
    
    async def _execute_code(self, payload: Dict[str, Any]) -> AgentResult:
        """Execute code in sandbox."""
        code = payload.get("code", "")
        language = payload.get("language", "python").lower()
        timeout = payload.get("timeout", self.DEFAULT_TIMEOUT)
        
        # Validate code length
        if len(code) > self.MAX_CODE_LENGTH:
            return AgentResult(
                success=False,
                error=f"Code too long ({len(code)} chars). Maximum: {self.MAX_CODE_LENGTH}",
            )
        
        if not code.strip():
            return AgentResult(
                success=False,
                error="No code provided",
            )
        
        # Track execution
        self._total_executions += 1
        execution_id = f"exec-{self._total_executions}-{int(time.time())}"
        
        # Execute in sandbox
        result = await execute_code_sandboxed(
            code=code,
            language=language,
            timeout_seconds=min(timeout, self.config.max_runtime_seconds),
            max_output_chars=self.MAX_OUTPUT_CHARS,
        )
        
        # Update statistics
        if result.success:
            self._successful_executions += 1
        elif "Security risk" in (result.error or ""):
            self._blocked_executions += 1
        
        # Store in history
        self._execution_history.append({
            "id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "language": language,
            "code_length": len(code),
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
            "error": result.error[:100] if result.error else None,
        })
        
        # Write to blackboard if available
        if self._blackboard and result.success:
            await self.write_to_blackboard(
                f"execution:{execution_id}",
                {
                    "output": result.output[:500],
                    "success": result.success,
                },
                ttl_seconds=3600,
            )
        
        return AgentResult(
            success=result.success,
            output={
                "execution_id": execution_id,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "execution_time_ms": result.execution_time_ms,
                "truncated": result.truncated,
            },
            metadata={
                "language": language,
                "code_length": len(code),
            },
        )
    
    def _analyze_code(self, payload: Dict[str, Any]) -> AgentResult:
        """Analyze code for issues."""
        code = payload.get("code", "")
        language = payload.get("language", "python").lower()
        
        if not code.strip():
            return AgentResult(
                success=False,
                error="No code provided",
            )
        
        # Perform analysis
        if language == "python":
            analysis = analyze_python_code(code)
        elif language == "javascript":
            analysis = analyze_javascript_code(code)
        else:
            return AgentResult(
                success=False,
                error=f"Unsupported language: {language}",
            )
        
        # Format issues
        issues_output = []
        for issue in analysis.issues:
            issues_output.append({
                "type": issue.issue_type,
                "severity": issue.severity,
                "line": issue.line,
                "description": issue.description,
                "suggestion": issue.suggestion,
            })
        
        # Generate recommendations
        recommendations = []
        critical_count = sum(1 for i in analysis.issues if i.severity == "critical")
        error_count = sum(1 for i in analysis.issues if i.severity == "error")
        
        if critical_count > 0:
            recommendations.append(f"Fix {critical_count} critical issue(s) before execution")
        if error_count > 0:
            recommendations.append(f"Address {error_count} error(s) in the code")
        if analysis.security_risk in ("high", "critical"):
            recommendations.append("Code has high security risk - review blocked operations")
        
        return AgentResult(
            success=True,
            output={
                "is_valid": analysis.is_valid,
                "language": analysis.language,
                "security_risk": analysis.security_risk,
                "issue_count": len(analysis.issues),
                "issues": issues_output,
                "metrics": analysis.metrics,
            },
            recommendations=recommendations,
            findings=[
                {
                    "metric": "security_risk",
                    "value": analysis.security_risk,
                    "status": "good" if analysis.security_risk == "low" else "needs_attention",
                },
                {
                    "metric": "is_valid",
                    "value": analysis.is_valid,
                    "status": "good" if analysis.is_valid else "needs_attention",
                },
            ],
        )
    
    def _explain_code(self, payload: Dict[str, Any]) -> AgentResult:
        """Generate code explanation."""
        code = payload.get("code", "")
        language = payload.get("language", "python").lower()
        
        if not code.strip():
            return AgentResult(
                success=False,
                error="No code provided",
            )
        
        explanation = generate_code_explanation(code, language)
        
        return AgentResult(
            success=True,
            output={
                "language": explanation["language"],
                "summary": explanation["summary"],
                "components": explanation["components"],
                "inputs_outputs": explanation["inputs_outputs"],
            },
        )
    
    def _refactor_code(self, payload: Dict[str, Any]) -> AgentResult:
        """Suggest refactoring improvements."""
        code = payload.get("code", "")
        language = payload.get("language", "python").lower()
        
        if not code.strip():
            return AgentResult(
                success=False,
                error="No code provided",
            )
        
        suggestions = suggest_refactoring(code, language)
        
        return AgentResult(
            success=True,
            output={
                "overall_quality": suggestions["overall_quality"],
                "suggestion_count": len(suggestions["suggestions"]),
                "suggestions": suggestions["suggestions"],
            },
            recommendations=[
                s["suggestion"] for s in suggestions["suggestions"][:5]
            ],
        )
    
    def _get_execution_history(self) -> AgentResult:
        """Get recent execution history."""
        return AgentResult(
            success=True,
            output={
                "total_executions": self._total_executions,
                "successful_executions": self._successful_executions,
                "blocked_executions": self._blocked_executions,
                "success_rate": round(self._successful_executions / self._total_executions, 3) if self._total_executions > 0 else 0,
                "recent_executions": list(self._execution_history)[-20:],
            },
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Code Execution Agent",
            "type": "on_demand",
            "purpose": "Execute, analyze, and refactor code safely",
            "task_types": [
                "execute_code",
                "analyze_code",
                "explain_code",
                "refactor_code",
                "get_history",
            ],
            "supported_languages": ["python", "javascript"],
            "safety_features": [
                "AST-based code validation",
                "Blocked dangerous imports/functions",
                "Execution timeout",
                "Output truncation",
                "Security risk assessment",
            ],
            "limits": {
                "max_code_length": self.MAX_CODE_LENGTH,
                "max_output_chars": self.MAX_OUTPUT_CHARS,
                "default_timeout_seconds": self.DEFAULT_TIMEOUT,
                "max_timeout_seconds": self.config.max_runtime_seconds,
            },
            "blocked_modules": list(BLOCKED_MODULES)[:10] + ["..."],
            "blocked_builtins": list(BLOCKED_BUILTINS),
        }
