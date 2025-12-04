"use client"

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
