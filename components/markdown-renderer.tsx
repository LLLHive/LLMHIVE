"use client"

import React, { memo, useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import { Check, Copy, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "@/lib/toast"

// ============================================================================
// INTELLIGENT CONTENT PREPROCESSOR
// Detects and formats code, restores structure, enhances markdown
// ============================================================================

/**
 * Preprocesses content to ensure proper markdown formatting
 * - Detects code patterns and wraps in code blocks
 * - Restores newlines that may have been stripped
 * - Formats inline code properly
 */
function preprocessContent(content: string): string {
  if (!content) return content
  
  let processed = content
  
  // If content already has proper code blocks, don't process
  if (processed.includes("```")) {
    return processed
  }
  
  // Detect if this looks like code that was flattened to a single line
  // Patterns: def func(), function name(), class Name, const/let/var, import statements
  const codePatterns = [
    // Python
    /def\s+\w+\s*\([^)]*\)\s*:/,
    /class\s+\w+\s*[:(]/,
    /import\s+\w+|from\s+\w+\s+import/,
    /#.*?(?:Example|Usage|Output):/i,
    
    // JavaScript/TypeScript
    /function\s+\w+\s*\(/,
    /const\s+\w+\s*=/,
    /let\s+\w+\s*=/,
    /var\s+\w+\s*=/,
    /=>\s*{/,
    /export\s+(default\s+)?/,
    
    // General code indicators
    /return\s+\w+/,
    /if\s*\([^)]+\)\s*{/,
    /for\s*\([^)]+\)\s*{/,
    /while\s*\([^)]+\)\s*{/,
  ]
  
  const looksLikeCode = codePatterns.some(pattern => pattern.test(processed))
  
  if (looksLikeCode) {
    // Detect the language
    let language = "code"
    if (/def\s+\w+|class\s+\w+.*:|import\s+\w+|from\s+\w+\s+import|print\(/.test(processed)) {
      language = "python"
    } else if (/function\s+\w+|const\s+|let\s+|var\s+|=>\s*{|console\.log/.test(processed)) {
      language = "javascript"
    } else if (/public\s+class|private\s+|System\.out/.test(processed)) {
      language = "java"
    } else if (/#include|int\s+main|std::/.test(processed)) {
      language = "cpp"
    }
    
    // Try to restore structure by detecting logical breakpoints
    processed = restoreCodeStructure(processed, language)
    
    // Wrap in code block
    processed = `\`\`\`${language}\n${processed}\n\`\`\``
  }
  
  return processed
}

/**
 * Attempts to restore code structure from flattened text
 */
function restoreCodeStructure(code: string, language: string): string {
  let restored = code
  
  if (language === "python") {
    // Add newlines before Python keywords
    restored = restored
      .replace(/\s*(def\s+)/g, '\n\n$1')
      .replace(/\s*(class\s+)/g, '\n\n$1')
      .replace(/\s*(#\s*(?:Example|Usage|Output|Note))/gi, '\n\n$1')
      .replace(/\s*(return\s+)/g, '\n    $1')
      .replace(/\s*(if\s+)/g, '\n    $1')
      .replace(/\s*(for\s+)/g, '\n    $1')
      .replace(/\s*(while\s+)/g, '\n    $1')
      .replace(/\s*(print\()/g, '\n$1')
      .replace(/"""\s*/g, '"""\n    ')
      .replace(/\s*"""/g, '\n    """')
      .trim()
  } else if (language === "javascript" || language === "typescript") {
    // Add newlines before JavaScript constructs
    restored = restored
      .replace(/\s*(function\s+)/g, '\n\n$1')
      .replace(/\s*(const\s+\w+\s*=\s*(?:function|\())/g, '\n\n$1')
      .replace(/\s*(\/\/\s*(?:Example|Usage|Output|Note))/gi, '\n\n$1')
      .replace(/\s*(return\s+)/g, '\n  $1')
      .replace(/\s*(if\s*\()/g, '\n  $1')
      .replace(/\s*(for\s*\()/g, '\n  $1')
      .replace(/\s*(console\.log)/g, '\n$1')
      .replace(/\s*}\s*/g, '\n}\n')
      .replace(/{\s*/g, ' {\n  ')
      .trim()
  }
  
  // Clean up excessive newlines
  restored = restored.replace(/\n{3,}/g, '\n\n').trim()
  
  return restored
}

// ============================================================================
// CODE BLOCK COMPONENT
// Premium code display with syntax highlighting and copy button
// ============================================================================

function CodeBlock({ 
  inline, 
  className, 
  children, 
  ...props 
}: { 
  inline?: boolean
  className?: string
  children?: React.ReactNode
}) {
  const [copied, setCopied] = React.useState(false)
  const match = /language-(\w+)/.exec(className || "")
  const language = match ? match[1] : "code"
  
  // Get code content as string
  const codeContent = String(children).replace(/\n$/, "")
  
  const handleCopy = () => {
    navigator.clipboard.writeText(codeContent)
    setCopied(true)
    toast.success("Code copied!")
    setTimeout(() => setCopied(false), 2000)
  }

  // Inline code
  if (inline) {
    return (
      <code
        className="px-1.5 py-0.5 rounded-md bg-[var(--bronze)]/10 text-[var(--bronze)] font-mono text-[0.9em] border border-[var(--bronze)]/20"
        {...props}
      >
        {children}
      </code>
    )
  }

  // Multi-line code block with premium styling
  return (
    <div className="group relative my-4 rounded-xl overflow-hidden border border-border bg-[#0d1117] shadow-lg">
      {/* Header with language label and copy button */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/10 bg-[#161b22]">
        <div className="flex items-center gap-2">
          {/* Language icon dots */}
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
            <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
            <div className="w-3 h-3 rounded-full bg-[#27ca40]" />
          </div>
          <span className="text-xs font-medium text-white/60 uppercase tracking-wider ml-2">
            {language}
          </span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="h-7 px-2.5 gap-1.5 text-xs text-white/60 hover:text-white hover:bg-white/10 transition-all"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-400" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Copy</span>
            </>
          )}
        </Button>
      </div>
      
      {/* Code content with syntax highlighting */}
      <pre className="p-4 overflow-x-auto text-sm leading-relaxed">
        <code className={cn("font-mono text-[#e6edf3]", className)} {...props}>
          {children}
        </code>
      </pre>
    </div>
  )
}

// ============================================================================
// CUSTOM LINK COMPONENT
// External links with indicators
// ============================================================================

function CustomLink({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const isExternal = href?.startsWith("http")
  
  return (
    <a
      href={href}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
      className="inline-flex items-center gap-1 text-[var(--bronze)] hover:text-[var(--gold)] underline underline-offset-2 decoration-[var(--bronze)]/30 hover:decoration-[var(--gold)] transition-colors"
      {...props}
    >
      {children}
      {isExternal && <ExternalLink className="h-3 w-3 flex-shrink-0" />}
    </a>
  )
}

// ============================================================================
// MARKDOWN RENDERER COMPONENT
// World-class markdown rendering with premium styling
// ============================================================================

interface MarkdownRendererProps {
  content: string
  className?: string
}

export const MarkdownRenderer = memo(function MarkdownRenderer({ 
  content, 
  className 
}: MarkdownRendererProps) {
  // Preprocess content to ensure proper formatting
  const processedContent = useMemo(() => preprocessContent(content), [content])
  
  return (
    <div className={cn("llmhive-markdown", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings with beautiful hierarchy
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold mt-6 mb-4 pb-2 border-b border-[var(--bronze)]/20 text-foreground first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold mt-5 mb-3 text-foreground flex items-center gap-2">
              <span className="w-1 h-5 bg-gradient-to-b from-[var(--bronze)] to-[var(--gold)] rounded-full" />
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold mt-4 mb-2 text-foreground">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-semibold mt-3 mb-2 text-foreground">
              {children}
            </h4>
          ),
          
          // Paragraphs
          p: ({ children }) => (
            <p className="mb-3 leading-relaxed text-foreground/90 last:mb-0">
              {children}
            </p>
          ),
          
          // Lists with premium styling
          ul: ({ children }) => (
            <ul className="my-3 ml-1 space-y-2">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 ml-1 space-y-2.5 list-none counter-reset-[item]">
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => {
            // Check if this is inside an ordered list
            const isOrdered = (props as any)?.ordered
            
            if (isOrdered) {
              return (
                <li className="flex items-start gap-3 [counter-increment:item]">
                  <span className="flex-shrink-0 min-w-[1.75rem] h-7 rounded-lg bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] text-background text-sm font-bold flex items-center justify-center mt-0.5 shadow-sm">
                    <span className="before:content-[counter(item)]" />
                  </span>
                  <span className="flex-1 pt-0.5">{children}</span>
                </li>
              )
            }
            
            return (
              <li className="flex items-start gap-3">
                <span className="flex-shrink-0 w-2 h-2 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] mt-2 shadow-sm" />
                <span className="flex-1">{children}</span>
              </li>
            )
          },
          
          // Code blocks - use our premium component
          code: CodeBlock as any,
          pre: ({ children }) => <>{children}</>,
          
          // Links
          a: CustomLink as any,
          
          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="my-4 pl-4 border-l-4 border-[var(--bronze)] bg-[var(--bronze)]/5 py-3 pr-4 rounded-r-lg italic text-foreground/80">
              {children}
            </blockquote>
          ),
          
          // Tables
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-border shadow-sm">
              <table className="w-full border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gradient-to-r from-[var(--bronze)]/10 to-[var(--gold)]/10 border-b border-border">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-border">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-muted/50 transition-colors">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-4 py-3 text-left font-semibold text-[var(--bronze)]">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-3 text-foreground/80">{children}</td>
          ),
          
          // Horizontal rule
          hr: () => (
            <hr className="my-6 border-0 h-px bg-gradient-to-r from-transparent via-[var(--bronze)]/30 to-transparent" />
          ),
          
          // Strong and emphasis
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-foreground/90">{children}</em>
          ),
          
          // Images
          img: ({ src, alt }) => (
            <figure className="my-4">
              <img
                src={src}
                alt={alt || ""}
                className="rounded-lg border border-border max-w-full h-auto shadow-sm"
                loading="lazy"
              />
              {alt && (
                <figcaption className="mt-2 text-center text-xs text-muted-foreground">
                  {alt}
                </figcaption>
              )}
            </figure>
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  )
})

export default MarkdownRenderer
