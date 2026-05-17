/**
 * Display-only markdown enhancements (client-side).
 * Does not alter orchestration output — only improves rendering fidelity.
 */

const CALLOUT_LINE =
  /^(Note|Tip|Important|Warning|Caution|Summary|Key takeaway|Takeaway):\s*(.+)$/i

const HEADING_LINE = /^(#{1,6})\s+/
const LIST_LINE = /^(\s*)([-*+]|\d+\.)\s+/

/** Ensure blank lines before block elements so GFM parses structure correctly. */
export function ensureBlockSeparation(text: string): string {
  const lines = text.split("\n")
  const out: string[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const prev = out[out.length - 1] ?? ""
    const prevBlank = prev.trim() === ""
    const isBlock =
      HEADING_LINE.test(line.trim()) ||
      LIST_LINE.test(line) ||
      line.trim().startsWith(">") ||
      line.trim().startsWith("```") ||
      line.trim() === "---"

    if (isBlock && prev.trim() !== "" && !prevBlank) {
      out.push("")
    }
    out.push(line)
  }

  return out.join("\n")
}

/** Promote standalone "Note: …" lines into GFM blockquotes for callout styling. */
export function promoteCallouts(text: string): string {
  const lines = text.split("\n")
  const out: string[] = []
  let inFence = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith("```")) {
      inFence = !inFence
      out.push(line)
      continue
    }
    if (inFence) {
      out.push(line)
      continue
    }
    if (trimmed.startsWith(">")) {
      out.push(line)
      continue
    }

    const m = trimmed.match(CALLOUT_LINE)
    if (m) {
      const label = m[1].replace(/\s+/g, " ")
      const body = m[2].trim()
      const capitalized =
        label.charAt(0).toUpperCase() + label.slice(1).toLowerCase()
      out.push(`> **${capitalized}:** ${body}`)
      continue
    }

    out.push(line)
  }

  return out.join("\n")
}

/** Normalize dash characters for consistent typography. */
export function normalizeTypography(text: string): string {
  return text
    .replace(/\s+--\s+/g, " — ")
    .replace(/([A-Za-z0-9])-\s+([A-Za-z])/g, "$1 — $2")
}

/** Collapse runs of spaces/tabs on each line (preserves newlines and fences). */
export function normalizeLineWhitespace(text: string): string {
  const lines = text.split("\n")
  let inFence = false
  return lines
    .map((line) => {
      if (line.trim().startsWith("```")) {
        inFence = !inFence
        return line
      }
      if (inFence) return line
      return line.replace(/[^\S\n]+/g, " ").replace(/ +$/, "")
    })
    .join("\n")
}

export function enhanceMarkdownForDisplay(text: string): string {
  let out = text
  out = normalizeLineWhitespace(out)
  out = normalizeTypography(out)
  out = ensureBlockSeparation(out)
  out = promoteCallouts(out)
  out = out.replace(/\n{3,}/g, "\n\n")
  return out.trim()
}
