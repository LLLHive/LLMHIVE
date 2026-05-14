/**
 * Inline attachment text for the orchestrator prompt.
 *
 * The Next.js / FastAPI stack only forwards `prompt` + `history` as plain
 * strings. Attachments must be merged into outbound text here; otherwise the
 * model never sees the file (which reads as "instant upload" + confident
 * hallucinations about document contents).
 */
import type { Attachment } from "@/lib/types"

/** FastAPI ChatRequest.prompt max_length (orchestration.py) minus safety margin */
const OUTBOUND_PROMPT_MAX = 9500

const GROUNDING_SUFFIX = `

---
Instructions: Base your answer only on the message and any attached excerpts above. If the question cannot be answered from that material, say clearly that the excerpt does not contain enough information — do not invent facts, figures, or quotes.
`

/** Max bytes read client-side per file (avoid freezing the tab on huge binaries). */
const MAX_TEXT_FILE_READ_BYTES = 512 * 1024

/** Max characters kept per file before global merge (second truncation in merge). */
const MAX_EXCERPT_PER_FILE = 32_000

const TEXT_LIKE_MIME = new Set([
  "text/plain",
  "text/markdown",
  "text/csv",
  "text/html",
  "text/xml",
  "application/json",
  "application/xml",
  "application/javascript",
  "application/typescript",
  "text/javascript",
  "text/css",
])

const TEXT_LIKE_EXT = new Set([
  ".txt",
  ".md",
  ".markdown",
  ".csv",
  ".tsv",
  ".json",
  ".jsonl",
  ".xml",
  ".html",
  ".htm",
  ".css",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".mjs",
  ".cjs",
  ".py",
  ".rb",
  ".go",
  ".rs",
  ".java",
  ".kt",
  ".c",
  ".h",
  ".cpp",
  ".hpp",
  ".cs",
  ".swift",
  ".sql",
  ".yaml",
  ".yml",
  ".toml",
  ".ini",
  ".cfg",
  ".sh",
  ".env",
  ".log",
])

export function isTextLikeFile(file: File): boolean {
  const t = (file.type || "").toLowerCase().split(";")[0].trim()
  if (TEXT_LIKE_MIME.has(t)) return true
  const name = file.name.toLowerCase()
  const dot = name.lastIndexOf(".")
  if (dot === -1) return false
  return TEXT_LIKE_EXT.has(name.slice(dot))
}

export async function readTextFileWithCap(
  file: File,
  maxChars: number
): Promise<{ text: string; truncated: boolean; note?: string }> {
  const slice = file.slice(0, Math.min(file.size, MAX_TEXT_FILE_READ_BYTES))
  const raw = await slice.text()
  const byteTruncated = file.size > MAX_TEXT_FILE_READ_BYTES
  let text = raw
  let truncated = byteTruncated
  if (text.length > maxChars) {
    text = text.slice(0, maxChars)
    truncated = true
  }
  return {
    text,
    truncated,
    note: truncated
      ? byteTruncated
        ? `Only the first ${MAX_TEXT_FILE_READ_BYTES.toLocaleString()} bytes were read; text may be truncated.`
        : `Truncated to ${maxChars.toLocaleString()} characters.`
      : undefined,
  }
}

/**
 * Merge user text + attachment excerpts into one string under the backend
 * prompt cap. Unsupported attachments become explicit disclaimers so the model
 * does not imply it read them.
 */
export function buildOutboundUserContent(
  userContent: string,
  attachments: Attachment[] | undefined
): string {
  const trimmed = userContent.trim()
  if (!attachments?.length) {
    return trimmed.slice(0, OUTBOUND_PROMPT_MAX)
  }

  const blocks: string[] = [trimmed]

  for (const a of attachments) {
    const excerpt = a.textExcerpt?.trim()
    if (excerpt) {
      const note = a.inlineNote
      blocks.push(
        `\n\n--- Attached: ${a.name} (${a.size} bytes)${note ? ` — ${note}` : ""} ---\n${excerpt}`
      )
    } else {
      const note =
        a.inlineNote ||
        "Paste a relevant excerpt into your message if you need the model to use this file."
      blocks.push(
        `\n\n[Attachment not sent as readable text: "${a.name}" (${a.type || "unknown type"}, ${a.size} bytes). ${note}]`
      )
    }
  }

  let body = blocks.join("")
  const maxBody = OUTBOUND_PROMPT_MAX - GROUNDING_SUFFIX.length
  if (body.length > maxBody) {
    body =
      body.slice(0, maxBody) +
      "\n\n[... message truncated to model input limit; shorten the file or split into smaller parts.]"
  }
  return (body + GROUNDING_SUFFIX).slice(0, OUTBOUND_PROMPT_MAX)
}

/** Read text for storage on the attachment before send (per-file cap). */
export async function extractTextExcerptForAttachment(
  file: File
): Promise<{ textExcerpt: string; inlineNote?: string }> {
  const { text, truncated, note } = await readTextFileWithCap(file, MAX_EXCERPT_PER_FILE)
  return {
    textExcerpt: text,
    inlineNote: note,
  }
}
