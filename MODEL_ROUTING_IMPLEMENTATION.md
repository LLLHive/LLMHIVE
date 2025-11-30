# Model Routing Implementation

This document describes the implementation of adaptive model routing and selection in LLMHive, enabling intelligent model selection, fallback, and ensemble execution.

## Overview

Model routing enhances LLMHive's ability to select the best model(s) for each query based on:
- Model capabilities and domain expertise
- Historical performance data
- Query characteristics (domain, complexity, importance)
- Cost and latency considerations
- Automatic fallback on failure or low quality
- Parallel ensemble for important queries

## Implementation Details

### 1. Model Router Module (`llmhive/src/llmhive/app/orchestration/router.py`)

**New Module Created** with the following components:

#### `ModelRouter` Class
- **Purpose**: Intelligent model selection, fallback, and ensemble execution
- **Features**:
  - Dynamic model selection based on query analysis
  - Automatic fallback on failure or low quality
  - Parallel ensemble execution
  - Quality-based voting/scoring
  - Routing decision logging

#### Key Methods:
- `route()`: Selects appropriate models for a query
- `execute_with_fallback()`: Executes query with automatic fallback
- `execute_ensemble()`: Executes query with parallel ensemble
- `vote_on_responses()`: Scores and selects best response from multiple models
- `_try_model()`: Attempts to execute a model and assess quality
- `_assess_quality()`: Assesses quality of a model response
- `_assess_confidence()`: Assesses confidence in a model response

#### `RoutingDecision` Dataclass
- Stores routing decision metadata:
  - `selected_models`: List of selected models
  - `primary_model`: Primary model for execution
  - `fallback_models`: Fallback models if primary fails
  - `reasoning`: Explanation of routing decision
  - `domain`: Detected domain
  - `confidence`: Confidence in routing decision
  - `use_ensemble`: Whether ensemble mode is used
  - `ensemble_size`: Number of models in ensemble

#### `ModelResponse` Dataclass
- Wraps model result with quality assessment:
  - `result`: LLMResult from model
  - `model`: Model name
  - `quality_score`: Quality score (0.0-1.0)
  - `confidence`: Confidence score (0.0-1.0)
  - `passed_quality_check`: Whether quality threshold was met
  - `failure_reason`: Reason for failure (if any)

### 2. Model Registry Enhancements

**File**: `llmhive/src/llmhive/app/model_registry.py`

#### Existing Features (Already Implemented):
- Model profiles with capabilities, domain expertise, reliability scores
- Performance tracking integration
- Domain detection from queries
- Adaptive model selection based on query and mode
- Performance-based filtering (deprioritizes low-accuracy models)

#### Model Profile Fields:
- `domain_expertise`: Dict[str, float] - Domain-specific accuracy scores
- `confidence_weight`: float - Reliability weight for ensemble voting
- `past_success_rate`: float - Historical success rate
- `total_queries`: int - Total queries processed
- `successful_queries`: int - Successful queries
- `avg_latency`: float - Average latency
- `accuracy`: float - Query-level accuracy

### 3. Performance Tracker Integration

**File**: `llmhive/src/llmhive/app/performance_tracker.py`

#### Existing Features (Already Implemented):
- Domain-specific performance tracking
- Query-level accuracy tracking
- Persistent storage to JSON file
- Automatic loading on startup

#### Integration with Router:
- Router uses performance data for model selection
- Router logs routing decisions for analysis
- Performance tracker updates model profiles based on outcomes

### 4. Orchestrator Integration

**File**: `llmhive/src/llmhive/app/orchestrator.py`

#### Router Initialization
- Router initialized in `__init__` with configurable settings
- Integrated with model registry and providers

#### Router Usage
- **Model Selection**: Router used for intelligent model selection
- **Step Execution**: Router used for draft step execution (optional)
- **Fallback Logic**: Router checks quality and triggers fallback if needed
- **Routing Logging**: Routing decisions logged for performance tracking

#### New Methods:
- `_execute_with_router()`: Execute query using router with fallback/ensemble
- Integrated into step execution for draft steps
- Integrated into post-initial-response quality checking

### 5. Configuration Settings

**File**: `llmhive/src/llmhive/app/config.py`

#### New Settings:
- `enable_model_routing`: Enable/disable model routing (default: True)
- `router_min_quality_threshold`: Minimum quality score to accept (default: 0.5)
- `router_enable_fallback`: Enable automatic fallback (default: True)
- `router_enable_ensemble`: Enable parallel ensemble (default: True)
- `router_max_fallback_attempts`: Maximum fallback attempts (default: 2)

## Routing Logic

### 1. Query Analysis
- **Domain Detection**: Analyzes query to detect domain (medical, legal, technical, etc.)
- **Complexity Assessment**: Determines if query is complex
- **Importance Assessment**: Determines if query is important (critical, urgent, etc.)

### 2. Model Selection
- **Domain Expertise**: Prefers models with high domain expertise
- **Performance History**: Considers past success rate and accuracy
- **Capability Match**: Matches required capabilities
- **Cost/Latency**: Considers cost and latency (especially in speed mode)
- **Reliability**: Considers model reliability score

### 3. Execution Modes

#### Single Model Mode
- Selects best model for query
- Executes with automatic fallback on failure
- Falls back to alternative models if quality check fails

#### Ensemble Mode
- Used for important/complex queries in accuracy mode
- Executes multiple models in parallel (2-4 models)
- Votes on responses to select best answer
- Combines quality, reliability, domain expertise, and confidence

### 4. Quality Assessment

#### Quality Heuristics:
- **Length Check**: Response length (too short or too long is suspicious)
- **Error Indicators**: Detects error messages in response
- **Model Performance**: Considers model's historical quality
- **Content Analysis**: Basic content quality checks

#### Quality Threshold:
- Default: 0.5 (configurable)
- Responses below threshold trigger fallback
- All responses below threshold trigger ensemble fallback

### 5. Fallback Logic

#### Automatic Fallback:
1. Primary model executes
2. Quality assessment performed
3. If quality check fails:
   - Try fallback models (up to max_fallback_attempts)
   - Select best fallback response
   - Log fallback decision

#### Fallback Model Selection:
- Alternative models for the domain
- High domain expertise
- Good performance history
- Cost/latency considerations

### 6. Ensemble Execution

#### When to Use Ensemble:
- Important queries (critical, urgent, medical, legal, financial)
- Complex queries (long, analysis requests)
- Accuracy mode (not speed mode)
- User preference or configuration

#### Ensemble Workflow:
1. Select 2-4 models based on routing logic
2. Execute all models in parallel
3. Assess quality of all responses
4. Vote on responses using scoring:
   - Quality score (40% weight)
   - Model reliability (30% weight)
   - Domain expertise (20% weight)
   - Confidence (10% weight)
5. Select best response
6. Log ensemble decision

## Integration Points

### 1. Model Selection
- Router integrated into orchestrator's model selection
- Can be used instead of or alongside existing adaptive ensemble logic
- Respects mode (speed vs accuracy)

### 2. Step Execution
- Router can be used for draft step execution
- Optional: controlled by `enable_model_routing` setting
- Provides fallback and ensemble support for draft generation

### 3. Post-Execution Quality Check
- Router checks quality of initial responses
- Triggers fallback if all responses fail quality check
- Logs routing decisions for analysis

### 4. Performance Tracking
- Routing decisions logged
- Model performance updated based on outcomes
- Domain-specific performance tracked
- Feedback loop closed for continuous improvement

## Logging

### Routing Decision Logging
- All routing decisions logged with:
  - Selected models
  - Domain
  - Ensemble mode
  - Confidence
  - Reasoning

### Quality Assessment Logging
- Quality scores logged for each response
- Fallback decisions logged
- Ensemble voting results logged

### Performance Logging
- Model performance updates logged
- Domain-specific performance tracked
- Routing history maintained for analysis

## Configuration

### Environment Variables
- `ENABLE_MODEL_ROUTING`: Enable/disable model routing (default: True)
- `ROUTER_MIN_QUALITY_THRESHOLD`: Minimum quality threshold (default: 0.5)
- `ROUTER_ENABLE_FALLBACK`: Enable fallback (default: True)
- `ROUTER_ENABLE_ENSEMBLE`: Enable ensemble (default: True)
- `ROUTER_MAX_FALLBACK_ATTEMPTS`: Max fallback attempts (default: 2)

### Settings
Can be configured in `llmhive/src/llmhive/app/config.py`:
```python
enable_model_routing: bool = True
router_min_quality_threshold: float = 0.5
router_enable_fallback: bool = True
router_enable_ensemble: bool = True
router_max_fallback_attempts: int = 2
```

## Testing

### Manual Testing Steps

1. **Domain-Specific Routing Test**:
   - Send medical query: "What are the symptoms of diabetes?"
   - Verify: Router selects medical-specialized models
   - Check logs for routing decision

2. **Fallback Test**:
   - Simulate low-quality response
   - Verify: Router triggers fallback
   - Verify: Fallback model executes
   - Check logs for fallback decision

3. **Ensemble Test**:
   - Send important/complex query
   - Verify: Router selects ensemble mode
   - Verify: Multiple models execute in parallel
   - Verify: Best response selected via voting
   - Check logs for ensemble decision

4. **Performance-Based Routing Test**:
   - Use model with low accuracy in a domain
   - Verify: Router deprioritizes low-accuracy model
   - Verify: Higher-accuracy model selected
   - Check logs for routing reasoning

### Unit Tests (To Be Implemented)

```python
def test_router_domain_selection():
    router = ModelRouter(model_registry, providers)
    decision = router.route("What are the symptoms of diabetes?", mode="accuracy")
    assert decision.domain == "medical"
    assert "medical" in decision.reasoning.lower()

def test_router_fallback():
    router = ModelRouter(model_registry, providers)
    # Mock low-quality response
    response = await router.execute_with_fallback(
        "test query",
        "test prompt",
        mode="accuracy",
    )
    assert response.passed_quality_check or response.failure_reason is not None

def test_router_ensemble():
    router = ModelRouter(model_registry, providers)
    responses = await router.execute_ensemble(
        "Analyze the pros and cons of cloud computing",
        "test prompt",
        mode="accuracy",
    )
    assert len(responses) >= 2
    # Verify voting selects best response
    best = router.vote_on_responses(responses)
    assert best is not None

def test_quality_assessment():
    router = ModelRouter(model_registry, providers)
    result = LLMResult(model="test", content="This is a good answer.", tokens=10)
    quality = router._assess_quality(result, "test")
    assert 0.0 <= quality <= 1.0
```

## Files Created/Modified

### New Files
- `llmhive/src/llmhive/app/orchestration/router.py` - Model router implementation

### Modified Files
- `llmhive/src/llmhive/app/orchestrator.py` - Router integration
- `llmhive/src/llmhive/app/config.py` - Router configuration settings

### Existing Files (Already Enhanced)
- `llmhive/src/llmhive/app/model_registry.py` - Model profiles and selection
- `llmhive/src/llmhive/app/performance_tracker.py` - Performance tracking

## Future Enhancements

1. **LLM-Based Routing**: Use LLM to analyze queries and select models
2. **Dynamic Thresholds**: Adjust quality thresholds based on query importance
3. **Cost Optimization**: More sophisticated cost/latency optimization
4. **Routing Analytics**: Dashboard for analyzing routing decisions
5. **A/B Testing**: Test different routing strategies
6. **Multi-Domain Queries**: Handle queries spanning multiple domains
7. **Confidence Calibration**: Better confidence estimation
8. **Routing Persistence**: Store routing decisions in database for analysis

## Notes

- Router works alongside existing adaptive ensemble logic
- Can be enabled/disabled via configuration
- Respects mode (speed vs accuracy) for model selection
- Integrates with performance tracker for continuous improvement
- Logs all routing decisions for analysis and debugging
- Fallback and ensemble are optional features
- Quality assessment uses heuristics (can be enhanced with ML)
- Routing decisions are logged but not persisted (future enhancement)

