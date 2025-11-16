"use client"

import { useState } from "react"
import { Sidebar } from "./sidebar"
import { ChatArea } from "./chat-area"
import { ArtifactPanel } from "./artifact-panel"
import type { Conversation, Message, Artifact } from "@/lib/types"

export function ChatInterface() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [showArtifact, setShowArtifact] = useState(false)
  const [currentArtifact, setCurrentArtifact] = useState<Artifact | null>(null)

  const currentConversation = conversations.find((c) => c.id === currentConversationId)

  const handleNewChat = () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      model: "gpt-5",
    }
    setConversations([newConv, ...conversations])
    setCurrentConversationId(newConv.id)
    setShowArtifact(false)
    setCurrentArtifact(null)
  }

  const handleSendMessage = (message: Message) => {
    if (!currentConversationId) {
      handleNewChat()
      // Delay to ensure conversation is created
      setTimeout(() => {
        addMessageToCurrentConversation(message)
      }, 50)
      return
    }

    addMessageToCurrentConversation(message)

    if (message.role === "user") {
      setTimeout(() => {
        const aiResponse: Message = {
          id: `msg-${Date.now()}-ai`,
          role: "assistant",
          content:
            "I've analyzed your request using our hive of specialized AI agents. Based on the collective intelligence of our legal, coding, research, and creative experts, here's a comprehensive response that synthesizes multiple perspectives.\n\nThe legal team verified all factual claims, the coding team optimized technical accuracy, and our research agents fact-checked against the latest sources.",
          timestamp: new Date(),
          model: "gpt-5-mini",
          agents: [
            {
              agentId: "agent-legal-1",
              agentName: "LegalExpert",
              agentType: "legal",
              contribution: "Verified legal facts and compliance requirements",
              confidence: 92,
              citations: [
                {
                  id: "cit-1",
                  text: "Legal precedent reference",
                  source: "Legal Database",
                  url: "https://example.com/legal",
                  verified: true,
                },
              ],
            },
            {
              agentId: "agent-code-1",
              agentName: "CodeGuru",
              agentType: "code",
              contribution: "Optimized technical implementation and code quality",
              confidence: 95,
            },
            {
              agentId: "agent-research-1",
              agentName: "ResearchBot",
              agentType: "research",
              contribution: "Fact-checked claims against academic sources",
              confidence: 88,
              citations: [
                {
                  id: "cit-2",
                  text: "Academic research citation",
                  source: "Journal of AI Research",
                  url: "https://example.com/research",
                  verified: true,
                },
              ],
            },
          ],
          consensus: {
            confidence: 92,
            debateOccurred: true,
            consensusNote:
              "Multiple perspectives were considered. The AI team reached consensus after evaluating different approaches to ensure accuracy and completeness.",
          },
          citations: [
            {
              id: "cit-3",
              text: "General knowledge reference",
              source: "Wikipedia",
              url: "https://wikipedia.org",
              verified: true,
            },
            {
              id: "cit-4",
              text: "Technical documentation",
              source: "MDN Web Docs",
              url: "https://developer.mozilla.org",
              verified: true,
            },
          ],
        }
        addMessageToCurrentConversation(aiResponse)
      }, 1500)
    }
  }

  const addMessageToCurrentConversation = (message: Message) => {
    setConversations((prev) =>
      prev.map((conv) => {
        if (conv.id === currentConversationId) {
          const updatedMessages = [...conv.messages, message]
          return {
            ...conv,
            messages: updatedMessages,
            updatedAt: new Date(),
            title: conv.title === "New Chat" && message.role === "user" ? message.content.slice(0, 50) : conv.title,
          }
        }
        return conv
      }),
    )

    // Show artifact if message contains one
    if (message.artifact) {
      setCurrentArtifact(message.artifact)
      setShowArtifact(true)
    }
  }

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
    const conv = conversations.find((c) => c.id === id)
    const lastArtifact = conv?.messages.reverse().find((m) => m.artifact)?.artifact
    if (lastArtifact) {
      setCurrentArtifact(lastArtifact)
      setShowArtifact(true)
    } else {
      setShowArtifact(false)
      setCurrentArtifact(null)
    }
  }

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id))
    if (currentConversationId === id) {
      setCurrentConversationId(null)
      setShowArtifact(false)
      setCurrentArtifact(null)
    }
  }

  const handleTogglePin = (id: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, pinned: !c.pinned } : c)))
  }

  return (
    <div className="flex h-full w-full bg-background relative">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onTogglePin={handleTogglePin}
      />
      <div className="flex flex-1 overflow-hidden">
        <ChatArea
          conversation={currentConversation}
          onSendMessage={handleSendMessage}
          onShowArtifact={(artifact) => {
            setCurrentArtifact(artifact)
            setShowArtifact(true)
          }}
        />
        {showArtifact && currentArtifact && (
          <ArtifactPanel artifact={currentArtifact} onClose={() => setShowArtifact(false)} />
        )}
      </div>
    </div>
  )
}
