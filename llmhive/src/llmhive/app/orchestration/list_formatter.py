"""High-quality list formatting for orchestrator output.

Converts model prose with inline bullets (e.g. "• A • B • C") into proper
Markdown lists using ``- `` markers so the frontend renders clean vertical lists.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# Markdown list marker (GFM); avoid Unicode • in stored output.
_MD_BULLET = "- "

_INLINE_BULLET_RE = re.compile(r"\s*[•·▪]\s+")
_INLINE_NUMBERED_RE = re.compile(
    r"(?:^|[\s:;])(\d{1,2})[.)]\s+([A-Za-z0-9][^•\n]*?)(?=\s+\d{1,2}[.)]\s+|$)",
    re.MULTILINE,
)
# "Facebook - 2.6B users" / "Facebook — description"
_NAMED_ITEM_RE = re.compile(
    r"(?:^|[\n•])\s*"
    r"([A-Z][A-Za-z0-9 .&'\-]{1,60}?)"
    r"\s*[-–—:]\s*"
    r"(.+?)"
    r"(?=\n[A-Z][A-Za-z]|\n[-•]|\s+[•·]|\Z)",
    re.MULTILINE,
)


def looks_like_markdown_list(text: str) -> bool:
    if not text or not text.strip():
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    list_lines = sum(
        1
        for ln in lines
        if re.match(r"^[-*+]\s+", ln) or re.match(r"^\d+[.)]\s+", ln) or ln.startswith("• ")
    )
    return list_lines >= 2


def format_as_markdown_bullets(content: str, query: str = "") -> str:
    """Turn list-like prose into a vertical Markdown bullet list."""
    text = (content or "").strip()
    if not text:
        return text

    if looks_like_markdown_list(text) and "\n-" not in text and not text.lstrip().startswith("- "):
        text = _normalize_existing_bullets_to_md(text)

    intro, body = _split_intro(text)
    items = _extract_list_items(body, query)
    if len(items) < 2:
        # Last resort: split on inline •
        if _INLINE_BULLET_RE.search(body):
            parts = [p.strip() for p in _INLINE_BULLET_RE.split(body) if p.strip()]
            if len(parts) >= 2:
                items = [_clean_item(p) for p in parts]

    if len(items) < 2:
        return text

    bullets = [_MD_BULLET + item for item in items]
    if intro:
        return f"{intro}\n\n" + "\n".join(bullets)
    return "\n".join(bullets)


def format_as_markdown_numbered(content: str, query: str = "") -> str:
    """Turn list-like prose into a Markdown numbered list."""
    text = (content or "").strip()
    if not text:
        return text

    intro, body = _split_intro(text)
    items = _extract_list_items(body, query)
    if len(items) < 2 and _INLINE_NUMBERED_RE.search(body):
        items = [m[1].strip() for m in _INLINE_NUMBERED_RE.findall(body)]

    if len(items) < 2:
        bullets_md = format_as_markdown_bullets(content, query)
        lines = [ln for ln in bullets_md.splitlines() if ln.strip().startswith("- ")]
        if len(lines) >= 2:
            return "\n".join(f"{i}. {ln[2:].strip()}" for i, ln in enumerate(lines, 1))
        return text

    numbered = [f"{i}. {item}" for i, item in enumerate(items, 1)]
    if intro:
        return f"{intro}\n\n" + "\n".join(numbered)
    return "\n".join(numbered)


def infer_format_from_query(query: str) -> Optional[str]:
    """Suggest output format slug for automatic mode."""
    q = (query or "").lower()
    if any(p in q for p in ("json only", "only json", "as json", "in json")):
        return "json"
    if any(p in q for p in ("step by step", "steps to", "how do i", "how to ", "tutorial")):
        return "numbered"
    if any(
        p in q
        for p in (
            "list ",
            "list the",
            "top ",
            "top-",
            "rank",
            "ranking",
            "compare",
            "best ",
            "worst ",
            "enumerate",
        )
    ):
        return "bullet"
    if "table" in q or "tabular" in q:
        return "table"
    return None


def format_style_prompt_instructions(format_style: str, query: str) -> str:
    """Strong formatting instructions injected into the orchestration prompt."""
    fmt = (format_style or "automatic").lower().replace("-", "_")
    if fmt == "automatic":
        inferred = infer_format_from_query(query)
        fmt = inferred or "paragraph"

    instructions = {
        "bullet": (
            "FORMAT: Markdown bullet list. One item per line starting with '- '. "
            "Put a blank line before the list. Use **bold** for the item title when naming entities. "
            "Never put multiple bullets on the same line. No inline • characters."
        ),
        "bullet_points": (
            "FORMAT: Markdown bullet list. One item per line starting with '- '. "
            "Put a blank line before the list. Use **bold** for names. Never inline bullets."
        ),
        "numbered": (
            "FORMAT: Markdown numbered list (1. 2. 3.), one item per line. "
            "Blank line before the list. Never embed numbers inline in a paragraph."
        ),
        "step_by_step": (
            "FORMAT: Numbered steps, one step per line. Short imperative titles allowed."
        ),
        "structured": (
            "FORMAT: Use ## section headings and short paragraphs; use '- ' lists for enumerations."
        ),
        "markdown": (
            "FORMAT: Clean Markdown with headings, lists, and emphasis where helpful."
        ),
        "executive_summary": (
            "FORMAT: 2-3 sentence summary, then a '- ' bullet list of key points."
        ),
        "concise": (
            "FORMAT: Brief lead sentence, then '- ' bullets for key facts only."
        ),
        "paragraph": (
            "FORMAT: Clear paragraphs separated by blank lines. Use a bullet list only if enumerating 4+ items."
        ),
    }
    key = fmt.replace("-", "_")
    if key == "step_by_step":
        key = "numbered"
    return instructions.get(key, instructions["paragraph"])


def _split_intro(text: str) -> Tuple[str, str]:
    """Keep a short intro paragraph before the list body."""
    # Inline list in one paragraph: "Here are the top platforms: • A • B"
    colon_split = re.split(r":\s*", text, maxsplit=1)
    if len(colon_split) == 2 and _INLINE_BULLET_RE.search(colon_split[1]):
        intro = colon_split[0].strip() + ":"
        return intro, colon_split[1].strip()

    lines = text.splitlines()
    if len(lines) <= 1:
        return "", text

    first = lines[0].strip()
    rest = "\n".join(lines[1:]).strip()
    if first and not _looks_like_item_line(first) and rest:
        return first, rest
    return "", text


def _extract_list_items(body: str, query: str) -> List[str]:
    body = body.strip()
    if not body:
        return []

    # Inline • separators
    if _INLINE_BULLET_RE.search(body) and body.count("•") + body.count("·") >= 2:
        parts = [p.strip() for p in _INLINE_BULLET_RE.split(body) if p.strip()]
        if len(parts) >= 2:
            return [_format_named_item(p) for p in parts]

    # Inline 1. 2. 3.
    numbered = _INLINE_NUMBERED_RE.findall(body)
    if len(numbered) >= 3:
        return [_format_named_item(m[1]) for m in numbered]

    # Line-based bullets / numbers
    line_items: List[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*+•·▪]\s+(.+)$", line)
        if m:
            line_items.append(_format_named_item(m.group(1)))
            continue
        m = re.match(r"^\d+[.)]\s+(.+)$", line)
        if m:
            line_items.append(_format_named_item(m.group(1)))
            continue
        if _looks_like_item_line(line):
            line_items.append(_format_named_item(line))

    if len(line_items) >= 2:
        return _dedupe_items(line_items)

    # Name — description patterns in prose
    named = _NAMED_ITEM_RE.findall(body)
    if len(named) >= 3:
        return _dedupe_items(
            [_format_named_item(f"**{n.strip()}** — {d.strip()}") for n, d in named]
        )

    return []


def _format_named_item(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^[•·▪\-*]+\s*", "", s)
    s = re.sub(r"^\d+[.)]\s+", "", s)
    # "Facebook - 2.6 billion" -> **Facebook** — 2.6 billion
    m = re.match(r"^([A-Z][A-Za-z0-9 .&'\-]{1,50}?)\s*[-–—:]\s*(.+)$", s)
    if m and len(m.group(1)) < 40:
        name, detail = m.group(1).strip(), m.group(2).strip()
        if not name.startswith("**"):
            return f"**{name}** — {detail}"
    return s


def _clean_item(s: str) -> str:
    s = s.strip().rstrip(".,;")
    return _format_named_item(s)


def _looks_like_item_line(line: str) -> bool:
    if re.match(r"^[-*+•·▪\d]", line):
        return True
    if re.match(r"^[A-Z][A-Za-z0-9 .&'\-]{1,50}\s*[-–—:]", line):
        return True
    return False


def _normalize_existing_bullets_to_md(text: str) -> str:
    out: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        m = re.match(r"^[•·▪]\s+(.+)$", stripped)
        if m:
            out.append(_MD_BULLET + m.group(1).strip())
        elif re.match(r"^[-*+]\s+", stripped):
            out.append(re.sub(r"^[-*+]\s+", _MD_BULLET, stripped))
        else:
            out.append(line)
    return "\n".join(out)


def _dedupe_items(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        key = re.sub(r"\*+", "", item).lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
