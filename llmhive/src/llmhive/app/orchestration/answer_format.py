"""Enterprise answer formatting — post-process orchestrator output for every format mode.

All user-facing format options (automatic, bullet, numbered, structured, etc.)
converge here so the UI receives clean, consistent Markdown.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional, Tuple

_MD_BULLET = "- "

_INLINE_BULLET_RE = re.compile(r"\s*[•·▪]\s+")
_INLINE_NUMBERED_RE = re.compile(
    r"(?:^|[\s:;])(\d{1,2})[.)]\s+([A-Za-z0-9][^•\n]*?)(?=\s+\d{1,2}[.)]\s+|$)",
    re.MULTILINE,
)
_NAMED_ITEM_SEPARATOR_RE = r"(?:\s+[–—-]\s+|:\s+)"
_NAMED_ITEM_RE = re.compile(
    r"(?:^|[\n•])\s*"
    r"([A-Z][A-Za-z0-9 .&'()/+\-]{1,80}?)"
    + _NAMED_ITEM_SEPARATOR_RE +
    r"(.+?)"
    r"(?=\n[A-Z][A-Za-z]|\n[-•]|\s+[•·]|\Z)",
    re.MULTILINE,
)


class FormatProfile(str, Enum):
    AUTOMATIC = "automatic"
    CONVERSATIONAL = "conversational"
    DEFAULT = "default"
    PARAGRAPH = "paragraph"
    STRUCTURED = "structured"
    BULLET = "bullet"
    BULLET_POINTS = "bullet_points"
    NUMBERED = "numbered"
    STEP_BY_STEP = "step_by_step"
    ACADEMIC = "academic"
    MARKDOWN = "markdown"
    CONCISE = "concise"
    EXECUTIVE_SUMMARY = "executive_summary"


def resolve_profile(format_style: str, query: str = "") -> FormatProfile:
    raw = (format_style or "automatic").lower().replace("-", "_")
    if raw in ("automatic", "auto"):
        inferred = infer_format_from_query(query)
        if inferred:
            raw = inferred.replace("-", "_")
        else:
            raw = "conversational"
    aliases = {
        "default": FormatProfile.CONVERSATIONAL,
        "paragraph": FormatProfile.CONVERSATIONAL,
        "bullet": FormatProfile.BULLET,
        "list": FormatProfile.BULLET,
        "step_by_step": FormatProfile.NUMBERED,
        "exec_summary": FormatProfile.CONCISE,
        "executive_summary": FormatProfile.CONCISE,
    }
    if raw in aliases:
        return aliases[raw]
    try:
        return FormatProfile(raw)
    except ValueError:
        return FormatProfile.CONVERSATIONAL


def apply_answer_format(content: str, format_style: str, query: str = "") -> str:
    """Apply profile-specific formatting to final answer Markdown."""
    text = (content or "").strip()
    if not text:
        return text

    profile = resolve_profile(format_style, query)
    text = _normalize_markdown_basics(text)

    if profile in (FormatProfile.BULLET, FormatProfile.BULLET_POINTS):
        text = format_as_markdown_bullets(text, query)
    elif profile in (FormatProfile.NUMBERED, FormatProfile.STEP_BY_STEP):
        text = format_as_markdown_numbered(text, query)
    elif profile == FormatProfile.STRUCTURED:
        text = _format_structured(text)
    elif profile == FormatProfile.ACADEMIC:
        text = _format_academic(text)
    elif profile == FormatProfile.CONCISE:
        text = _format_concise(text, query)
    elif profile == FormatProfile.CONVERSATIONAL:
        text = _format_conversational(text)
    else:
        text = _format_conversational(text)

    return _finalize_document(text)


def infer_format_from_query(query: str) -> Optional[str]:
    q = (query or "").lower()
    if any(p in q for p in ("json only", "only json", "as json", "in json")):
        return "json"
    if any(p in q for p in ("step by step", "steps to", "how do i", "how to ", "tutorial", "guide me")):
        return "numbered"
    if any(
        p in q
        for p in (
            "list ",
            "list the",
            "list of",
            "top ",
            "top-",
            "rank",
            "ranking",
            "compare",
            "best ",
            "worst ",
            "enumerate",
            "pros and cons",
        )
    ):
        return "bullet"
    if "table" in q or "tabular" in q or " vs " in q:
        return "table"
    if any(p in q for p in ("explain", "why", "how does", "overview")):
        return "structured"
    return None


def format_style_prompt_instructions(format_style: str, query: str = "") -> str:
    profile = resolve_profile(format_style, query)
    instructions = {
        FormatProfile.BULLET: (
            "OUTPUT FORMAT (required):\n"
            "- Start with one short introductory sentence.\n"
            "- Then a blank line, then a Markdown bullet list.\n"
            "- Exactly one item per line; each line must start with '- '.\n"
            "- Use **Bold Name** — detail for ranked or named items.\n"
            "- Never use inline • characters or multiple bullets on one line."
        ),
        FormatProfile.NUMBERED: (
            "OUTPUT FORMAT (required):\n"
            "- Short intro sentence, blank line, then numbered list '1. 2. 3.' one per line.\n"
            "- Each step/item on its own line; never embed numbers inside a paragraph."
        ),
        FormatProfile.STRUCTURED: (
            "OUTPUT FORMAT (required):\n"
            "- Use ## Section headings for major parts.\n"
            "- Short paragraphs (2–4 sentences max).\n"
            "- Use '- ' bullet lists for enumerations; tables only when comparing columns."
        ),
        FormatProfile.ACADEMIC: (
            "OUTPUT FORMAT (required):\n"
            "- Formal tone with ## headings.\n"
            "- Structured paragraphs; cite sources as [n] when applicable.\n"
            "- Use '- ' lists sparingly for enumerations."
        ),
        FormatProfile.CONCISE: (
            "OUTPUT FORMAT (required):\n"
            "- One-sentence direct answer first.\n"
            "- Then '- ' bullets for supporting facts only (max 5 unless asked for more)."
        ),
        FormatProfile.CONVERSATIONAL: (
            "OUTPUT FORMAT (required):\n"
            "- Clear paragraphs separated by blank lines.\n"
            "- Use a bullet list only when listing 4+ distinct items."
        ),
    }
    return instructions.get(profile, instructions[FormatProfile.CONVERSATIONAL])


# Re-export list helpers used elsewhere
def format_as_markdown_bullets(content: str, query: str = "") -> str:
    text = (content or "").strip()
    if not text:
        return text
    if looks_like_markdown_list(text):
        text = _normalize_list_markers_to_md(text)
    intro, body = _split_intro(text)
    items = _extract_list_items(body, query)
    if len(items) < 2 and _INLINE_BULLET_RE.search(body):
        parts = [p.strip() for p in _INLINE_BULLET_RE.split(body) if p.strip()]
        if len(parts) >= 2:
            items = [_clean_item(p) for p in parts]
    if len(items) < 2:
        return _format_conversational(text)
    bullets = [_MD_BULLET + item for item in items]
    if intro:
        return f"{intro}\n\n" + "\n".join(bullets)
    return "\n".join(bullets)


def format_as_markdown_numbered(content: str, query: str = "") -> str:
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
            numbered = [f"{i}. {ln[2:].strip()}" for i, ln in enumerate(lines, 1)]
            if intro:
                return f"{intro}\n\n" + "\n".join(numbered)
            return "\n".join(numbered)
        return _format_conversational(text)
    numbered = [f"{i}. {item}" for i, item in enumerate(items, 1)]
    if intro:
        return f"{intro}\n\n" + "\n".join(numbered)
    return "\n".join(numbered)


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


def _format_structured(text: str) -> str:
    if re.search(r"^##\s", text, re.MULTILINE):
        return _ensure_paragraph_spacing(text)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if len(paragraphs) <= 1 and len(text) > 400:
        paragraphs = _split_wall_of_text(text)
    if len(paragraphs) <= 1:
        return text
    sections: List[str] = []
    for i, para in enumerate(paragraphs):
        if i == 0 and len(para) < 120 and not para.endswith(":"):
            sections.append(para)
            continue
        title = _derive_section_title(para, i + 1)
        if para.startswith("##"):
            sections.append(para)
        else:
            sections.append(f"## {title}\n\n{para}")
    return "\n\n".join(sections)


def _format_academic(text: str) -> str:
    return _format_structured(text)


def _format_concise(text: str, query: str = "") -> str:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if not paragraphs:
        return text
    lead = paragraphs[0]
    if len(lead.split()) > 45:
        sentences = re.split(r"(?<=[.!?])\s+", lead)
        lead = sentences[0] if sentences else lead
    rest = "\n\n".join(paragraphs[1:])
    bullets = format_as_markdown_bullets(rest or lead, query)
    if bullets != rest and rest and bullets.count("\n- ") >= 1:
        return f"{lead}\n\n{bullets}"
    if looks_like_markdown_list(text):
        return format_as_markdown_bullets(text, query)
    return _ensure_paragraph_spacing(f"{lead}\n\n{rest}".strip())


def _format_conversational(text: str) -> str:
    if looks_like_markdown_list(text):
        return _normalize_list_markers_to_md(text)
    if len(text) > 500 and "\n\n" not in text:
        return _split_wall_of_text(text)
    return _ensure_paragraph_spacing(text)


def _normalize_markdown_basics(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Line-start bullets first (avoid inline regex eating "• item" at BOL)
    text = re.sub(r"^\s*[•·▪]\s*", _MD_BULLET, text, flags=re.MULTILINE)
    fixed_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if (
            stripped
            and not re.match(r"^[-*+]\s+", stripped)
            and (_INLINE_BULLET_RE.search(line) or "•" in line)
            and (line.count("•") + line.count("·") + line.count("▪")) >= 2
        ):
            fixed_lines.append(_INLINE_BULLET_RE.sub("\n- ", line).strip())
        else:
            fixed_lines.append(line)
    text = "\n".join(fixed_lines)
    return text.strip()


def _normalize_list_markers_to_md(text: str) -> str:
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
        elif re.match(r"^\d+[.)]\s+", stripped):
            out.append(stripped)
        else:
            out.append(line)
    return "\n".join(out)


def _ensure_paragraph_spacing(text: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    return "\n\n".join(blocks)


def _split_wall_of_text(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) < 4:
        return text
    chunks: List[str] = []
    current: List[str] = []
    for s in sentences:
        current.append(s)
        if len(current) >= 3:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return "\n\n".join(chunks)


def _derive_section_title(para: str, index: int) -> str:
    first = para.split(".")[0].strip()
    if 5 < len(first) <= 60:
        return first
    return f"Section {index}"


def _finalize_document(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = _repair_code_copy_leakage(text)
    text = _repair_flattened_list_boundaries(text)
    text = _repair_spaced_urls(text)
    return re.sub(r"\n{3,}", "\n\n", text.strip())


def _repair_code_copy_leakage(text: str) -> str:
    return re.sub(r"\s*\bcode\s+Copy\s*", " ", text, flags=re.IGNORECASE)


def _repair_flattened_list_boundaries(text: str) -> str:
    repaired = text
    repaired = re.sub(r"([.!?])(\d+[.)])\s+(?=[A-Z])", r"\1\n\n\2 ", repaired)
    repaired = re.sub(r"(\))\.(\d+[.)])\s+(?=[A-Z])", r"\1.\n\n\2 ", repaired)
    repaired = re.sub(r"(\S)\.-\s+", r"\1.\n\n- ", repaired)
    return repaired


def _repair_spaced_urls(text: str) -> str:
    """Repair common model-generated URL spacing like ``https://foo. bar. com``."""
    repaired = text
    for _ in range(8):
        updated = re.sub(
            r"(https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+)\s+\.\s+([A-Za-z0-9-])",
            r"\1.\2",
            repaired,
        )
        updated = re.sub(
            r"(https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+)\.\s+([A-Za-z0-9-])",
            r"\1.\2",
            updated,
        )
        if updated == repaired:
            break
        repaired = updated
    return repaired


def _split_intro(text: str) -> Tuple[str, str]:
    colon_split = re.split(r":\s*", text, maxsplit=1)
    if len(colon_split) == 2 and _INLINE_BULLET_RE.search(colon_split[1]):
        return colon_split[0].strip() + ":", colon_split[1].strip()
    lines = text.splitlines()
    if len(lines) <= 1:
        return "", text
    first, rest = lines[0].strip(), "\n".join(lines[1:]).strip()
    if first and not _looks_like_item_line(first) and rest:
        return first, rest
    return "", text


def _extract_list_items(body: str, query: str) -> List[str]:
    body = body.strip()
    if not body:
        return []
    if _INLINE_BULLET_RE.search(body) and body.count("•") + body.count("·") >= 2:
        parts = [p.strip() for p in _INLINE_BULLET_RE.split(body) if p.strip()]
        if len(parts) >= 2:
            return [_format_named_item(p) for p in parts]
    numbered = _INLINE_NUMBERED_RE.findall(body)
    if len(numbered) >= 3:
        return [_format_named_item(m[1]) for m in numbered]
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
    named = _NAMED_ITEM_RE.findall(body)
    if len(named) >= 3:
        return _dedupe_items(
            [f"**{n.strip()}** — {d.strip()}" for n, d in named]
        )
    return []


def _format_named_item(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^[•·▪\-]+\s*", "", s)
    s = re.sub(r"^\d+[.)]\s+", "", s)
    if _has_balanced_bold(s):
        return s
    m = re.match(
        rf"^([A-Z][A-Za-z0-9 .&'()/+\-]{{1,80}}?){_NAMED_ITEM_SEPARATOR_RE}(.+)$",
        s,
    )
    if m and len(m.group(1)) < 80:
        name, detail = m.group(1).strip(), m.group(2).strip()
        if not name.startswith("**"):
            return f"**{name}** — {detail}"
    return s


def _clean_item(s: str) -> str:
    return _format_named_item(s.strip().rstrip(".,;"))


def _looks_like_item_line(line: str) -> bool:
    if re.match(r"^[-*+•·▪\d]", line):
        return True
    return bool(
        re.match(
            rf"^[A-Z][A-Za-z0-9 .&'()/+\-]{{1,80}}{_NAMED_ITEM_SEPARATOR_RE}",
            line,
        )
    )


def _has_balanced_bold(text: str) -> bool:
    """Return True when the item already has complete Markdown bold spans."""
    return text.count("**") >= 2 and text.count("**") % 2 == 0


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
