"use client"

import type React from "react"
import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Paperclip, Mic, Code, FileText, Lightbulb, TrendingUp, ImageIcon, X, Briefcase } from 'lucide-react'
import { getModelById } from "@/lib/models"
import type { Conversation, Message, Attachment, Artifact, CriteriaSettings } from "@/lib/types"
import { MessageBubble } from "./message-bubble"
import { HiveActivityIndicator } from "./hive-activity-indicator"
import { AgentInsightsPanel } from "./agent-insights-panel"
import { ChatHeader } from "./chat-header"

interface ChatAreaProps {
  conversation?: Conversation
  onSendMessage: (message: Message) => void
  onShowArtifact: (artifact: Artifact) => void
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

export function ChatArea({ conversation, onSendMessage, onShowArtifact }: ChatAreaProps) {
  const [input, setInput] = useState("")
  const [selectedModels, setSelectedModels] = useState<string[]>(["gpt-5-mini", "claude-3-opus"])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [reasoningMode, setReasoningMode] = useState<"deep" | "standard" | "fast">("standard")
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
  const [showInsights, setShowInsights] = useState(false)
  const [selectedMessageForInsights, setSelectedMessageForInsights] = useState<Message | null>(null)
  const [incognitoMode, setIncognitoMode] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const activeModels = selectedModels
    .map((modelId) => getModelById(modelId))
    .filter((model): model is NonNullable<ReturnType<typeof getModelById>> => Boolean(model))

  const toggleModelSelection = (modelId: string) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelId)) {
        return prev.length === 1 ? prev : prev.filter((id) => id !== modelId)
      }
      return [...prev, modelId]
    })
  }

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
    if ((!input.trim() && attachments.length === 0) || selectedModels.length === 0) return

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: input,
      timestamp: new Date(),
      attachments: attachments.length > 0 ? attachments : undefined,
    }

    onSendMessage(userMessage)

    setInput("")
    setAttachments([])
    setIsLoading(true)

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...(conversation?.messages || []), userMessage],
          models: selectedModels,
          reasoningMode,
          capabilities: activeModels.map((model) => ({
            id: model.id,
            capabilities: model.capabilities,
          })),
          criteriaSettings,
          orchestrationEngine,
          advancedFeatures,
        }),
      })

      if (!response.ok) throw new Error("Failed to get response")

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ""

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          assistantContent += decoder.decode(value)
        }
      }

      const assistantMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: assistantContent,
        timestamp: new Date(),
        model: selectedModels.join(", "),
        agents: [
          {
            agentId: "agent-general",
            agentName: "Generalist",
            agentType: "general",
            contribution: "Primary response synthesis",
            confidence: 90,
          },
          {
            agentId: "agent-research",
            agentName: "ResearchBot",
            agentType: "research",
            contribution: "Fact verification",
            confidence: 85,
          },
        ],
        consensus: {
          confidence: 88,
          debateOccurred: true,
          consensusNote: "Consensus reached after validating research findings.",
        },
      }

      onSendMessage(assistantMessage)
    } catch (error) {
      console.error("Chat send failed:", error)
      const errorMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: "I apologize, but I encountered an error. Please try again.",
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
        onToggleModel={toggleModelSelection}
        reasoningMode={reasoningMode}
        onReasoningModeChange={setReasoningMode}
        orchestrationEngine={orchestrationEngine}
        onOrchestrationChange={setOrchestrationEngine}
        advancedFeatures={advancedFeatures}
        onToggleFeature={toggleAdvancedFeature}
        criteriaSettings={criteriaSettings}
        onCriteriaChange={setCriteriaSettings}
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
                      className="h-auto flex flex-col items-center gap-2 p-4 border-border hover:border-[var(--bronze)] transition-all duration-500 bg-card/50 backdrop-blur-xl group"
                      onClick={() => setInput(suggestion.text)}
                    >
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-transform duration-500 group-hover:scale-110 group-hover:shadow-xl">
                        <Icon className="h-4 w-4 text-background" />
                      </div>
                      <div className="text-xs font-semibold">{suggestion.label}</div>
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
                      className="h-auto flex flex-col items-center gap-2 p-4 border-border hover:border-[var(--bronze)] transition-all duration-500 bg-card/50 backdrop-blur-xl group"
                      onClick={() => setInput(suggestion.text)}
                    >
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-transform duration-500 group-hover:scale-110 group-hover:shadow-xl">
                        <Icon className="h-4 w-4 text-background" />
                      </div>
                      <div className="text-xs font-semibold">{suggestion.label}</div>
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
                      className="h-auto flex flex-col items-center gap-2 p-4 border-border hover:border-[var(--bronze)] transition-all duration-500 bg-card/50 backdrop-blur-xl group"
                      onClick={() => setInput(suggestion.text)}
                    >
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-transform duration-500 group-hover:scale-110 group-hover:shadow-xl">
                        <Icon className="h-4 w-4 text-background" />
                      </div>
                      <div className="text-xs font-semibold">{suggestion.label}</div>
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
          </div>
        )}
      </ScrollArea>

      {showInsights && selectedMessageForInsights?.agents && (
        <AgentInsightsPanel
          agents={selectedMessageForInsights.agents}
          consensus={selectedMessageForInsights.consensus!}
          citations={selectedMessageForInsights.citations}
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
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Ask the hive mind anything..."
              className="min-h-[72px] pr-36 resize-none bg-secondary/50 border-border focus:border-[var(--bronze)]"
            />
            <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1.5">
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
                disabled={(!input.trim() && attachments.length === 0) || isLoading || selectedModels.length === 0}
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
