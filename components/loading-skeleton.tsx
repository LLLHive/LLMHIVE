"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"

interface SkeletonProps {
  className?: string
}

/**
 * Basic skeleton component for loading states
 */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted/50",
        className
      )}
    />
  )
}

/**
 * Message skeleton for chat loading state
 */
export function MessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <Skeleton className="w-8 h-8 rounded-full shrink-0" />
      
      {/* Message content */}
      <div className={cn("flex flex-col gap-2", isUser ? "items-end" : "items-start")}>
        <Skeleton className="h-4 w-24" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-56" />
        </div>
      </div>
    </div>
  )
}

/**
 * Chat area loading skeleton
 */
export function ChatSkeleton() {
  return (
    <div className="flex flex-col gap-6 p-4 max-w-4xl mx-auto">
      <MessageSkeleton isUser />
      <MessageSkeleton />
      <MessageSkeleton isUser />
      <MessageSkeleton />
    </div>
  )
}

/**
 * AI response loading indicator with typing animation
 */
export function TypingIndicator() {
  return (
    <div className="flex gap-3 items-start">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center shrink-0">
        <span className="text-xs font-bold text-background">AI</span>
      </div>
      <div className="flex gap-1.5 p-4 rounded-2xl bg-secondary/50">
        {[0, 200, 400].map((delay) => (
          <div
            key={delay}
            className="w-2 h-2 rounded-full bg-[var(--bronze)] animate-bounce"
            style={{ 
              animationDelay: `${delay}ms`, 
              animationDuration: "1s" 
            }}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * World-class AI processing indicator with stage progression
 * Shows users exactly what's happening during multi-model orchestration
 */
interface ProcessingStage {
  id: string
  label: string
  icon: string
  duration: number // Expected duration in ms
}

const PROCESSING_STAGES: ProcessingStage[] = [
  { id: "analyzing", label: "Analyzing your question", icon: "🔍", duration: 2000 },
  { id: "consulting", label: "Consulting AI models", icon: "🤖", duration: 15000 },
  { id: "synthesizing", label: "Synthesizing response", icon: "⚡", duration: 20000 },
  { id: "verifying", label: "Verifying accuracy", icon: "✅", duration: 10000 },
]

const TOTAL_EXPECTED_TIME = PROCESSING_STAGES.reduce((sum, s) => sum + s.duration, 0)

// Professional tips to show while waiting
const WAITING_TIPS = [
  "LLMHive consults multiple AI models to give you the best answer",
  "Our verification system ensures 100% factual accuracy",
  "Complex questions get deeper analysis for better results",
  "We're cross-checking responses from multiple AI experts",
  "Quality takes time — we never rush your answers",
]

export function AIProcessingIndicator({ 
  startTime, 
  onCancel 
}: { 
  startTime?: number
  onCancel?: () => void 
}) {
  const [currentStage, setCurrentStage] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [tipIndex, setTipIndex] = useState(0)
  
  useEffect(() => {
    const start = startTime || Date.now()
    
    const timer = setInterval(() => {
      const elapsed = Date.now() - start
      setElapsedTime(elapsed)
      
      // Progress through stages based on elapsed time
      let accumulatedTime = 0
      for (let i = 0; i < PROCESSING_STAGES.length; i++) {
        accumulatedTime += PROCESSING_STAGES[i].duration
        if (elapsed < accumulatedTime) {
          setCurrentStage(i)
          break
        }
      }
      // Stay on last stage if exceeded
      if (elapsed >= accumulatedTime) {
        setCurrentStage(PROCESSING_STAGES.length - 1)
      }
    }, 100)
    
    return () => clearInterval(timer)
  }, [startTime])
  
  // Rotate tips every 8 seconds
  useEffect(() => {
    const tipTimer = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % WAITING_TIPS.length)
    }, 8000)
    return () => clearInterval(tipTimer)
  }, [])
  
  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }
  
  const getEstimatedTimeRemaining = () => {
    let completedTime = 0
    for (let i = 0; i < currentStage; i++) {
      completedTime += PROCESSING_STAGES[i].duration
    }
    // Add progress within current stage
    let stageProgress = 0
    if (currentStage > 0) {
      const stageStartTime = PROCESSING_STAGES.slice(0, currentStage).reduce((sum, s) => sum + s.duration, 0)
      const timeInCurrentStage = elapsedTime - stageStartTime
      stageProgress = Math.min(timeInCurrentStage, PROCESSING_STAGES[currentStage].duration)
    } else {
      stageProgress = Math.min(elapsedTime, PROCESSING_STAGES[0].duration)
    }
    completedTime += stageProgress
    
    const remaining = Math.max(TOTAL_EXPECTED_TIME - completedTime, 0)
    if (remaining === 0 && elapsedTime > TOTAL_EXPECTED_TIME) {
      return "almost done"
    }
    return formatTime(remaining)
  }
  
  const progressPercent = Math.min((elapsedTime / TOTAL_EXPECTED_TIME) * 100, 95)
  
  return (
    <div className="flex gap-3 items-start">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center shrink-0 animate-pulse">
        <span className="text-xs font-bold text-background">AI</span>
      </div>
      <div className="flex flex-col gap-2 p-4 rounded-2xl bg-secondary/50 min-w-[300px] max-w-[400px]">
        {/* Header with elapsed and remaining time */}
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
          <span>Processing your query...</span>
          <span className="font-mono">{formatTime(elapsedTime)}</span>
        </div>
        
        {/* Stage progression */}
        <div className="flex flex-col gap-1.5">
          {PROCESSING_STAGES.map((stage, index) => (
            <div
              key={stage.id}
              className={cn(
                "flex items-center gap-2 text-sm transition-all duration-300",
                index < currentStage && "text-green-500",
                index === currentStage && "text-foreground font-medium",
                index > currentStage && "text-muted-foreground/40"
              )}
            >
              <span className={cn(
                "text-base transition-transform duration-300",
                index === currentStage && "animate-pulse scale-110"
              )}>
                {index < currentStage ? "✓" : stage.icon}
              </span>
              <span>{stage.label}</span>
              {index === currentStage && (
                <div className="ml-auto flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--bronze)] animate-ping" />
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Progress bar with gradient */}
        <div className="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[var(--bronze)] via-[var(--gold)] to-[var(--bronze)] transition-all duration-500 ease-out"
            style={{
              width: `${progressPercent}%`,
              backgroundSize: "200% 100%",
              animation: "shimmer 2s linear infinite",
            }}
          />
        </div>
        <style jsx>{`
          @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }
        `}</style>
        
        {/* Estimated time remaining */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Est. remaining:</span>
          <span className="text-[var(--bronze)] font-medium">{getEstimatedTimeRemaining()}</span>
        </div>
        
        {/* Professional tip (shows after 10s) */}
        {elapsedTime > 10000 && (
          <div className="mt-2 p-2 rounded-lg bg-[var(--bronze)]/5 border border-[var(--bronze)]/20">
            <p className="text-xs text-muted-foreground italic">
              💡 {WAITING_TIPS[tipIndex]}
            </p>
          </div>
        )}
        
        {/* Long query warning with cancel option (shows after 45s) */}
        {elapsedTime > 45000 && onCancel && (
          <button
            onClick={onCancel}
            className="mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors underline"
          >
            Taking too long? Cancel and try a simpler question
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * Card loading skeleton
 */
export function CardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}

/**
 * Settings card skeleton
 */
export function SettingsCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3 w-48" />
        </div>
      </div>
      <Skeleton className="h-9 w-24" />
    </div>
  )
}

/**
 * Orchestration panel skeleton
 */
export function OrchestrationSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-3">
        <Skeleton className="w-8 h-8 rounded-full" />
        <Skeleton className="h-5 w-48" />
      </div>
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton className="w-4 h-4 rounded" />
            <Skeleton className="h-4 w-full" />
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Full page loading skeleton
 */
export function PageSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="h-14 border-b border-border px-4 flex items-center gap-4">
        <Skeleton className="w-8 h-8 rounded" />
        <Skeleton className="h-5 w-32" />
      </div>
      
      {/* Content */}
      <div className="p-4 max-w-4xl mx-auto">
        <ChatSkeleton />
      </div>
    </div>
  )
}

export default Skeleton
