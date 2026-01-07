# LLMHive Benchmarking System

This document describes the comprehensive benchmarking harness for comparing LLMHive against baseline systems across complex reasoning tasks.

## Overview

The benchmarking system provides:
- **Reproducible runs** with versioned configs, git commits, and timestamps
- **Multi-system comparison** (LLMHive, OpenAI, Anthropic, Perplexity)
- **Objective + rubric scoring** for fair evaluation
- **CI integration** with quality gates
- **Admin UI** for viewing results

## Quick Start

### Running LLMHive-only benchmark (no API keys needed)

```bash
# From project root
cd llmhive
PYTHONPATH=./src python -m llmhive.app.benchmarks.cli \
  --suite ../benchmarks/suites/complex_reasoning_v1.yaml \
  --systems llmhive \
  --mode local

# Or use the convenience script
python scripts/run_benchmarks.py --systems llmhive --mode local
```

### Running multi-system benchmark (requires API keys)

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

python scripts/run_benchmarks.py \
  --systems llmhive,openai,anthropic \
  --mode local \
  --runs-per-case 1
```

## CLI Options

```
python -m llmhive.app.benchmarks.cli [OPTIONS]

Options:
  --suite PATH           Path to benchmark suite YAML
                         (default: benchmarks/suites/complex_reasoning_v1.yaml)
  --systems LIST         Comma-separated systems to benchmark
                         (default: llmhive)
  --runs-per-case N      Number of runs per case for variance (default: 1)
  --mode {local,http}    LLMHive mode: local or http (default: local)
  --outdir PATH          Output directory (default: artifacts/benchmarks/TIMESTAMP)
  --temperature FLOAT    Inference temperature (default: 0.0)
  --max-tokens INT       Max response tokens (default: 2048)
  --timeout FLOAT        Per-case timeout in seconds (default: 120)
  --enable-rubric        Enable rubric-based scoring (requires judge model)
  --judge-system NAME    System to use as judge (default: llmhive)
  --category LIST        Filter by category (comma-separated)
  --prompts LIST         Run specific prompts only (comma-separated IDs)
  --critical-only        Only run critical prompts (quick regression check)
  -v, --verbose          Verbose output
```

### Filtering Examples

```bash
# Run only multi-hop reasoning tests
python scripts/run_benchmarks.py --category multi_hop_reasoning

# Run only critical prompts (quick regression check)
python scripts/run_benchmarks.py --critical-only

# Run specific prompts by ID
python scripts/run_benchmarks.py --prompts mhr_001,mhr_002,tbr_003

# Run domain-specific suite
python scripts/run_benchmarks.py --suite benchmarks/suites/domain_specific_v1.yaml

# Combine filters: critical prompts in tool-backed category
python scripts/run_benchmarks.py --category tool_backed_reasoning --critical-only
```

## Benchmark Suite Format

Suites are YAML files with the following structure:

```yaml
metadata:
  suite_name: "Complex Reasoning Benchmark"
  version: "1.0.0"
  categories:
    - multi_hop_reasoning
    - tool_backed_reasoning
    # ...

prompts:
  - id: mhr_001
    category: multi_hop_reasoning
    prompt: "What is the population of France?"
    expected:
      expected_contains: "67 million"
      expected_regex: "6[0-9]\\s*million"
      expected_numeric:
        value: 67000000
        tolerance: 5000000
    requirements:
      requires_rag: true
      requires_no_clarification: true
    scoring:
      objective_weight: 0.8
      rubric_weight: 0.2
      critical: false
    notes: "Factual question about population"
```

### Expected Value Types

| Type | Description | Example |
|------|-------------|---------|
| `expected_contains` | Case-insensitive substring match | `"Paris"` |
| `expected_regex` | Regular expression match | `"6[0-9]\\s*million"` |
| `expected_not_contains` | Forbidden substring | `"clarify"` |
| `expected_numeric` | Numeric with tolerance | `{value: 42, tolerance: 1}` |
| `expected_jsonschema` | JSON Schema validation | `{type: "object", ...}` |

### Requirements Flags

| Flag | Description |
|------|-------------|
| `requires_rag` | Expects RAG retrieval |
| `requires_tools` | Expects tool usage |
| `requires_mcp2` | Expects sandbox execution |
| `requires_no_clarification` | Should NOT ask clarifying questions |
| `requires_clarification` | SHOULD ask clarifying questions |

## Scoring System

### Objective Scoring (Deterministic)

- **Contains**: 1.0 if substring found, 0.0 otherwise
- **Regex**: 1.0 if pattern matches, 0.0 otherwise
- **Numeric**: 1.0 if within tolerance, 0.0 otherwise
- **Not Contains**: 1.0 if forbidden text absent, 0.0 otherwise

Multiple checks are averaged.

### Rubric Scoring (Qualitative)

When enabled, a judge model evaluates answers on:
- Reasoning depth (1-5)
- Accuracy likelihood (1-5)
- Clarity (1-5)
- Hallucination risk (5=no risk, 1=high risk)
- Completeness (1-5)

Normalized to 0-1 scale.

### Composite Score

```
composite = (objective_weight × objective_score) + (rubric_weight × rubric_score)
```

Weights are defined per prompt in the suite.

## Output Artifacts

Each benchmark run creates:

```
artifacts/benchmarks/YYYYMMDD_HHMMSS/
├── report.json     # Complete structured results
├── report.md       # Human-readable Markdown report
└── cases/          # Per-case JSON files
    ├── mhr_001_LLMHive_0.json
    ├── mhr_001_OpenAI_0.json
    └── ...
```

### Report JSON Structure

```json
{
  "suite_name": "Complex Reasoning Benchmark",
  "suite_version": "1.0.0",
  "git_commit": "abc123def",
  "timestamp": "20260106_143052",
  "config": { "temperature": 0.0, ... },
  "systems": ["LLMHive", "OpenAI"],
  "results": [...],
  "scores": [...],
  "aggregate": {
    "total_cases": 50,
    "systems": {
      "LLMHive": {
        "composite_mean": 0.847,
        "passed_count": 42,
        "failed_count": 8,
        "critical_failures": 0
      }
    }
  },
  "critical_failures": [],
  "passed": true
}
```

## System Runners

### LLMHive Runner

Runs prompts through the full LLMHive orchestration pipeline:
- Same path as frontend (API route)
- Supports local (in-process) or HTTP mode
- Captures all metadata: tools, RAG, HRM, consensus

### External Runners (Optional)

External runners only activate when API keys are present:

| Runner | Environment Variable | Default Model |
|--------|---------------------|---------------|
| OpenAI | `OPENAI_API_KEY` | gpt-4-turbo |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-5-sonnet |
| Perplexity | `PERPLEXITY_API_KEY` | llama-3.1-sonar-large |

**Important**: External runners use raw API calls without tools/RAG for fair comparison.

### Perplexity Import Mode

If no API key but import file exists:

```bash
# Pre-captured responses
benchmarks/baselines/perplexity_responses.json
```

## CI Integration

### GitHub Actions Workflow

The workflow (`.github/workflows/benchmark-comparison.yml`) provides:

1. **Unit tests** - Always run, no external calls
2. **Local benchmark** - LLMHive only, no secrets required
3. **Multi-system benchmark** - Manual dispatch with secrets
4. **Golden regression gate** - Fails if critical prompts fail

### Quality Gates

- Critical prompt failures → CI fails
- Failure rate > 30% → Warning
- Benchmark runs saved as artifacts

### Running in CI

```yaml
# Manual trigger with external baselines
workflow_dispatch:
  inputs:
    enable_external: true
    systems: "llmhive,openai,anthropic"
```

## Admin UI

Access the benchmark viewer at `/admin/benchmarks` (dev mode only).

Enable in production:
```bash
export ADMIN_BENCHMARKS_ENABLED=true
```

Features:
- Leaderboard by system
- Category breakdown
- Per-case drill-down
- Critical failure highlighting

## Fairness Notes

### Temperature = 0

All systems run with `temperature=0` for objective tests to ensure determinism.

### Tool Use Differences

- **LLMHive**: Full tool access (calculator, web search, sandbox)
- **Baselines**: No tools (raw model capability)

This reflects real-world usage but note that LLMHive may excel on tool-requiring tasks due to this advantage.

### Rubric Bias Mitigation

When using rubric scoring:
1. Use multiple judges if available (average scores)
2. Judge critiques are stored but not shown
3. LLMHive as judge may slightly favor itself

## Regression Monitoring

### Summary Script

Use the summary script to analyze benchmark results and detect regressions:

```bash
# View summary of latest benchmark
python scripts/benchmark_summary.py

# Compare with a previous run
python scripts/benchmark_summary.py --compare-to artifacts/benchmarks/20260105_100000/report.json

# Alert on critical failures (useful in CI)
python scripts/benchmark_summary.py --alert

# Output as JSON
python scripts/benchmark_summary.py --json

# Send Slack alert if failures detected
python scripts/benchmark_summary.py --alert --slack-webhook $SLACK_WEBHOOK_URL
```

### Automated Regression Detection

The summary script identifies:
- **New failures**: Prompts that passed before but fail now
- **Fixed prompts**: Previously failing prompts that now pass
- **Score regressions**: >10% score drop
- **Score improvements**: >10% score gain

### Scheduled Benchmarks

Set up a cron job or GitHub Actions schedule for regular benchmarking:

```yaml
# In .github/workflows/benchmark-comparison.yml
on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM UTC
```

## Adding New Suites

1. Create YAML file in `benchmarks/suites/`
2. Follow the schema (see existing suite)
3. Include:
   - Metadata section
   - At least 30 prompts
   - At least one critical prompt
   - Mix of categories
4. Run schema validation:
   ```bash
   pytest tests/benchmarks/test_suite_schema.py -v
   ```

### Available Suites

| Suite | Description | Prompts | Critical |
|-------|-------------|---------|----------|
| `complex_reasoning_v1.yaml` | Core reasoning benchmark (multi-hop, tool, factoid, code, clarification, adversarial) | 55 | 14 |
| `domain_specific_v1.yaml` | Domain expertise (finance, medical, legal, technical, scientific) | 30 | 0 |
| `advanced_reasoning_v1.yaml` | Advanced patterns (proofs, puzzles, counterfactual, analogical, metacognitive, constraint satisfaction) | 36 | 4 |

**Total: 121 prompts across 3 suites**

## Troubleshooting

### "No runners available"

Check that at least one runner has its requirements:
- LLMHive: Always available in local mode
- OpenAI: `pip install openai` + `OPENAI_API_KEY`
- Anthropic: `pip install anthropic` + `ANTHROPIC_API_KEY`

### "Suite file not found"

Ensure path is relative to project root or absolute:
```bash
--suite benchmarks/suites/complex_reasoning_v1.yaml
```

### "Timeout" errors

Increase timeout for complex queries:
```bash
--timeout 300
```

### "Critical failures" in CI

Check the report artifact for details on which prompts failed and why.

## Known Limitations

1. **Perplexity Live Mode**: Requires undocumented API endpoint
2. **Rubric Scoring**: May be biased toward judge model style
3. **Cost Tracking**: Estimates only; actual costs may vary
4. **Latency**: Includes network overhead in HTTP mode

## Contributing

To add new test categories or improve scoring:

1. Add prompts to suite YAML
2. Update scoring logic if needed
3. Add tests to `tests/benchmarks/`
4. Update this documentation

## Automation Scripts

### `scripts/benchmark_summary.py`
Analyze and summarize benchmark results with regression detection.

```bash
python scripts/benchmark_summary.py --help
```

### `scripts/create_regression_issue.py`
Automatically create GitHub issues when regressions are detected.

```bash
python scripts/create_regression_issue.py --dry-run
```

### `scripts/run_benchmarks.py`
Main CLI entrypoint for running benchmarks.

## Admin Dashboard

Access the benchmark dashboard at `/admin/benchmarks/dashboard` (dev mode only).

Features:
- Historical trend visualization
- Score tracking over time
- Critical failure monitoring
- Multi-system comparison

## References

- [Benchmark Suites](../benchmarks/suites/)
- [Runner Implementation](../llmhive/src/llmhive/app/benchmarks/)
- [CI Workflow](../.github/workflows/benchmark-comparison.yml)
- [Scheduled Workflow](../.github/workflows/scheduled-benchmarks.yml)
- [Admin UI](../app/admin/benchmarks/)

