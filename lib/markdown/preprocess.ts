/**
 * Client-side markdown normalization — mirrors backend list rules and adds
 * display-only enhancements. Safe for all stored messages; does not call APIs.
 */

import { enhanceMarkdownForDisplay } from "./enhance"

const INLINE_BULLET = /\s*[•·▪]\s+/g

export function preprocessMarkdown(content: string): string {
  if (!content?.trim()) return content

  let text = content.replace(/\r\n/g, "\n")

  // Remove UI leakage from copied code blocks that models sometimes echo.
  text = text.replace(/\s*\bcode\s+Copy\s*/gi, " ")

  // Repair flattened numbered/list output such as "... Documentation.2. Next".
  text = text
    .replace(/([.!?])(\d+\.)\s+(?=[A-Z])/g, "$1\n\n$2 ")
    .replace(/(\))\.(\d+\.)\s+(?=[A-Z])/g, "$1.\n\n$2 ")
    .replace(/(\S)\.-\s+/g, "$1.\n\n- ")

  // Line-start bullets before inline (same order as backend)
  text = text
    .split("\n")
    .map((line) => line.replace(/^\s*[•·▪]\s+/, "- "))
    .join("\n")

  // Inline bullets on a single line only
  if (/[•·▪]/.test(text) && !/^[-*+]\s/m.test(text)) {
    const lines = text.split("\n").map((line) => {
      const count = (line.match(/[•·▪]/g) || []).length
      if (count >= 2 && !/^\s*[-*+]\s/.test(line)) {
        return line.replace(INLINE_BULLET, "\n- ").trim()
      }
      return line
    })
    text = lines.join("\n")
  }

  // "1. Foo 2. Bar 3. Baz" on one line
  const numMatches = text.match(/\d+\.\s+/g)
  if (numMatches && numMatches.length >= 3 && !text.includes("\n1.")) {
    const items: string[] = []
    let m: RegExpExecArray | null
    const re = /(\d+)\.\s+([^0-9]+?)(?=\s+\d+\.|$)/g
    while ((m = re.exec(text)) !== null) {
      items.push(`${m[1]}. ${m[2].trim().replace(/\s+/g, " ")}`)
    }
    if (items.length >= 3) {
      const idx = text.search(/\d+\.\s+[A-Za-z]/)
      const intro = idx > 0 ? text.slice(0, idx).trim() : ""
      text = intro ? `${intro}\n\n${items.join("\n")}` : items.join("\n")
    }
  }

  return enhanceMarkdownForDisplay(text)
}
