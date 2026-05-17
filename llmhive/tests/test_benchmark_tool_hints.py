"""Unit tests for TBR calculator and CDR code-extraction hints."""
from __future__ import annotations

import pytest

from llmhive.app.orchestration.tool_broker import (
    build_code_from_prompt,
    extract_math_expression,
    should_use_calculator,
    should_use_code_execution,
)
from llmhive.app.orchestration.scientific_calculator import ScientificCalculator


@pytest.mark.parametrize(
    "prompt,expected_substr",
    [
        (
            "Calculate: If a company has revenue of $4.5 million and expenses of $3.2 million, what is the profit margin as a percentage?",
            "4500000",
        ),
        (
            "Convert 100 kilometers to miles and then calculate how many minutes it would take to travel that distance at 60 mph.",
            "0.621371",
        ),
        (
            "What is 17^3 + sqrt(625) - 12!",
            "factorial(12)",
        ),
    ],
)
def test_extract_math_expression_benchmark_prompts(prompt: str, expected_substr: str) -> None:
    expr = extract_math_expression(prompt)
    assert expected_substr in expr


def test_calculator_evaluates_tbr_prompts() -> None:
    calc = ScientificCalculator()
    margin_expr = extract_math_expression(
        "Calculate: If a company has revenue of $4.5 million and expenses of $3.2 million, "
        "what is the profit margin as a percentage?"
    )
    margin = calc.evaluate(margin_expr)["result"]
    assert abs(float(margin) - 28.89) < 0.1

    time_expr = extract_math_expression(
        "Convert 100 kilometers to miles and then calculate how many minutes it would take "
        "to travel that distance at 60 mph."
    )
    minutes = calc.evaluate(time_expr)["result"]
    assert abs(float(minutes) - 62.14) < 1.0

    complex_expr = extract_math_expression("What is 17^3 + sqrt(625) - 12!")
    value = calc.evaluate(complex_expr)["result"]
    assert int(value) == -478996662


def test_cdr_sort_code_generation() -> None:
    prompt = (
        "Execute Python code to sort the list [64, 34, 25, 12, 22, 11, 90] "
        "in ascending order and return the sorted list."
    )
    assert should_use_code_execution(prompt)
    code = build_code_from_prompt(prompt)
    assert code is not None
    assert "sorted" in code
    assert "[64, 34, 25, 12, 22, 11, 90]" in code


def test_should_use_calculator_tbr() -> None:
    assert should_use_calculator(
        "Calculate: If a company has revenue of $4.5 million and expenses of $3.2 million, "
        "what is the profit margin as a percentage?"
    )


def test_benchmark_code_short_circuit() -> None:
    from types import SimpleNamespace

    from llmhive.app.orchestration.benchmark_tool_forcing import (
        try_benchmark_tool_short_circuit,
    )

    metadata = SimpleNamespace(
        chat_id="benchmark-cdr_002",
        benchmark_category="code_reasoning",
        force_code_execution=True,
        force_calculator=False,
    )
    prompt = (
        "Execute Python code to sort the list [64, 34, 25, 12, 22, 11, 90] "
        "in ascending order and return the sorted list."
    )
    answer = try_benchmark_tool_short_circuit(
        metadata,
        {"used": True, "code_output": "[11, 12, 22, 25, 34, 64, 90]\n"},
        prompt,
    )
    assert answer is not None
    assert "[11, 12, 22, 25, 34, 64, 90]" in answer
