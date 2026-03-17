# LLMHive Public Benchmark Report

Generated: 2026-02-23T02:20:06.994761+00:00
Intelligence mode: `advisory`
Registry models: 9

## Category Scores

| Category | Accuracy | Samples | Avg Latency |
|----------|----------|---------|-------------|
| coding | 100.0% | 5 | 38922ms |

## Performance vs Single-Model Baselines

### vs gpt-5.2-pro (aggregate uplift: -82.09%)

| Category | LLMHive | Baseline | Uplift |
|----------|---------|----------|--------|
| coding | 100.0% | 90.0% | +11.11% |
| dialogue | 0.0% | 6.5% | -100.00% |
| long_context | 0.0% | 88.0% | -100.00% |
| math | 0.0% | 95.0% | -100.00% |
| multilingual | 0.0% | 76.0% | -100.00% |
| rag | 0.0% | 40.0% | -100.00% |
| reasoning | 0.0% | 78.0% | -100.00% |
| tool_use | 0.0% | 85.0% | -100.00% |

### vs claude-sonnet-4.6 (aggregate uplift: -81.79%)

| Category | LLMHive | Baseline | Uplift |
|----------|---------|----------|--------|
| coding | 100.0% | 88.0% | +13.64% |
| dialogue | 0.0% | 7.0% | -100.00% |
| long_context | 0.0% | 85.0% | -100.00% |
| math | 0.0% | 91.0% | -100.00% |
| multilingual | 0.0% | 82.0% | -100.00% |
| rag | 0.0% | 38.0% | -100.00% |
| reasoning | 0.0% | 76.0% | -100.00% |
| tool_use | 0.0% | 82.0% | -100.00% |

### vs gemini-2.5-pro (aggregate uplift: -81.58%)

| Category | LLMHive | Baseline | Uplift |
|----------|---------|----------|--------|
| coding | 100.0% | 84.0% | +19.05% |
| dialogue | 0.0% | 6.0% | -100.00% |
| long_context | 0.0% | 96.0% | -100.00% |
| math | 0.0% | 89.0% | -100.00% |
| multilingual | 0.0% | 78.0% | -100.00% |
| rag | 0.0% | 36.0% | -100.00% |
| reasoning | 0.0% | 74.0% | -100.00% |
| tool_use | 0.0% | 80.0% | -100.00% |


## RAG Quality Index (RQI) Uplift

| vs Baseline | LLMHive RQI | Baseline RQI | Uplift |
|-------------|-------------|--------------|--------|
| gpt-5.2-pro | 0.0000 | 0.3800 | -0.3800 (-100.00%) |
| claude-sonnet-4.6 | 0.0000 | 0.3500 | -0.3500 (-100.00%) |
| gemini-2.5-pro | 0.0000 | 0.3300 | -0.3300 (-100.00%) |

## Competitive Advantage Index

- **CAI Composite**: 0.00 (improvement_needed)
- RAG Quality Index (RQI): 0.0000
- SLA Compliance: 0.0%
- Entropy Stability: 1.0000

## Ensemble Precision

- Avg Entropy: 0.0000
- Escalations: 0
- Instability Fallbacks: 0

## Verify Pipeline

- Timeout Rate: 0.00%
- Latency p95: 0ms

## Cost Efficiency

- Cost per correct answer: $0.0300
- Total cost: $0.1498

## Reliability

- Total alerts: 0
