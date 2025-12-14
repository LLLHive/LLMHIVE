"""Enhanced Tool Broker Module for LLMHive Elite Orchestrator.

Implements ReAct-style tool integration with advanced capabilities:
- Web search (real-time information retrieval)
- Calculator (mathematical computations)
- Code execution (testing and validation)
- Database queries (structured data retrieval)
- Image generation (text-to-image)
- Tool chaining (sequential execution with dependencies)

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
    DATABASE = "database"               # Legacy DB access
    WEB_BROWSER = "web_browser"         # Fetch full page content
    DOC_QA = "doc_qa"                   # Question answering over provided doc
    IMAGE_GENERATION = "image_generation"  # text-to-image
    KNOWLEDGE_BASE = "knowledge_base"  # RAG lookup
    VISION = "vision"  # general image caption/OCR


class ToolPriority(str, Enum):
    """Tool usage priority levels."""
    CRITICAL = "critical"  # Must use - query depends on it
    HIGH = "high"  # Strongly recommended
    MEDIUM = "medium"  # Would improve answer
    LOW = "low"  # Optional enhancement


class ToolStatus(str, Enum):
    """Status of tool execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    PENDING = "pending"


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
    depends_on: Optional[List[ToolType]] = None  # New: dependencies


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
    status: ToolStatus = ToolStatus.SUCCESS


@dataclass(slots=True)
class ToolAnalysis:
    """Analysis of which tools are needed for a query."""
    requires_tools: bool
    tool_requests: List[ToolRequest]
    reasoning: str
    has_dependencies: bool = False  # New: indicates chained execution needed
    trace: List[str] = field(default_factory=list)  # Tool types suggested


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
                    status=ToolStatus.SUCCESS,
                )
            else:
                # Placeholder - in production, integrate with actual search API
                return ToolResult(
                    tool_type=self.tool_type,
                    success=False,
                    data=None,
                    error_message="Web search not configured",
                    latency_ms=(time.time() - start_time) * 1000,
                    status=ToolStatus.FAILED,
                )
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
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
                    status=ToolStatus.FAILED,
                )
            
            # Check for variable substitution from context
            context_values = kwargs.get("context_values", {})
            for var, val in context_values.items():
                sanitized = sanitized.replace(var, str(val))
            
            # Evaluate safely
            result = self._safe_eval(sanitized)
            
            return ToolResult(
                tool_type=self.tool_type,
                success=True,
                data={"expression": sanitized, "result": result},
                latency_ms=(time.time() - start_time) * 1000,
                source="calculator",
                status=ToolStatus.SUCCESS,
            )
        except Exception as e:
            logger.error("Calculation failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
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
        self._available = True  # Always available for syntax checking
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.CODE_EXECUTION
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute code."""
        start_time = time.time()
        language = kwargs.get('language', 'python')
        
        try:
            if self._executor_fn:
                result = await self._executor_fn(query, language=language)
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=result,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="code_execution",
                    status=ToolStatus.SUCCESS,
                )
            else:
                # Basic Python execution in sandbox
                if language in ["python", "py"]:
                    exec_result = await self._safe_python_exec(query)
                    return ToolResult(
                        tool_type=self.tool_type,
                        success=exec_result.get("success", False),
                        data=exec_result,
                        latency_ms=(time.time() - start_time) * 1000,
                        source="code_execution",
                        status=ToolStatus.SUCCESS if exec_result.get("success") else ToolStatus.FAILED,
                    )
                else:
                    return ToolResult(
                        tool_type=self.tool_type,
                        success=False,
                        data=None,
                        error_message=f"Execution not supported for language: {language}",
                        latency_ms=(time.time() - start_time) * 1000,
                        status=ToolStatus.FAILED,
                    )
        except Exception as e:
            logger.error("Code execution failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
    
    async def _safe_python_exec(self, code: str) -> Dict[str, Any]:
        """Execute Python code in a restricted sandbox."""
        result = {"success": True, "output": None, "error": None}
        try:
            # Use MCP2 sandbox if available
            from ..mcp2.sandbox import CodeSandbox, SandboxConfig
            cfg = SandboxConfig(timeout_seconds=5.0, memory_limit_mb=256, allow_network=False)
            sandbox = CodeSandbox(cfg, session_token="tool_broker")
            exec_result = await sandbox.execute_python(code)
            result["output"] = exec_result.get("stdout", "") or exec_result.get("result")
            if exec_result.get("stderr"):
                result["error"] = exec_result.get("stderr")
                result["success"] = False
        except Exception as e:
            result["success"] = False
            result["error"] = f"Sandbox error: {e}"
        return result


class ImageGenerationTool(BaseTool):
    """Image generation tool for text-to-image creation."""
    
    def __init__(self, generator_fn: Optional[Callable] = None):
        """Initialize with optional custom generator function."""
        self._generator_fn = generator_fn
        self._available = True
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.IMAGE_GENERATION
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Generate an image from text prompt."""
        start_time = time.time()
        
        try:
            if self._generator_fn:
                # Use provided generator (e.g., DALL-E, Stable Diffusion API)
                result = await self._generator_fn(query, **kwargs)
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=result,  # Could be URL or base64
                    latency_ms=(time.time() - start_time) * 1000,
                    source="image_generation",
                    status=ToolStatus.SUCCESS,
                )
            else:
                # Placeholder response
                placeholder = {
                    "status": "placeholder",
                    "prompt": query,
                    "message": f"[Image generated of: {query}]",
                    "markdown": f"![Generated image: {query[:50]}...](placeholder_image.png)",
                }
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=placeholder,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="image_generation_placeholder",
                    status=ToolStatus.SUCCESS,
                )
        except Exception as e:
            logger.error("Image generation failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )


class KnowledgeBaseTool(BaseTool):
    """Knowledge base tool for RAG lookups."""
    
    def __init__(self, retriever_fn: Optional[Callable] = None):
        """Initialize with optional retriever function."""
        self._retriever_fn = retriever_fn
        self._available = retriever_fn is not None
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.KNOWLEDGE_BASE
    
    def is_available(self) -> bool:
        return self._available
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Retrieve from knowledge base."""
        start_time = time.time()
        
        try:
            if self._retriever_fn:
                results = await self._retriever_fn(query, **kwargs)
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=results,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="knowledge_base",
                    status=ToolStatus.SUCCESS,
                )
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message="Retriever unavailable",
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
        except Exception as e:
            logger.warning("KnowledgeBaseTool failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )


class WebBrowserTool(BaseTool):
    """Fetch full page content (text-only) for a given URL."""
    
    def __init__(self, fetch_fn: Optional[Callable] = None):
        self._fetch_fn = fetch_fn
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.WEB_BROWSER
    
    def is_available(self) -> bool:
        return True
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        start_time = time.time()
        url = query.strip()
        try:
            if self._fetch_fn:
                content = await self._fetch_fn(url)
            else:
                import requests
                resp = requests.get(url, timeout=10)
                text = resp.text
                content = self._strip_html(text)
            return ToolResult(
                tool_type=self.tool_type,
                success=True,
                data=content[:5000],  # limit size
                latency_ms=(time.time() - start_time) * 1000,
                source="web_browser",
                status=ToolStatus.SUCCESS,
            )
        except Exception as e:
            logger.warning("WebBrowserTool failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
    
    def _strip_html(self, html: str) -> str:
        """Basic tag stripper using regex; avoids extra deps."""
        import re
        text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


class DocumentQATool(BaseTool):
    """Lightweight QA over provided document text."""
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.DOC_QA
    
    def is_available(self) -> bool:
        return True
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        start_time = time.time()
        doc = kwargs.get("document") or kwargs.get("doc") or ""
        question = query
        if not doc:
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message="No document provided",
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
        try:
            answer = self._qa(doc, question)
            return ToolResult(
                tool_type=self.tool_type,
                success=True,
                data=answer,
                latency_ms=(time.time() - start_time) * 1000,
                source="doc_qa",
                status=ToolStatus.SUCCESS,
            )
        except Exception as e:
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
    
    def _qa(self, doc: str, question: str) -> str:
        """Heuristic QA: return top sentences matching keywords."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', doc)
        q_tokens = set(question.lower().split())
        scored = []
        for s in sentences:
            st = s.strip()
            if not st:
                continue
            s_tokens = set(st.lower().split())
            score = len(q_tokens & s_tokens)
            scored.append((score, st))
        scored.sort(reverse=True, key=lambda x: x[0])
        top = [s for _, s in scored[:3]]
        return "\n".join(top) if top else "No relevant content found in document."


class DatabaseQueryTool(BaseTool):
    """Stub/guarded database query tool (read-only)."""
    
    def __init__(self, query_fn: Optional[Callable] = None, enabled: bool = False, max_rows: int = 200, timeout_seconds: float = 5.0):
        self._query_fn = query_fn
        self._enabled = enabled
        self._max_rows = max_rows
        self._timeout = timeout_seconds
    
    @property
    def tool_type(self) -> ToolType:
        return ToolType.DATABASE
    
    def is_available(self) -> bool:
        return self._enabled and self._query_fn is not None
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        start_time = time.time()
        if not self.is_available():
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message="Database tool not configured",
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
        try:
            import asyncio
            result = await asyncio.wait_for(self._query_fn(query), timeout=self._timeout)
            # Enforce row limit if result is list-like
            if isinstance(result, list) and len(result) > self._max_rows:
                result = result[: self._max_rows]
            return ToolResult(
                tool_type=self.tool_type,
                success=True,
                data=result,
                latency_ms=(time.time() - start_time) * 1000,
                source="database",
                status=ToolStatus.SUCCESS,
            )
        except Exception as e:
            logger.warning("Database tool failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )


# ==============================================================================
# Tool Broker Implementation
# ==============================================================================

class ToolBroker:
    """
    Enhanced Tool Broker for LLMHive Elite Orchestrator.
    
    Responsibilities:
    1. Analyze queries to determine tool requirements
    2. Execute tools in parallel when possible
    3. Handle tool chaining with dependencies
    4. Integrate tool outputs into orchestration context
    5. Handle tool failures gracefully
    """
    
    # Expanded keywords that trigger tool usage
    SEARCH_TRIGGERS = [
        # Time-sensitive
        "latest", "current", "recent", "today", "2024", "2025", "2026",
        "news", "update", "now", "real-time", "live", "right now",
        "as of", "this year", "this month", "this week",
        # Rankings and lists (often need current data)
        "top 10", "top 5", "top 20", "best", "leading", "ranking",
        "most popular", "highest rated", "number one", "#1",
        # Technology/fast-changing domains
        "llm", "ai model", "gpt", "claude", "gemini", "chatgpt",
        "cryptocurrency", "bitcoin", "stock", "market",
        # Factual queries
        "who is", "when did", "what year", "where is",
        "how many", "population of", "price of", "stock price",
        "weather", "score", "result", "statistics",
        # Verification
        "is it true", "fact check", "verify", "confirm",
        # Explicit current data requests
        "no old data", "current data", "up to date", "updated",
    ]
    
    CALC_TRIGGERS = [
        "calculate", "compute", "solve", "equation", "formula",
        "percentage", "average", "sum", "difference", "multiply",
        "divide", "total", "how much", "how many", "what is",
        "plus", "minus", "times", "divided by",
    ]
    
    CODE_TRIGGERS = [
        "run this", "execute", "test this code", "debug",
        "compile", "what's the output", "run code", "eval",
    ]
    
    IMAGE_TRIGGERS = [
        "image of", "picture of", "diagram of", "draw",
        "generate image", "create image", "visualize",
        "illustration of", "show me", "create a picture",
    ]
    VISION_TRIGGERS = [".png", ".jpg", ".jpeg", ".gif", "data:image", "image:"]
    
    def __init__(self):
        """Initialize the Tool Broker."""
        self.tools: Dict[ToolType, BaseTool] = {
            ToolType.CALCULATOR: CalculatorTool(),
            ToolType.WEB_SEARCH: WebSearchTool(),
            ToolType.CODE_EXECUTION: CodeExecutionTool(),
            ToolType.IMAGE_GENERATION: ImageGenerationTool(),
            ToolType.WEB_BROWSER: WebBrowserTool(),
            ToolType.DOC_QA: DocumentQATool(),
            ToolType.DATABASE: DatabaseQueryTool(enabled=False),
        }
        
        # Track tool failures for fallback decisions
        self._failure_counts: Dict[ToolType, int] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool implementation."""
        self.tools[tool.tool_type] = tool
        logger.info("Registered tool: %s", tool.tool_type.value)

    def log_failure(self, tool_type: ToolType, error: str, latency_ms: float) -> None:
        logger.warning("Tool failed: %s error=%s latency_ms=%.1f", tool_type.value, error, latency_ms)
    
    def analyze_tool_needs(
        self, 
        query: str, 
        context: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> ToolAnalysis:
        """
        Analyze a query to determine which tools are needed.
        
        Args:
            query: The user's query
            context: Optional additional context
            task_type: Optional task type from PromptOps
            
        Returns:
            ToolAnalysis with required tools and reasoning
        """
        query_lower = query.lower()
        tool_requests: List[ToolRequest] = []
        reasoning_parts: List[str] = []
        has_dependencies = False
        
        # Check for search needs - expanded triggers
        needs_search = any(trigger in query_lower for trigger in self.SEARCH_TRIGGERS)
        
        # Also check for date patterns that indicate current data needed
        # Patterns: 12/6/25, 12/06/2025, December 2025, Dec 2025, etc.
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # 12/6/25 or 12/06/2025
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # 12-6-25 or 12-06-2025
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}',  # December 2025
            r'\d{4}',  # Just a year like 2025
        ]
        if any(re.search(p, query_lower) for p in date_patterns):
            needs_search = True
            reasoning_parts.append("Query contains date reference indicating current data needed")
        
        if needs_search:
            tool_requests.append(ToolRequest(
                tool_type=ToolType.WEB_SEARCH,
                query=self._extract_search_query(query),
                purpose="Retrieve current/real-time information",
                priority=ToolPriority.HIGH,
            ))
            reasoning_parts.append("Query contains time-sensitive or factual keywords requiring web search")
        
        # Also trigger search for factual task types
        if task_type == "factual_question" and not any(r.tool_type == ToolType.WEB_SEARCH for r in tool_requests):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.WEB_SEARCH,
                query=query,
                purpose="Verify factual information",
                priority=ToolPriority.MEDIUM,
            ))
            reasoning_parts.append("Factual question task type - web search for verification")
        
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
        
        # Check for image generation needs
        if any(trigger in query_lower for trigger in self.IMAGE_TRIGGERS):
            image_prompt = self._extract_image_prompt(query)
            tool_requests.append(ToolRequest(
                tool_type=ToolType.IMAGE_GENERATION,
                query=image_prompt,
                purpose="Generate image from description",
                priority=ToolPriority.MEDIUM,
            ))
            reasoning_parts.append("Query requests image generation")

        # Check for vision analysis needs (image inputs)
        if any(trigger in query_lower for trigger in self.VISION_TRIGGERS):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.VISION,
                query=query,
                purpose="Analyze image (caption/OCR)",
                priority=ToolPriority.MEDIUM,
            ))
            reasoning_parts.append("Image detected; added vision analysis")

        # Check for browser fetch needs (explicit URLs)
        if "http://" in query_lower or "https://" in query_lower or "open url" in query_lower or "fetch url" in query_lower:
            url = self._extract_url(query)
            if url:
                tool_requests.append(ToolRequest(
                    tool_type=ToolType.WEB_BROWSER,
                    query=url,
                    purpose="Fetch page content for analysis",
                    priority=ToolPriority.MEDIUM,
                ))
                reasoning_parts.append("Detected URL; added web browser fetch")

        # Check for document QA needs
        if any(k in query_lower for k in ["attached document", "attached file", "pdf", "document below", "doc:"]):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.DOC_QA,
                query=query,
                purpose="Answer based on provided document",
                priority=ToolPriority.MEDIUM,
            ))
            reasoning_parts.append("Document mentioned; added doc QA")
        
        # Check for fact-verification needs (implicit search)
        fact_patterns = [
            r"is it true that",
            r"did .+ really",
            r"verify that",
            r"fact check",
        ]
        if any(re.search(p, query_lower) for p in fact_patterns):
            if not any(r.tool_type == ToolType.WEB_SEARCH for r in tool_requests):
                tool_requests.append(ToolRequest(
                    tool_type=ToolType.WEB_SEARCH,
                    query=query,
                    purpose="Verify factual claims",
                    priority=ToolPriority.MEDIUM,
                ))
                reasoning_parts.append("Query requires fact verification")
        
        # Detect tool chaining needs
        if self._needs_chaining(query_lower, tool_requests):
            has_dependencies = True
            tool_requests = self._setup_dependencies(tool_requests, query)
            reasoning_parts.append("Tools have dependencies - sequential execution required")
        
        return ToolAnalysis(
            requires_tools=len(tool_requests) > 0,
            tool_requests=tool_requests,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No tools required",
            has_dependencies=has_dependencies,
            trace=[tr.tool_type.value for tr in tool_requests],
        )
    
    def _needs_chaining(
        self, 
        query_lower: str, 
        requests: List[ToolRequest]
    ) -> bool:
        """Detect if tools need to be chained."""
        # If we have both search and calculator, might need chaining
        has_search = any(r.tool_type == ToolType.WEB_SEARCH for r in requests)
        has_calc = any(r.tool_type == ToolType.CALCULATOR for r in requests)
        
        # Pattern: "what is X? calculate Y with X"
        if has_search and has_calc:
            # Check if calculation references something that needs lookup
            calc_patterns = [
                r"calculate.*with.*the",
                r"compute.*using.*result",
                r"add.*to.*price",
                r"multiply.*by.*value",
            ]
            if any(re.search(p, query_lower) for p in calc_patterns):
                return True
        
        return False
    
    def _setup_dependencies(
        self, 
        requests: List[ToolRequest],
        query: str,
    ) -> List[ToolRequest]:
        """Set up dependencies between tools for chaining."""
        # Simple heuristic: search comes before calculator
        sorted_requests = []
        
        # Search first
        for r in requests:
            if r.tool_type == ToolType.WEB_SEARCH:
                sorted_requests.append(r)
        
        # Then calculator with dependency
        for r in requests:
            if r.tool_type == ToolType.CALCULATOR:
                r.depends_on = [ToolType.WEB_SEARCH]
                sorted_requests.append(r)
        
        # Then everything else
        for r in requests:
            if r not in sorted_requests:
                sorted_requests.append(r)
        
        return sorted_requests
    
    async def execute_tools(
        self,
        requests: List[ToolRequest],
        parallel: bool = True,
    ) -> Dict[ToolType, ToolResult]:
        """
        Execute multiple tool requests with error handling.
        
        Args:
            requests: List of tool requests
            parallel: Whether to execute in parallel (when no dependencies)
            
        Returns:
            Dictionary mapping tool types to results
        """
        results: Dict[ToolType, ToolResult] = {}
        
        if not requests:
            return results
        
        # Check for dependencies
        has_deps = any(r.depends_on for r in requests)
        
        if parallel and not has_deps:
            # Execute all tools in parallel
            results = await self._execute_parallel(requests)
        else:
            # Execute sequentially with dependency handling
            results = await self._execute_sequential(requests)
        
        return results
    
    async def _execute_parallel(
        self, 
        requests: List[ToolRequest]
    ) -> Dict[ToolType, ToolResult]:
        """Execute tools in parallel."""
        results: Dict[ToolType, ToolResult] = {}
        tasks = []
        request_map = {}
        
        for req in requests:
            tool = self.tools.get(req.tool_type)
            if tool and tool.is_available():
                task = self._execute_with_timeout(tool, req)
                tasks.append(task)
                request_map[id(task)] = req.tool_type
            else:
                results[req.tool_type] = ToolResult(
                    tool_type=req.tool_type,
                    success=False,
                    data=None,
                    error_message=f"Tool {req.tool_type.value} not available",
                    status=ToolStatus.SKIPPED,
                )
        
        if tasks:
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in parallel_results:
                if isinstance(result, ToolResult):
                    results[result.tool_type] = result
                    if not result.success:
                        self._record_failure(result.tool_type)
                elif isinstance(result, Exception):
                    logger.error("Tool execution failed with exception: %s", result)
        
        return results
    
    async def _execute_sequential(
        self, 
        requests: List[ToolRequest]
    ) -> Dict[ToolType, ToolResult]:
        """Execute tools sequentially with dependency handling."""
        results: Dict[ToolType, ToolResult] = {}
        context_values: Dict[str, Any] = {}
        
        for req in requests:
            # Check if dependencies are satisfied
            if req.depends_on:
                deps_met = all(
                    dep in results and results[dep].success 
                    for dep in req.depends_on
                )
                if not deps_met:
                    results[req.tool_type] = ToolResult(
                        tool_type=req.tool_type,
                        success=False,
                        data=None,
                        error_message="Dependencies not satisfied",
                        status=ToolStatus.SKIPPED,
                    )
                    continue
                
                # Extract values from dependencies
                for dep in req.depends_on:
                    if dep in results and results[dep].data:
                        context_values.update(
                            self._extract_context_values(results[dep])
                        )
            
            tool = self.tools.get(req.tool_type)
            if tool and tool.is_available():
                # Add context values to metadata
                req.metadata["context_values"] = context_values
                result = await self._execute_with_timeout(tool, req)
                results[req.tool_type] = result
                
                if not result.success:
                    self._record_failure(req.tool_type)
            else:
                results[req.tool_type] = ToolResult(
                    tool_type=req.tool_type,
                    success=False,
                    data=None,
                    error_message=f"Tool {req.tool_type.value} not available",
                    status=ToolStatus.SKIPPED,
                )
        
        return results
    
    def _extract_context_values(self, result: ToolResult) -> Dict[str, Any]:
        """Extract values from tool result for use in dependent tools."""
        values = {}
        
        if result.tool_type == ToolType.WEB_SEARCH and result.data:
            # Try to extract numbers from search results
            if isinstance(result.data, str):
                numbers = re.findall(r'\$?([\d,]+(?:\.\d+)?)', result.data)
                for i, num in enumerate(numbers[:3]):
                    values[f"search_result_{i}"] = num.replace(",", "")
            elif isinstance(result.data, dict):
                for key, val in result.data.items():
                    if isinstance(val, (int, float)):
                        values[key] = val
        
        return values
    
    async def _execute_with_timeout(
        self,
        tool: BaseTool,
        request: ToolRequest,
    ) -> ToolResult:
        """Execute a tool with timeout and error handling."""
        try:
            result = await asyncio.wait_for(
                tool.execute(request.query, **request.metadata),
                timeout=request.timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("Tool %s timed out after %ss", 
                          request.tool_type.value, request.timeout_seconds)
            return ToolResult(
                tool_type=request.tool_type,
                success=False,
                data=None,
                error_message=f"Tool timed out after {request.timeout_seconds}s",
                status=ToolStatus.TIMEOUT,
            )
        except Exception as e:
            logger.error("Tool %s failed: %s", request.tool_type.value, e)
            return ToolResult(
                tool_type=request.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                status=ToolStatus.FAILED,
            )
    
    def _record_failure(self, tool_type: ToolType) -> None:
        """Record a tool failure for tracking."""
        self._failure_counts[tool_type] = self._failure_counts.get(tool_type, 0) + 1
    
    def format_tool_results(
        self, 
        results: Dict[ToolType, ToolResult],
        include_failures: bool = True,
    ) -> str:
        """
        Format tool results for inclusion in model context.
        
        Args:
            results: Dictionary of tool results
            include_failures: Whether to include failed tool info
            
        Returns:
            Formatted string for model consumption
        """
        if not results:
            return ""
        
        formatted_parts: List[str] = []
        
        for tool_type, result in results.items():
            if result.success:
                # Format successful result
                data_str = self._format_data(result.data)
                formatted_parts.append(
                    f"[TOOL: {tool_type.value}]\n"
                    f"Result: {data_str}\n"
                    f"Source: {result.source or 'N/A'}\n"
                )
            elif include_failures:
                formatted_parts.append(
                    f"[TOOL: {tool_type.value}]\n"
                    f"Status: {result.status.value}\n"
                    f"Note: {result.error_message}\n"
                )
        
        return "\n".join(formatted_parts)
    
    def _format_data(self, data: Any) -> str:
        """Format tool data for context."""
        if data is None:
            return "No data"
        
        if isinstance(data, dict):
            # Handle image generation
            if "markdown" in data:
                return data["markdown"]
            if "result" in data:
                return f"{data.get('expression', '')} = {data['result']}"
            return str(data)
        
        if isinstance(data, list):
            # More content for better LLM understanding
            return "\n".join(str(item)[:500] for item in data[:8])
        
        return str(data)[:1000]
    
    def _extract_search_query(self, query: str) -> str:
        """Extract the core search query from user input."""
        # Remove common question prefixes
        prefixes = [
            "what is the latest",
            "what are the current",
            "find me",
            "search for",
            "look up",
            "tell me about",
            "what is the",
        ]
        
        query_lower = query.lower()
        for prefix in prefixes:
            if query_lower.startswith(prefix):
                return query[len(prefix):].strip()
        
        return query

    def _extract_url(self, query: str) -> str:
        """Extract first URL from query."""
        import re
        match = re.search(r'(https?://[^\s]+)', query)
        if match:
            return match.group(1)
        return query.strip()
    
    def _extract_math_expression(self, query: str) -> Optional[str]:
        """Extract mathematical expression from query."""
        # Look for patterns like "calculate 2+2" or "what is 5*3"
        patterns = [
            r'calculate\s+(.+)',
            r'compute\s+(.+)',
            r'what is\s+([\d\+\-\*\/\.\(\)\%\^\s]+)',
            r'solve\s+(.+)',
            r'([\d\+\-\*\/\.\(\)\%\^\s]+\s*=)',
            r'(\d+\s*[\+\-\*\/\^]\s*\d+(?:\s*[\+\-\*\/\^]\s*\d+)*)',
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
    
    def _extract_image_prompt(self, query: str) -> str:
        """Extract image generation prompt from query."""
        # Remove trigger phrases
        triggers = [
            "create an image of",
            "generate an image of",
            "draw a picture of",
            "create a picture of",
            "image of",
            "picture of",
            "diagram of",
            "draw",
            "show me",
        ]
        
        prompt = query.lower()
        for trigger in triggers:
            if trigger in prompt:
                idx = prompt.find(trigger) + len(trigger)
                return query[idx:].strip()
        
        return query


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


def configure_tool_broker(
    search_fn: Optional[Callable] = None,
    code_executor_fn: Optional[Callable] = None,
    image_generator_fn: Optional[Callable] = None,
    knowledge_retriever_fn: Optional[Callable] = None,
    browser_fetch_fn: Optional[Callable] = None,
    doc_qa_fn: Optional[Callable] = None,
    db_query_fn: Optional[Callable] = None,
    enable_db: bool = False,
    vision_fn: Optional[Callable] = None,
    image_gen_fn: Optional[Callable] = None,
) -> ToolBroker:
    """Configure the global tool broker with custom functions."""
    global _tool_broker
    _tool_broker = ToolBroker()
    
    if search_fn:
        _tool_broker.register_tool(WebSearchTool(search_fn))
    if code_executor_fn:
        _tool_broker.register_tool(CodeExecutionTool(code_executor_fn))
    if image_generator_fn:
        _tool_broker.register_tool(ImageGenerationTool(image_generator_fn))
    elif image_gen_fn:
        _tool_broker.register_tool(ImageGenerationTool(image_gen_fn))
    else:
        _tool_broker.register_tool(ImageGenerationTool())
    if knowledge_retriever_fn:
        _tool_broker.register_tool(KnowledgeBaseTool(knowledge_retriever_fn))
    if browser_fetch_fn:
        _tool_broker.register_tool(WebBrowserTool(browser_fetch_fn))
    if doc_qa_fn:
        _tool_broker.register_tool(DocumentQATool())
        _tool_broker.tools[ToolType.DOC_QA]._qa = doc_qa_fn  # type: ignore
    if db_query_fn:
        _tool_broker.register_tool(DatabaseQueryTool(db_query_fn, enabled=enable_db))
    # Vision tool registration: use provided fn or placeholder
    from .vision_tool import VisionTool
    if vision_fn:
        _tool_broker.register_tool(VisionTool(vision_fn))
    else:
        _tool_broker.register_tool(VisionTool())
    
    return _tool_broker


async def check_and_execute_tools(
    query: str,
    task_type: Optional[str] = None,
) -> Tuple[bool, str, Dict[ToolType, ToolResult]]:
    """
    Convenience function to check for tool needs and execute.
    
    Returns:
        Tuple of (tools_used: bool, formatted_results: str, raw_results: dict)
    """
    broker = get_tool_broker()
    analysis = broker.analyze_tool_needs(query, task_type=task_type)
    
    if not analysis.requires_tools:
        return False, "", {}
    
    # Execute based on dependencies
    parallel = not analysis.has_dependencies
    results = await broker.execute_tools(analysis.tool_requests, parallel=parallel)
    formatted = broker.format_tool_results(results)
    
    return True, formatted, results
