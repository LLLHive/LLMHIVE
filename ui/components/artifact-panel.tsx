"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { X, Copy, Download, Check, Play, AlertCircle } from "lucide-react"
import type { Artifact } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ArtifactPanelProps {
  artifact: Artifact
  onClose: () => void
}

export function ArtifactPanel({ artifact, onClose }: ArtifactPanelProps) {
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState<"code" | "preview">("code")
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<{ success: boolean; output?: string; error?: string } | null>(
    null,
  )

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([artifact.content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${artifact.title}.${artifact.language || "txt"}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleExecute = async () => {
    if (artifact.type !== "code") return

    setExecuting(true)
    setExecutionResult(null)

    try {
      const response = await fetch("/api/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: artifact.content,
          language: artifact.language || "javascript",
        }),
      })

      const result = await response.json()
      setExecutionResult(result)
    } catch (error) {
      setExecutionResult({
        success: false,
        error: error instanceof Error ? error.message : "Failed to execute code",
      })
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="w-[600px] border-l border-border bg-card flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold">{artifact.title}</h3>
          <p className="text-xs text-muted-foreground mt-1">
            {artifact.type === "code" && `${artifact.language || "Code"} Artifact`}
            {artifact.type === "document" && "Document Artifact"}
            {artifact.type === "visualization" && "Visualization Artifact"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {artifact.type === "code" && (
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-2 border-[var(--bronze)] text-[var(--bronze)] hover:bg-[var(--bronze)]/10 bg-transparent"
              onClick={handleExecute}
              disabled={executing}
            >
              <Play className="h-3 w-3" />
              {executing ? "Running..." : "Run"}
            </Button>
          )}
          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleDownload}>
            <Download className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      {artifact.type === "code" && (
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as "code" | "preview")}
          className="flex-1 flex flex-col"
        >
          <div className="px-4 pt-3">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="code">Code</TabsTrigger>
              <TabsTrigger value="preview">Output</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="code" className="flex-1 m-0 p-0">
            <ScrollArea className="h-full">
              <pre className="p-4 text-xs font-mono bg-secondary/30">
                <code className={cn("language-" + artifact.language)}>{artifact.content}</code>
              </pre>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="preview" className="flex-1 m-0 p-0">
            <div className="h-full flex flex-col">
              {executionResult ? (
                <ScrollArea className="flex-1">
                  <div className="p-4">
                    {executionResult.success ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm font-medium text-green-500">
                          <Check className="h-4 w-4" />
                          Execution Successful
                        </div>
                        <pre className="p-3 rounded-lg bg-secondary text-xs font-mono whitespace-pre-wrap">
                          {executionResult.output || "No output"}
                        </pre>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                          <AlertCircle className="h-4 w-4" />
                          Execution Failed
                        </div>
                        <pre className="p-3 rounded-lg bg-destructive/10 text-xs font-mono text-destructive whitespace-pre-wrap">
                          {executionResult.error}
                        </pre>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              ) : (
                <div className="flex-1 flex items-center justify-center bg-secondary/30">
                  <div className="text-center text-muted-foreground">
                    <Play className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">Click "Run" to execute code</p>
                    <p className="text-xs mt-1">Supports JavaScript and TypeScript</p>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      )}

      {artifact.type === "document" && (
        <ScrollArea className="flex-1">
          <div className="p-4 prose prose-sm dark:prose-invert max-w-none">{artifact.content}</div>
        </ScrollArea>
      )}

      {artifact.type === "visualization" && (
        <div className="flex-1 p-4">
          <div className="h-full flex items-center justify-center bg-secondary/30 rounded-lg">
            <p className="text-sm text-muted-foreground">Visualization would render here</p>
          </div>
        </div>
      )}
    </div>
  )
}
