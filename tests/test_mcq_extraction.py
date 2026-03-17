"""Unit tests for MCQ letter extraction (no A-skew, regression-safe)."""
import pytest

# Import from scripts (add parent to path if needed)
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from mcq_extraction import extract_mcq_letter_strict, MCQExtractionResult


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Answer: C", "C"),
        ("ANSWER: C", "C"),
        ("Answer - C", "C"),
        ("FINAL: D", "D"),
        ("FINAL_ANSWER: D", "D"),
        ("FINAL ANSWER: D", "D"),
        ("A", "A"),
        ("(B)", "B"),
        ("[B]", "B"),
        ("Answer: (C)", "C"),
        ("Answer: C. Explanation...", "C"),
        ("Answer: C\n", "C"),
        ("The answer is C", "C"),
        ("The correct answer is B", "B"),
        ("FINAL_ANSWER: A\nCONFIDENCE: 0.9", "A"),
        ("Based on the analysis, the answer is B.", "B"),
        ("Option A is wrong. The answer is C.", "C"),
    ],
)
def test_extract_valid(text: str, expected: str) -> None:
    """Valid extractions return correct letter."""
    assert extract_mcq_letter_strict(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "No letter here",
        "Maybe B or C",
        "Answer:",  # no letter after
        "The answer is",  # no letter
    ],
)
def test_extract_invalid_returns_none(text: str) -> None:
    """Invalid input returns None — never A."""
    result = extract_mcq_letter_strict(text)
    assert result is None


def test_extract_never_defaults_to_a() -> None:
    """Invalid extraction must never return A as default."""
    invalid_inputs = ["", "No answer", "Error", "N/A", "???"]
    for text in invalid_inputs:
        assert extract_mcq_letter_strict(text) is not "A"


def test_extract_answer_prefix_not_confused() -> None:
    """'A' in 'Answer' must not be extracted when answer is different."""
    # "Answer: B" — must get B, not A
    assert extract_mcq_letter_strict("Answer: B") == "B"
    assert extract_mcq_letter_strict("ANSWER: C") == "C"
    assert extract_mcq_letter_strict("The answer is D") == "D"


def test_extract_with_metadata() -> None:
    """return_metadata=True returns (letter, MCQExtractionResult)."""
    letter, meta = extract_mcq_letter_strict("Answer: C", return_metadata=True)
    assert letter == "C"
    assert meta.letter == "C"
    assert meta.method in ("answer_colon", "answer_is")
    assert meta.raw_truncated


def test_extract_invalid_with_metadata() -> None:
    """Invalid returns (None, result) with method=invalid."""
    letter, meta = extract_mcq_letter_strict("", return_metadata=True)
    assert letter is None
    assert meta.method == "invalid"
    assert meta.letter is None
