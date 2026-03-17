"""MCQ letter extraction — regression-safe, no A-skew.

Used by run_category_benchmarks for MMLU/MMMLU. Handles common formats without
confusing "A" in "Answer" as the answer letter. Never defaults invalid to A.

All behavior is behind internal bench flags; production defaults unchanged.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class MCQExtractionResult:
    """Result of MCQ extraction with diagnostic metadata."""
    letter: Optional[str]  # A, B, C, or D; None if invalid
    method: str  # answer_colon, final_colon, single_token, last_isolated, answer_is, invalid
    is_letter_only: bool  # True if output was effectively just a letter
    raw_truncated: str  # First 400 chars of normalized input


def _normalize(text: str) -> str:
    """Normalize: strip, NFKC, uppercase copy for matching."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text.strip())
    stripped = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFKC", stripped).strip().upper()


def extract_mcq_letter_strict(
    text: str,
    *,
    return_metadata: bool = False,
) -> Optional[str] | Tuple[Optional[str], MCQExtractionResult]:
    """Extract MCQ answer letter with strict format handling.

    Order of strategies:
    1. ANSWER\\s*[:\\-]\\s*([ABCD])\\b  — avoid grabbing A from "Answer"
    2. FINAL\\s*[:\\-]\\s*([ABCD])\\b
    3. Single-token: exactly one of A|B|C|D, optionally (A), [A], A.
    4. Last valid isolated token [ABCD] near end (not first token)
    5. "The answer is X" / multilingual patterns
    6. Return None — never default invalid to A.

    Returns:
        Letter (A/B/C/D) or None if invalid.
        If return_metadata=True, returns (letter, MCQExtractionResult).
    """
    if not text:
        result = MCQExtractionResult(
            letter=None,
            method="invalid",
            is_letter_only=False,
            raw_truncated="",
        )
        return (None, result) if return_metadata else None

    normalized = _normalize(text)
    raw_truncated = normalized[:400]

    # Letter-only: entire normalized is just optional whitespace + one letter + optional punctuation
    letter_only_match = re.match(r"^\s*([ABCD])\s*[.)\]}\s]*$", normalized)
    is_letter_only = bool(letter_only_match)

    # Strategy 1: ANSWER\s*[:\-]\s*([ABCD])\b — explicit, avoids "Answer" A
    m = re.search(r"ANSWER\s*[:\-]\s*([ABCD])\b", normalized)
    if m:
        letter = m.group(1)
        result = MCQExtractionResult(
            letter=letter,
            method="answer_colon",
            is_letter_only=is_letter_only,
            raw_truncated=raw_truncated,
        )
        return (letter, result) if return_metadata else letter

    # Strategy 2: FINAL\s*[:\-]\s*([ABCD])\b
    m = re.search(r"FINAL(?:\s*_?ANSWER)?\s*[:\-]\s*([ABCD])\b", normalized)
    if m:
        letter = m.group(1)
        result = MCQExtractionResult(
            letter=letter,
            method="final_colon",
            is_letter_only=is_letter_only,
            raw_truncated=raw_truncated,
        )
        return (letter, result) if return_metadata else letter

    # Strategy 3: Single-token — exactly one of A|B|C|D, optionally (A), [A], A.
    # Require word boundaries so we don't match "A" in "ANSWER"
    wrapped = re.findall(r"(?:^|[\s(\[\{])\s*([ABCD])\s*(?:$|[\s)\]\}\.,;:])", normalized)
    if len(wrapped) == 1:
        letter = wrapped[0]
        result = MCQExtractionResult(
            letter=letter,
            method="single_token",
            is_letter_only=is_letter_only,
            raw_truncated=raw_truncated,
        )
        return (letter, result) if return_metadata else letter

    # Reject ambiguous: multiple different letters with "or"/"and" (e.g. "B or C")
    if re.search(r"\b(?:OR|AND)\b", normalized):
        letters_in_text = set(re.findall(r"\b([ABCD])\b", normalized))
        if len(letters_in_text) > 1:
            result = MCQExtractionResult(
                letter=None,
                method="invalid",
                is_letter_only=is_letter_only,
                raw_truncated=raw_truncated,
            )
            return (None, result) if return_metadata else None

    # Strategy 4: Last valid isolated token — only in "answer position"
    # (after colon/equals, in parens, or at end) to avoid "A" in "Answer"
    answer_position_matches = []
    for pat in [
        r"[:\=]\s*([ABCD])\b",  # after colon/equals
        r"\(([ABCD])\)",  # in parens
        r"\[([ABCD])\]",  # in brackets
        r"(?:^|[\s:.\-])([ABCD])[.)\]}\s]*$",  # at end, letter after space/colon/start (avoid N/A)
    ]:
        answer_position_matches.extend(re.findall(pat, normalized))
    if answer_position_matches:
        letter = answer_position_matches[-1]
        result = MCQExtractionResult(
            letter=letter,
            method="last_isolated",
            is_letter_only=is_letter_only,
            raw_truncated=raw_truncated,
        )
        return (letter, result) if return_metadata else letter

    # Strategy 5: "The answer is X" / multilingual (must have letter after)
    answer_is = re.search(
        r"(?:ANSWER|CORRECT|CHOICE|RESPUESTA|R[EÉ]PONSE|ANTWORT|RISPOSTA|答案|정답|回答|JAWABAN)\s*(?:IS|ES|EST|IST|E|[:=]|는|은)\s+\(?([ABCD])\)?",  # \s+ requires space before letter
        normalized,
    )
    if answer_is:
        letter = answer_is.group(1)
        result = MCQExtractionResult(
            letter=letter,
            method="answer_is",
            is_letter_only=is_letter_only,
            raw_truncated=raw_truncated,
        )
        return (letter, result) if return_metadata else letter

    # Invalid — never default to A
    result = MCQExtractionResult(
        letter=None,
        method="invalid",
        is_letter_only=is_letter_only,
        raw_truncated=raw_truncated,
    )
    return (None, result) if return_metadata else None
