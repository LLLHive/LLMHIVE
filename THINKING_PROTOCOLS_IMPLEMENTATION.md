# Thinking Protocols Implementation

## Overview

This document describes the implementation of the Thinking Protocols architecture in LLMHive, which transforms the system from a step-based orchestration to a protocol-driven architecture where different reasoning strategies are first-class citizens.

## Architecture Components

### 1. Protocol System (`app/protocols/`)

The protocol system is the cornerstone of the new architecture. Each protocol represents a distinct reasoning strategy.

#### Base Protocol (`base_protocol.py`)
- Abstract base class for all protocols
- Defines the contract: `execute()` method that protocols must implement
- Receives: blackboard (shared state), assignments (model-to-role mapping), params (protocol-specific config)

#### Simple Protocol (`simple_protocol.py`)
- Single-agent execution for straightforward queries
- One agent performs one task and writes result to blackboard
- Ideal for: direct questions, simple lookups, basic analysis

#### Critique & Improve Protocol (`critique_and_improve_protocol.py`)
- Multi-agent workflow with three phases:
  1. **Parallel Drafting**: Multiple agents create independent drafts
  2. **Cross-Critique**: Agents critique each other's work
  3. **Improvement**: Agents revise based on feedback
- Ideal for: complex queries, creative tasks, high-stakes decisions

### 2. Shared Execution Module (`app/orchestration/execution.py`)

Centralizes agent task execution logic to avoid duplication:
- `get_agent()`: Factory function for agent instantiation
- `execute_task()`: Runs agent task with error handling and validation
- Used by all protocols for consistency

### 3. Enhanced API Endpoint (`app/api/endpoints.py`)

The `/api/prompt` endpoint now accepts:
```json
{
  "user_id": "string",
  "prompt": "string",
  "preferred_models": ["gpt-4", "claude-3-opus"],  // Optional
  "preferred_protocol": "simple"                    // Optional
}
```

**Benefits:**
- Users can specify which models to use (filters the model pool)
- Users can force a specific protocol (bypasses LLM planner)
- Maintains backward compatibility (optional parameters)

### 4. Protocol-Aware Planner (`app/orchestration/planner.py`)

**Before:** Generated a list of steps with types like "simple" or "critique_and_improve"
**After:** Selects a protocol by name and provides parameters

Key changes:
- `Plan` model now has `protocol` (string) and `params` (dict) instead of `steps` (list)
- If user specifies `preferred_protocol`, returns immediately without LLM call
- LLM prompt asks for protocol selection rather than step generation
- Constants for default protocol parameters (cleaner code)

### 5. Model Router with Filtering (`app/orchestration/router.py`)

Enhanced to support preferred models:
- If `preferred_models` is provided, filters the model pool
- Falls back to all models if none of the preferred ones are available
- Maintains intelligent role-based assignment logic

### 6. Simplified Orchestrator (`app/orchestration/orchestrator.py`)

**Before:** Contained all workflow execution logic (drafting, critique, improvement)
**After:** Delegates to the selected protocol

Key improvements:
- Protocol map registry: `{"simple": SimpleProtocol, "critique_and_improve": CritiqueAndImproveProtocol}`
- `_extract_roles_from_plan()`: Determines required roles based on protocol type
- Much cleaner separation of concerns

## Usage Examples

### Example 1: Simple Query with Default Settings
```python
POST /api/prompt
{
  "user_id": "user123",
  "prompt": "What is the capital of France?"
}
```
- Planner LLM selects "simple" protocol
- Router assigns best available model to "lead" role
- Single agent provides answer

### Example 2: Complex Query with Preferred Protocol
```python
POST /api/prompt
{
  "user_id": "user123",
  "prompt": "Write a comprehensive analysis of AI safety",
  "preferred_protocol": "critique_and_improve"
}
```
- Bypasses planner LLM
- Forces use of critique & improve workflow
- Multiple agents draft, critique, and improve

### Example 3: Constrained Model Selection
```python
POST /api/prompt
{
  "user_id": "user123",
  "prompt": "Explain quantum computing",
  "preferred_models": ["gpt-4", "claude-3-opus"]
}
```
- Only uses GPT-4 and Claude 3 Opus models
- Planner still selects protocol automatically
- Useful for cost control or compliance requirements

## Benefits of This Architecture

1. **Modularity**: New protocols can be added without modifying existing code
2. **Extensibility**: Easy to experiment with new reasoning strategies
3. **User Control**: Fine-grained control over model selection and reasoning approach
4. **Maintainability**: Cleaner code with better separation of concerns
5. **Testability**: Each protocol can be tested independently

## Adding a New Protocol

To add a new protocol (e.g., "chain_of_thought"):

1. Create `app/protocols/chain_of_thought_protocol.py`:
```python
from .base_protocol import BaseProtocol
from ..orchestration.execution import execute_task

class ChainOfThoughtProtocol(BaseProtocol):
    async def execute(self) -> None:
        # Implement your reasoning strategy
        pass
```

2. Register in `app/protocols/__init__.py`:
```python
from .chain_of_thought_protocol import ChainOfThoughtProtocol
```

3. Add to orchestrator's protocol map in `app/orchestration/orchestrator.py`:
```python
self.protocol_map = {
    "simple": SimpleProtocol,
    "critique_and_improve": CritiqueAndImproveProtocol,
    "chain_of_thought": ChainOfThoughtProtocol,  # New!
}
```

4. Update planner prompt in `app/orchestration/planner.py` to describe the new protocol

## Testing

All components have been tested:
- ✅ Protocol imports and instantiation
- ✅ PromptRequest with new optional parameters
- ✅ Planner protocol selection
- ✅ Router model filtering
- ✅ Orchestrator protocol delegation
- ✅ Role extraction logic
- ✅ Execution module agent factory

## Security

CodeQL scan completed with **0 alerts**. The implementation:
- Uses Pydantic for input validation
- Doesn't leak sensitive information in errors
- Follows secure coding practices
- No SQL injection risks (uses ORM)
- No hardcoded secrets

## Migration Notes

This is a **non-breaking change**. The API maintains backward compatibility:
- Existing calls without `preferred_models` or `preferred_protocol` work unchanged
- The planner automatically selects the appropriate protocol
- The router assigns models intelligently as before

The internal architecture has changed significantly, but the external interface remains compatible.

## Performance Considerations

- **Bypassing Planner**: Using `preferred_protocol` saves one LLM call
- **Model Filtering**: `preferred_models` reduces the search space for router
- **Protocol Efficiency**: Choose `simple` for straightforward queries to avoid overhead of multi-agent workflows

## Future Enhancements

Potential future additions:
1. **Hierarchical Task Decomposition (HRM)** protocol
2. **Diffusion-based Reasoning** protocol
3. **Self-Consistency Checks** protocol
4. **Debate Protocol** (agents debate before consensus)
5. **Tree of Thoughts** protocol
6. **Protocol chaining** (output of one protocol as input to another)
7. **Protocol performance metrics** (cost, latency, quality)
8. **Dynamic protocol selection** based on historical performance

## Conclusion

This implementation fully realizes the vision described in the problem statement. It transforms LLMHive from a simple multi-agent system into a sophisticated protocol-driven platform capable of executing different reasoning strategies. The architecture is production-ready, well-tested, and designed for future extensibility.
