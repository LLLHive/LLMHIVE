"""Tool Broker Module for LLMHive Elite Orchestrator.

Implements ReAct-style tool integration for:
- Web search (real-time information retrieval)
- Calculator (mathematical computations)
- Code execution (testing and validation)
- Database queries (structured data retrieval)

The Tool Broker decides when tools are needed and seamlessly
integrates their outputs into the orchestration pipeline.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """Available tool types."""
    WEB_SEARCH = "web_search"
    CALCULATOR = "calculator"
    CODE_EXECUTION = "code_execution"
    DATABASE = "database"
    IMAGE_ANALYSIS = "image_analysis"


class ToolPriority(str, Enum):
    """Tool usage priority levels."""
    CRITICAL = "critical"  # Must use - query depends on it
    HIGH = "high"  # Strongly recommended
    MEDIUM = "medium"  # Would improve answer
    LOW = "low"  # Optional enhancement


@dataclass(slots=True)
class ToolRequest:
    """A request to use an external tool."""
    tool_type: ToolType
    query: str
    purpose: str
    priority: ToolPriority
    fallback_action: str = "proceed_without"
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """Result from a tool execution."""
    tool_type: ToolType
    success: bool
    data: Any
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    source: Optional[str] = None
    confidence: float = 1.0


@dataclass(slots=True)
class ToolAnalysis:
    """Analysis of which tools are needed for a query."""
    requires_tools: bool
    tool_requests: List[ToolRequest]
    reasoning: str


# ==============================================================================
# Tool Implementations (Abstract Base)
# ==============================================================================

class BaseTool(ABC):
    """Base class for tool implementations."""
    
    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        """Return the tool type."""
        pass
    
    @abstractmethod
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute the tool with the given query."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the tool is available."""
        pass


class WebSearchTool(BaseTool):
    """Web search tool for real-time information retrieval."""
    
    def __init__(self, search_fn: Optional[Callable] = None):
        """Initialize with optional custom search function."""
        self._search_fn = search_fn
        self._available = True
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.WEB_SEARCH
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute web search."""
        start_time = time.time()
        
        try:
            if self._search_fn:
                results = await self._search_fn(query, **kwargs)
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=results,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="web_search",
                )
            else:
                # Placeholder - in production, integrate with actual search API
                return ToolResult(
                    tool_type=self.tool_type,
                    success=False,
                    data=None,
                    error_message="Web search not configured",
                    latency_ms=(time.time() - start_time) * 1000,
                )
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )


class CalculatorTool(BaseTool):
    """Calculator tool for mathematical computations."""
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.CALCULATOR
    
    def is_available(self) -> bool:
        return True  # Always available
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute calculation."""
        start_time = time.time()
        
        try:
            # Sanitize input - only allow safe math operations
            sanitized = self._sanitize_expression(query)
            
            if not sanitized:
                return ToolResult(
                    tool_type=self.tool_type,
                    success=False,
                    data=None,
                    error_message="Invalid mathematical expression",
                    latency_ms=(time.time() - start_time) * 1000,
                )
            
            # Evaluate safely
            result = self._safe_eval(sanitized)
            
            return ToolResult(
                tool_type=self.tool_type,
                success=True,
                data=result,
                latency_ms=(time.time() - start_time) * 1000,
                source="calculator",
            )
        except Exception as e:
            logger.error("Calculation failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    def _sanitize_expression(self, expr: str) -> Optional[str]:
        """Sanitize mathematical expression for safe evaluation."""
        # Remove all whitespace
        expr = expr.replace(" ", "")
        
        # Only allow: numbers, operators, parentheses, decimal points
        if not re.match(r'^[\d\+\-\*\/\.\(\)\%\^]+$', expr):
            # Check for common math functions
            allowed_funcs = ['sqrt', 'sin', 'cos', 'tan', 'log', 'exp', 'abs', 'pow']
            for func in allowed_funcs:
                expr = expr.replace(func, f'__{func}__')
            
            # Re-check after function replacement
            if not re.match(r'^[\d\+\-\*\/\.\(\)\%\^\_a-z]+$', expr):
                return None
            
            # Restore function names
            for func in allowed_funcs:
                expr = expr.replace(f'__{func}__', func)
        
        return expr
    
    def _safe_eval(self, expr: str) -> float:
        """Safely evaluate a mathematical expression."""
        import math
        
        # Replace ^ with ** for exponentiation
        expr = expr.replace('^', '**')
        
        # Safe namespace for evaluation
        safe_dict = {
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'exp': math.exp,
            'abs': abs,
            'pow': pow,
            'pi': math.pi,
            'e': math.e,
        }
        
        return eval(expr, {"__builtins__": {}}, safe_dict)


class CodeExecutionTool(BaseTool):
    """Code execution tool for testing and validation."""
    
    def __init__(self, executor_fn: Optional[Callable] = None):
        """Initialize with optional custom executor."""
        self._executor_fn = executor_fn
        self._available = executor_fn is not None
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.CODE_EXECUTION
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute code."""
        start_time = time.time()
        
        try:
            if self._executor_fn:
                language = kwargs.get('language', 'python')
                result = await self._executor_fn(query, language=language)
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=result,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="code_execution",
                )
            else:
                return ToolResult(
                    tool_type=self.tool_type,
                    success=False,
                    data=None,
                    error_message="Code execution not configured",
                    latency_ms=(time.time() - start_time) * 1000,
                )
        except Exception as e:
            logger.error("Code execution failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )


# ==============================================================================
# Tool Broker Implementation
# ==============================================================================

class ToolBroker:
    """
    Intelligent Tool Broker for LLMHive Elite Orchestrator.
    
    Responsibilities:
    1. Analyze queries to determine tool requirements
    2. Execute tools in parallel when possible
    3. Integrate tool outputs into orchestration context
    4. Handle tool failures gracefully
    """
    
    # Keywords that trigger tool usage
    SEARCH_TRIGGERS = [
        "latest", "current", "recent", "today", "2024", "2025",
        "news", "update", "now", "real-time", "live",
    ]
    
    CALC_TRIGGERS = [
        "calculate", "compute", "solve", "equation", "formula",
        "percentage", "average", "sum", "difference", "multiply",
        "divide", "total", "how much", "how many",
    ]
    
    CODE_TRIGGERS = [
        "run this", "execute", "test this code", "debug",
        "compile", "what's the output",
    ]
    
    def __init__(self):
        """Initialize the Tool Broker."""
        self.tools: Dict[ToolType, BaseTool] = {
            ToolType.CALCULATOR: CalculatorTool(),
            ToolType.WEB_SEARCH: WebSearchTool(),
            ToolType.CODE_EXECUTION: CodeExecutionTool(),
        }
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool implementation."""
        self.tools[tool.tool_type] = tool
        logger.info("Registered tool: %s", tool.tool_type.value)
    
    def analyze_tool_needs(self, query: str, context: Optional[str] = None) -> ToolAnalysis:
        """
        Analyze a query to determine which tools are needed.
        
        Args:
            query: The user's query
            context: Optional additional context
            
        Returns:
            ToolAnalysis with required tools and reasoning
        """
        query_lower = query.lower()
        tool_requests: List[ToolRequest] = []
        reasoning_parts: List[str] = []
        
        # Check for search needs
        if any(trigger in query_lower for trigger in self.SEARCH_TRIGGERS):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.WEB_SEARCH,
                query=self._extract_search_query(query),
                purpose="Retrieve current/real-time information",
                priority=ToolPriority.HIGH,
            ))
            reasoning_parts.append("Query contains time-sensitive keywords requiring web search")
        
        # Check for calculation needs
        if any(trigger in query_lower for trigger in self.CALC_TRIGGERS):
            math_expr = self._extract_math_expression(query)
            if math_expr:
                tool_requests.append(ToolRequest(
                    tool_type=ToolType.CALCULATOR,
                    query=math_expr,
                    purpose="Perform mathematical calculation",
                    priority=ToolPriority.HIGH,
                ))
                reasoning_parts.append("Query requires mathematical computation")
        
        # Check for code execution needs
        if any(trigger in query_lower for trigger in self.CODE_TRIGGERS):
            code = self._extract_code_block(query)
            if code:
                tool_requests.append(ToolRequest(
                    tool_type=ToolType.CODE_EXECUTION,
                    query=code,
                    purpose="Execute and test code",
                    priority=ToolPriority.HIGH,
                ))
                reasoning_parts.append("Query requests code execution/testing")
        
        # Check for fact-verification needs (implicit search)
        fact_patterns = [
            r"is it true that",
            r"did .+ really",
            r"verify that",
            r"fact check",
        ]
        if any(re.search(p, query_lower) for p in fact_patterns):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.WEB_SEARCH,
                query=query,
                purpose="Verify factual claims",
                priority=ToolPriority.MEDIUM,
            ))
            reasoning_parts.append("Query requires fact verification")
        
        return ToolAnalysis(
            requires_tools=len(tool_requests) > 0,
            tool_requests=tool_requests,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No tools required",
        )
    
    async def execute_tools(
        self,
        requests: List[ToolRequest],
        parallel: bool = True,
    ) -> Dict[ToolType, ToolResult]:
        """
        Execute multiple tool requests.
        
        Args:
            requests: List of tool requests
            parallel: Whether to execute in parallel
            
        Returns:
            Dictionary mapping tool types to results
        """
        results: Dict[ToolType, ToolResult] = {}
        
        if not requests:
            return results
        
        if parallel:
            # Execute all tools in parallel
            tasks = []
            for req in requests:
                tool = self.tools.get(req.tool_type)
                if tool and tool.is_available():
                    tasks.append(self._execute_with_timeout(tool, req))
                else:
                    results[req.tool_type] = ToolResult(
                        tool_type=req.tool_type,
                        success=False,
                        data=None,
                        error_message=f"Tool {req.tool_type.value} not available",
                    )
            
            if tasks:
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in parallel_results:
                    if isinstance(result, ToolResult):
                        results[result.tool_type] = result
                    elif isinstance(result, Exception):
                        logger.error("Tool execution failed: %s", result)
        else:
            # Execute sequentially
            for req in requests:
                tool = self.tools.get(req.tool_type)
                if tool and tool.is_available():
                    result = await self._execute_with_timeout(tool, req)
                    results[req.tool_type] = result
                else:
                    results[req.tool_type] = ToolResult(
                        tool_type=req.tool_type,
                        success=False,
                        data=None,
                        error_message=f"Tool {req.tool_type.value} not available",
                    )
        
        return results
    
    async def _execute_with_timeout(
        self,
        tool: BaseTool,
        request: ToolRequest,
    ) -> ToolResult:
        """Execute a tool with timeout handling."""
        try:
            return await asyncio.wait_for(
                tool.execute(request.query, **request.metadata),
                timeout=request.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_type=request.tool_type,
                success=False,
                data=None,
                error_message=f"Tool timed out after {request.timeout_seconds}s",
            )
        except Exception as e:
            return ToolResult(
                tool_type=request.tool_type,
                success=False,
                data=None,
                error_message=str(e),
            )
    
    def format_tool_results(self, results: Dict[ToolType, ToolResult]) -> str:
        """
        Format tool results for inclusion in model context.
        
        Args:
            results: Dictionary of tool results
            
        Returns:
            Formatted string for model consumption
        """
        if not results:
            return ""
        
        formatted_parts: List[str] = []
        
        for tool_type, result in results.items():
            if result.success:
                formatted_parts.append(
                    f"[TOOL: {tool_type.value}]\n"
                    f"Result: {result.data}\n"
                    f"Source: {result.source or 'N/A'}\n"
                )
            else:
                formatted_parts.append(
                    f"[TOOL: {tool_type.value}]\n"
                    f"Status: Failed\n"
                    f"Error: {result.error_message}\n"
                )
        
        return "\n".join(formatted_parts)
    
    def _extract_search_query(self, query: str) -> str:
        """Extract the core search query from user input."""
        # Remove common question prefixes
        prefixes = [
            "what is the latest",
            "what are the current",
            "find me",
            "search for",
            "look up",
        ]
        
        query_lower = query.lower()
        for prefix in prefixes:
            if query_lower.startswith(prefix):
                return query[len(prefix):].strip()
        
        return query
    
    def _extract_math_expression(self, query: str) -> Optional[str]:
        """Extract mathematical expression from query."""
        # Look for patterns like "calculate 2+2" or "what is 5*3"
        patterns = [
            r'calculate\s+(.+)',
            r'compute\s+(.+)',
            r'what is\s+([\d\+\-\*\/\.\(\)\%\^]+)',
            r'solve\s+(.+)',
            r'([\d\+\-\*\/\.\(\)\%\^\s]+\s*=)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                expr = match.group(1).strip()
                # Clean up the expression
                expr = re.sub(r'[^0-9\+\-\*\/\.\(\)\%\^]', '', expr)
                if expr:
                    return expr
        
        return None
    
    def _extract_code_block(self, query: str) -> Optional[str]:
        """Extract code block from query."""
        # Look for code in markdown blocks
        code_match = re.search(r'```(?:\w+)?\n(.*?)```', query, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # Look for inline code
        inline_match = re.search(r'`([^`]+)`', query)
        if inline_match:
            return inline_match.group(1).strip()
        
        return None


# ==============================================================================
# Convenience Functions
# ==============================================================================

# Global tool broker instance
_tool_broker: Optional[ToolBroker] = None


def get_tool_broker() -> ToolBroker:
    """Get or create the global tool broker instance."""
    global _tool_broker
    if _tool_broker is None:
        _tool_broker = ToolBroker()
    return _tool_broker


async def check_and_execute_tools(query: str) -> Tuple[bool, str]:
    """
    Convenience function to check for tool needs and execute.
    
    Returns:
        Tuple of (tools_used: bool, formatted_results: str)
    """
    broker = get_tool_broker()
    analysis = broker.analyze_tool_needs(query)
    
    if not analysis.requires_tools:
        return False, ""
    
    results = await broker.execute_tools(analysis.tool_requests)
    formatted = broker.format_tool_results(results)
    
    return True, formatted

