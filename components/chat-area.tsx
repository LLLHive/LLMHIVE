"use client"

import type React from "react"
import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Paperclip, Mic, X, ImageIcon, FileText } from "lucide-react"
import { getModelById } from "@/lib/models"
import type { Conversation, Message, Attachment, Artifact, OrchestratorSettings } from "@/lib/types"
import { MessageBubble } from "./message-bubble"
import { HiveActivityIndicator } from "./hive-activity-indicator"
import { AgentInsightsPanel } from "./agent-insights-panel"
import { ChatToolbar } from "./chat-toolbar"

interface ChatAreaProps {
  conversation?: Conversation
  onSendMessage: (message: Message) => void
  onShowArtifact: (artifact: Artifact) => void
  orchestratorSettings: OrchestratorSettings
  onOrchestratorSettingsChange: (settings: Partial<OrchestratorSettings>) => void
  onOpenAdvancedSettings: () => void
  userAccountMenu?: React.ReactNode
}

export function ChatArea({
  conversation,
  onSendMessage,
  onShowArtifact,
  orchestratorSettings,
  onOrchestratorSettingsChange,
  onOpenAdvancedSettings,
  userAccountMenu,
}: ChatAreaProps) {
  const [input, setInput] = useState("")
  const [selectedModels, setSelectedModels] = useState<string[]>(["gpt-5-mini"])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [showInsights, setShowInsights] = useState(false)
  const [selectedMessageForInsights, setSelectedMessageForInsights] = useState<Message | null>(null)
  const [incognitoMode, setIncognitoMode] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const currentModel = getModelById(selectedModels[0] || "gpt-5-mini")

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
          model: selectedModels[0],
          orchestratorSettings,
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
        model: selectedModels[0],
        agents: [
          { type: "general", contribution: "Primary response", confidence: 0.9 },
          { type: "research", contribution: "Fact verification", confidence: 0.85 },
        ],
        consensus: { level: 0.88, agreementCount: 5, totalAgents: 6 },
      }

      onSendMessage(assistantMessage)
    } catch (error) {
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

  const displayMessages = conversation?.messages || []

  return (
    <div className="flex-1 flex flex-col relative min-h-0">
      {/* Hexagonal pattern background */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 0l25.98 15v30L30 60 4.02 45V15z' fill='none' stroke='%23C48E48' strokeWidth='1'/%3E%3C/svg%3E")`,
          backgroundSize: "60px 60px",
        }}
      />

      <header className="border-b border-border p-3 flex items-center justify-between gap-4 bg-card/50 backdrop-blur-xl sticky top-0 z-40 flex-wrap">
        <ChatToolbar
          settings={orchestratorSettings}
          onSettingsChange={onOrchestratorSettingsChange}
          onOpenAdvanced={onOpenAdvancedSettings}
        />
        {userAccountMenu}
      </header>

      <HiveActivityIndicator active={isLoading} agentCount={6} />

      <ScrollArea className="flex-1 relative z-10">
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
      </ScrollArea>

      {showInsights && selectedMessageForInsights?.agents && (
        <AgentInsightsPanel
          agents={selectedMessageForInsights.agents}
          consensus={selectedMessageForInsights.consensus!}
          citations={selectedMessageForInsights.citations}
          onClose={() => setShowInsights(false)}
        />
      )}

      <div className="border-t border-border p-3 md:p-4 bg-card/80 backdrop-blur-xl relative z-10 sticky bottom-0">
        <div className="max-w-4xl mx-auto">
          {attachments.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {attachments.map((att) => (
                <div key={att.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border text-sm">
                  {att.type.startsWith("image/") ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                  <span className="truncate max-w-[100px] md:max-w-[150px]">{att.name}</span>
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
              className="min-h-[56px] md:min-h-[72px] pr-28 md:pr-36 resize-none bg-secondary/50 border-border focus:border-[var(--bronze)] text-sm md:text-base"
            />
            <div className="absolute bottom-2 md:bottom-2.5 right-2 md:right-2.5 flex items-center gap-1 md:gap-1.5">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 md:h-8 md:w-8"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>
              <Button size="icon" variant="ghost" className="h-7 w-7 md:h-8 md:w-8">
                <Mic className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>
              <Button
                size="icon"
                onClick={handleSend}
                disabled={(!input.trim() && attachments.length === 0) || isLoading}
                className="h-7 w-7 md:h-8 md:w-8 bronze-gradient disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>
            </div>
          </div>
          <p className="text-[9px] md:text-[10px] text-muted-foreground mt-2 text-center opacity-60">
            LLMHive uses multiple AI agents for enhanced accuracy
          </p>
        </div>
      </div>
    </div>
  )
}
