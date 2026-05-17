"use client"

import { memo, useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeHighlight from "rehype-highlight"
import { cn } from "@/lib/utils"
import { preprocessMarkdown } from "@/lib/markdown/preprocess"
import { markdownComponents } from "@/lib/markdown/renderer-components"

/**
 * Restores structure for flattened code snippets (display-only heuristic).
 */
function restoreCodeStructure(code: string, language: string): string {
  let restored = code

  if (language === "python") {
    restored = restored
      .replace(/\s*(def\s+)/g, "\n\n$1")
      .replace(/\s*(class\s+)/g, "\n\n$1")
      .replace(/\s*(#\s*(?:Example|Usage|Output|Note))/gi, "\n\n$1")
      .replace(/\s*(return\s+)/g, "\n    $1")
      .replace(/\s*(if\s+)/g, "\n    $1")
      .replace(/\s*(for\s+)/g, "\n    $1")
      .replace(/\s*(while\s+)/g, "\n    $1")
      .replace(/\s*(print\()/g, "\n$1")
      .trim()
  } else if (language === "javascript" || language === "typescript") {
    restored = restored
      .replace(/\s*(function\s+)/g, "\n\n$1")
      .replace(/\s*(const\s+\w+\s*=\s*(?:function|\())/g, "\n\n$1")
      .replace(/\s*(\/\/\s*(?:Example|Usage|Output|Note))/gi, "\n\n$1")
      .replace(/\s*(return\s+)/g, "\n  $1")
      .replace(/\s*(if\s*\()/g, "\n  $1")
      .replace(/\s*(for\s*\()/g, "\n  $1")
      .replace(/\s*(console\.log)/g, "\n$1")
      .trim()
  }

  return restored.replace(/\n{3,}/g, "\n\n").trim()
}

function preprocessContent(content: string): string {
  if (!content) return content

  let processed = preprocessMarkdown(content)

  if (processed.includes("```")) {
    return processed
  }

  const codePatterns = [
    /def\s+\w+\s*\([^)]*\)\s*:/,
    /class\s+\w+\s*[:(]/,
    /import\s+\w+|from\s+\w+\s+import/,
    /function\s+\w+\s*\(/,
    /const\s+\w+\s*=/,
    /export\s+(default\s+)?/,
  ]

  if (!codePatterns.some((p) => p.test(processed))) {
    return processed
  }

  let language = "code"
  if (/def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import/.test(processed)) {
    language = "python"
  } else if (/function\s+\w+|const\s+|=>|console\.log/.test(processed)) {
    language = "javascript"
  }

  processed = restoreCodeStructure(processed, language)
  return `\`\`\`${language}\n${processed}\n\`\`\``
}

interface MarkdownRendererProps {
  content: string
  className?: string
}

export const MarkdownRenderer = memo(function MarkdownRenderer({
  content,
  className,
}: MarkdownRendererProps) {
  const processedContent = useMemo(() => preprocessContent(content), [content])

  return (
    <div className={cn("llmhive-markdown", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={markdownComponents as never}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  )
})

export default MarkdownRenderer
