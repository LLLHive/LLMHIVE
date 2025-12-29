# LLMHive Pipelines Package

This package implements technique-aligned reasoning pipelines that are selected and executed based on the LLMHive Techniques Knowledge Base.

## Architecture

```
Query → QueryClassifier → PipelineSelector → Pipeline Execution → GuardrailsFilter → Response
                              ↓
                    Techniques Knowledge Base
```

## Components

### Core Types (`types.py`)

- **`PipelineContext`**: Input context for pipeline execution
  - `query`: Sanitized user query
  - `reasoning_type`: Classified reasoning type
  - `risk_level`: low/medium/high
  - `domain`: Detected domain
  - `tools_available`: List of available tools
  - `cost_budget`: low/medium/high

- **`PipelineResult`**: Output from pipeline execution
  - `final_answer`: The response (CoT-free)
  - `pipeline_name`: Which pipeline was used
  - `technique_ids`: KB technique IDs applied
  - `confidence`: low/medium/high
  - `citations`: Optional list of sources
  - `tool_calls`: Summary of tool invocations

### Guardrails (`guardrails.py`)

Global safety mechanisms applied to all pipelines:

| Function | Purpose | Technique |
|----------|---------|-----------|
| `sanitize_input()` | HTML escape, injection detection | TECH_0022/0023 |
| `enforce_no_cot()` | Remove internal reasoning from output | TECH_0023 |
| `allowlist_tools()` | Filter to approved tools only | TECH_0024 |
| `validate_structured()` | Basic schema validation | TECH_0025 |
| `bounded_loop()` | Decorator for max iterations/timeout | Safety |
| `summarize_tool_output()` | Truncate long tool responses | Safety |
| `delimit_untrusted()` | Wrap untrusted content with markers | TECH_0023 |

### Pipeline Registry (`pipeline_registry.py`)

Centralized registration and lookup of pipeline implementations:

```python
from llmhive.pipelines import get_pipeline, list_pipelines

# Get a specific pipeline
pipeline_fn = get_pipeline("PIPELINE_MATH_REASONING")

# List all registered pipelines
all_pipelines = list_pipelines()
```

### Pipeline Implementations (`pipelines_impl.py`)

| Pipeline | Techniques | Use Case |
|----------|-----------|----------|
| `PIPELINE_BASELINE_SINGLECALL` | - | Simple queries, fallback |
| `PIPELINE_MATH_REASONING` | TECH_0001, 0002, 0003 | Math, logic problems |
| `PIPELINE_TOOL_USE_REACT` | TECH_0004 | Tool-requiring queries |
| `PIPELINE_SELF_REFINE` | TECH_0005 | Iterative improvement |
| `PIPELINE_RAG` | TECH_0006 | Factual queries with citations |
| `PIPELINE_MULTIAGENT_DEBATE` | TECH_0007 | High-risk, controversial |
| `PIPELINE_ENSEMBLE_PANEL` | TECH_0008 | Complex multi-perspective |
| `PIPELINE_CHALLENGE_REFINE` | TECH_0009 | Adversarial refinement |
| `PIPELINE_CODING_AGENT` | TECH_0005, 0009 | Code generation |
| `PIPELINE_COST_OPTIMIZED_ROUTING` | - | Budget-aware routing |

**Experimental** (enabled via `LLMHIVE_ENABLE_EXPERIMENTAL_PIPELINES=true`):
- `PIPELINE_CHATDEV` (TECH_0010)
- `PIPELINE_MACNET` (TECH_0011)
- `PIPELINE_HUGGINGGPT` (TECH_0012)

### Orchestrator Bridge (`kb_orchestrator_bridge.py`)

Integration layer connecting KB components to the main orchestrator:

```python
from llmhive.pipelines.kb_orchestrator_bridge import process_with_kb_pipeline

result = await process_with_kb_pipeline(
    query="Calculate the derivative of x^2 + 3x",
    tools_available=["calculator"],
    cost_budget="medium",
)

print(result.final_answer)
print(result.pipeline_name)  # "PIPELINE_MATH_REASONING"
print(result.technique_ids)  # ["TECH_0001", "TECH_0002"]
```

## Flow Details

### 1. Input Sanitization
```python
sanitized = sanitize_input(user_query)
# - HTML escapes dangerous characters
# - Detects injection patterns
# - Truncates to max length (10000 chars)
```

### 2. Query Classification
```python
from llmhive.kb import get_query_classifier

classifier = get_query_classifier()
result = classifier.classify(query)

# result.reasoning_type: "mathematical_reasoning" | "coding" | "factual" | ...
# result.risk_level: "low" | "medium" | "high"
# result.domain: "math" | "coding" | "medical" | ...
# result.citations_requested: bool
# result.tools_needed: ["calculator", "web_search", ...]
```

### 3. Pipeline Selection
```python
from llmhive.kb import select_pipeline

selection = select_pipeline(
    query=sanitized_query,
    tools_available=["web_search"],
    cost_budget="medium",
)

# selection.pipeline_name: PipelineName enum
# selection.technique_ids: ["TECH_0001", ...]
# selection.rationale: "Selected for mathematical reasoning..."
```

### 4. Pipeline Execution

Each pipeline:
1. Receives `PipelineContext`
2. Applies its technique(s)
3. May call tools (bounded, allowlisted)
4. Returns `PipelineResult`

### 5. CoT Removal

Before returning to user:
```python
final_answer = enforce_no_cot(result.final_answer)
# Removes: <thinking>...</thinking>, [SCRATCHPAD]..., "let's think step by step", etc.
```

### 6. Trace Logging

All executions are logged (if `LLMHIVE_TRACE_PATH` is set):
```json
{
  "event": "pipeline_execution",
  "selected_pipeline": "PIPELINE_MATH_REASONING",
  "technique_ids": ["TECH_0001", "TECH_0002"],
  "outcome_confidence": "high",
  "latency_ms": 1234.5,
  "timestamp": "2025-12-27T12:00:00+00:00"
}
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `LLMHIVE_TRACE_PATH` | Path for JSONL trace logs | (disabled) |
| `LLMHIVE_ENABLE_EXPERIMENTAL_PIPELINES` | Enable experimental pipelines | false |

## Testing

```bash
# Run unit tests
pytest llmhive/tests/test_kb_classifier.py llmhive/tests/test_kb_pipelines.py -v

# Run evaluation harness
python scripts/eval_orchestrator_kb.py
```

## Adding a New Pipeline

1. Implement the pipeline function in `pipelines_impl.py`:
```python
async def pipeline_my_custom(context: PipelineContext) -> PipelineResult:
    # Your implementation
    return PipelineResult(
        final_answer="...",
        pipeline_name="PIPELINE_MY_CUSTOM",
        technique_ids=["TECH_XXXX"],
        confidence="high",
    )
```

2. Register it in the same file:
```python
register_pipeline("PIPELINE_MY_CUSTOM", pipeline_my_custom)
```

3. Update `pipeline_selector.py` to route appropriate queries to your pipeline.

4. Add tests in `test_kb_pipelines.py`.
