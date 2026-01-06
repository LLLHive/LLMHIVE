# LLMHive Quality Evaluation Test Suite

This directory contains the comprehensive quality evaluation test suite for LLMHive. It validates all critical orchestration features and ensures answer quality meets production standards.

## Overview

The test suite covers:

| Module | Coverage |
|--------|----------|
| `test_prompt_ops.py` | Query analysis, complexity classification, ambiguity detection |
| `test_tool_orchestration.py` | Tool Broker integration, multi-step tool sequences |
| `test_mcp2.py` | Code execution sandbox, security enforcement |
| `test_adaptive_routing.py` | Model selection, fallback logic, ensemble routing |
| `test_deep_consensus.py` | Multi-agent debate, conflict resolution, voting |
| `test_fact_checker.py` | Fact verification, correction loops, citation handling |
| `test_answer_refiner.py` | Output formatting, confidence indicators |
| `test_memory_recall.py` | Blackboard persistence, session isolation |
| `test_guardrails.py` | Safety validation, injection defense, PII redaction |

## Quick Start

### Run All Tests
```bash
# From project root
pytest tests/quality_eval -v

# Or use the convenience script
./scripts/run_quality_suite.sh
```

### Run Specific Test Module
```bash
pytest tests/quality_eval/test_fact_checker.py -v
```

### Run with Coverage
```bash
pytest tests/quality_eval --cov=llmhive --cov-report=html
```

## Test Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QUALITY_THRESHOLD` | `0.7` | Minimum pass rate for CI gate |
| `MAX_FAILURES` | `3` | Maximum allowed test failures |
| `QUALITY_LOG_FILE` | `quality_eval_results.json` | Results output file |
| `SKIP_UI_VALIDATION` | `false` | Skip UI wiring validation |

### PyTest Markers

```bash
# Run only fast unit tests
pytest tests/quality_eval -m "unit and not slow"

# Run integration tests
pytest tests/quality_eval -m integration

# Skip tests requiring external APIs
pytest tests/quality_eval -m "not requires_api"
```

## Continuous Evaluation

### eval_quality.py

Runs the full test suite and logs results for trend tracking:

```bash
python tests/quality_eval/eval_quality.py
```

Output is saved to `quality_eval_results.json` with:
- Pass/fail counts
- Pass rate percentage
- Test-by-test details
- Timestamp for trending

### validate_ui_wiring.py

Verifies that API responses contain all fields expected by the UI:

```bash
python tests/quality_eval/validate_ui_wiring.py
```

Checks for:
- `answer` field (required)
- `sources` list (recommended)
- `confidence` score (recommended)
- Proper type validation

## CI/CD Integration

### GitHub Actions Example

```yaml
jobs:
  quality-eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install pytest pytest-asyncio
      
      - name: Run Quality Suite
        run: ./scripts/run_quality_suite.sh
        env:
          QUALITY_THRESHOLD: 0.7
          MAX_FAILURES: 3
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: quality-results
          path: quality_eval_results.json
```

### Quality Gate

The suite implements a quality gate that fails CI if:
- Pass rate falls below `QUALITY_THRESHOLD` (default 70%)
- More than `MAX_FAILURES` tests fail (default 3)

## Adding New Tests

### Test Structure

```python
"""Tests for [feature name].

This suite validates:
- Feature aspect 1
- Feature aspect 2

Edge cases:
- Edge case 1
- Edge case 2
"""
import pytest

class TestFeatureName:
    """Test suite for [feature]."""

    def test_basic_functionality(self):
        """Description of what this tests."""
        # Arrange
        input_data = "test input"
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected_output

    def test_edge_case(self):
        """Test handling of edge case."""
        # ...
```

### Using Fixtures

```python
def test_with_fixtures(self, sample_simple_query, mock_orchestrator):
    """Test using shared fixtures from conftest.py."""
    result = mock_orchestrator.orchestrate(sample_simple_query)
    assert result is not None
```

## Troubleshooting

### Import Errors

If you see import errors, ensure the llmhive package is in your Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/llmhive/src"
```

### Async Test Failures

For async tests, ensure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio
```

### Skipped Tests

Some tests may be skipped if dependencies are not available. Check the import guards at the top of each test module.

## Results Interpretation

### Pass Rate Targets

| Level | Pass Rate | Status |
|-------|-----------|--------|
| Excellent | ≥ 95% | Production ready |
| Good | ≥ 85% | Minor issues |
| Acceptable | ≥ 70% | Needs attention |
| Poor | < 70% | Block deployment |

### Common Failure Patterns

1. **Fact Checker Failures**: May indicate hallucination issues
2. **Consensus Failures**: Model disagreement problems
3. **Guardrails Failures**: Safety validation gaps
4. **Memory Failures**: Session state issues

## Contributing

When adding new tests:

1. Follow the existing naming convention (`test_*.py`)
2. Add appropriate docstrings
3. Use fixtures from `conftest.py` when possible
4. Include both positive and negative test cases
5. Document edge cases in the module docstring

