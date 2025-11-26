"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Lightbulb, Code, FileText, TrendingUp, BookOpen, Briefcase, Database } from 'lucide-react'

const firstRowSuggestions = [
  { icon: Lightbulb, label: "Prompt Optimization", text: "Optimize my prompt for better AI responses" },
  { icon: Code, label: "Output Validation", text: "Validate and verify the output for accuracy" },
  { icon: FileText, label: "Answer Structure", text: "Structure the answer with clear sections and examples" },
]

const secondRowSuggestions = [
  { icon: TrendingUp, label: "Strategize", text: "Help me develop a strategic approach" },
  { icon: FileText, label: "Write", text: "Write comprehensive content for me" },
  { icon: BookOpen, label: "Learn", text: "Teach me about this topic in detail" },
]

const thirdRowSuggestions = [
  { icon: Briefcase, label: "Industry Specific", text: "Provide industry-specific insights" },
  { icon: Code, label: "Code", text: "Help me write and debug code" },
  { icon: Database, label: "Shared Data", text: "Analyze and work with shared data" },
]

interface ChatAreaProps {
  conversation?: any
  onSendMessage: (message: any) => void
  onShowArtifact?: (artifact: any) => void
}

export function ChatArea({ conversation, onSendMessage }: ChatAreaProps) {
  const [isLoading, setIsLoading] = useState(false)

  const handlePromptClick = async (text: string) => {
    const userMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    }

    onSendMessage(userMessage)
    setIsLoading(true)

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...(conversation?.messages || []), userMessage],
        }),
      })

      if (!response.ok) throw new Error("Failed to get response")

      const data = await response.json()
      
      const assistantMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: data.content || data.message || "Response received",
        timestamp: new Date(),
      }

      onSendMessage(assistantMessage)
    } catch (error) {
      console.error("[v0] Chat error:", error)
      const errorMessage = {
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
    <div className="flex-1 flex flex-col relative">
      <ScrollArea className="flex-1 relative z-10">
        {displayMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center pt-12 max-w-4xl mx-auto px-4">
            <div className="flex flex-col gap-4 w-full">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {firstRowSuggestions.map((suggestion) => {
                  const Icon = suggestion.icon
                  return (
                    <Button
                      key={suggestion.label}
                      variant="outline"
                      className="group h-auto flex flex-col items-center gap-3 p-4 border-border hover:border-[var(--bronze)] hover:bg-gradient-to-br hover:from-orange-500/10 hover:to-amber-600/10 transition-all duration-300 bg-card/50"
                      onClick={() => handlePromptClick(suggestion.text)}
                    >
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:shadow-xl">
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <div className="text-xs font-semibold text-white">{suggestion.label}</div>
                    </Button>
                  )
                })}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {secondRowSuggestions.map((suggestion) => {
                  const Icon = suggestion.icon
                  return (
                    <Button
                      key={suggestion.label}
                      variant="outline"
                      className="group h-auto flex flex-col items-center gap-3 p-4 border-border hover:border-[var(--bronze)] hover:bg-gradient-to-br hover:from-orange-500/10 hover:to-amber-600/10 transition-all duration-300 bg-card/50"
                      onClick={() => handlePromptClick(suggestion.text)}
                    >
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:shadow-xl">
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <div className="text-xs font-semibold text-white">{suggestion.label}</div>
                    </Button>
                  )
                })}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {thirdRowSuggestions.map((suggestion) => {
                  const Icon = suggestion.icon
                  return (
                    <Button
                      key={suggestion.label}
                      variant="outline"
                      className="group h-auto flex flex-col items-center gap-3 p-4 border-border hover:border-[var(--bronze)] hover:bg-gradient-to-br hover:from-orange-500/10 hover:to-amber-600/10 transition-all duration-300 bg-card/50"
                      onClick={() => handlePromptClick(suggestion.text)}
                    >
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-[var(--gold)] flex items-center justify-center shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:shadow-xl">
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <div className="text-xs font-semibold text-white">{suggestion.label}</div>
                    </Button>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
            {displayMessages.map((message: any) => (
              <div key={message.id} className="flex gap-3">
                <div className={`p-4 rounded-lg max-w-[80%] ${
                  message.role === "user" 
                    ? "bg-accent ml-auto" 
                    : "bg-card"
                }`}>
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
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
    </div>
  )
}
