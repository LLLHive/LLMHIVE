import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_category_benchmarks import (
    _build_humaneval_impl_prompt,
    _completion_from_response,
    _sanitize_completion,
)


def test_humaneval_impl_prompt_forbids_prose_and_example_usage() -> None:
    prompt = _build_humaneval_impl_prompt(
        "def truncate_number(number: float) -> float:\n    pass\n",
        ["  3.5 -> 0.5"],
    )
    assert "Return only valid Python code." in prompt
    assert "No markdown, no prose, no headers, no example usage, no tests." in prompt
    assert "same name and signature as the prompt" in prompt
    assert "docstring examples and explicit checks are the source of truth" in prompt
    assert "If the function name suggests something different" in prompt


def test_humaneval_impl_prompt_includes_optional_style_hint() -> None:
    prompt = _build_humaneval_impl_prompt(
        "def truncate_number(number: float) -> float:\n    pass\n",
        ["  3.5 -> 0.5"],
        style_hint="Prefer the simplest brute-force implementation.",
    )

    assert "Strategy hint:" in prompt
    assert "Prefer the simplest brute-force implementation." in prompt
    assert "Return only valid Python code." in prompt


def test_completion_from_response_skips_shadowed_string_import() -> None:
    problem = {
        "prompt": (
            "def how_many_times(string: str, substring: str) -> int:\n"
            "    \"\"\"Count overlapping substring occurrences.\"\"\"\n"
        ),
        "entry_point": "how_many_times",
    }
    response = (
        "def how_many_times(string: str, substring: str) -> int:\n"
        "    return string.find(substring)\n"
    )

    completion = _completion_from_response(problem, response)

    assert "import string" not in completion
    assert "return string.find(substring)" in completion


def test_completion_from_response_still_adds_math_import_when_needed() -> None:
    problem = {
        "prompt": (
            "def truncate_number(number: float) -> float:\n"
            "    \"\"\"Return the decimal part.\"\"\"\n"
        ),
        "entry_point": "truncate_number",
    }
    response = (
        "def truncate_number(number: float) -> float:\n"
        "    return math.modf(number)[0]\n"
    )

    completion = _completion_from_response(problem, response)

    assert "import math" in completion
    assert "return math.modf(number)[0]" in completion


def test_sanitize_completion_removes_trailing_explanatory_prose() -> None:
    completion = _sanitize_completion(
        "    return float(int(number))\n"
        "    This function converts the number to an integer, effectively truncating it.\n",
        "truncate_number",
    )

    assert completion == "    return float(int(number))\n"
