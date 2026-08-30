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


def test_calculator_display_large_integer_matches_benchmark_regex() -> None:
    from llmhive.app.orchestration.benchmark_tool_forcing import _format_calculator_display
    import re

    display = _format_calculator_display(-478996662, "What is 17^3 + sqrt(625) - 12!")
    assert re.search(r"-?478,?996,?662", display)
    assert ".00" not in display


def test_broker_class_extract_math_matches_module_level() -> None:
    from llmhive.app.orchestration.tool_broker import ToolBroker

    broker = ToolBroker.__new__(ToolBroker)
    prompt = "What is 17^3 + sqrt(625) - 12!"
    class_expr = broker._extract_math_expression(prompt)
    module_expr = extract_math_expression(prompt)
    assert class_expr == module_expr
    assert "factorial(12)" in class_expr
    assert class_expr != "17^3+"


def test_analyze_tool_needs_calculator_query_is_evaluable() -> None:
    from llmhive.app.orchestration.tool_broker import ToolBroker, ToolType
    from llmhive.app.orchestration.scientific_calculator import ScientificCalculator

    broker = ToolBroker.__new__(ToolBroker)
    broker.CALC_TRIGGERS = getattr(ToolBroker, "CALC_TRIGGERS", ("calculate", "what is", "^", "sqrt", "!"))
    # Use a real broker instance for analyze_tool_needs
    from llmhive.app.orchestration.tool_broker import get_tool_broker

    live = get_tool_broker()
    analysis = live.analyze_tool_needs("What is 17^3 + sqrt(625) - 12!")
    calc_reqs = [r for r in analysis.tool_requests if r.tool_type == ToolType.CALCULATOR]
    assert calc_reqs, "expected calculator request"
    result = ScientificCalculator().evaluate(calc_reqs[0].query)
    assert result.get("success")
    assert int(result["result"]) == -478996662


def test_ensure_year_span_answer_appends_difference() -> None:
    from llmhive.app.orchestration.benchmark_tool_forcing import ensure_year_span_answer

    prompt = (
        "How many years passed between Watson and Crick's discovery of DNA's structure "
        "and the completion of the Human Genome Project?"
    )
    incomplete = (
        "Watson and Crick discovered the structure of DNA in 1953.\n"
        "- 2003 (completion of the Human Genome Project)\n"
        "- 1953 (discovery of DNA's structure)"
    )
    fixed = ensure_year_span_answer(prompt, incomplete)
    assert "50 years" in fixed

    already = "About 50 years passed between 1953 and 2003."
    assert ensure_year_span_answer(prompt, already) == already
