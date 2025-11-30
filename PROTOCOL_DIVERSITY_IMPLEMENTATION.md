# Protocol Diversity Implementation

This document describes the implementation of protocol diversity in LLMHive, allowing the system to support multiple reasoning strategies or "protocols" for answering queries.

## Overview

Protocol diversity enables LLMHive to choose between different orchestration strategies based on query characteristics or user preferences. Instead of a one-size-fits-all pipeline, the system can dynamically select the most appropriate protocol (e.g., simple single-model answer vs. multi-model critique-and-improve workflow).

## Implementation Details

### 1. Protocol Framework (`llmhive/src/llmhive/app/protocols/`)

**New Module Created** with the following structure:

#### `base.py` - Base Protocol Interface
- **`BaseProtocol`**: Abstract base class for all protocols
  - Standard interface with `execute()` method
  - Provides common utilities (`_select_provider()`, `_gather_with_handling()`)
  - Handles provider selection and async result gathering

- **`ProtocolResult`**: Dataclass containing all artifacts from protocol execution
  - `final_response`: Final answer
  - `initial_responses`: Initial model outputs
  - `critiques`: Critique results
  - `improvements`: Improved answers
  - `consensus_notes`: Consensus information
  - `step_outputs`: Outputs by step
  - `quality_assessments`: Quality metrics
  - And more...

#### `simple.py` - Simple Protocol
- **Purpose**: Single-step answer from one model
- **Best For**: Simple Q&A, factual queries, low-complexity requests
- **Workflow**:
  1. Select best model for query (or use provided model)
  2. Generate direct answer
  3. Return result

#### `critique_and_improve.py` - Critique and Improve Protocol
- **Purpose**: Multi-step, multi-model collaboration
- **Best For**: Complex, open-ended, or high-stakes queries
- **Workflow**:
  1. **Draft**: Multiple models generate initial answers in parallel
  2. **Critique**: Models critique each other's drafts
  3. **Improve**: Models refine answers based on critiques
  4. **Synthesize**: Final answer synthesis from improved drafts

#### `__init__.py` - Protocol Registry
- **`PROTOCOL_REGISTRY`**: Maps protocol names to classes
  - `"simple"` → `SimpleProtocol`
  - `"critique-and-improve"` → `CritiqueAndImproveProtocol`
- **`get_protocol()`**: Helper to retrieve protocol class by name
- **`list_protocols()`**: List all available protocols

### 2. Planner Integration

**File**: `llmhive/src/llmhive/app/planner.py`

#### New Method: `select_protocol()`
- Heuristic-based protocol selection
- Analyzes query characteristics:
  - **Simple indicators**: Short queries, simple factual questions
  - **Complex indicators**: Long queries, analysis requests, recommendations
- Returns appropriate protocol name
- Respects `preferred_protocol` if user-specified

#### Updated Method: `create_plan()`
- Added `preferred_protocol` parameter
- Calls `select_protocol()` if protocol not provided
- Passes protocol information to plan

### 3. Orchestrator Integration

**File**: `llmhive/src/llmhive/app/orchestrator.py`

#### Protocol Framework Integration
- Detects if protocol is a framework protocol (simple, critique-and-improve)
- Distinguishes from advanced protocols (HRM, DeepConf, Adaptive Ensemble)
- Executes protocol framework if selected
- Converts protocol results to orchestrator artifacts
- Skips standard execution when using protocol framework
- Continues with post-processing (fact-checking, formatting, etc.)

#### Flow Control
- `using_protocol_framework` flag controls execution path
- Protocol execution happens after plan creation
- Standard orchestration skipped if protocol framework used
- Synthesis skipped if protocol already provides final_response

### 4. API Integration

**File**: `llmhive/src/llmhive/app/api/orchestration.py`

- Extracts `preferred_protocol` from request payload
- Validates preferred protocol (must be framework protocol)
- Passes protocol to orchestrator
- Logs protocol selection decisions

### 5. Schema Updates

**File**: `llmhive/src/llmhive/app/schemas.py`

#### `OrchestrationRequest` - New Field:
- `preferred_protocol`: User-specified protocol preference
  - If provided, overrides planner's automatic selection
  - Supported: "simple", "critique-and-improve"

## Protocol Selection Logic

### Automatic Selection (Planner)

The planner uses heuristics to select protocols:

**Simple Protocol Indicators:**
- Query length < 10 words
- Simple factual questions ("what is", "who is", "when did", "where is")
- Short questions (< 100 characters)

**Critique-and-Improve Protocol Indicators:**
- Query length > 50 words
- Analysis keywords ("analyze", "compare", "evaluate", "critique")
- Recommendation requests ("should I", "what should", "how should")
- Long statements/requests (> 100 characters, no question mark)

**Selection Algorithm:**
1. Count simple indicators
2. Count complex indicators
3. If complex_score >= 2 → "critique-and-improve"
4. If simple_score >= 2 → "simple"
5. Default → "critique-and-improve" (better quality)

### User-Specified Protocol

Users can override automatic selection:
- Set `preferred_protocol` in request
- System uses specified protocol if valid
- Falls back to automatic selection if invalid

## Protocol Workflows

### Simple Protocol Workflow

```
Query → Select Model → Generate Answer → Return
```

**Characteristics:**
- Single model
- Direct answer generation
- No refinement
- Fast execution
- Lower cost

### Critique and Improve Protocol Workflow

```
Query → Select Models (2-4) → 
  [Parallel] Draft Generation →
  [Sequential] Critique Generation →
  [Sequential] Improvement Generation →
  Synthesis → Return
```

**Characteristics:**
- Multiple models (2-4)
- Multi-step refinement
- Cross-model critique
- Higher quality
- Slower execution
- Higher cost

## Concurrency & Sequencing

### Parallel Execution
- **Draft Generation**: All models generate drafts concurrently using `asyncio.gather()`
- **Critique Generation**: Can be parallelized (future enhancement)

### Sequential Execution
- **Critique → Improve**: Critiques must complete before improvements
- **Improve → Synthesize**: Improvements must complete before synthesis

### Error Handling
- Failed drafts are logged and filtered out
- Fallback to simple protocol if no drafts succeed
- Exceptions don't crash the pipeline

## Integration with Existing Features

### Advanced Protocols
Protocol framework protocols coexist with advanced protocols:
- **HRM**: Hierarchical Role Management (separate logic)
- **DeepConf**: Deep Consensus Framework (separate logic)
- **Adaptive Ensemble**: Adaptive model selection (separate logic)
- **Prompt Diffusion**: Prompt refinement (separate logic)

### Subscription Tiers
- Protocol selection respects tier limits
- Advanced protocols may be disabled for lower tiers
- Framework protocols available to all tiers

### Mode (Speed vs Accuracy)
- **Speed Mode**: Prefers simple protocol
- **Accuracy Mode**: Prefers critique-and-improve protocol
- Protocol selection considers mode preference

## Testing

### Manual Testing Steps

1. **Simple Query Test**:
   - Send: "What is Python?"
   - Verify: Simple protocol selected
   - Verify: Single model answer
   - Verify: Fast response

2. **Complex Query Test**:
   - Send: "Analyze the pros and cons of using microservices architecture for a large-scale e-commerce platform"
   - Verify: Critique-and-improve protocol selected
   - Verify: Multiple models used
   - Verify: Critique and improvement steps executed

3. **User-Specified Protocol Test**:
   - Send query with `preferred_protocol: "simple"`
   - Verify: Simple protocol used regardless of query complexity
   - Verify: User preference honored

4. **Protocol Selection Test**:
   - Send ambiguous query
   - Verify: Planner selects appropriate protocol
   - Check logs for selection reasoning

### Unit Tests (To Be Implemented)

```python
def test_simple_protocol():
    protocol = SimpleProtocol(providers, model_registry, planner)
    result = await protocol.execute("What is Python?")
    assert result.final_response is not None
    assert len(result.initial_responses) == 1
    assert len(result.critiques) == 0

def test_critique_and_improve_protocol():
    protocol = CritiqueAndImproveProtocol(providers, model_registry, planner)
    result = await protocol.execute("Analyze the benefits of cloud computing")
    assert result.final_response is not None
    assert len(result.initial_responses) >= 2
    assert len(result.critiques) > 0
    assert len(result.improvements) > 0

def test_protocol_selection():
    planner = ReasoningPlanner()
    protocol = planner.select_protocol("What is Python?")
    assert protocol == "simple"
    
    protocol = planner.select_protocol("Analyze the pros and cons of...")
    assert protocol == "critique-and-improve"

def test_user_specified_protocol():
    # Test that preferred_protocol overrides automatic selection
    pass
```

## Files Created/Modified

### New Files
- `llmhive/src/llmhive/app/protocols/__init__.py` - Protocol registry
- `llmhive/src/llmhive/app/protocols/base.py` - Base protocol interface
- `llmhive/src/llmhive/app/protocols/simple.py` - Simple protocol
- `llmhive/src/llmhive/app/protocols/critique_and_improve.py` - Critique and improve protocol

### Modified Files
- `llmhive/src/llmhive/app/orchestrator.py` - Protocol framework integration
- `llmhive/src/llmhive/app/planner.py` - Protocol selection logic
- `llmhive/src/llmhive/app/schemas.py` - Added preferred_protocol field
- `llmhive/src/llmhive/app/api/orchestration.py` - Protocol parameter handling

## Configuration

### Environment Variables
- `ENABLE_PROTOCOL_DIVERSITY`: Enable/disable protocol diversity (default: True)
- `DEFAULT_PROTOCOL`: Default protocol if selection fails (default: "critique-and-improve")

### Settings
Can be configured in `llmhive/src/llmhive/app/config.py`:
```python
enable_protocol_diversity: bool = True
default_protocol: str = "critique-and-improve"
simple_protocol_max_models: int = 1
critique_protocol_min_models: int = 2
critique_protocol_max_models: int = 4
critique_protocol_max_rounds: int = 2
```

## Future Enhancements

1. **More Protocols**: Add research-heavy, debate, etc.
2. **LLM-Based Selection**: Use LLM to select protocol instead of heuristics
3. **Protocol Chaining**: Chain multiple protocols for complex queries
4. **Performance Metrics**: Track protocol performance and auto-tune selection
5. **Domain-Specific Protocols**: Protocols optimized for specific domains
6. **Parallel Critiques**: Parallelize critique generation for faster execution
7. **Adaptive Rounds**: Dynamically adjust critique rounds based on convergence

## Notes

- Protocol framework protocols are distinct from advanced protocols (HRM, DeepConf, etc.)
- Advanced protocols have their own execution paths and take precedence
- Protocol framework provides a clean, extensible way to add new orchestration strategies
- All protocols share the same interface, making them interchangeable
- Protocol selection is automatic but can be overridden by users
- Protocol execution is fully async and supports parallel operations where appropriate

