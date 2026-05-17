"use client"

import React from "react"
import { cn } from "@/lib/utils"
import { Check, Copy, ExternalLink, AlertTriangle, Info, Lightbulb, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "@/lib/toast"

function getNodeText(node: React.ReactNode): string {
  if (typeof node === "string") return node
  if (typeof node === "number") return String(node)
  if (Array.isArray(node)) return node.map(getNodeText).join("")
  if (React.isValidElement(node)) {
    const props = node.props as { children?: React.ReactNode }
    return getNodeText(props.children)
  }
  return ""
}

type CalloutKind = "note" | "tip" | "important" | "warning" | "summary" | "default"

function detectCallout(children: React.ReactNode): CalloutKind {
  const text = getNodeText(children).trim()
  if (/^note:/i.test(text)) return "note"
  if (/^tip:/i.test(text)) return "tip"
  if (/^important:/i.test(text)) return "important"
  if (/^(warning|caution):/i.test(text)) return "warning"
  if (/^(summary|key takeaway|takeaway):/i.test(text)) return "summary"
  return "default"
}

const CALLOUT_ICONS: Record<CalloutKind, React.ReactNode> = {
  note: <Info className="h-4 w-4 shrink-0" />,
  tip: <Lightbulb className="h-4 w-4 shrink-0" />,
  important: <Sparkles className="h-4 w-4 shrink-0" />,
  warning: <AlertTriangle className="h-4 w-4 shrink-0" />,
  summary: <Sparkles className="h-4 w-4 shrink-0" />,
  default: <Info className="h-4 w-4 shrink-0 opacity-60" />,
}

export function SmartBlockquote({ children }: { children?: React.ReactNode }) {
  const kind = detectCallout(children)
  const isCallout = kind !== "default"

  return (
    <blockquote
      className={cn(
        "my-5 rounded-lg border text-[0.9375rem] leading-relaxed",
        isCallout
          ? cn("callout py-3.5 px-4 not-italic", `callout-${kind}`)
          : "border-l-[3px] border-[var(--bronze)]/40 bg-muted/30 py-3 px-4 pl-4 text-foreground/85 italic"
      )}
    >
      {isCallout ? (
        <div className="flex gap-3 items-start">
          <span className={cn("callout-icon mt-0.5", `callout-icon-${kind}`)}>
            {CALLOUT_ICONS[kind]}
          </span>
          <div className="callout-body min-w-0 flex-1 [&>p]:mb-0">{children}</div>
        </div>
      ) : (
        children
      )}
    </blockquote>
  )
}

export function CodeBlock({
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
  const highlighted = className?.includes("hljs")
  const codeContent = getNodeText(children).replace(/\n$/, "")

  const handleCopy = () => {
    navigator.clipboard.writeText(codeContent)
    setCopied(true)
    toast.success("Code copied!")
    setTimeout(() => setCopied(false), 2000)
  }

  if (inline) {
    return (
      <code
        className="rounded-md border border-[var(--bronze)]/15 bg-[var(--bronze)]/8 px-1.5 py-0.5 font-mono text-[0.85em] text-[var(--bronze)]"
        {...props}
      >
        {children}
      </code>
    )
  }

  return (
    <div className="group relative my-5 overflow-hidden rounded-xl border border-border/80 bg-[#0d1117] shadow-md">
      <div className="flex items-center justify-between border-b border-white/10 bg-[#161b22] px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5" aria-hidden>
            <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
            <div className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
            <div className="h-2.5 w-2.5 rounded-full bg-[#27ca40]" />
          </div>
          <span className="ml-1 text-[11px] font-medium uppercase tracking-widest text-white/50">
            {language}
          </span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="h-7 gap-1.5 px-2 text-xs text-white/60 hover:bg-white/10 hover:text-white"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-400" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Copy
            </>
          )}
        </Button>
      </div>
      <pre className="overflow-x-auto p-4 text-[0.8125rem] leading-[1.65]">
        <code
          className={cn("font-mono", highlighted ? className : "text-[#e6edf3]")}
          {...props}
        >
          {children}
        </code>
      </pre>
    </div>
  )
}

export function CustomLink({
  href,
  children,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const isExternal = href?.startsWith("http")

  return (
    <a
      href={href}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
      className="font-medium text-[var(--bronze)] underline decoration-[var(--bronze)]/25 underline-offset-[3px] transition-colors hover:text-[var(--gold)] hover:decoration-[var(--gold)]/50"
      {...props}
    >
      {children}
      {isExternal && <ExternalLink className="ml-0.5 inline h-3 w-3 shrink-0 opacity-70" />}
    </a>
  )
}

export const markdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="mb-4 mt-8 border-b border-[var(--bronze)]/15 pb-2 text-2xl font-bold tracking-tight text-foreground first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="mb-3 mt-7 flex items-center gap-2.5 text-xl font-semibold tracking-tight text-foreground first:mt-0">
      <span
        className="h-5 w-1 shrink-0 rounded-full bg-gradient-to-b from-[var(--bronze)] to-[var(--gold)]"
        aria-hidden
      />
      {children}
    </h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="mb-2 mt-6 text-lg font-semibold text-foreground first:mt-0">{children}</h3>
  ),
  h4: ({ children }: { children?: React.ReactNode }) => (
    <h4 className="mb-2 mt-5 text-base font-semibold text-foreground/95 first:mt-0">{children}</h4>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-4 text-[0.9375rem] leading-[1.75] text-foreground/88 last:mb-0">{children}</p>
  ),
  ul: ({
    children,
    className,
  }: {
    children?: React.ReactNode
    className?: string
  }) => (
    <ul
      className={cn(
        "my-4 space-y-2 pl-6",
        className?.includes("contains-task-list")
          ? "list-none pl-1 task-list"
          : "list-disc list-outside",
        "[&_ul]:mt-2 [&_ul]:mb-0",
        className
      )}
    >
      {children}
    </ul>
  ),
  ol: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <ol
      className={cn(
        "my-4 list-decimal list-outside space-y-2.5 pl-6",
        "[&_ol]:mt-2 [&_ol]:mb-0",
        className
      )}
    >
      {children}
    </ol>
  ),
  li: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <li
      className={cn(
        "pl-0.5 leading-[1.7] text-foreground/88",
        "[&>p]:mb-1.5 [&>p:last-child]:mb-0",
        "task-list-item:flex task-list-item:items-start task-list-item:gap-2.5",
        className
      )}
    >
      {children}
    </li>
  ),
  code: CodeBlock,
  pre: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  a: CustomLink,
  blockquote: SmartBlockquote,
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="my-5 overflow-x-auto rounded-xl border border-border/80 shadow-sm">
      <table className="w-full min-w-[280px] border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="border-b border-border bg-muted/40">{children}</thead>
  ),
  tbody: ({ children }: { children?: React.ReactNode }) => (
    <tbody className="divide-y divide-border/80">{children}</tbody>
  ),
  tr: ({ children }: { children?: React.ReactNode }) => (
    <tr className="transition-colors hover:bg-muted/30">{children}</tr>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[var(--bronze)]">
      {children}
    </th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="px-4 py-3 align-top text-foreground/85">{children}</td>
  ),
  hr: () => (
    <hr
      className="my-8 border-0"
      style={{
        height: "1px",
        background:
          "linear-gradient(90deg, transparent, color-mix(in srgb, var(--bronze) 35%, transparent), transparent)",
      }}
    />
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="text-foreground/85 italic">{children}</em>
  ),
  del: ({ children }: { children?: React.ReactNode }) => (
    <del className="text-muted-foreground line-through">{children}</del>
  ),
  kbd: ({ children }: { children?: React.ReactNode }) => (
    <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[0.8em] shadow-sm">
      {children}
    </kbd>
  ),
  sup: ({ children }: { children?: React.ReactNode }) => (
    <sup className="text-[0.7em] text-[var(--bronze)]">{children}</sup>
  ),
  img: ({ src, alt }: { src?: string; alt?: string }) => (
    <figure className="my-5">
      <img
        src={src}
        alt={alt || ""}
        className="h-auto max-w-full rounded-xl border border-border shadow-sm"
        loading="lazy"
      />
      {alt ? (
        <figcaption className="mt-2 text-center text-xs text-muted-foreground">{alt}</figcaption>
      ) : null}
    </figure>
  ),
}
