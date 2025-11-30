"use client"

import { useEffect, useState, useMemo } from "react"
import { cn } from "@/lib/utils"
import {
  CheckCircle2,
  Loader2,
  MessageSquare,
  Brain,
  Search,
  Users,
  Sparkles,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
  Zap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { OrchestrationStatus, OrchestrationEvent, OrchestrationEventType } from "@/lib/types"

interface LiveStatusPanelProps {
  status: OrchestrationStatus
  className?: string
}

const eventIcons: Record<OrchestrationEventType, React.ElementType> = {
  started: Zap,
  refining_prompt: Sparkles,
  dispatching_model: Cpu,
  model_responding: Brain,
  model_critiquing: MessageSquare,
  verifying_facts: Search,
  consensus_building: Users,
  finalizing: CheckCircle2,
  completed: CheckCircle2,
  error: AlertCircle,
}

const eventColors: Record<OrchestrationEventType, string> = {
  started: "text-blue-500",
  refining_prompt: "text-purple-500",
  dispatching_model: "text-orange-500",
  model_responding: "text-emerald-500",
  model_critiquing: "text-pink-500",
  verifying_facts: "text-cyan-500",
  consensus_building: "text-indigo-500",
  finalizing: "text-[var(--bronze)]",
  completed: "text-green-500",
  error: "text-red-500",
}

function EventItem({
  event,
  isLast,
  isActive,
}: {
  event: OrchestrationEvent
  isLast: boolean
  isActive: boolean
}) {
  const Icon = eventIcons[event.type]
  const colorClass = eventColors[event.type]
  const isCompleted = event.type === "completed"
  const isError = event.type === "error"

  return (
    <div className="flex gap-3 animate-in fade-in-0 slide-in-from-left-2 duration-300">
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300",
            isLast && isActive
              ? "bg-[var(--bronze)]/20 ring-2 ring-[var(--bronze)] ring-offset-2 ring-offset-background"
              : isCompleted
                ? "bg-green-500/20"
                : isError
                  ? "bg-red-500/20"
                  : "bg-secondary"
          )}
        >
          {isLast && isActive ? (
            <Loader2 className={cn("h-4 w-4 animate-spin", colorClass)} />
          ) : (
            <Icon className={cn("h-4 w-4", colorClass)} />
          )}
        </div>
        {!isLast && <div className="w-0.5 h-full min-h-[20px] bg-border" />}
      </div>

      {/* Content */}
      <div className="flex-1 pb-4">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "text-sm font-medium",
              isLast && isActive ? "text-[var(--bronze)]" : "text-foreground"
            )}
          >
            {event.message}
          </span>
          {event.modelName && (
            <span className="text-xs px-1.5 py-0.5 rounded-md bg-secondary text-muted-foreground">
              {event.modelName}
            </span>
          )}
        </div>
        {event.details && (
          <p className="text-xs text-muted-foreground mt-0.5">{event.details}</p>
        )}
        <span className="text-[10px] text-muted-foreground">
          {event.timestamp.toLocaleTimeString()}
        </span>
      </div>
    </div>
  )
}

export function LiveStatusPanel({ status, className }: LiveStatusPanelProps) {
  const [isOpen, setIsOpen] = useState(true)

  // Calculate progress
  const progress = useMemo(() => {
    if (!status.isActive && status.events.length === 0) return 0
    const lastEvent = status.events[status.events.length - 1]
    return lastEvent?.progress ?? 0
  }, [status.events, status.isActive])

  // Auto-collapse after completion
  useEffect(() => {
    if (!status.isActive && progress === 100) {
      const timer = setTimeout(() => setIsOpen(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [status.isActive, progress])

  // Don't show if no events
  if (status.events.length === 0) {
    return null
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn("w-full", className)}>
      <div
        className={cn(
          "rounded-xl border transition-all duration-300",
          status.isActive
            ? "border-[var(--bronze)]/30 bg-[var(--bronze)]/5"
            : "border-border bg-card/50"
        )}
      >
        {/* Header */}
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full h-auto p-3 justify-between hover:bg-transparent"
          >
            <div className="flex items-center gap-3">
              {status.isActive ? (
                <div className="relative">
                  <div className="w-3 h-3 rounded-full bg-[var(--bronze)] animate-pulse" />
                  <div className="absolute inset-0 w-3 h-3 rounded-full bg-[var(--bronze)] animate-ping opacity-50" />
                </div>
              ) : (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
              <span className="text-sm font-medium">
                {status.isActive ? "Processing..." : "Orchestration Complete"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {status.latencyMs && !status.isActive && (
                <span className="text-xs text-muted-foreground">{status.latencyMs}ms</span>
              )}
              {isOpen ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>

        {/* Progress bar */}
        {status.isActive && (
          <div className="px-3 pb-2">
            <Progress
              value={progress}
              className="h-1.5 [&>div]:bg-gradient-to-r [&>div]:from-[var(--bronze)] [&>div]:to-[var(--gold)]"
            />
          </div>
        )}

        {/* Timeline content */}
        <CollapsibleContent>
          <div className="px-4 pb-4 pt-2 max-h-64 overflow-y-auto">
            {status.events.map((event, idx) => (
              <EventItem
                key={event.id}
                event={event}
                isLast={idx === status.events.length - 1}
                isActive={status.isActive}
              />
            ))}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

