"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Paperclip, Mic, Code, FileText, Lightbulb, TrendingUp, ImageIcon, X, Briefcase } from 'lucide-react'
import { getModelById } from "@/lib/models"
import type {
  Conversation,
  Message,
  Attachment,
  Artifact,
  CriteriaSettings,
  AgentContribution,
  Citation,
  ModelFeedback,
} from "@/lib/types"
import { MessageBubble } from "./message-bubble"
import { HiveActivityIndicator } from "./hive-activity-indicator"
import { AgentInsightsPanel } from "./agent-insights-panel"
import { ChatHeader } from "./chat-header"
import { cn } from "@/lib/utils"

interface ChatAreaProps {
  conversation?: Conversation
  onSendMessage: (message: Message) => void
  onShowArtifact: (artifact: Artifact) => void
  onConversationUpdate?: (backendConversationId?: number) => void
}

const firstRowSuggestions = [
  { icon: Lightbulb, label: "Prompt Optimization", text: "Optimize my prompt for better AI responses" },
  { icon: Code, label: "Output Validation", text: "Validate and verify the output for accuracy" },
  { icon: FileText, label: "Answer Structure", text: "Structure the answer with clear sections and examples" },
]

const secondRowSuggestions = [
  { icon: TrendingUp, label: "Strategize", text: "Help me develop a comprehensive business strategy" },
  { icon: FileText, label: "Write", text: "Draft a professional email" },
  { icon: Lightbulb, label: "Learn", text: "Explain quantum computing in simple terms" },
]

const thirdRowSuggestions = [
  { icon: Briefcase, label: "Industry Specific", text: "Provide industry-specific insights and solutions" },
  { icon: Code, label: "Code", text: "Build a React component with TypeScript" },
  { icon: FileText, label: "Shared Data", text: "Access and utilize shared data across conversations" },
]

type OrchestrationEngine = "hrm" | "prompt-diffusion" | "deep-conf" | "adaptive-ensemble"
type AdvancedFeature = "vector-db" | "rag" | "shared-memory" | "loop-back" | "live-data"
type ReasoningMode = "deep" | "standard" | "fast"

export function ChatArea({
  conversation,
  onSendMessage,
  onShowArtifact,
  onConversationUpdate,
}: ChatAreaProps) {
  const [input, setInput] = useState("")
  const [selectedModels, setSelectedModels] = useState<string[]>(["gpt-5-mini"])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [reasoningMode, setReasoningMode] = useState<ReasoningMode>("standard")
  const [orchestrationEngine, setOrchestrationEngine] = useState<OrchestrationEngine>("hrm")
  const [advancedFeatures, setAdvancedFeatures] = useState<AdvancedFeature[]>([
    "vector-db",
    "rag",
    "shared-memory",
    "loop-back",
    "live-data",
  ])
  const [criteriaSettings, setCriteriaSettings] = useState<CriteriaSettings>({
    accuracy: 70,
    speed: 70,
    creativity: 50,
  })
  const [preset, setPreset] = useState<string | null>(null)
  const [useDeepconf, setUseDeepconf] = useState<boolean | null>(null)
  const [useVerification, setUseVerification] = useState<boolean | null>(null)
  const [formatStyle, setFormatStyle] = useState<"bullet" | "paragraph">("paragraph")
  const [showInsights, setShowInsights] = useState(false)
  const [selectedMessageForInsights, setSelectedMessageForInsights] = useState<Message | null>(null)
  const [incognitoMode, setIncognitoMode] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [pendingClarification, setPendingClarification] = useState<{ originalQuery: string; clarificationMessageId: string } | null>(null)
  const [subscriptionError, setSubscriptionError] = useState<{ message: string; upgradeMessage?: string; tier?: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const primaryModelId = selectedModels[0]
  const currentModel = primaryModelId ? getModelById(primaryModelId) : undefined

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newAttachments: Attachment[] = files.map((file) => ({
      id: `att-${Date.now()}-${Math.random()}`,
      name: file.name,
      type: file.type,
      size: file.size,
      url: URL.createObjectURL(file),
    }))
    setAttachments([...attachments, ...newAttachments])
  }

  const removeAttachment = (id: string) => {
    setAttachments(attachments.filter((att) => att.id !== id))
  }

  const handleSend = async () => {
    if (!input.trim() && attachments.length === 0) return
    if (selectedModels.length === 0) return

    // Clarification Loop: Check if this is a response to a clarification
    const isClarificationResponse = pendingClarification !== null
    const originalQuery = pendingClarification?.originalQuery || null

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: input,
      timestamp: new Date(),
      attachments: attachments.length > 0 ? attachments : undefined,
    }

    onSendMessage(userMessage)

    const userInput = input
    setInput("")
    setAttachments([])
    setIsLoading(true)

    // Clarification Loop: Clear pending clarification after sending response
    if (isClarificationResponse) {
      setPendingClarification(null)
    }

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...(conversation?.messages || []), userMessage],
          models: selectedModels,
          reasoningMode,
          capabilities: currentModel?.capabilities,
          criteriaSettings,
          orchestrationEngine,
          advancedFeatures,
          preset,
          useDeepconf,
          useVerification,
          formatStyle,
          // Clarification Loop: Include clarification parameters if responding to clarification
          clarificationResponse: isClarificationResponse ? userInput : undefined,
          isClarificationResponse: isClarificationResponse,
          originalQuery: originalQuery,
          conversationId: conversation?.backendConversationId,
          userId: "ui-session",
        }),
      })

      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        // Subscription Enforcement: Handle subscription limit errors
        if (response.status === 403) {
          const errorDetail = payload?.detail || payload?.backend?.detail || {}
          const isSubscriptionError = 
            errorDetail.error === "subscription_limit_exceeded" ||
            errorDetail.error === "Usage limit exceeded" ||
            errorDetail.error === "Tier limit exceeded" ||
            errorDetail.message?.toLowerCase().includes("upgrade") ||
            errorDetail.message?.toLowerCase().includes("limit")
          
          if (isSubscriptionError) {
            setSubscriptionError({
              message: errorDetail.message || "Subscription limit exceeded",
              upgradeMessage: errorDetail.upgrade_message || errorDetail.message,
              tier: errorDetail.tier || "free",
            })
            const errorMessage: Message = {
              id: `msg-${Date.now()}`,
              role: "assistant",
              content: errorDetail.upgrade_message || errorDetail.message || "You've reached your subscription limit. Please upgrade to continue.",
              timestamp: new Date(),
              metadata: {
                subscriptionError: true,
                tier: errorDetail.tier,
                limitType: errorDetail.limit_type,
              },
            }
            onSendMessage(errorMessage)
            setIsLoading(false)
            return
          }
        }
        
        // Handle other errors
        const errorText =
          (payload && (payload.error || payload?.backend?.detail || payload?.backend?.detail?.detail)) ||
          "The orchestration engine returned an error. Please check backend logs."

        const errorMessage: Message = {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: errorText,
          timestamp: new Date(),
        }
        onSendMessage(errorMessage)
        return
      }
      
      // Clear subscription error on successful request
      if (subscriptionError) {
        setSubscriptionError(null)
      }

      // Backend returns OrchestrationResponse directly, API route wraps it in 'orchestration' field
      const orchestration = payload?.orchestration

      if (!orchestration) {
        // If payload itself is the orchestration response (direct backend response)
        if (payload?.final_response) {
          // Backend response was returned directly, use it
          const directResponse = payload as any
          const assistantMessage: Message = {
            id: `msg-${Date.now()}-assistant`,
            role: "assistant",
            content: directResponse.final_response || "The hive could not produce a response for this request.",
            timestamp: new Date(),
            model: "LLMHive Orchestrator",
          }
          if (directResponse.conversation_id && onConversationUpdate) {
            onConversationUpdate(directResponse.conversation_id)
          }
          onSendMessage(assistantMessage)
          return
        }
        
        const errorMessage: Message = {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: "The orchestration API responded without a payload. Please try again.",
          timestamp: new Date(),
        }
        onSendMessage(errorMessage)
        return
      }

      if (payload.conversationId && onConversationUpdate) {
        onConversationUpdate(payload.conversationId)
      } else if (orchestration.conversation_id && onConversationUpdate) {
        onConversationUpdate(orchestration.conversation_id)
      }

      // Clarification Loop: Check if clarification is needed
      if (orchestration.requires_clarification && orchestration.clarification_question) {
        // Display clarification question
        const clarificationMessageId = `msg-${Date.now()}-clarification`
        const clarificationMessage: Message = {
          id: clarificationMessageId,
          role: "assistant",
          content: orchestration.clarification_question,
          timestamp: new Date(),
          model: "LLMHive Clarification",
          // Store original query and possible interpretations for context
          metadata: {
            requiresClarification: true,
            originalQuery: userMessage.content,
            possibleInterpretations: orchestration.possible_interpretations || [],
          },
        }
        onSendMessage(clarificationMessage)
        // Store pending clarification so we know the next user message is a response
        setPendingClarification({
          originalQuery: userMessage.content,
          clarificationMessageId: clarificationMessageId,
        })
        setIsLoading(false)
        return  // Don't proceed with normal response
      }
      
      // Extract final_response - backend returns it at root level of OrchestrationResponse
      const finalResponse = orchestration.final_response || "The hive could not produce a response for this request."
      
      console.log("[LLMHive] Orchestration response:", { orchestration, finalResponse })
      
      const assistantMessage: Message = {
        id: `msg-${Date.now()}-assistant`,
        role: "assistant",
        content: finalResponse,
        timestamp: new Date(),
        model: "LLMHive Orchestrator",
      }

      // Try to build full message with metadata if available
      try {
        const fullMessage = buildAssistantMessage({
          orchestration,
          fallbackModel: primaryModelId || "orchestrator",
          reasoningMode,
        })
        Object.assign(assistantMessage, fullMessage)
        console.log("[LLMHive] Built assistant message:", assistantMessage)
      } catch (err) {
        console.warn("[LLMHive] Failed to build full message metadata:", err)
        // Use basic message structure
      }

      console.log("[LLMHive] Sending assistant message:", assistantMessage)
      onSendMessage(assistantMessage)
    } catch (error) {
      console.error("[LLMHive] UI orchestration error:", error)
      const errorMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: "I’m sorry, but I couldn’t reach the orchestration engine. Please try again in a moment.",
        timestamp: new Date(),
      }
      onSendMessage(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleAdvancedFeature = (feature: AdvancedFeature) => {
    setAdvancedFeatures((prev) => (prev.includes(feature) ? prev.filter((f) => f !== feature) : [...prev, feature]))
  }

  const displayMessages = conversation?.messages || []
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [displayMessages.length, isLoading])
  
  console.log("[LLMHive] ChatArea render:", { 
    conversationId: conversation?.id, 
    messageCount: displayMessages.length,
    messages: displayMessages.map(m => ({ id: m.id, role: m.role, contentPreview: m.content.slice(0, 50) }))
  })

  return (
    <div className="flex-1 flex flex-col relative">
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 0l25.98 15v30L30 60 4.02 45V15z' fill='none' stroke='%23C48E48' strokeWidth='1'/%3E%3C/svg%3E")`,
          backgroundSize: "60px 60px",
        }}
      />

      <ChatHeader
        selectedModels={selectedModels}
        onModelChange={setSelectedModels}
        reasoningMode={reasoningMode}
        onReasoningModeChange={setReasoningMode}
        orchestrationEngine={orchestrationEngine}
        onOrchestrationChange={setOrchestrationEngine}
        advancedFeatures={advancedFeatures}
        onToggleFeature={toggleAdvancedFeature}
        criteriaSettings={criteriaSettings}
        onCriteriaChange={setCriteriaSettings}
        currentModel={currentModel}
        preset={preset}
        onPresetChange={setPreset}
        useDeepconf={useDeepconf}
        onUseDeepconfChange={setUseDeepconf}
        useVerification={useVerification}
        onUseVerificationChange={setUseVerification}
        formatStyle={formatStyle}
        onFormatStyleChange={setFormatStyle}
      />

      <HiveActivityIndicator active={isLoading} agentCount={6} />

      <ScrollArea className="flex-1 relative z-10">
        {displayMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center pt-[48px] max-w-4xl mx-auto px-4">
            <div className="flex flex-col gap-2.5 w-full max-w-3xl">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                {firstRowSuggestions.map((suggestion) => {
                  const Icon = suggestion.icon
                  return (
                    <Button
                      key={suggestion.label}
                      variant="outline"
                      className="h-auto flex flex-col items-center gap-2 p-4 border-2 border-border hover:bronze-gradient hover:border-[var(--bronze)] transition-all duration-500 bg-card/50 backdrop-blur-xl group relative"
                      onClick={() => setInput(suggestion.text)}
                    >
                      <div className="absolute inset-0 border-2 border-[var(--bronze)] rounded-lg transition-all duration-500 opacity-0 group-hover:opacity-100 -m-[2px] pointer-events-none" />
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-all duration-500 group-hover:scale-110 group-hover:shadow-xl group-hover:rotate-3 relative z-10">
                        <Icon className="h-4 w-4 text-background transition-transform duration-500 group-hover:scale-110" />
                      </div>
                      <div className="text-xs font-semibold text-foreground group-hover:text-primary-foreground transition-colors duration-500 relative z-10 whitespace-nowrap">{suggestion.label}</div>
                    </Button>
                  )
                })}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                {secondRowSuggestions.map((suggestion) => {
                  const Icon = suggestion.icon
                  return (
                    <Button
                      key={suggestion.label}
                      variant="outline"
                      className="h-auto flex flex-col items-center gap-2 p-4 border-2 border-border hover:bronze-gradient hover:border-[var(--bronze)] transition-all duration-500 bg-card/50 backdrop-blur-xl group relative"
                      onClick={() => setInput(suggestion.text)}
                    >
                      <div className="absolute inset-0 border-2 border-[var(--bronze)] rounded-lg transition-all duration-500 opacity-0 group-hover:opacity-100 -m-[2px] pointer-events-none" />
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-all duration-500 group-hover:scale-110 group-hover:shadow-xl group-hover:rotate-3 relative z-10">
                        <Icon className="h-4 w-4 text-background transition-transform duration-500 group-hover:scale-110" />
                      </div>
                      <div className="text-xs font-semibold text-foreground group-hover:text-primary-foreground transition-colors duration-500 relative z-10 whitespace-nowrap">{suggestion.label}</div>
                    </Button>
                  )
                })}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                {thirdRowSuggestions.map((suggestion) => {
                  const Icon = suggestion.icon
                  return (
                    <Button
                      key={suggestion.label}
                      variant="outline"
                      className="h-auto flex flex-col items-center gap-2 p-4 border-2 border-border hover:bronze-gradient hover:border-[var(--bronze)] transition-all duration-500 bg-card/50 backdrop-blur-xl group relative"
                      onClick={() => setInput(suggestion.text)}
                    >
                      <div className="absolute inset-0 border-2 border-[var(--bronze)] rounded-lg transition-all duration-500 opacity-0 group-hover:opacity-100 -m-[2px] pointer-events-none" />
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-all duration-500 group-hover:scale-110 group-hover:shadow-xl group-hover:rotate-3 relative z-10">
                        <Icon className="h-4 w-4 text-background transition-transform duration-500 group-hover:scale-110" />
                      </div>
                      <div className="text-xs font-semibold text-foreground group-hover:text-primary-foreground transition-colors duration-500 relative z-10 whitespace-nowrap">{suggestion.label}</div>
                    </Button>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
            {displayMessages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onShowArtifact={onShowArtifact}
                onShowInsights={() => {
                  setSelectedMessageForInsights(message)
                  setShowInsights(true)
                }}
                incognitoMode={incognitoMode}
                onToggleIncognito={() => setIncognitoMode(!incognitoMode)}
              />
            ))}
            {isLoading && (
              <div className="flex gap-3 items-start">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                  <span className="text-xs font-bold text-background">AI</span>
                </div>
                <div className="flex gap-1.5 p-4">
                  {[0, 200, 400].map((delay) => (
                    <div
                      key={delay}
                      className="w-1.5 h-1.5 rounded-full bg-[var(--bronze)] animate-bounce"
                      style={{ animationDelay: `${delay}ms`, animationDuration: "1s" }}
                    />
                  ))}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </ScrollArea>

      {showInsights && selectedMessageForInsights?.agents && selectedMessageForInsights?.consensus && (
        <AgentInsightsPanel
          agents={selectedMessageForInsights.agents}
          consensus={selectedMessageForInsights.consensus}
          citations={selectedMessageForInsights.citations}
          modelFeedback={selectedMessageForInsights.modelFeedback} // Model Feedback: Pass feedback data
          onClose={() => setShowInsights(false)}
        />
      )}

      <div className="border-t border-border p-4 bg-card/50 backdrop-blur-xl relative z-10">
        <div className="max-w-4xl mx-auto">
          {attachments.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {attachments.map((att) => (
                <div key={att.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border">
                  {att.type.startsWith("image/") ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                  <span className="text-sm truncate max-w-[150px]">{att.name}</span>
                  <Button size="icon" variant="ghost" className="h-5 w-5" onClick={() => removeAttachment(att.id)}>
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="relative">
            {pendingClarification && (
              <div className="mb-2 p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-xs text-yellow-600 dark:text-yellow-400">
                  <strong>Clarification needed:</strong> Please provide more details about your query.
                </p>
              </div>
            )}
            {subscriptionError && (
              <div className="mb-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-xs text-red-600 dark:text-red-400 mb-1">
                  <strong>Subscription Limit:</strong> {subscriptionError.message}
                </p>
                <a
                  href="mailto:support@llmhive.com?subject=Upgrade Request"
                  className="text-xs text-red-600 dark:text-red-400 hover:underline font-medium"
                >
                  Contact us to upgrade →
                </a>
              </div>
            )}
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={
                pendingClarification
                  ? "Please clarify your query..."
                  : subscriptionError
                  ? "Upgrade required to continue..."
                  : "Ask the hive mind anything..."
              }
              className={cn(
                "min-h-[72px] pr-20 sm:pr-36 resize-none bg-secondary/50 border-border focus:border-[var(--bronze)] transition-colors",
                pendingClarification && "border-yellow-500/50 focus:border-yellow-500",
                subscriptionError && "border-red-500/50 focus:border-red-500"
              )}
              disabled={isLoading || !!subscriptionError}
            />
            <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1.5 flex-wrap">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => fileInputRef.current?.click()}>
                <Paperclip className="h-3.5 w-3.5" />
              </Button>
              <Button size="icon" variant="ghost" className="h-7 w-7">
                <Mic className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="icon"
                onClick={handleSend}
                disabled={(!input.trim() && attachments.length === 0) || isLoading || selectedModels.length === 0 || !!subscriptionError}
                className="h-7 w-7 bronze-gradient disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground mt-2 text-center opacity-60">
            LLMHive uses multiple AI agents for enhanced accuracy
          </p>
        </div>
      </div>
    </div>
  )
}

interface OrchestrationApiResponse {
  final_response?: string
  initial_responses?: { model?: string; content: string }[]
  quality?: { model?: string; score?: number; confidence?: number; highlights?: string[] }[]
  consensus_notes?: string[]
  confirmation_notes?: string[] // Confirmation notes from verification
  model_feedback?: ModelFeedback[] // Model Feedback: Performance feedback for each model
  fact_check?: FactCheckPayload
  refinement_rounds?: number
  plan?: {
    steps?: { role: string; description: string }[]
  }
}

interface FactCheckClaim {
  text: string
  status?: string
  evidence_urls?: string[]
}

interface FactCheckPayload {
  verified_count?: number
  contested_count?: number
  claims?: FactCheckClaim[]
}

function buildAssistantMessage({
  orchestration,
  fallbackModel: _fallbackModel,
  reasoningMode,
}: {
  orchestration: OrchestrationApiResponse
  fallbackModel: string
  reasoningMode: ReasoningMode
}): Message {
  const now = new Date()
  const finalResponse = orchestration.final_response || "The hive could not produce a response for this request."
  const quality = orchestration.quality || []

  const avgQuality =
    quality.length > 0
      ? quality.reduce((acc, entry) => acc + (entry.confidence ?? entry.score ?? 0), 0) / quality.length
      : undefined

  const consensusConfidence = avgQuality !== undefined ? clampPercent(avgQuality) : undefined
  const consensusNote = orchestration.consensus_notes?.[0]
  const consensus =
    consensusConfidence !== undefined
      ? {
          confidence: consensusConfidence,
          debateOccurred: (orchestration.refinement_rounds ?? 1) > 1,
          consensusNote,
        }
      : undefined

  const agents = buildAgentContributions(orchestration.initial_responses || [], quality)
  const citations = buildCitations(orchestration.fact_check)
  const factCheckSummary = summarizeFactCheck(orchestration.fact_check)
  const reasoningSteps = orchestration.plan?.steps?.map(
    (step) => `${step.role.toUpperCase()}: ${step.description}`,
  )

  return {
    id: `msg-${now.getTime()}-assistant`,
    role: "assistant",
    content: finalResponse,
    timestamp: now,
    model: "LLMHive Orchestrator",
    agents: agents.length > 0 ? agents : undefined,
    consensus,
    citations: citations.length > 0 ? citations : undefined,
    factCheckSummary,
    refinementRounds: orchestration.refinement_rounds,
    qualityScore: avgQuality,
    confidence: consensusConfidence !== undefined ? consensusConfidence / 100 : undefined,
    confirmation: orchestration.confirmation_notes && orchestration.confirmation_notes.length > 0 
      ? orchestration.confirmation_notes 
      : undefined,
    modelFeedback: orchestration.model_feedback && orchestration.model_feedback.length > 0
      ? orchestration.model_feedback as ModelFeedback[]
      : undefined, // Model Feedback: Extract feedback data from API response
    reasoning: reasoningSteps?.length
      ? {
          mode: reasoningMode,
          steps: reasoningSteps,
        }
      : { mode: reasoningMode },
  }
}

function buildAgentContributions(
  responses: { model?: string; content: string }[],
  quality: { model?: string; score?: number; confidence?: number }[],
): AgentContribution[] {
  return responses.map((response, idx) => {
    const qualityEntry = quality.find((entry) => entry.model === response.model)
    const confidenceScore = clampPercent(qualityEntry?.confidence ?? qualityEntry?.score)

    return {
      agentId: response.model || `model-${idx + 1}`,
      agentName: response.model || `Model ${idx + 1}`,
      agentType: inferAgentType(response.model),
      contribution: response.content,
      confidence: confidenceScore ?? 0,
    }
  })
}

function inferAgentType(model?: string): AgentContribution["agentType"] {
  const value = (model || "").toLowerCase()
  if (value.includes("legal") || value.includes("law")) return "legal"
  if (value.includes("math")) return "math"
  if (value.includes("research") || value.includes("gemini") || value.includes("sonnet")) return "research"
  if (value.includes("code") || value.includes("gpt") || value.includes("deepseek")) return "code"
  if (value.includes("creative") || value.includes("grok")) return "creative"
  return "general"
}

function buildCitations(factCheck?: FactCheckPayload): Citation[] {
  if (!factCheck?.claims) return []
  const citations: Citation[] = []

  factCheck.claims.forEach((claim, idx) => {
    const url = claim.evidence_urls?.find(Boolean)
    if (!url) return
    let source = url
    try {
      source = new URL(url).hostname
    } catch {
      // ignore malformed URLs
    }
    citations.push({
      id: `fact-${idx}`,
      text: claim.text,
      source,
      url,
      verified: claim.status === "verified",
    })
  })

  return citations
}

function summarizeFactCheck(factCheck?: FactCheckPayload): string | undefined {
  if (!factCheck?.claims || factCheck.claims.length === 0) return undefined
  const total = factCheck.claims.length
  const verified =
    factCheck.verified_count ?? factCheck.claims.filter((claim) => claim.status === "verified").length
  const contested =
    factCheck.contested_count ??
    factCheck.claims.filter((claim) => claim.status && claim.status !== "verified").length
  const unresolved = Math.max(total - verified - contested, 0)

  let summary = `Fact-check: ${verified}/${total} claims verified`
  if (contested > 0) summary += ` · ${contested} contested`
  if (unresolved > 0) summary += ` · ${unresolved} pending`
  return summary
}

function clampPercent(value?: number): number | undefined {
  if (typeof value !== "number" || Number.isNaN(value)) return undefined
  const clamped = Math.min(Math.max(value, 0), 1)
  return Math.round(clamped * 100)
}

