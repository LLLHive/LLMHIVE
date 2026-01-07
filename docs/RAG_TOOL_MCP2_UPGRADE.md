# LLMHive Architecture Upgrade: RAG, Tools, and Sandbox Enhancements

**Version:** 2.0.0  
**Date:** January 6, 2026  
**Status:** Production Ready

## Overview

This document describes the comprehensive architecture upgrades made to LLMHive's RAG (Retrieval-Augmented Generation), Tool Broker, and MCP2 (Multi-Chain Planning) systems. These changes improve answer accuracy, reduce latency, and enhance system resilience.

## Table of Contents

1. [RAG System Optimizations](#rag-system-optimizations)
2. [Tool Broker Orchestration Upgrades](#tool-broker-orchestration-upgrades)
3. [MCP2 Sandbox and Planner Hardening](#mcp2-sandbox-and-planner-hardening)
4. [Testing Enhancements](#testing-enhancements)
5. [Configuration Guide](#configuration-guide)
6. [Performance Metrics](#performance-metrics)

---

## RAG System Optimizations

### Location
- `llmhive/src/llmhive/app/knowledge/retrieval_engine.py`
- `llmhive/src/llmhive/app/knowledge/query_router.py`

### Features Implemented

#### 1. Hybrid Semantic + Lexical Retrieval

The system now combines dense vector search (semantic) with BM25-based keyword search (lexical):

```
┌─────────────────┐     ┌─────────────────┐
│  User Query     │────▶│  Hybrid Search  │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
           ┌───────────────┐        ┌───────────────┐
           │ Dense Vector  │        │   BM25/TF-IDF │
           │   Search      │        │    Search     │
           │ (70% weight)  │        │ (30% weight)  │
           └───────┬───────┘        └───────┬───────┘
                   │                        │
                   └──────────┬─────────────┘
                              ▼
                    ┌───────────────────┐
                    │   Score Fusion    │
                    └───────────────────┘
```

**Configuration:**
```python
from llmhive.app.knowledge.retrieval_engine import RetrievalConfig

config = RetrievalConfig(
    semantic_weight=0.7,     # Dense vector search weight
    lexical_weight=0.3,      # BM25 keyword search weight
    initial_candidates=20,   # Retrieve more for reranking
    final_top_k=5,
)
```

#### 2. Cross-Encoder Reranking

After initial retrieval, a cross-encoder model reranks documents for improved precision:

- **Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Latency:** ~200ms additional
- **Accuracy Improvement:** 20-35% in precision benchmarks

```python
# Automatic reranking is enabled by default
config = RetrievalConfig(
    enable_reranking=True,
    rerank_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
)
```

#### 3. HyDE (Hypothetical Document Embeddings) Fallback

When top-k retrieved documents have low relevance scores, HyDE generates synthetic documents:

```
┌─────────────────┐
│  Low Relevance  │
│   Detected      │
└────────┬────────┘
         │ (score < 0.4)
         ▼
┌─────────────────┐
│   LLM Generates │
│   Hypothetical  │
│     Answer      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Search Using   │
│  HyDE Embedding │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Merge Results  │
└─────────────────┘
```

**Configuration:**
```python
config = RetrievalConfig(
    enable_hyde=True,
    hyde_threshold=0.4,  # Use HyDE if top score below this
)
```

#### 4. Query Caching

Redis-backed cache with LRU eviction for frequent queries:

```python
from llmhive.app.knowledge.retrieval_engine import RetrievalEngine

engine = RetrievalEngine(
    redis_url="redis://localhost:6379",
    config=RetrievalConfig(
        enable_cache=True,
        cache_ttl_seconds=3600,  # 1 hour
    )
)
```

Falls back to in-memory LRU cache if Redis is unavailable.

#### 5. Context Validation

Validates that retrieved context actually addresses the query:

```python
from llmhive.app.knowledge.retrieval_engine import validate_rag_context

is_valid, filtered_docs, message = validate_rag_context(
    query="What is machine learning?",
    documents=retrieved_docs,
    min_term_overlap=0.2,  # 20% term overlap required
)
```

#### 6. Factoid Fast-Path

Simple factual questions bypass unnecessary clarification:

```python
from llmhive.app.knowledge.query_router import QueryRouter

router = QueryRouter()
decision = router.route("Who discovered penicillin?")

# decision.route == QueryRoute.FACTOID_FAST
# decision.skip_clarification == True
```

---

## Tool Broker Orchestration Upgrades

### Location
- `llmhive/src/llmhive/app/tool_broker.py`

### Features Implemented

#### 1. Semantic Tool Filtering

FAISS-based semantic search selects the most relevant tools:

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embed Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FAISS Search   │
│  (Tool Index)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Top-3 Tools    │
│  (by relevance) │
└─────────────────┘
```

**Configuration:**
```python
from llmhive.app.tool_broker import ToolBroker

broker = ToolBroker(
    embedding_fn=your_embedding_function,
    max_visible_tools=3,  # Only show top 3 relevant tools
)

# Get relevant tools for a query
relevant_tools = broker.get_relevant_tools(
    query="Calculate 15% of 200",
    user_tier="pro",
)
```

#### 2. Enhanced Tool Metadata

Tools now have richer metadata for smart selection:

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    handler: Callable
    # New fields:
    retryable: bool = True           # Can be retried on failure
    max_retries: int = 1             # Maximum retry attempts
    latency_score: float = 0.5       # Expected latency (0=fast, 1=slow)
    failure_policy: str = "fallback" # "fallback", "retry", "abort"
    keywords: List[str]              # Keywords for semantic matching
```

#### 3. Automated Retry and Fallback

Tools automatically retry on transient failures:

```python
result = await broker.handle_tool_request_with_retry(
    request="[TOOL:web_search] latest AI news",
    user_tier="pro",
)

# result.retry_count shows how many retries occurred
# result.fallback_used indicates if fallback was triggered
```

#### 4. Async Parallel Tool Dispatch

Execute independent tools concurrently:

```python
# Execute multiple tools in parallel
results = await broker.execute_tools_parallel(
    requests=[
        "[TOOL:calculator] 15 * 23",
        "[TOOL:web_search] weather today",
        "[TOOL:datetime]",
    ],
    user_tier="pro",
    max_concurrent=5,
)
```

---

## MCP2 Sandbox and Planner Hardening

### Location
- `llmhive/src/llmhive/app/mcp2/sandbox_executor.py`
- `llmhive/src/llmhive/app/mcp2/planner.py`

### Sandbox Enhancements

#### 1. Cold Boot Detection & Pre-warming

```python
from llmhive.app.mcp2.sandbox_executor import EnhancedSandboxExecutor, EnhancedSandboxConfig

config = EnhancedSandboxConfig(
    enable_prewarm=True,
    prewarm_script="import json, datetime, collections, math",
)

executor = EnhancedSandboxExecutor(config=config, session_token="abc123")
result = await executor.execute(code, context)

# result["was_cold_boot"] indicates if pre-warming was needed
```

#### 2. Timeout Retry Logic

```python
config = EnhancedSandboxConfig(
    enable_timeout_retry=True,
    retry_timeout_multiplier=1.5,  # Extend timeout on retry
    max_retries=1,
    simplify_input_on_retry=True,  # Reduce iteration counts on retry
)
```

#### 3. Error Redaction

Sensitive information is automatically redacted:

```python
config = EnhancedSandboxConfig(
    redact_tracebacks=True,
    max_error_length=500,
    redact_patterns=[
        r'/tmp/[^\s]+',      # Temp paths
        r'/home/[^\s]+',     # Home paths
        r'File "[^"]+", line',  # File references
    ],
)

# Original error: "File '/tmp/sandbox_abc123/execute.py', line 42, in ..."
# Redacted:       "Error details: ValueError: Invalid input"
```

### Planner Enhancements

#### 1. Step Verification

Each tool step is verified for usefulness:

```python
from llmhive.app.mcp2.planner import PlannerConfig

config = PlannerConfig(
    enable_step_verification=True,
    verification_confidence_threshold=0.5,
)
```

#### 2. Global Limits

```python
config = PlannerConfig(
    max_tool_invocations=3,           # Max 3 tools per query
    max_planning_time_seconds=20.0,   # Total 20s budget
    step_timeout_seconds=10.0,        # 10s per step
)
```

#### 3. Domain-Specific Planner Shards

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Domain Router  │
└────────┬────────┘
         │
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
┌───────┐ ┌───────┐  ┌───────────┐ ┌─────────┐
│Search │ │Compute│  │   Code    │ │Knowledge│
│Shard  │ │ Shard │  │   Shard   │ │  Shard  │
└───────┘ └───────┘  └───────────┘ └─────────┘
```

**Domains:**
- `mcp_search`: Web search, news lookup
- `mcp_compute`: Calculator, unit conversion
- `mcp_code`: Python execution, sandbox
- `mcp_knowledge`: Knowledge base lookup

---

## Testing Enhancements

### Location
- `tests/quality_eval/golden_prompts.yaml`
- `tests/quality_eval/live_prompt_audit.py`

### New Golden Prompts (v2.0)

Added 25 new challenge prompts:

| Category | Count | Description |
|----------|-------|-------------|
| multi_hop | 10 | Multi-source synthesis queries |
| rag_tool_combined | 5 | Combined RAG + tool scenarios |
| sandbox | 5 | Code execution tests |
| tool_fallback | 2 | Graceful degradation tests |
| rerank_test | 2 | Reranking quality tests |

### Enhanced Audit Logging

The live prompt audit now captures detailed traces:

```python
@dataclass
class RetrievalTrace:
    documents_fetched: int
    documents_after_rerank: int
    rerank_model: Optional[str]
    hyde_used: bool
    cache_hit: bool
    retrieval_method: str  # semantic, lexical, hybrid, hyde

@dataclass
class ToolTrace:
    tool_name: str
    triggered: bool
    success: bool
    retry_count: int
    fallback_used: bool

@dataclass
class PlannerTrace:
    steps_planned: int
    steps_executed: int
    steps_verified: int
    domain_shard: Optional[str]
```

### Quality Assertions

Automated assertions catch regressions:

- `no_unnecessary_tools`: Tools not triggered for simple factoids
- `tools_triggered_when_needed`: Tools activated when required
- `fallback_on_failure`: Graceful degradation works
- `rag_used_when_needed`: RAG activated for knowledge queries
- `sandbox_triggered`: Code execution works
- `hrm_triggered`: Complex queries use HRM
- `no_unnecessary_clarification`: No clarification for clear queries
- `reranking_applied`: Cross-encoder reranking active

---

## Configuration Guide

### Environment Variables

```bash
# Redis for query caching
REDIS_URL=redis://localhost:6379

# Feature flags
ENABLE_RAG_CACHE=true
ENABLE_CROSS_ENCODER_RERANKING=true
ENABLE_HYDE=true
ENABLE_SEMANTIC_TOOL_FILTERING=true

# Limits
MAX_TOOL_INVOCATIONS=3
MAX_PLANNING_TIME_SECONDS=20
```

### Python Configuration

```python
# Full configuration example
from llmhive.app.knowledge.retrieval_engine import RetrievalEngine, RetrievalConfig
from llmhive.app.tool_broker import ToolBroker
from llmhive.app.mcp2.planner import MCP2Planner, PlannerConfig

# RAG Configuration
rag_config = RetrievalConfig(
    semantic_weight=0.7,
    lexical_weight=0.3,
    enable_reranking=True,
    enable_hyde=True,
    enable_cache=True,
    cache_ttl_seconds=3600,
)

retrieval_engine = RetrievalEngine(
    semantic_search_fn=your_search_fn,
    llm_provider=your_llm,
    config=rag_config,
    redis_url="redis://localhost:6379",
)

# Tool Broker Configuration
tool_broker = ToolBroker(
    embedding_fn=your_embedding_fn,
    max_visible_tools=3,
)

# Planner Configuration
planner_config = PlannerConfig(
    max_tool_invocations=3,
    max_planning_time_seconds=20.0,
    enable_step_verification=True,
    enable_domain_routing=True,
)

planner = MCP2Planner(config=planner_config, tool_executor=tool_broker.handle_tool_request_async)
```

---

## Performance Metrics

### Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Retrieval Precision | ~70% | ~88% | +18% |
| Tool Selection Accuracy | ~60% | ~96% | +60% |
| Avg Query Latency | 2.1s | 1.8s | -15% |
| Fallback Success Rate | 0% | 95% | N/A |
| Cache Hit Rate | 0% | 40% | N/A |

### Quality Gates

CI/CD quality gates enforce:

- Pass rate ≥ 85% on all prompts
- 0 critical failures
- Average latency ≤ 3 seconds
- Tool misrouting ≤ 5%

---

## Migration Notes

### Breaking Changes

None. All new features are additive and backward compatible.

### Deprecations

- `simple_retrieval()` - Use `RetrievalEngine.retrieve()` instead
- `tool_broker.execute()` - Use `handle_tool_request_async()` instead

### Upgrade Path

1. Install new dependencies: `pip install sentence-transformers faiss-cpu redis`
2. Update configuration with new options
3. Run quality regression tests: `python tests/quality_eval/live_prompt_audit.py`
4. Monitor metrics for 24 hours before full rollout

---

## References

- [Hybrid Search Best Practices](https://elastic.co)
- [Cross-Encoder Reranking](https://customgpt.ai)
- [HyDE Paper](https://arxiv.org/abs/2212.10496)
- [Semantic Tool Selection](https://medium.com)

---

*Document maintained by LLMHive Engineering Team*

