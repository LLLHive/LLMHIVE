# Cost Tracking - Financial Instrumentation

## Overview

LLMHive tracks all costs associated with model inference to enable:
- Budget-aware routing
- Cost optimization
- Financial reporting
- Usage forecasting

## What Is Tracked

### Per-Request Metrics

| Metric | Source | Description |
|--------|--------|-------------|
| prompt_tokens | OpenRouter response | Input tokens |
| completion_tokens | OpenRouter response | Output tokens |
| reasoning_tokens | OpenRouter response | Internal reasoning tokens (if applicable) |
| prompt_cost | Calculated | prompt_tokens × pricing.prompt |
| completion_cost | Calculated | completion_tokens × pricing.completion |
| reasoning_cost | Calculated | reasoning_tokens × pricing.internal_reasoning |
| total_cost | Calculated | Sum of all costs |
| cache_read_tokens | OpenRouter response | Cached input tokens |
| cache_write_tokens | OpenRouter response | New cache writes |
| cache_savings | Calculated | Tokens saved from cache |

### Per-Strategy Metrics

| Metric | Description |
|--------|-------------|
| total_requests | Number of orchestration runs |
| total_cost | Sum of all request costs |
| avg_cost_per_request | Average cost per run |
| cost_per_success | Cost per successful completion |
| token_efficiency | Useful tokens / total tokens |
| model_cost_breakdown | Cost by model in team |

### Per-Model Metrics

| Metric | Description |
|--------|-------------|
| total_requests | Times model was used |
| total_tokens | Total tokens consumed |
| total_cost | Total cost incurred |
| avg_cost_per_request | Average per request |
| role_usage | Usage by role (primary/validator/etc) |

## Database Schema

### Table: `usage_records`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Auto-increment ID |
| timestamp | TIMESTAMP | When request completed |
| model_id | VARCHAR(255) | Model used |
| strategy | VARCHAR(100) | Orchestration strategy |
| prompt_tokens | INTEGER | Input tokens |
| completion_tokens | INTEGER | Output tokens |
| reasoning_tokens | INTEGER | Reasoning tokens (nullable) |
| total_cost_usd | DECIMAL(10,6) | Total cost in USD |
| latency_ms | INTEGER | Request latency |
| success | BOOLEAN | Whether request succeeded |
| tenant_id | VARCHAR(100) | Tenant identifier |
| request_hash | VARCHAR(64) | Hash for deduplication |

### Table: `daily_cost_summary`

Pre-aggregated daily summaries:

| Column | Type | Description |
|--------|------|-------------|
| date | DATE PK | Summary date |
| model_id | VARCHAR(255) PK | Model |
| strategy | VARCHAR(100) PK | Strategy |
| total_requests | INTEGER | Request count |
| total_tokens | BIGINT | Token count |
| total_cost_usd | DECIMAL(12,4) | Total cost |
| avg_latency_ms | INTEGER | Average latency |
| success_rate | DECIMAL(5,4) | Success rate |

## Cost Calculation

### Standard Pricing Model

```python
def calculate_cost(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    reasoning_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Calculate total cost for a request."""
    
    model = get_model(model_id)
    pricing = model.pricing
    
    # Convert from per-token to actual cost
    prompt_cost = prompt_tokens * pricing.prompt
    completion_cost = completion_tokens * pricing.completion
    reasoning_cost = reasoning_tokens * pricing.internal_reasoning
    
    # Cache reads are typically free or discounted
    cache_cost = cache_read_tokens * pricing.cache_read
    
    return prompt_cost + completion_cost + reasoning_cost + cache_cost
```

### Multi-Model Request

For orchestration strategies using multiple models:

```python
def calculate_orchestration_cost(
    model_calls: List[ModelCall],
) -> Dict[str, float]:
    """Calculate cost breakdown for multi-model orchestration."""
    
    total = 0.0
    breakdown = {}
    
    for call in model_calls:
        cost = calculate_cost(
            call.model_id,
            call.prompt_tokens,
            call.completion_tokens,
            call.reasoning_tokens,
        )
        
        breakdown[call.model_id] = breakdown.get(call.model_id, 0) + cost
        total += cost
    
    return {
        "total": total,
        "by_model": breakdown,
        "by_role": aggregate_by_role(model_calls),
    }
```

## API Endpoints

### Cost Dashboard

```http
GET /api/costs/dashboard?range=7d
```

Response:
```json
{
  "range": "7d",
  "totals": {
    "requests": 12450,
    "tokens": 45678900,
    "cost_usd": 234.56
  },
  "by_model": [
    {
      "model_id": "openai/gpt-4o",
      "requests": 3200,
      "cost_usd": 89.50,
      "percentage": 38.1
    }
  ],
  "by_strategy": [
    {
      "strategy": "parallel_race",
      "requests": 2100,
      "cost_usd": 67.30,
      "avg_cost": 0.032
    }
  ],
  "daily_trend": [
    {"date": "2025-12-17", "cost_usd": 32.10},
    {"date": "2025-12-18", "cost_usd": 28.45}
  ]
}
```

### Export CSV

```http
GET /api/costs/export?range=30d&format=csv
```

Returns CSV with columns:
- date
- model_id
- strategy
- requests
- tokens
- cost_usd
- avg_latency_ms
- success_rate

## Budget Controls

### Max Cost Per Request

```python
# PR5: Applied in adaptive_router.py
if estimated_cost > budget_constraints.max_cost_usd:
    # Skip this model, too expensive
    score -= 0.5  # Heavy penalty
    
    if budget_constraints.prefer_cheaper:
        # Also boost cheaper alternatives
        cheaper_models = [m for m in candidates if m.cost < max_cost * 0.5]
```

### Daily/Monthly Limits

```python
# Check against tenant budget
def check_budget(tenant_id: str, estimated_cost: float) -> bool:
    daily_usage = get_daily_usage(tenant_id)
    daily_limit = get_tenant_daily_limit(tenant_id)
    
    return daily_usage + estimated_cost <= daily_limit
```

## Alerts

### Cost Anomaly Detection

```python
def detect_cost_anomaly(
    tenant_id: str,
    current_cost: float,
    period: str = "1h",
) -> Optional[Alert]:
    """Detect if current spending is anomalous."""
    
    # Get historical average for this period
    historical = get_historical_average(tenant_id, period, lookback="7d")
    
    # Alert if > 3x normal
    if current_cost > historical * 3:
        return Alert(
            type="cost_anomaly",
            severity="warning",
            message=f"Spending {current_cost/historical:.1f}x normal rate",
        )
    
    return None
```

## Optimization Tips

1. **Use caching**: Enable input caching for repeated contexts
2. **Right-size models**: Use cheaper models for simple tasks
3. **Batch requests**: Combine related queries when possible
4. **Monitor patterns**: Track cost per success, not just per request
5. **Set budgets**: Use max_cost_usd to prevent runaway costs

