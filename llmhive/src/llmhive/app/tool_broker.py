"""Tool Broker: Centralized tool execution interface for LLMHive.

This module provides:
- Multiple tool types (web search, calculator, code exec, knowledge lookup)
- Tool request parsing and execution
- Tier-based access control
- Safe expression evaluation
- Integration hooks for orchestrator
"""
from __future__ import annotations

import ast
import json
import logging
import math
import operator
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Tool Types and Configuration
# ==============================================================================

class ToolCategory(str, Enum):
    """Categories of tools."""
    SEARCH = "search"
    COMPUTE = "compute"
    CODE = "code"
    KNOWLEDGE = "knowledge"
    API = "api"


@dataclass(slots=True)
class ToolDefinition:
    """Definition of a tool."""
    name: str
    description: str
    category: ToolCategory
    handler: Callable
    is_async: bool = False
    allowed_tiers: Set[str] = field(default_factory=lambda: {"free", "pro", "enterprise"})
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_sandbox: bool = False


@dataclass(slots=True)
class ToolRequest:
    """Parsed tool request."""
    tool_name: str
    arguments: str
    raw_request: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """Result of tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# Safe Calculator
# ==============================================================================

class SafeCalculator:
    """Safe mathematical expression evaluator.
    
    Supports basic arithmetic, common math functions, and constants.
    Does NOT use eval() - uses AST parsing for safety.
    """
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Allowed functions
    FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
        # Math functions
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "factorial": math.factorial,
        "gcd": math.gcd,
        "pow": pow,
    }
    
    # Allowed constants
    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
    }
    
    def evaluate(self, expression: str) -> Union[int, float, str]:
        """
        Safely evaluate a mathematical expression.
        
        Args:
            expression: Math expression string
            
        Returns:
            Numeric result or error string
        """
        try:
            # Clean expression
            expr = expression.strip()
            
            # Parse to AST
            tree = ast.parse(expr, mode='eval')
            
            # Evaluate AST safely
            result = self._eval_node(tree.body)
            
            # Round to avoid floating point artifacts
            if isinstance(result, float):
                if result == int(result):
                    return int(result)
                return round(result, 10)
            
            return result
            
        except SyntaxError as e:
            return f"Syntax error: {e}"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except ValueError as e:
            return f"Math error: {e}"
        except Exception as e:
            return f"Calculation error: {e}"
    
    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """Recursively evaluate AST node."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n
        
        elif isinstance(node, ast.Name):
            name = node.id.lower()
            if name in self.CONSTANTS:
                return self.CONSTANTS[name]
            raise ValueError(f"Unknown variable: {node.id}")
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id.lower() if isinstance(node.func, ast.Name) else None
            if func_name in self.FUNCTIONS:
                args = [self._eval_node(arg) for arg in node.args]
                return self.FUNCTIONS[func_name](*args)
            raise ValueError(f"Unknown function: {func_name}")
        
        elif isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]
        
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elem) for elem in node.elts)
        
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")


# ==============================================================================
# Tool Broker
# ==============================================================================

class ToolBroker:
    """Centralized broker for tool execution with security and access control.
    
    Features:
    - Multiple tool types (search, calculator, code, knowledge)
    - Tool request parsing from model output
    - Tier-based access control
    - Safe execution environment
    - Async and sync support
    """
    
    # Tool request pattern: [TOOL:tool_name] arguments
    # Also supports JSON format: {"tool": "name", "args": {...}}
    TOOL_PATTERN = re.compile(r'^\[TOOL:(\w+)\]\s*(.*)$', re.DOTALL)
    JSON_TOOL_PATTERN = re.compile(r'\{["\']?tool["\']?\s*:\s*["\'](\w+)["\']', re.IGNORECASE)
    
    def __init__(
        self,
        web_research: Optional[Any] = None,
        enable_sandbox: bool = True,
        memory_manager: Optional[Any] = None,
    ) -> None:
        """
        Initialize the ToolBroker.
        
        Args:
            web_research: Optional WebResearchClient instance
            enable_sandbox: Whether to enable sandbox for code execution
            memory_manager: Optional memory manager for knowledge lookups
        """
        self.web_research = web_research
        self.memory_manager = memory_manager
        self.calculator = SafeCalculator()
        
        # Initialize sandbox
        self.sandbox: Optional[Any] = None
        if enable_sandbox:
            try:
                from .guardrails import ExecutionSandbox
                self.sandbox = ExecutionSandbox()
            except ImportError:
                logger.warning("ExecutionSandbox not available")
        
        # Initialize web research if not provided
        if self.web_research is None:
            try:
                from .services.web_research import WebResearchClient
                self.web_research = WebResearchClient()
            except ImportError:
                logger.warning("WebResearchClient not available")
        
        # Tool definitions
        self.tool_definitions: Dict[str, ToolDefinition] = {}
        self.tools: Dict[str, Callable[..., Any]] = {}
        
        # Register built-in tools
        self._register_builtin_tools()
        
        # Allowed tools per tier
        self.tier_tools: Dict[str, Set[str]] = {
            "free": {"calculator", "web_search", "spell_check", "datetime", "convert"},
            "pro": {"calculator", "web_search", "spell_check", "datetime", "convert", 
                   "knowledge_lookup", "python_exec"},
            "enterprise": {"calculator", "web_search", "spell_check", "datetime", "convert",
                          "knowledge_lookup", "python_exec", "api_call", "advanced_search"},
        }
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        # Calculator
        self.register_tool(
            ToolDefinition(
                name="calculator",
                description="Evaluate mathematical expressions safely",
                category=ToolCategory.COMPUTE,
                handler=self._tool_calculator,
                is_async=False,
                parameters={"expression": "Math expression to evaluate"},
            )
        )
        
        # Web search
        self.register_tool(
            ToolDefinition(
                name="web_search",
                description="Search the web for information",
                category=ToolCategory.SEARCH,
                handler=self._tool_web_search,
                is_async=True,
                parameters={"query": "Search query"},
            )
        )
        
        # Python execution
        self.register_tool(
            ToolDefinition(
                name="python_exec",
                description="Execute Python code in a secure sandbox",
                category=ToolCategory.CODE,
                handler=self._tool_python_exec,
                is_async=False,
                requires_sandbox=True,
                allowed_tiers={"pro", "enterprise"},
                parameters={"code": "Python code to execute"},
            )
        )
        
        # Knowledge lookup
        self.register_tool(
            ToolDefinition(
                name="knowledge_lookup",
                description="Look up information from the knowledge base",
                category=ToolCategory.KNOWLEDGE,
                handler=self._tool_knowledge_lookup,
                is_async=False,
                allowed_tiers={"pro", "enterprise"},
                parameters={"query": "Query to search in knowledge base"},
            )
        )
        
        # Date/time
        self.register_tool(
            ToolDefinition(
                name="datetime",
                description="Get current date and time information",
                category=ToolCategory.COMPUTE,
                handler=self._tool_datetime,
                is_async=False,
                parameters={"format": "Optional datetime format string"},
            )
        )
        
        # Unit conversion
        self.register_tool(
            ToolDefinition(
                name="convert",
                description="Convert between units",
                category=ToolCategory.COMPUTE,
                handler=self._tool_unit_convert,
                is_async=False,
                parameters={
                    "value": "Numeric value to convert",
                    "from_unit": "Source unit",
                    "to_unit": "Target unit",
                },
            )
        )
        
        # Spell check
        self.register_tool(
            ToolDefinition(
                name="spell_check",
                description="Check text for spelling errors and get corrections",
                category=ToolCategory.COMPUTE,
                handler=self._tool_spell_check,
                is_async=False,
                parameters={
                    "text": "Text to check for spelling errors",
                    "mode": "Optional: 'suggest', 'auto_correct', or 'highlight'",
                },
            )
        )
    
    def register_tool(self, definition: ToolDefinition) -> None:
        """Register a new tool."""
        self.tool_definitions[definition.name] = definition
        self.tools[definition.name] = definition.handler
        logger.info("Registered tool: %s (%s)", definition.name, definition.category.value)
    
    def list_tools(self, user_tier: str = "free") -> List[Dict[str, Any]]:
        """
        List available tools for a user tier.
        
        Args:
            user_tier: User's account tier
            
        Returns:
            List of tool information dictionaries
        """
        tier = user_tier.lower()
        allowed = self.tier_tools.get(tier, self.tier_tools["free"])
        
        result = []
        for name, defn in self.tool_definitions.items():
            if name in allowed or tier in defn.allowed_tiers:
                result.append({
                    "name": name,
                    "description": defn.description,
                    "category": defn.category.value,
                    "parameters": defn.parameters,
                })
        
        return result
    
    def is_tool_request(self, text: str) -> bool:
        """
        Check if text contains a tool request.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains a tool request
        """
        if not text:
            return False
        
        text = text.strip()
        
        # Check for [TOOL:name] pattern
        if self.TOOL_PATTERN.match(text):
            return True
        
        # Check for JSON tool format
        if self.JSON_TOOL_PATTERN.search(text):
            return True
        
        return False
    
    def parse_tool_request(self, text: str) -> Optional[ToolRequest]:
        """
        Parse a tool request from text.
        
        Supports formats:
        - [TOOL:calculator] 5 * 7
        - {"tool": "calculator", "args": "5 * 7"}
        
        Args:
            text: Text containing tool request
            
        Returns:
            ToolRequest or None if not a valid request
        """
        if not text:
            return None
        
        text = text.strip()
        
        # Try [TOOL:name] format
        match = self.TOOL_PATTERN.match(text)
        if match:
            tool_name = match.group(1).lower()
            arguments = match.group(2).strip()
            return ToolRequest(
                tool_name=tool_name,
                arguments=arguments,
                raw_request=text,
            )
        
        # Try JSON format
        try:
            # Find JSON object in text
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                tool_name = data.get("tool", "").lower()
                arguments = data.get("args", data.get("arguments", ""))
                
                if isinstance(arguments, dict):
                    arguments = json.dumps(arguments)
                
                if tool_name:
                    return ToolRequest(
                        tool_name=tool_name,
                        arguments=str(arguments),
                        raw_request=text,
                        metadata=data,
                    )
        except json.JSONDecodeError:
            pass
        
        return None
    
    def handle_tool_request(
        self,
        request: Union[str, ToolRequest],
        user_tier: str = "free",
    ) -> ToolResult:
        """
        Handle a tool request (synchronous).
        
        Args:
            request: Tool request string or ToolRequest object
            user_tier: User's account tier
            
        Returns:
            ToolResult with execution result
        """
        import time
        start_time = time.time()
        
        # Parse if string
        if isinstance(request, str):
            parsed = self.parse_tool_request(request)
            if parsed is None:
                return ToolResult(
                    tool_name="unknown",
                    success=False,
                    result=None,
                    error="Invalid tool request format. Use [TOOL:name] arguments or JSON format.",
                )
            request = parsed
        
        tool_name = request.tool_name
        arguments = request.arguments
        
        # Check if tool exists
        if tool_name not in self.tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Unknown tool: {tool_name}. Available tools: {list(self.tools.keys())}",
            )
        
        # Check tier access
        tier = user_tier.lower()
        allowed_tools = self.tier_tools.get(tier, self.tier_tools["free"])
        defn = self.tool_definitions.get(tool_name)
        
        if tool_name not in allowed_tools and (not defn or tier not in defn.allowed_tiers):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not available for tier '{tier}'. Upgrade to access.",
            )
        
        # Check sandbox requirement
        if defn and defn.requires_sandbox and not self.sandbox:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' requires sandbox which is not available.",
            )
        
        # Execute tool
        try:
            tool_func = self.tools[tool_name]
            import inspect
            
            if inspect.iscoroutinefunction(tool_func):
                # For sync context, we can't await - return error
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    error=f"Tool '{tool_name}' is async. Use handle_tool_request_async() instead.",
                )
            
            result = tool_func(arguments)
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            logger.error("Tool execution failed for %s: %s", tool_name, e)
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    async def handle_tool_request_async(
        self,
        request: Union[str, ToolRequest],
        user_tier: str = "free",
    ) -> ToolResult:
        """
        Handle a tool request (asynchronous).
        
        Args:
            request: Tool request string or ToolRequest object
            user_tier: User's account tier
            
        Returns:
            ToolResult with execution result
        """
        import time
        start_time = time.time()
        
        # Parse if string
        if isinstance(request, str):
            parsed = self.parse_tool_request(request)
            if parsed is None:
                return ToolResult(
                    tool_name="unknown",
                    success=False,
                    result=None,
                    error="Invalid tool request format.",
                )
            request = parsed
        
        tool_name = request.tool_name
        arguments = request.arguments
        
        # Check if tool exists
        if tool_name not in self.tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Unknown tool: {tool_name}",
            )
        
        # Check tier access
        tier = user_tier.lower()
        allowed_tools = self.tier_tools.get(tier, self.tier_tools["free"])
        defn = self.tool_definitions.get(tool_name)
        
        if tool_name not in allowed_tools and (not defn or tier not in defn.allowed_tiers):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not available for tier '{tier}'.",
            )
        
        # Execute tool
        try:
            tool_func = self.tools[tool_name]
            import inspect
            
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(arguments)
            else:
                result = tool_func(arguments)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            logger.error("Tool execution failed for %s: %s", tool_name, e)
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    # ==========================================================================
    # Tool Implementations
    # ==========================================================================
    
    def _tool_calculator(self, expression: str) -> str:
        """
        Calculator tool: Safely evaluate math expression.
        
        Args:
            expression: Math expression
            
        Returns:
            Result as string
        """
        result = self.calculator.evaluate(expression)
        return str(result)
    
    async def _tool_web_search(self, query: str) -> str:
        """
        Web search tool: Search the web for information.
        
        Args:
            query: Search query
            
        Returns:
            Search results summary
        """
        if not self.web_research:
            return "Web search not available."
        
        try:
            results = await self.web_research.search(query)
            
            if not results:
                return "No results found."
            
            # Format results
            output_parts = []
            for i, doc in enumerate(results[:3], 1):
                title = getattr(doc, 'title', 'No title')
                snippet = getattr(doc, 'snippet', '') or ""
                url = getattr(doc, 'url', '')
                
                output_parts.append(f"{i}. {title}")
                if snippet:
                    output_parts.append(f"   {snippet[:200]}")
                if url:
                    output_parts.append(f"   URL: {url}")
            
            return "\n".join(output_parts)
            
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return f"Web search error: {e}"
    
    def _tool_python_exec(self, code: str) -> str:
        """
        Python execution tool: Execute code in sandbox.
        
        Args:
            code: Python code
            
        Returns:
            Execution output or error
        """
        if not self.sandbox:
            return "Python execution not available: sandbox disabled."
        
        try:
            output, success, error = self.sandbox.execute_python(code)
            
            if success:
                return output if output else "Execution completed (no output)"
            else:
                return f"Execution error: {error}"
                
        except Exception as e:
            logger.error("Python execution failed: %s", e)
            return f"Execution error: {e}"
    
    def _tool_knowledge_lookup(self, query: str) -> str:
        """
        Knowledge lookup tool: Search internal knowledge base.
        
        Args:
            query: Query to search
            
        Returns:
            Relevant knowledge or message
        """
        if not self.memory_manager:
            return "Knowledge base not available."
        
        try:
            hits = self.memory_manager.query_memory(
                query_text=query,
                top_k=3,
                min_score=0.6,
            )
            
            if not hits:
                return "No relevant knowledge found."
            
            output_parts = ["Found relevant knowledge:"]
            for i, hit in enumerate(hits, 1):
                text = hit.text[:300] if hasattr(hit, 'text') else str(hit)[:300]
                score = hit.score if hasattr(hit, 'score') else 0
                output_parts.append(f"{i}. (Score: {score:.2f}) {text}")
            
            return "\n".join(output_parts)
            
        except Exception as e:
            logger.error("Knowledge lookup failed: %s", e)
            return f"Knowledge lookup error: {e}"
    
    def _tool_datetime(self, format_str: str = "") -> str:
        """
        Datetime tool: Get current date/time.
        
        Args:
            format_str: Optional format string
            
        Returns:
            Formatted datetime string
        """
        from datetime import datetime
        
        now = datetime.now()
        
        if format_str.strip():
            try:
                return now.strftime(format_str.strip())
            except ValueError as e:
                return f"Invalid format: {e}. Using default."
        
        # Default format
        return now.strftime("%Y-%m-%d %H:%M:%S (%A)")
    
    def _tool_unit_convert(self, args: str) -> str:
        """
        Unit conversion tool: Convert between units.
        
        Args:
            args: "value from_unit to_unit" (e.g., "100 km miles")
            
        Returns:
            Conversion result
        """
        # Conversion factors (to base units)
        # Length -> meters
        LENGTH = {
            "m": 1.0, "meter": 1.0, "meters": 1.0,
            "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
            "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
            "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
            "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
            "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
            "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
            "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
        }
        
        # Weight -> grams
        WEIGHT = {
            "g": 1.0, "gram": 1.0, "grams": 1.0,
            "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
            "mg": 0.001, "milligram": 0.001, "milligrams": 0.001,
            "lb": 453.592, "pound": 453.592, "pounds": 453.592,
            "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
        }
        
        # Temperature (special handling)
        TEMPERATURE = {"c", "celsius", "f", "fahrenheit", "k", "kelvin"}
        
        # Parse args
        parts = args.lower().split()
        if len(parts) < 3:
            return "Usage: value from_unit to_unit (e.g., 100 km miles)"
        
        try:
            value = float(parts[0])
            from_unit = parts[1]
            to_unit = parts[2] if len(parts) > 2 else parts[1]
        except ValueError:
            return "Invalid value. Please provide a number."
        
        # Check for temperature
        if from_unit in TEMPERATURE or to_unit in TEMPERATURE:
            return self._convert_temperature(value, from_unit, to_unit)
        
        # Find conversion category
        if from_unit in LENGTH and to_unit in LENGTH:
            base = value * LENGTH[from_unit]
            result = base / LENGTH[to_unit]
        elif from_unit in WEIGHT and to_unit in WEIGHT:
            base = value * WEIGHT[from_unit]
            result = base / WEIGHT[to_unit]
        else:
            return f"Cannot convert between {from_unit} and {to_unit}. Unsupported units."
        
        return f"{value} {from_unit} = {result:.6g} {to_unit}"
    
    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> str:
        """Convert temperature between units."""
        # Normalize unit names
        from_u = from_unit[0].lower()
        to_u = to_unit[0].lower()
        
        # Convert to Celsius first
        if from_u == 'c':
            celsius = value
        elif from_u == 'f':
            celsius = (value - 32) * 5/9
        elif from_u == 'k':
            celsius = value - 273.15
        else:
            return f"Unknown temperature unit: {from_unit}"
        
        # Convert from Celsius to target
        if to_u == 'c':
            result = celsius
            unit_name = "°C"
        elif to_u == 'f':
            result = celsius * 9/5 + 32
            unit_name = "°F"
        elif to_u == 'k':
            result = celsius + 273.15
            unit_name = "K"
        else:
            return f"Unknown temperature unit: {to_unit}"
        
        return f"{value} {from_unit} = {result:.2f} {unit_name}"
    
    def _tool_spell_check(self, args: str) -> str:
        """
        Spell check tool: Check text for spelling errors.
        
        Args:
            args: Text to check, optionally followed by | mode=suggest/auto_correct/highlight
            
        Returns:
            Spell check results with corrections
        """
        try:
            from .tools.spell_check import spell_check_tool, SpellCheckMode
            
            # Parse args for mode
            mode = "auto_correct"
            text = args
            
            if "|" in args:
                parts = args.split("|", 1)
                text = parts[0].strip()
                mode_part = parts[1].strip().lower()
                if "suggest" in mode_part:
                    mode = "suggest"
                elif "highlight" in mode_part:
                    mode = "highlight"
                elif "auto" in mode_part or "correct" in mode_part:
                    mode = "auto_correct"
            
            result = spell_check_tool(text, mode)
            
            if result["error_count"] == 0:
                return f"✓ No spelling errors found in: \"{text}\""
            
            # Format output
            output_parts = [f"Found {result['error_count']} spelling error(s):"]
            
            for error in result["errors"]:
                suggestions = ", ".join(error["suggestions"][:3]) if error["suggestions"] else "no suggestions"
                output_parts.append(f"  • \"{error['word']}\" → {suggestions}")
            
            if result["was_corrected"]:
                output_parts.append(f"\nCorrected text: \"{result['corrected']}\"")
            
            return "\n".join(output_parts)
            
        except Exception as e:
            logger.warning("Spell check failed: %s", e)
            return f"Spell check error: {str(e)}"
    
    # ==========================================================================
    # Orchestrator Integration Helpers
    # ==========================================================================
    
    def extract_tool_calls(self, model_output: str) -> List[Tuple[int, int, ToolRequest]]:
        """
        Extract all tool calls from model output.
        
        Args:
            model_output: Model's text output
            
        Returns:
            List of (start_pos, end_pos, ToolRequest) tuples
        """
        tool_calls = []
        
        # Find [TOOL:name] patterns
        for match in re.finditer(r'\[TOOL:(\w+)\]([^\[]*?)(?=\[TOOL:|$)', model_output, re.DOTALL):
            start = match.start()
            end = match.end()
            tool_name = match.group(1).lower()
            arguments = match.group(2).strip()
            
            tool_calls.append((
                start,
                end,
                ToolRequest(
                    tool_name=tool_name,
                    arguments=arguments,
                    raw_request=match.group(0),
                ),
            ))
        
        return tool_calls
    
    async def process_model_output_with_tools(
        self,
        model_output: str,
        user_tier: str = "free",
        max_tool_calls: int = 5,
    ) -> Tuple[str, List[ToolResult]]:
        """
        Process model output, executing any tool calls found.
        
        Args:
            model_output: Model's raw output
            user_tier: User's account tier
            max_tool_calls: Maximum tool calls to execute
            
        Returns:
            Tuple of (processed_output, list_of_tool_results)
        """
        tool_calls = self.extract_tool_calls(model_output)
        
        if not tool_calls:
            return model_output, []
        
        # Limit tool calls
        tool_calls = tool_calls[:max_tool_calls]
        
        results = []
        processed_output = model_output
        
        # Process in reverse order to maintain positions
        for start, end, request in reversed(tool_calls):
            result = await self.handle_tool_request_async(request, user_tier)
            results.append(result)
            
            # Replace tool call with result
            if result.success:
                replacement = f"[Tool Result ({request.tool_name})]: {result.result}"
            else:
                replacement = f"[Tool Error ({request.tool_name})]: {result.error}"
            
            processed_output = (
                processed_output[:start] + replacement + processed_output[end:]
            )
        
        # Reverse results to match original order
        results.reverse()
        
        return processed_output, results


# ==============================================================================
# Global Instance and Helpers
# ==============================================================================

_tool_broker: Optional[ToolBroker] = None


def get_tool_broker() -> ToolBroker:
    """Get global tool broker instance."""
    global _tool_broker
    if _tool_broker is None:
        _tool_broker = ToolBroker()
    return _tool_broker


def reset_tool_broker() -> None:
    """Reset global tool broker instance."""
    global _tool_broker
    _tool_broker = None
