#!/usr/bin/env python3
"""Replace hardcoded https://llmhive.ai URLs with sitePath()/getSiteUrl() calls."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP = {
    "lib/site-url.ts",
    "components/auth/clerk-localhost-blocked.tsx",
    "scripts/codemod_site_urls.py",
}

# Static URLs only (no ${...} in the match).
URL_RE = re.compile(r'"https://llmhive\.ai(/[^"]*)?"')


def ensure_import(text: str) -> str:
    if "from \"@/lib/site-url\"" in text:
        return text

    uses_path = "sitePath(" in text
    uses_get = "getSiteUrl(" in text
    if not uses_path and not uses_get:
        return text

    if uses_path and uses_get:
        import_line = "import { getSiteUrl, sitePath } from \"@/lib/site-url\""
    elif uses_path:
        import_line = "import { sitePath } from \"@/lib/site-url\""
    else:
        import_line = "import { getSiteUrl } from \"@/lib/site-url\""

    lines = text.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            insert_at = i + 1
    lines.insert(insert_at, import_line + "\n")
    return "".join(lines)


def replace_url(match: re.Match[str]) -> str:
    quoted = match.group(0)
    inner = quoted[1:-1]  # strip quotes
    path = inner.removeprefix("https://llmhive.ai")
    if path == "":
        return "getSiteUrl()"
    return f"sitePath({path!r})"


def process_file(path: Path) -> bool:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    if rel in SKIP:
        return False

    original = path.read_text(encoding="utf-8")
    if "https://llmhive.ai" not in original:
        return False

    updated = URL_RE.sub(replace_url, original)
    if updated == original:
        remaining = [m.group(0) for m in re.finditer(r"https://llmhive\.ai", original)]
        if remaining:
            print(f"skip (dynamic URLs remain): {rel} ({len(remaining)} refs)")
        return False

    updated = ensure_import(updated)
    path.write_text(updated, encoding="utf-8")
    print(f"updated {rel}")
    return True


def main() -> None:
    count = 0
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "node_modules" in path.parts or ".next" in path.parts:
            continue
        if process_file(path):
            count += 1
    print(f"done: {count} files")


if __name__ == "__main__":
    main()
