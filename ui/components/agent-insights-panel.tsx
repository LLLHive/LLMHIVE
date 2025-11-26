"use client"

import {
  X,
  Shield,
  Code,
  Scale,
  Microscope,
  Sparkles,
  Brain,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import type { AgentContribution, Citation, ConsensusInfo, ModelFeedback } from "@/lib/types"
import { cn } from "@/lib/utils"

interface AgentInsightsPanelProps {
  agents: AgentContribution[]
  consensus: ConsensusInfo
  citations?: Citation[]
  modelFeedback?: ModelFeedback[] // Model Feedback: Performance feedback for each model
  onClose: () => void
}

const agentIcons = {
  legal: Scale,
  code: Code,
  research: Microscope,
  math: Brain,
  creative: Sparkles,
  general: Shield,
}

const agentColors = {
  legal: "from-blue-500 to-blue-600",
  code: "from-green-500 to-green-600",
  research: "from-purple-500 to-purple-600",
  math: "from-orange-500 to-orange-600",
  creative: "from-pink-500 to-pink-600",
  general: "from-gray-500 to-gray-600",
}

export function AgentInsightsPanel({ agents, consensus, citations, modelFeedback, onClose }: AgentInsightsPanelProps) {
  // Model Feedback: Helper function to get outcome icon and color
  const getOutcomeDisplay = (outcome: ModelFeedback["outcome"], wasUsed: boolean) => {
    if (wasUsed && outcome === "success") {
      return { icon: CheckCircle2, color: "text-green-500", label: "Used in final answer" }
    } else if (wasUsed && outcome === "corrected") {
      return { icon: AlertTriangle, color: "text-yellow-500", label: "Used but corrected" }
    } else if (outcome === "failed_verification") {
      return { icon: XCircle, color: "text-red-500", label: "Failed verification" }
    } else if (outcome === "rejected") {
      return { icon: XCircle, color: "text-gray-500", label: "Answer discarded" }
    } else if (outcome === "partial") {
      return { icon: AlertCircle, color: "text-yellow-500", label: "Partial contribution" }
    } else {
      return { icon: AlertCircle, color: "text-gray-400", label: "Unknown outcome" }
    }
  }
  return (
    <div className="absolute top-0 right-0 h-full w-96 bg-background border-l border-border shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">Agent Insights</h3>
          <p className="text-xs text-muted-foreground">Multi-agent collaboration details</p>
        </div>
        <Button size="icon" variant="ghost" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 p-4">
        {/* Consensus Score */}
        <div className="mb-6 p-4 rounded-lg bg-gradient-to-br from-[var(--bronze)]/10 to-[var(--gold)]/10 border border-[var(--bronze)]/20">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Consensus Confidence</span>
            <div className="flex items-center gap-1">
              {consensus.confidence >= 80 ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <AlertCircle className="h-4 w-4 text-yellow-500" />
              )}
              <span className="text-lg font-bold text-[var(--bronze)]">{consensus.confidence}%</span>
            </div>
          </div>
          <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bronze-gradient transition-all duration-500"
              style={{ width: `${consensus.confidence}%` }}
            />
          </div>
          {consensus.debateOccurred && consensus.consensusNote && (
            <p className="text-xs text-muted-foreground mt-3 leading-relaxed">{consensus.consensusNote}</p>
          )}
        </div>

        {/* Agents */}
        <div className="mb-6">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <div className="w-1 h-4 bg-[var(--bronze)] rounded-full" />
            Contributing Agents ({agents.length})
          </h4>
          <div className="space-y-3">
            {agents.map((agent) => {
              const Icon = agentIcons[agent.agentType]
              const colorClass = agentColors[agent.agentType]
              return (
                <div
                  key={agent.agentId}
                  className="p-3 rounded-lg bg-card border border-border hover:border-[var(--bronze)]/30 transition-colors"
                >
                  <div className="flex items-start gap-3 mb-2">
                    <div
                      className={cn(
                        "w-8 h-8 rounded-lg bg-gradient-to-br flex items-center justify-center flex-shrink-0",
                        colorClass,
                      )}
                    >
                      <Icon className="h-4 w-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{agent.agentName}</span>
                        <Badge variant="outline" className="text-xs">
                          {agent.confidence}% confidence
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{agent.contribution}</p>
                    </div>
                  </div>
                  {agent.citations && agent.citations.length > 0 && (
                    <div className="mt-2 pl-11 space-y-1">
                      {agent.citations.map((citation) => (
                        <a
                          key={citation.id}
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-xs text-[var(--bronze)] hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                          {citation.source}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Model Feedback: Display model performance feedback */}
        {modelFeedback && modelFeedback.length > 0 ? (
          <div className="mb-6">
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <div className="w-1 h-4 bg-[var(--bronze)] rounded-full" />
              Model Performance ({modelFeedback.length})
            </h4>
            <div className="space-y-3">
              {modelFeedback.map((feedback, idx) => {
                const outcomeDisplay = getOutcomeDisplay(feedback.outcome, feedback.was_used_in_final)
                const OutcomeIcon = outcomeDisplay.icon
                return (
                  <div
                    key={`${feedback.model_name}-${idx}`}
                    className={cn(
                      "p-3 rounded-lg border transition-colors",
                      feedback.was_used_in_final
                        ? "bg-card border-[var(--bronze)]/30"
                        : "bg-secondary border-border"
                    )}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <OutcomeIcon className={cn("h-4 w-4", outcomeDisplay.color)} />
                        <span className="font-medium text-sm">{feedback.model_name}</span>
                      </div>
                      <Badge
                        variant={feedback.was_used_in_final ? "default" : "outline"}
                        className={cn(
                          "text-xs",
                          feedback.was_used_in_final && "bg-[var(--bronze)] text-white"
                        )}
                      >
                        {outcomeDisplay.label}
                      </Badge>
                    </div>
                    {feedback.notes && (
                      <p className="text-xs text-muted-foreground mb-2">{feedback.notes}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      {feedback.quality_score !== undefined && (
                        <span>Quality: {(feedback.quality_score * 100).toFixed(0)}%</span>
                      )}
                      {feedback.confidence_score !== undefined && (
                        <span>Confidence: {(feedback.confidence_score * 100).toFixed(0)}%</span>
                      )}
                      {feedback.response_time_ms !== undefined && (
                        <span>Time: {feedback.response_time_ms.toFixed(0)}ms</span>
                      )}
                      {feedback.token_usage !== undefined && (
                        <span>Tokens: {feedback.token_usage}</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          // Model Feedback: Show message if no feedback available
          <div className="mb-6 p-4 rounded-lg bg-secondary border border-border">
            <p className="text-xs text-muted-foreground text-center">
              No performance feedback available for this query
            </p>
          </div>
        )}

        {/* Citations */}
        {citations && citations.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <div className="w-1 h-4 bg-[var(--bronze)] rounded-full" />
              Sources & Citations ({citations.length})
            </h4>
            <div className="space-y-2">
              {citations.map((citation, idx) => (
                <div key={citation.id} className="p-3 rounded-lg bg-secondary border border-border">
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-mono text-[var(--bronze)] mt-0.5">[{idx + 1}]</span>
                    <div className="flex-1">
                      <p className="text-xs mb-1 leading-relaxed">{citation.text}</p>
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-muted-foreground hover:text-[var(--bronze)] flex items-center gap-1"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {citation.source}
                        {citation.verified && <CheckCircle2 className="h-3 w-3 text-green-500 ml-1" />}
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
