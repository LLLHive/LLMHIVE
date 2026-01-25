"use client"

import React, { memo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import { Check, Copy, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "@/lib/toast"

// Code block with copy functionality and syntax highlighting
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
  const language = match ? match[1] : ""
  
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

  // Code block
  return (
    <div className="group relative my-4 rounded-xl overflow-hidden border border-border bg-[#0d1117]">
      {/* Header with language label and copy button */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/50 bg-[#161b22]">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {language || "code"}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="h-7 px-2 gap-1.5 text-xs text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-500" />
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
      
      {/* Code content */}
      <pre className="p-4 overflow-x-auto text-sm leading-relaxed">
        <code className={cn("font-mono", className)} {...props}>
          {children}
        </code>
      </pre>
    </div>
  )
}

// Custom link component
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

// Markdown renderer props
interface MarkdownRendererProps {
  content: string
  className?: string
}

// World-class markdown renderer component
export const MarkdownRenderer = memo(function MarkdownRenderer({ 
  content, 
  className 
}: MarkdownRendererProps) {
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
            <ul className="my-3 ml-1 space-y-1.5">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 ml-1 space-y-2 list-none counter-reset-item">
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => {
            // Check if this is inside an ordered list by looking at parent context
            const isOrdered = (props as any)?.ordered
            
            if (isOrdered) {
              return (
                <li className="flex items-start gap-3 counter-increment-item">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] text-background text-xs font-bold flex items-center justify-center mt-0.5">
                    <span className="counter-item" />
                  </span>
                  <span className="flex-1">{children}</span>
                </li>
              )
            }
            
            return (
              <li className="flex items-start gap-2.5">
                <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-[var(--bronze)] mt-2" />
                <span className="flex-1">{children}</span>
              </li>
            )
          },
          
          // Code blocks
          code: CodeBlock as any,
          pre: ({ children }) => <>{children}</>,
          
          // Links
          a: CustomLink as any,
          
          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="my-4 pl-4 border-l-4 border-[var(--bronze)] bg-[var(--bronze)]/5 py-2 pr-4 rounded-r-lg italic text-foreground/80">
              {children}
            </blockquote>
          ),
          
          // Tables
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-border">
              <table className="w-full border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[var(--bronze)]/10 border-b border-border">
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
            <th className="px-4 py-2.5 text-left font-semibold text-[var(--bronze)]">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2.5 text-foreground/80">{children}</td>
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
                className="rounded-lg border border-border max-w-full h-auto"
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
        {content}
      </ReactMarkdown>
    </div>
  )
})

export default MarkdownRenderer
