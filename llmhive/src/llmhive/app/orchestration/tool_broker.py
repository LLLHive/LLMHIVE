"""Enhanced Tool Broker Module for LLMHive Elite Orchestrator.

Implements ReAct-style tool integration with advanced capabilities:
- Web search (real-time information retrieval)
- Calculator (mathematical computations)
- Code execution (testing and validation)
- Database queries (structured data retrieval)
- Image generation (text-to-image)
- Tool chaining (sequential execution with dependencies)

Enhancement-1: Thread-safe operations for concurrent access to shared state.

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
from threading import Lock  # Enhancement-1: use threading lock for sync sections
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
    AUDIO = "audio"  # Q4 2025: speech-to-text transcription


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

class RetrievalMode(str, Enum):
    """PR4: Retrieval mode for RAG operations."""
    FULL = "full"  # Full retrieval with all context
    SHORT = "short"  # Quick retrieval for simple queries
    DEEP = "deep"  # Deep retrieval with multiple passes
    NONE = "none"  # No retrieval needed


@dataclass
class RAGConfig:
    """PR4: Configuration for RAG-based retrieval."""
    mode: RetrievalMode = RetrievalMode.SHORT
    max_chunks: int = 5
    min_relevance_score: float = 0.7
    include_metadata: bool = True
    rerank: bool = False
    time_decay_weight: float = 0.1  # Weight for recency


class ToolBroker:
    """
    Enhanced Tool Broker for LLMHive Elite Orchestrator.
    
    Responsibilities:
    1. Analyze queries to determine tool requirements
    2. Execute tools in parallel when possible
    3. Handle tool chaining with dependencies
    4. Integrate tool outputs into orchestration context
    5. Handle tool failures gracefully
    6. PR4: Decide on RAG retrieval mode (full vs short)
    7. PR4: Route to appropriate external APIs
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
    VISION_TRIGGERS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", "data:image", "image:", "[image]", "attached image", "this image", "the image"]
    
    # Q4 2025: Audio input triggers
    AUDIO_TRIGGERS = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", "audio:", "[audio]", "attached audio", "voice message", "audio file", "recording", "transcribe"]
    
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
        # Enhancement-1: lock to guard shared state
        self._lock = Lock()
        
        # PR4: Memory manager for RAG lookups
        self.memory_manager: Optional[Any] = None
        
        # PR4: External API configurations
        self._api_configs: Dict[str, Dict[str, Any]] = {}
    
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
            # Build metadata for search - add recency filter for temporal queries
            search_metadata = {
                "max_results": 10,  # Get more results for list queries
                "search_depth": "advanced",  # Thorough search
            }
            
            # Detect temporal queries - CRITICAL for current data
            temporal_patterns = [
                r'\b(today|now|current|currently|latest|recent|newest)\b',
                r'\b(this year|this month|this week|2025|2024)\b',
                r'\b(right now|at the moment|presently|these days)\b',
                r'\b(top \d+|best \d+|leading)\b',  # Ranking queries need current data
            ]
            is_temporal = any(re.search(p, query_lower) for p in temporal_patterns)
            
            if is_temporal:
                search_metadata["days"] = 7  # Last 7 days for temporal queries
                search_metadata["topic"] = "news"  # Focus on recent news/updates
                reasoning_parts.append("Temporal query detected - using recency filter (last 7 days)")
            
            tool_requests.append(ToolRequest(
                tool_type=ToolType.WEB_SEARCH,
                query=self._extract_search_query(query),
                purpose="Retrieve current/real-time information",
                priority=ToolPriority.HIGH,
                metadata=search_metadata,  # CRITICAL: Pass recency params
            ))
            reasoning_parts.append("Query contains time-sensitive or factual keywords requiring web search")
        
        # Also trigger search for factual task types
        if task_type == "factual_question" and not any(r.tool_type == ToolType.WEB_SEARCH for r in tool_requests):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.WEB_SEARCH,
                query=query,
                purpose="Verify factual information",
                priority=ToolPriority.MEDIUM,
                metadata={"max_results": 10, "search_depth": "advanced"},
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
        
        # Q4 2025: Check for audio analysis needs (audio inputs)
        if any(trigger in query_lower for trigger in self.AUDIO_TRIGGERS):
            tool_requests.append(ToolRequest(
                tool_type=ToolType.AUDIO,
                query=query,
                purpose="Transcribe audio (speech-to-text)",
                priority=ToolPriority.MEDIUM,
            ))
            reasoning_parts.append("Audio detected; added audio transcription")

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
        """Record a tool failure for tracking (thread-safe)."""
        # Enhancement-1: ensure thread-safe failure count update
        with self._lock:
            self._failure_counts[tool_type] = self._failure_counts.get(tool_type, 0) + 1
        
        # Enhancement-2: Update tool usage metric for failures
        try:
            from ..api.orchestrator_metrics import TOOL_USAGE
            TOOL_USAGE.labels(tool_type=tool_type.value, status="failure").inc()
        except Exception:
            pass  # Metrics not available
    
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
        """Extract the core search query from user input, enhanced for recency."""
        from datetime import datetime
        
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
        clean_query = query
        for prefix in prefixes:
            if query_lower.startswith(prefix):
                clean_query = query[len(prefix):].strip()
                break
        
        # For temporal/ranking queries, add current date for better recency
        temporal_patterns = [
            r'\b(today|now|current|latest|recent|top \d+|best)\b',
            r'\b(this year|this month|2025|2024)\b',
        ]
        import re
        is_temporal = any(re.search(p, query_lower) for p in temporal_patterns)
        
        if is_temporal:
            # Add current month/year to ensure search engines return recent results
            current_date = datetime.now().strftime("%B %Y")  # e.g., "December 2025"
            # Only add date if not already present in query
            if "2025" not in clean_query and "2024" not in clean_query:
                clean_query = f"{clean_query} {current_date}"
                logger.info(f"Enhanced search query with date: '{clean_query}'")
        
        return clean_query

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
    
    # ==========================================================================
    # PR4: Additional Methods for Tool Integration
    # ==========================================================================
    
    def list_tools(self) -> List[str]:
        """List all registered tools."""
        return [t.value for t in self.tools.keys()]
    
    def is_tool_request(self, content: str) -> bool:
        """
        PR4: Check if model output contains a tool request.
        
        Detects patterns like:
        - [TOOL:web_search] query
        - <tool>calculator</tool>
        - ```tool:code_execution
        """
        content_lower = content.lower()
        
        # Pattern 1: [TOOL:type] or [tool:type]
        if re.search(r'\[tool:\w+\]', content_lower):
            return True
        
        # Pattern 2: <tool>type</tool>
        if re.search(r'<tool>\w+</tool>', content_lower):
            return True
        
        # Pattern 3: ```tool:type
        if re.search(r'```tool:\w+', content_lower):
            return True
        
        # Pattern 4: ACTION: TOOL_NAME
        if re.search(r'action:\s*(search|calculate|execute|browse)', content_lower):
            return True
        
        return False
    
    async def process_model_output_with_tools(
        self,
        content: str,
        *,
        user_tier: str = "free",
        max_tool_calls: int = 5,
    ) -> Tuple[str, List[ToolResult]]:
        """
        PR4: Process model output that contains tool calls.
        
        Extracts tool calls from the model output, executes them,
        and replaces the tool call markers with results.
        
        Args:
            content: Model output containing tool calls
            user_tier: User tier for access control
            max_tool_calls: Maximum number of tool calls to process
            
        Returns:
            Tuple of (processed_content, list of tool results)
        """
        tool_results: List[ToolResult] = []
        processed_content = content
        tool_calls_found = 0
        
        # Pattern 1: [TOOL:type] query [/TOOL]
        pattern1 = r'\[TOOL:(\w+)\](.*?)\[/TOOL\]'
        matches = re.findall(pattern1, content, re.DOTALL | re.IGNORECASE)
        
        for tool_type_str, query in matches:
            if tool_calls_found >= max_tool_calls:
                break
            
            try:
                tool_type = ToolType(tool_type_str.lower())
                tool = self.tools.get(tool_type)
                
                if tool and tool.is_available():
                    result = await tool.execute(query.strip())
                    tool_results.append(result)
                    
                    # Replace tool call with result
                    replacement = self._format_tool_result_inline(result)
                    processed_content = processed_content.replace(
                        f'[TOOL:{tool_type_str}]{query}[/TOOL]',
                        replacement,
                        1
                    )
                    tool_calls_found += 1
                    
            except (ValueError, KeyError) as e:
                logger.warning("Unknown tool type: %s", tool_type_str)
        
        # Pattern 2: <tool>type</tool><query>text</query>
        pattern2 = r'<tool>(\w+)</tool>\s*<query>(.*?)</query>'
        matches = re.findall(pattern2, content, re.DOTALL | re.IGNORECASE)
        
        for tool_type_str, query in matches:
            if tool_calls_found >= max_tool_calls:
                break
            
            try:
                tool_type = ToolType(tool_type_str.lower())
                tool = self.tools.get(tool_type)
                
                if tool and tool.is_available():
                    result = await tool.execute(query.strip())
                    tool_results.append(result)
                    
                    # Replace tool call with result
                    replacement = self._format_tool_result_inline(result)
                    original = f'<tool>{tool_type_str}</tool><query>{query}</query>'
                    processed_content = processed_content.replace(original, replacement, 1)
                    tool_calls_found += 1
                    
            except (ValueError, KeyError) as e:
                logger.warning("Unknown tool type: %s", tool_type_str)
        
        return processed_content, tool_results
    
    def _format_tool_result_inline(self, result: ToolResult) -> str:
        """Format a tool result for inline replacement."""
        if result.success:
            data_str = self._format_data(result.data)
            return f"[Result: {data_str}]"
        else:
            return f"[Tool failed: {result.error_message}]"
    
    # ==========================================================================
    # PR4: RAG Routing and Retrieval Mode Decision
    # ==========================================================================
    
    def decide_retrieval_mode(
        self,
        query: str,
        context: Optional[str] = None,
        accuracy_level: int = 5,
    ) -> RAGConfig:
        """
        PR4: Decide on the appropriate retrieval mode for a query.
        
        This implements the logic for full vs short retrieval based on
        query complexity, accuracy requirements, and context.
        
        Args:
            query: The user's query
            context: Optional additional context
            accuracy_level: Required accuracy (1-10)
            
        Returns:
            RAGConfig with the appropriate settings
        """
        query_lower = query.lower()
        
        # Start with default config
        config = RAGConfig()
        
        # Analyze query complexity
        word_count = len(query.split())
        has_multiple_questions = query.count('?') > 1 or ' and ' in query_lower
        
        # Check for complexity indicators
        complex_patterns = [
            r'\b(compare|contrast|analyze|evaluate|synthesize)\b',
            r'\b(explain|describe|discuss)\s+\w+\s+\w+',
            r'\b(how does|why does|what causes)\b',
            r'\b(relationship between|difference between)\b',
            r'\b(pros and cons|advantages and disadvantages)\b',
        ]
        is_complex = any(re.search(p, query_lower) for p in complex_patterns)
        
        # Check for simple patterns
        simple_patterns = [
            r'^what is\s+\w+\s*\??$',
            r'^who is\s+',
            r'^when did\s+',
            r'^where is\s+',
            r'^define\s+',
        ]
        is_simple = any(re.search(p, query_lower) for p in simple_patterns)
        
        # Decision logic
        if is_simple and word_count < 10 and accuracy_level <= 5:
            # Short retrieval for simple queries
            config.mode = RetrievalMode.SHORT
            config.max_chunks = 3
            config.rerank = False
            
        elif is_complex or has_multiple_questions or accuracy_level >= 8:
            # Full retrieval for complex queries
            config.mode = RetrievalMode.FULL
            config.max_chunks = 10
            config.rerank = True
            
        elif accuracy_level >= 9 or (is_complex and has_multiple_questions):
            # Deep retrieval for highest accuracy
            config.mode = RetrievalMode.DEEP
            config.max_chunks = 15
            config.rerank = True
            config.min_relevance_score = 0.6
            
        else:
            # Default: short retrieval
            config.mode = RetrievalMode.SHORT
            config.max_chunks = 5
        
        logger.debug(
            "PR4: Decided retrieval mode=%s for query (complexity=%s, accuracy=%d)",
            config.mode.value,
            "complex" if is_complex else "simple",
            accuracy_level,
        )
        
        return config
    
    async def perform_rag_retrieval(
        self,
        query: str,
        config: Optional[RAGConfig] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        PR4: Perform RAG retrieval based on the configured mode.
        
        Args:
            query: The query to retrieve for
            config: RAG configuration (uses default if None)
            namespace: Optional namespace for multi-tenant retrieval
            
        Returns:
            List of retrieved chunks with metadata
        """
        config = config or RAGConfig()
        
        if config.mode == RetrievalMode.NONE:
            return []
        
        if not self.memory_manager:
            logger.warning("PR4: Memory manager not available for RAG retrieval")
            return []
        
        try:
            # Query the knowledge base
            hits = self.memory_manager.query_memory(
                query_text=query,
                top_k=config.max_chunks,
                filter_verified=True,
                namespace=namespace,
            )
            
            # Filter by relevance score
            chunks = []
            for hit in hits:
                if getattr(hit, 'score', 1.0) >= config.min_relevance_score:
                    chunk = {
                        "text": getattr(hit, 'text', str(hit)),
                        "score": getattr(hit, 'score', 1.0),
                        "source": getattr(hit, 'source', None),
                        "metadata": getattr(hit, 'metadata', {}),
                    }
                    chunks.append(chunk)
            
            # Optional: rerank if configured
            if config.rerank and len(chunks) > 1:
                chunks = self._rerank_chunks(chunks, query)
            
            logger.info(
                "PR4: RAG retrieval returned %d chunks (mode=%s)",
                len(chunks),
                config.mode.value,
            )
            
            return chunks
            
        except Exception as e:
            logger.error("PR4: RAG retrieval failed: %s", e)
            return []
    
    def _rerank_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """Simple reranking based on keyword overlap."""
        query_tokens = set(query.lower().split())
        
        def score_chunk(chunk: Dict[str, Any]) -> float:
            text = chunk.get("text", "").lower()
            text_tokens = set(text.split())
            overlap = len(query_tokens & text_tokens)
            original_score = chunk.get("score", 0.5)
            return original_score * 0.7 + (overlap / max(len(query_tokens), 1)) * 0.3
        
        chunks.sort(key=score_chunk, reverse=True)
        return chunks
    
    # ==========================================================================
    # PR4: External API Configuration
    # ==========================================================================
    
    def configure_external_apis(
        self,
        serpapi_key: Optional[str] = None,
        tavily_key: Optional[str] = None,
        browserless_key: Optional[str] = None,
        wolframalpha_key: Optional[str] = None,
    ) -> None:
        """
        PR4: Configure external API keys for tools.
        
        This should be called during initialization with keys from env vars.
        
        Args:
            serpapi_key: SerpAPI key for web search
            tavily_key: Tavily API key for search
            browserless_key: Browserless key for web scraping
            wolframalpha_key: WolframAlpha key for calculations
        """
        if serpapi_key:
            self._api_configs["serpapi"] = {
                "key": serpapi_key,
                "base_url": "https://serpapi.com/search",
            }
            logger.info("PR4: SerpAPI configured")
        
        if tavily_key:
            self._api_configs["tavily"] = {
                "key": tavily_key,
                "base_url": "https://api.tavily.com",
            }
            logger.info("PR4: Tavily API configured")
        
        if browserless_key:
            self._api_configs["browserless"] = {
                "key": browserless_key,
                "base_url": "https://chrome.browserless.io",
            }
            logger.info("PR4: Browserless configured")
        
        if wolframalpha_key:
            self._api_configs["wolframalpha"] = {
                "key": wolframalpha_key,
                "base_url": "http://api.wolframalpha.com/v2",
            }
            logger.info("PR4: WolframAlpha configured")
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for an external API."""
        return self._api_configs.get(api_name)
    
    async def run_tool(
        self,
        tool_type: ToolType,
        query: str,
        **kwargs,
    ) -> ToolResult:
        """
        PR4: Convenience method to run a single tool.
        
        This is the main entry point for programmatic tool invocation.
        
        Args:
            tool_type: Type of tool to run
            query: Query/input for the tool
            **kwargs: Additional arguments for the tool
            
        Returns:
            ToolResult from the tool execution
        """
        tool = self.tools.get(tool_type)
        
        if not tool:
            return ToolResult(
                tool_type=tool_type,
                success=False,
                data=None,
                error_message=f"Tool {tool_type.value} not registered",
                status=ToolStatus.FAILED,
            )
        
        if not tool.is_available():
            return ToolResult(
                tool_type=tool_type,
                success=False,
                data=None,
                error_message=f"Tool {tool_type.value} not available",
                status=ToolStatus.SKIPPED,
            )
        
        try:
            timeout = kwargs.pop("timeout", 30.0)
            result = await asyncio.wait_for(
                tool.execute(query, **kwargs),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                tool_type=tool_type,
                success=False,
                data=None,
                error_message=f"Tool timed out after {timeout}s",
                status=ToolStatus.TIMEOUT,
            )
        except Exception as e:
            logger.error("PR4: Tool execution failed: %s", e)
            return ToolResult(
                tool_type=tool_type,
                success=False,
                data=None,
                error_message=str(e),
                status=ToolStatus.FAILED,
            )


# ==============================================================================
# Convenience Functions
# ==============================================================================

# Global tool broker instance with thread-safe access (Enhancement-1)
_tool_broker: Optional[ToolBroker] = None
_tool_broker_lock = Lock()  # Enhancement-1: lock to prevent race on instantiation


def get_tool_broker() -> ToolBroker:
    """Get or create the global tool broker instance (thread-safe)."""
    global _tool_broker
    # Enhancement-1: Double-checked locking pattern for thread-safe singleton
    if _tool_broker is None:
        with _tool_broker_lock:
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
