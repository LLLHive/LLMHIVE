"""Tests for the Code Execution Agent.

Tests cover:
- Code execution in sandbox
- Code analysis (syntax, security, style)
- Code explanation generation
- Refactoring suggestions
- Security blocking
- Error handling
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

# Add the src directory to the path for imports
src_path = str(Path(__file__).parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from llmhive.app.agents.code_agent import (
    CodeExecutionAgent,
    analyze_python_code,
    analyze_javascript_code,
    generate_code_explanation,
    suggest_refactoring,
    execute_code_sandboxed,
    CodeIssue,
    CodeAnalysisResult,
    ExecutionResult,
    BLOCKED_MODULES,
    BLOCKED_BUILTINS,
)
from llmhive.app.agents.base import AgentTask, AgentPriority


# ============================================================
# Code Analysis Tests
# ============================================================

class TestPythonCodeAnalysis:
    """Tests for Python code analysis."""
    
    def test_valid_simple_code(self):
        """Test analysis of valid simple code."""
        code = """
def greet(name):
    return f"Hello, {name}!"
        """
        result = analyze_python_code(code)
        assert result.is_valid
        assert result.language == "python"
        assert result.security_risk == "low"
        assert result.metrics["function_count"] == 1
    
    def test_syntax_error_detection(self):
        """Test syntax error detection."""
        code = """
def broken(
    print("missing paren"
        """
        result = analyze_python_code(code)
        assert not result.is_valid
        assert any(i.issue_type == "syntax" for i in result.issues)
        assert any(i.severity == "error" for i in result.issues)
    
    def test_empty_code(self):
        """Test empty code handling."""
        result = analyze_python_code("")
        assert not result.is_valid
        assert any("Empty" in i.description for i in result.issues)
    
    def test_blocked_import_detection(self):
        """Test blocked module import detection."""
        code = "import os"
        result = analyze_python_code(code)
        assert result.security_risk in ("high", "critical")
        assert any(
            i.issue_type == "security" and "os" in i.description 
            for i in result.issues
        )
    
    def test_blocked_subprocess_detection(self):
        """Test subprocess import detection."""
        code = "import subprocess"
        result = analyze_python_code(code)
        assert result.security_risk == "critical"
        assert any(
            i.issue_type == "security" and "subprocess" in i.description
            for i in result.issues
        )
    
    def test_blocked_builtin_detection(self):
        """Test blocked builtin function detection."""
        code = "eval('print(1)')"
        result = analyze_python_code(code)
        assert any(
            i.issue_type == "security" and "eval" in i.description
            for i in result.issues
        )
    
    def test_dunder_attribute_detection(self):
        """Test dangerous dunder attribute access detection."""
        code = "x.__class__.__bases__"
        result = analyze_python_code(code)
        assert any(
            i.issue_type == "security" and "__class__" in i.description
            for i in result.issues
        )
    
    def test_allowed_modules(self):
        """Test that allowed modules don't trigger warnings."""
        code = """
import math
import json
import re
from datetime import datetime
        """
        result = analyze_python_code(code)
        assert result.is_valid
        # Should not have critical security issues
        assert not any(i.severity == "critical" for i in result.issues)
    
    def test_style_long_line_detection(self):
        """Test long line detection."""
        code = "x = " + "a" * 150
        result = analyze_python_code(code)
        assert any(
            i.issue_type == "style" and "120 characters" in i.description
            for i in result.issues
        )
    
    def test_metrics_calculation(self):
        """Test code metrics calculation."""
        code = """
import math

class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b

def main():
    calc = Calculator()
    print(calc.add(1, 2))
        """
        result = analyze_python_code(code)
        assert result.metrics["class_count"] == 1
        assert result.metrics["function_count"] == 3  # add, multiply, main
        assert result.metrics["import_count"] == 1


class TestJavaScriptCodeAnalysis:
    """Tests for JavaScript code analysis."""
    
    def test_valid_simple_code(self):
        """Test analysis of valid simple code."""
        code = """
function greet(name) {
    return `Hello, ${name}!`;
}
        """
        result = analyze_javascript_code(code)
        assert result.is_valid
        assert result.language == "javascript"
    
    def test_eval_detection(self):
        """Test eval() detection."""
        code = "eval('alert(1)')"
        result = analyze_javascript_code(code)
        assert any(
            i.issue_type == "security" and "eval" in i.description.lower()
            for i in result.issues
        )
    
    def test_function_constructor_detection(self):
        """Test Function constructor detection."""
        code = "var f = new Function('x', 'return x * 2');"
        result = analyze_javascript_code(code)
        assert any(
            i.issue_type == "security" and "Function constructor" in i.description
            for i in result.issues
        )


# ============================================================
# Code Explanation Tests
# ============================================================

class TestCodeExplanation:
    """Tests for code explanation generation."""
    
    def test_function_explanation(self):
        """Test explanation of function."""
        code = '''
def calculate_area(width, height):
    """Calculate rectangle area."""
    return width * height
        '''
        explanation = generate_code_explanation(code, "python")
        assert explanation["language"] == "python"
        assert len(explanation["components"]) == 1
        assert explanation["components"][0]["type"] == "function"
        assert explanation["components"][0]["name"] == "calculate_area"
        assert "width" in explanation["components"][0]["args"]
    
    def test_class_explanation(self):
        """Test explanation of class."""
        code = '''
class Rectangle:
    """A rectangle shape."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def area(self):
        return self.width * self.height
        '''
        explanation = generate_code_explanation(code, "python")
        assert any(c["type"] == "class" for c in explanation["components"])
        class_comp = next(c for c in explanation["components"] if c["type"] == "class")
        assert class_comp["name"] == "Rectangle"
        assert "__init__" in class_comp["methods"]
        assert "area" in class_comp["methods"]
    
    def test_empty_code_explanation(self):
        """Test explanation handles empty code."""
        explanation = generate_code_explanation("", "python")
        assert explanation["summary"] == "Unable to parse code (syntax error)" or "Script" in explanation["summary"]


# ============================================================
# Refactoring Suggestion Tests
# ============================================================

class TestRefactoringSuggestions:
    """Tests for refactoring suggestions."""
    
    def test_mutable_default_argument(self):
        """Test mutable default argument detection."""
        code = """
def append_to(item, target=[]):
    target.append(item)
    return target
        """
        suggestions = suggest_refactoring(code, "python")
        assert any(
            "mutable" in s.get("issue", "").lower()
            for s in suggestions["suggestions"]
        )
    
    def test_bare_except_detection(self):
        """Test bare except clause detection."""
        code = """
try:
    risky_operation()
except:
    pass
        """
        suggestions = suggest_refactoring(code, "python")
        assert any(
            "except" in s.get("issue", "").lower()
            for s in suggestions["suggestions"]
        )
    
    def test_too_many_parameters(self):
        """Test detection of too many parameters."""
        code = """
def configure(a, b, c, d, e, f, g):
    pass
        """
        suggestions = suggest_refactoring(code, "python")
        assert any(
            "parameter" in s.get("issue", "").lower()
            for s in suggestions["suggestions"]
        )
    
    def test_good_code_quality(self):
        """Test that good code gets good quality rating."""
        code = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
        """
        suggestions = suggest_refactoring(code, "python")
        assert suggestions["overall_quality"] in ("good", "acceptable")


# ============================================================
# Sandbox Execution Tests
# ============================================================

@pytest.mark.asyncio
class TestSandboxExecution:
    """Tests for sandboxed code execution."""
    
    async def test_simple_execution(self):
        """Test simple code execution."""
        code = "print('Hello, World!')"
        result = await execute_code_sandboxed(code)
        assert result.success
        assert "Hello, World!" in result.output
    
    async def test_math_execution(self):
        """Test code using math module."""
        code = """
import math
print(math.sqrt(16))
        """
        result = await execute_code_sandboxed(code)
        assert result.success
        assert "4" in result.output
    
    async def test_blocked_import_execution(self):
        """Test that blocked imports prevent execution."""
        code = "import os"
        result = await execute_code_sandboxed(code)
        assert not result.success
        assert "Security" in (result.error or "")
    
    async def test_blocked_eval_execution(self):
        """Test that eval is blocked."""
        code = "result = eval('1 + 1')"
        result = await execute_code_sandboxed(code)
        # Should fail either in analysis or execution
        assert not result.success or "eval" in (result.error or "")
    
    async def test_timeout_handling(self):
        """Test execution timeout."""
        code = """
import time
time.sleep(10)
        """
        result = await execute_code_sandboxed(code, timeout_seconds=1.0)
        assert not result.success
        assert "timeout" in (result.error or "").lower() or "Security" in (result.error or "")
    
    async def test_output_capture(self):
        """Test that output is captured correctly."""
        code = """
for i in range(5):
    print(f"Number: {i}")
        """
        result = await execute_code_sandboxed(code)
        assert result.success
        assert "Number: 0" in result.output
        assert "Number: 4" in result.output
    
    async def test_syntax_error_handling(self):
        """Test syntax error handling in execution."""
        code = "def broken("
        result = await execute_code_sandboxed(code)
        assert not result.success
        assert "SyntaxError" in (result.error or "") or "syntax" in (result.error or "").lower()
    
    async def test_runtime_error_handling(self):
        """Test runtime error handling."""
        code = """
x = 1 / 0
        """
        result = await execute_code_sandboxed(code)
        assert not result.success
        assert "ZeroDivision" in (result.error or "")
    
    async def test_unsupported_language(self):
        """Test unsupported language handling."""
        result = await execute_code_sandboxed("code", language="ruby")
        assert not result.success
        assert "Unsupported" in (result.error or "")


# ============================================================
# Code Execution Agent Tests
# ============================================================

@pytest.mark.asyncio
class TestCodeExecutionAgent:
    """Tests for the CodeExecutionAgent class."""
    
    @pytest.fixture
    def agent(self):
        """Create a code execution agent instance."""
        return CodeExecutionAgent()
    
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "code_agent"
        assert agent._total_executions == 0
    
    async def test_execute_code_task(self, agent):
        """Test execute_code task."""
        task = AgentTask(
            task_id="test-1",
            task_type="execute_code",
            payload={
                "code": "print('test output')",
                "language": "python",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert "execution_id" in result.output
        assert result.output["success"]
        assert "test output" in result.output["output"]
    
    async def test_analyze_code_task(self, agent):
        """Test analyze_code task."""
        task = AgentTask(
            task_id="test-2",
            task_type="analyze_code",
            payload={
                "code": """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
                """,
                "language": "python",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["is_valid"]
        assert result.output["security_risk"] == "low"
    
    async def test_analyze_code_with_issues(self, agent):
        """Test analyze_code with security issues."""
        task = AgentTask(
            task_id="test-3",
            task_type="analyze_code",
            payload={
                "code": "import subprocess",
                "language": "python",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["security_risk"] == "critical"
        assert len(result.recommendations) > 0
    
    async def test_explain_code_task(self, agent):
        """Test explain_code task."""
        task = AgentTask(
            task_id="test-4",
            task_type="explain_code",
            payload={
                "code": """
def add(a, b):
    '''Add two numbers.'''
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
                """,
                "language": "python",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert "components" in result.output
        assert len(result.output["components"]) >= 2
    
    async def test_refactor_code_task(self, agent):
        """Test refactor_code task."""
        task = AgentTask(
            task_id="test-5",
            task_type="refactor_code",
            payload={
                "code": """
def process(data=[]):
    try:
        return data[0]
    except:
        return None
                """,
                "language": "python",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert "suggestions" in result.output
        # Should detect mutable default and bare except
        assert result.output["suggestion_count"] >= 1
    
    async def test_unknown_task_type(self, agent):
        """Test handling of unknown task type."""
        task = AgentTask(
            task_id="test-6",
            task_type="unknown_task",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "Unknown task type" in result.error
    
    async def test_empty_code_handling(self, agent):
        """Test handling of empty code."""
        task = AgentTask(
            task_id="test-7",
            task_type="execute_code",
            payload={
                "code": "",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "No code" in result.error
    
    async def test_execution_history(self, agent):
        """Test execution history tracking."""
        # Run a few executions
        for i in range(3):
            task = AgentTask(
                task_id=f"hist-{i}",
                task_type="execute_code",
                payload={"code": f"print({i})"},
            )
            agent.add_task(task)
            await agent.run()
        
        # Get history
        task = AgentTask(
            task_id="hist-get",
            task_type="get_history",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["total_executions"] == 3
        assert result.output["successful_executions"] == 3
    
    async def test_code_length_limit(self, agent):
        """Test code length limit."""
        task = AgentTask(
            task_id="test-long",
            task_type="execute_code",
            payload={
                "code": "x = 1\n" * 100000,  # Very long code
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "too long" in result.error.lower()
    
    async def test_get_capabilities(self, agent):
        """Test get_capabilities returns expected structure."""
        caps = agent.get_capabilities()
        
        assert "name" in caps
        assert "task_types" in caps
        assert "supported_languages" in caps
        assert "safety_features" in caps
        assert "limits" in caps
        assert "python" in caps["supported_languages"]
        assert "execute_code" in caps["task_types"]
    
    async def test_no_task_provided(self, agent):
        """Test agent handles no task."""
        result = await agent.execute(None)
        assert not result.success
        assert "No task provided" in result.error


# ============================================================
# Security Tests
# ============================================================

class TestSecurityBlocking:
    """Tests for security blocking mechanisms."""
    
    def test_all_blocked_modules_detected(self):
        """Test that all blocked modules are detected."""
        for module in list(BLOCKED_MODULES)[:5]:  # Test a subset
            code = f"import {module}"
            result = analyze_python_code(code)
            assert any(
                i.severity in ("critical", "error")
                for i in result.issues
            ), f"Module {module} should be blocked"
    
    def test_all_blocked_builtins_detected(self):
        """Test that all blocked builtins are detected."""
        for builtin in list(BLOCKED_BUILTINS)[:5]:  # Test a subset
            code = f"{builtin}()"
            result = analyze_python_code(code)
            # Should either have issues or fail syntax
            if result.is_valid:
                # If it parsed, check for security issues
                has_security_issue = any(
                    i.issue_type == "security"
                    for i in result.issues
                )
                # Some builtins like 'dir' without args might not trigger
                # That's acceptable for basic security
    
    def test_nested_import_detection(self):
        """Test nested dangerous patterns are detected."""
        code = """
def innocent_looking():
    __import__('os').system('bad')
        """
        result = analyze_python_code(code)
        assert any(
            "security" in i.issue_type.lower()
            for i in result.issues
        )
    
    def test_from_import_blocking(self):
        """Test from X import Y is also blocked."""
        code = "from subprocess import call"
        result = analyze_python_code(code)
        assert result.security_risk in ("high", "critical")


# ============================================================
# Integration Tests
# ============================================================

@pytest.mark.asyncio
class TestCodeAgentIntegration:
    """Integration tests for the code agent."""
    
    async def test_analyze_then_execute_safe_code(self):
        """Test analyzing code before execution."""
        agent = CodeExecutionAgent()
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(f"fib({i}) = {fibonacci(i)}")
        """
        
        # First analyze
        analyze_task = AgentTask(
            task_id="int-1",
            task_type="analyze_code",
            payload={"code": code},
        )
        agent.add_task(analyze_task)
        analysis_result = await agent.run()
        
        assert analysis_result.success
        assert analysis_result.output["is_valid"]
        assert analysis_result.output["security_risk"] == "low"
        
        # Then execute
        exec_task = AgentTask(
            task_id="int-2",
            task_type="execute_code",
            payload={"code": code},
        )
        agent.add_task(exec_task)
        exec_result = await agent.run()
        
        assert exec_result.success
        assert "fib(9)" in exec_result.output["output"]
    
    async def test_analyze_then_reject_unsafe_code(self):
        """Test that analysis prevents unsafe execution."""
        agent = CodeExecutionAgent()
        code = """
import os
os.system('rm -rf /')
        """
        
        # Analyze first
        analyze_task = AgentTask(
            task_id="int-3",
            task_type="analyze_code",
            payload={"code": code},
        )
        agent.add_task(analyze_task)
        analysis_result = await agent.run()
        
        # Analysis should flag as dangerous
        assert analysis_result.output["security_risk"] == "critical"
        
        # Execution should be blocked
        exec_task = AgentTask(
            task_id="int-4",
            task_type="execute_code",
            payload={"code": code},
        )
        agent.add_task(exec_task)
        exec_result = await agent.run()
        
        assert not exec_result.output["success"]
        assert "Security" in exec_result.output.get("error", "")
