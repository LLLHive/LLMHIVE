"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { 
  ChevronDown, 
  ChevronUp, 
  Shield, 
  Cpu, 
  Search, 
  Database, 
  Wrench,
  ExternalLink,
  Copy,
  Check,
  Brain,
  Sparkles,
  AlertTriangle
} from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "@/lib/toast"

/**
 * Quality metadata for an AI response.
 * This matches the QualityMetadata structure from the backend.
 */
export interface QualityMetadata {
  traceId?: string
  confidence?: number
  confidenceLabel?: string
  modelsUsed?: string[]
  strategyUsed?: string
  verificationStatus?: string
  verificationScore?: number
  toolsUsed?: string[]
  ragUsed?: boolean
  memoryUsed?: boolean
  sources?: Array<{ title: string; url?: string }>
  isStub?: boolean
  selfGraded?: boolean
  improvementApplied?: boolean
}

interface AnswerQualityDrawerProps {
  metadata?: QualityMetadata
  isDevMode?: boolean
  className?: string
}

/**
 * "Why this answer?" drawer component.
 * 
 * Displays quality metadata about an AI response in a collapsible drawer.
 * Shows confidence, verification status, models used, tools, sources, etc.
 */
export function AnswerQualityDrawer({
  metadata,
  isDevMode = false,
  className,
}: AnswerQualityDrawerProps) {
  const [isOpen, setIsOpen] = useState(isDevMode)
  const [copiedTraceId, setCopiedTraceId] = useState(false)
  
  // Don't render if no metadata
  if (!metadata) return null
  
  const {
    traceId,
    confidence,
    confidenceLabel,
    modelsUsed = [],
    strategyUsed,
    verificationStatus,
    verificationScore,
    toolsUsed = [],
    ragUsed,
    memoryUsed,
    sources = [],
    isStub,
    selfGraded,
    improvementApplied,
  } = metadata
  
  // Confidence display
  const confidencePercent = confidence ? Math.round(confidence * 100) : null
  const confidenceColor = confidence 
    ? confidence >= 0.8 
      ? "text-green-500" 
      : confidence >= 0.5 
        ? "text-yellow-500" 
        : "text-red-500"
    : "text-muted-foreground"
  
  // Verification badge
  const isVerified = verificationStatus === "PASS"
  
  const handleCopyTraceId = () => {
    if (traceId) {
      navigator.clipboard.writeText(traceId)
      setCopiedTraceId(true)
      toast.success("Trace ID copied")
      setTimeout(() => setCopiedTraceId(false), 2000)
    }
  }
  
  const getStrategyLabel = (strategy?: string) => {
    switch (strategy) {
      case "hrm": return "Hierarchical Reasoning"
      case "consensus": return "Multi-Model Consensus"
      case "tools": return "Tool-Augmented"
      case "rag": return "Retrieval-Augmented"
      case "direct": return "Direct Response"
      case "verification": return "Verified Response"
      default: return strategy || "Standard"
    }
  }
  
  const getStrategyIcon = (strategy?: string) => {
    switch (strategy) {
      case "hrm": return <Brain className="h-3 w-3" />
      case "consensus": return <Cpu className="h-3 w-3" />
      case "tools": return <Wrench className="h-3 w-3" />
      case "rag": return <Database className="h-3 w-3" />
      case "verification": return <Shield className="h-3 w-3" />
      default: return <Sparkles className="h-3 w-3" />
    }
  }
  
  return (
    <div className={cn("mt-2 rounded-lg border border-border/50", className)}>
      {/* Header - always visible */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium">Why this answer?</span>
          
          {/* Quick stats in header */}
          {confidencePercent !== null && (
            <span className={cn("flex items-center gap-1", confidenceColor)}>
              <span className="font-mono">{confidencePercent}%</span>
              {isVerified && <Shield className="h-3 w-3" />}
            </span>
          )}
          
          {isStub && (
            <span className="flex items-center gap-1 text-red-500">
              <AlertTriangle className="h-3 w-3" />
              <span>Stub</span>
            </span>
          )}
        </div>
        
        {isOpen ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>
      
      {/* Drawer content */}
      {isOpen && (
        <div className="px-3 pb-3 space-y-3 border-t border-border/50">
          {/* Confidence & Verification */}
          <div className="pt-3 flex flex-wrap gap-2">
            {confidencePercent !== null && (
              <div className={cn(
                "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs",
                "bg-secondary border border-border"
              )}>
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  confidence! >= 0.8 ? "bg-green-500" : 
                  confidence! >= 0.5 ? "bg-yellow-500" : "bg-red-500"
                )} />
                <span>
                  <span className={cn("font-medium", confidenceColor)}>
                    {confidencePercent}%
                  </span>
                  {" "}
                  <span className="text-muted-foreground">
                    {confidenceLabel || "confidence"}
                  </span>
                </span>
              </div>
            )}
            
            {isVerified && (
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs bg-green-500/10 border border-green-500/20 text-green-500">
                <Shield className="h-3 w-3" />
                <span>Verified</span>
                {verificationScore && (
                  <span className="font-mono">({Math.round(verificationScore * 100)}%)</span>
                )}
              </div>
            )}
            
            {verificationStatus === "PARTIAL" && (
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs bg-yellow-500/10 border border-yellow-500/20 text-yellow-500">
                <Shield className="h-3 w-3" />
                <span>Partially Verified</span>
              </div>
            )}
            
            {improvementApplied && (
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs bg-blue-500/10 border border-blue-500/20 text-blue-500">
                <Sparkles className="h-3 w-3" />
                <span>Enhanced</span>
              </div>
            )}
          </div>
          
          {/* Strategy & Models */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            {strategyUsed && (
              <div>
                <div className="text-muted-foreground mb-1">Strategy</div>
                <div className="flex items-center gap-1.5 text-foreground">
                  {getStrategyIcon(strategyUsed)}
                  <span>{getStrategyLabel(strategyUsed)}</span>
                </div>
              </div>
            )}
            
            {modelsUsed.length > 0 && (
              <div>
                <div className="text-muted-foreground mb-1">Models</div>
                <div className="flex flex-wrap gap-1">
                  {modelsUsed.slice(0, 3).map((model, idx) => (
                    <span 
                      key={idx}
                      className="inline-flex items-center px-1.5 py-0.5 rounded bg-secondary text-foreground"
                    >
                      <Cpu className="h-2.5 w-2.5 mr-1" />
                      {model.split('/').pop() || model}
                    </span>
                  ))}
                  {modelsUsed.length > 3 && (
                    <span className="text-muted-foreground">+{modelsUsed.length - 3}</span>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Tools & Context */}
          {(toolsUsed.length > 0 || ragUsed || memoryUsed) && (
            <div className="flex flex-wrap gap-2 text-xs">
              {toolsUsed.map((tool, idx) => (
                <div 
                  key={idx}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-secondary"
                >
                  <Wrench className="h-2.5 w-2.5" />
                  <span>{tool}</span>
                </div>
              ))}
              
              {ragUsed && (
                <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-secondary">
                  <Search className="h-2.5 w-2.5" />
                  <span>Knowledge Search</span>
                </div>
              )}
              
              {memoryUsed && (
                <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-secondary">
                  <Database className="h-2.5 w-2.5" />
                  <span>Memory</span>
                </div>
              )}
            </div>
          )}
          
          {/* Sources */}
          {sources.length > 0 && (
            <div>
              <div className="text-xs text-muted-foreground mb-1">Sources</div>
              <div className="space-y-1">
                {sources.slice(0, 3).map((source, idx) => (
                  <div key={idx} className="text-xs flex items-center gap-1">
                    <span className="text-muted-foreground">[{idx + 1}]</span>
                    {source.url ? (
                      <a 
                        href={source.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-[var(--bronze)] hover:underline flex items-center gap-1"
                      >
                        {source.title}
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    ) : (
                      <span>{source.title}</span>
                    )}
                  </div>
                ))}
                {sources.length > 3 && (
                  <div className="text-xs text-muted-foreground">
                    +{sources.length - 3} more sources
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Trace ID (developer info) */}
          {traceId && (
            <div className="pt-2 border-t border-border/50 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Trace ID:</span>
              <button
                onClick={handleCopyTraceId}
                className="flex items-center gap-1 text-muted-foreground hover:text-foreground font-mono"
              >
                {traceId.substring(0, 8)}...
                {copiedTraceId ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Hook to check if dev mode is enabled.
 * Dev mode shows the quality drawer by default.
 */
export function useDevMode(): boolean {
  if (typeof window === "undefined") return false
  
  // Check for dev mode flag in localStorage or URL param
  try {
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get("dev") === "true") return true
    if (localStorage.getItem("llmhive_dev_mode") === "true") return true
  } catch {
    // Ignore errors in SSR or restricted contexts
  }
  
  return process.env.NODE_ENV === "development"
}

