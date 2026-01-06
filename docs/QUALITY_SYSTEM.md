# LLMHive Quality System

This document describes the comprehensive quality assurance system for LLMHive's AI orchestration.

## Overview

The quality system ensures LLMHive delivers accurate, reliable answers through:

1. **Golden Prompt Regression** - Production-representative test cases
2. **Live Prompt Audit** - Real API testing against staging/production
3. **Calibrated Confidence** - Trustworthy uncertainty quantification
4. **Self-Grading** - Automatic quality improvement for high-accuracy modes
5. **Trace Metadata** - Full observability for debugging

## Golden Prompts

### Location

`tests/quality_eval/golden_prompts.yaml`

### Categories

| Category | Description | Example |
|----------|-------------|---------|
| `factoid` | Simple factual questions | "Who discovered penicillin?" |
| `math` | Mathematical calculations | "What is 15 * 23?" |
| `tool_required` | Questions needing live data | "Current Bitcoin price?" |
| `ambiguous` | Legitimately unclear questions | "Tell me about it" |
| `multi_step` | Complex planning tasks | "Create a marketing plan..." |
| `safety` | Should refuse/handle safely | "How to hack..." |
| `creative` | Open-ended creative tasks | "Write a haiku about..." |

### Prompt Schema

```yaml
- id: factoid_001
  category: factoid
  prompt: "Who discovered penicillin?"
  expected_contains: "Alexander Fleming"
  expected_not_contains: "Could you provide more"
  critical: true
  requirements:
    requires_no_clarification: true
  notes: "Classic factoid - must answer directly with Fleming"
```

### Fields

- `id`: Unique identifier
- `category`: One of the categories above
- `prompt`: The user query
- `expected_contains`: Answer must contain this (case-insensitive)
- `expected_regex`: Answer must match this regex
- `expected_not_contains`: Answer must NOT contain this
- `critical`: If true, failure blocks the build
- `requirements`: Behavioral requirements
- `notes`: Explanation for maintainers

### Critical vs Non-Critical

- **Critical prompts**: Must pass or the build fails
  - All factoid questions with known answers
  - Safety refusals
  - Stub provider detection

- **Non-critical prompts**: Logged but don't fail build
  - Tool-dependent questions (may vary by configuration)
  - Creative outputs (subjective quality)

## Live Prompt Audit

### Running the Audit

```bash
# Local mode (in-process, no API calls)
python tests/quality_eval/live_prompt_audit.py --mode=local

# Staging mode
python tests/quality_eval/live_prompt_audit.py --mode=staging --url=https://staging.llmhive.ai

# Production mode
python tests/quality_eval/live_prompt_audit.py --mode=prod

# Quick check (10 prompts)
python tests/quality_eval/live_prompt_audit.py --mode=local --max-prompts=10

# Critical prompts only
python tests/quality_eval/live_prompt_audit.py --mode=local --critical-only

# Specific categories
python tests/quality_eval/live_prompt_audit.py --mode=local --categories factoid math
```

### Output

The audit produces:
- Console summary table
- JSON report at `artifacts/quality/live_audit_report.json`

### CI Integration

The `quality-regression.yml` workflow:
1. Runs unit quality tests
2. Runs live audit against staging (if secrets available)
3. Fails if critical prompts fail
4. Detects stub provider drift

## Confidence Calculation

### Components

The `confidence` score (0-1) is computed from:

| Factor | Weight | Description |
|--------|--------|-------------|
| Ensemble agreement | 0.3 | How much do models agree? |
| Verification score | 0.25 | Did fact-check pass? |
| Source presence | 0.2 | Are citations provided? |
| Tool success | 0.15 | Did tools execute correctly? |
| Domain risk | 0.1 | Is this a high-risk domain? |

### Formula

```
confidence = (
    agreement_score * 0.3 +
    verification_score * 0.25 +
    source_score * 0.2 +
    tool_success_rate * 0.15 +
    domain_safety * 0.1
)
```

### Domain Risk Adjustments

- Medical/Legal queries: confidence capped at 0.7 without verification
- Financial advice: requires source citations for >0.8 confidence

### Interpretation

| Confidence | Meaning | UI Display |
|------------|---------|------------|
| ≥ 0.9 | Very high confidence | "Verified ✓" badge |
| 0.7-0.89 | High confidence | Standard display |
| 0.5-0.69 | Moderate confidence | "May need verification" |
| < 0.5 | Low confidence | "Uncertain" warning |

## Self-Grader

### Overview

For `accuracy_level >= 4` (Quality/Elite modes), a self-grading step evaluates the draft answer and may trigger improvement.

### Process

1. Generate draft answer
2. Judge model evaluates:
   - Correctness likelihood (0-1)
   - Completeness (0-1)
   - Hallucination risk (0-1)
3. If composite score < 0.7:
   - Enable tools if not used
   - Enable consensus if not used
   - Switch to higher-capability model
4. Regenerate (max 1 improvement iteration)

### Configuration

```python
# Environment variables
SELF_GRADE_ENABLED=true  # Enable self-grading
SELF_GRADE_THRESHOLD=0.7  # Score threshold for improvement
```

### Rate Limiting

- Maximum 1 improvement iteration per request
- Only in accuracy_level >= 4
- Budget-aware (won't exceed token limits)

## Trace Metadata

### Response Schema

Every API response includes:

```json
{
  "content": "The answer...",
  "trace_id": "uuid-v4",
  "confidence": 0.85,
  "models_used": ["gpt-4o", "claude-3-sonnet"],
  "strategy_used": "consensus",
  "verification_status": "PASS",
  "verification_score": 0.92,
  "tools_used": ["web_search"],
  "rag_used": false,
  "memory_used": true,
  "sources": [
    {"title": "Source Name", "url": "https://..."}
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | Unique request identifier |
| `confidence` | float | Calibrated confidence (0-1) |
| `models_used` | array | Models that contributed |
| `strategy_used` | string | hrm/consensus/tools/rag/direct |
| `verification_status` | string | PASS/FAIL/PARTIAL/SKIPPED |
| `verification_score` | float | Fact-check score (0-1) |
| `tools_used` | array | External tools invoked |
| `rag_used` | bool | Whether retrieval was used |
| `memory_used` | bool | Whether session memory was used |
| `sources` | array | Citation sources |

### Using Trace Metadata

#### Debugging

1. Copy `trace_id` from response
2. Search logs for that trace
3. View full orchestration path

#### User Trust

UI displays:
- Confidence badge
- "Verified" status
- Source citations
- Expandable "Why this answer?" drawer

## Factoid Fast Path

### Problem

Simple factoid questions were sometimes triggering generic clarification requests ("Could you provide more details?") when no clarification was needed.

### Solution

The orchestrator now detects "simple factoid" queries and:
1. Disables clarification unless explicitly ambiguous
2. Routes directly to best general model
3. Runs lightweight verification if accuracy >= 3

### Detection Criteria

A query is a "simple factoid" if:
- Single sentence
- Contains WH-word (who, what, when, where)
- Low ambiguity score
- No pronouns needing resolution
- Single clear entity reference

### Tests

```python
# tests/quality_eval/test_prompt_ops.py
def test_factoid_no_clarification():
    """Simple factoids should not trigger clarification."""
    factoids = [
        "Who discovered penicillin?",
        "What is the capital of France?",
        "When did World War II end?",
    ]
    for query in factoids:
        result = orchestrator.process(query)
        assert "clarify" not in result.lower()
        assert "more details" not in result.lower()
```

## Consensus Tie-Breaker

### Problem

When multiple models disagreed, consensus sometimes chose the wrong answer.

### Solution

When deep consensus detects conflict:
1. Run verification on competing candidates
2. Prefer candidate with highest verification score
3. If verification unavailable:
   - Prefer answer with source citations
   - Prefer majority answer
   - Mark with lower confidence

### Example

Query: "Who discovered penicillin - Fleming or Florey?"

- Model A says: "Alexander Fleming discovered penicillin"
- Model B says: "Howard Florey discovered penicillin"

Verification step checks both claims:
- Fleming: Verified (discovered in 1928)
- Florey: Partial (developed production, didn't discover)

Result: "Alexander Fleming" with high confidence

## Stub Provider Detection

### Problem

In misconfigured environments, the system might use a stub provider instead of real models, producing low-quality responses.

### Solution

1. Trace metadata includes `provider_used` and `models_used`
2. Live audit checks for "stub" in models_used
3. CI fails if stub provider detected in staging/prod

### Test

```python
def test_no_stub_provider():
    """Production should never use stub provider."""
    response = api.chat("What is 1+1?")
    assert "stub" not in str(response.get("models_used", [])).lower()
```

## Adding New Golden Prompts

1. Edit `tests/quality_eval/golden_prompts.yaml`
2. Add new prompt with appropriate fields:

```yaml
- id: factoid_new
  category: factoid
  prompt: "Your new question?"
  expected_contains: "Expected answer"
  critical: true  # or false
  requirements:
    requires_no_clarification: true
```

3. Run local audit to verify:

```bash
python tests/quality_eval/live_prompt_audit.py --mode=local
```

4. Commit and push

## Monitoring Quality Over Time

### Metrics to Track

- Pass rate by category
- Average latency by strategy
- Confidence distribution
- Critical failure rate

### Dashboards

(Future) `/admin/quality` page will show:
- Latest audit results
- Trend charts
- Failure analysis

### Alerts

Configure `SLACK_WEBHOOK_URL` secret to receive alerts when:
- Quality regression tests fail
- Critical prompts fail
- Stub provider detected

