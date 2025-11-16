"use client"

import { useMemo, useState } from "react"
import { Sidebar } from "./sidebar"
import { ChatArea } from "./chat-area"
import { ArtifactPanel } from "./artifact-panel"
import type { Conversation, Message, Artifact } from "@/lib/types"

const buildConversation = (title = "New Chat"): Conversation => ({
  id: `conv-${crypto.randomUUID()}`,
  title,
  messages: [],
  createdAt: new Date(),
  updatedAt: new Date(),
  model: "gpt-5",
})

export function ChatInterface() {
  // Seed an initial empty conversation so the first message always has a target.
  const initialConversation = useMemo(() => buildConversation(), [])
  const [conversations, setConversations] = useState<Conversation[]>([initialConversation])
  const [currentConversationId, setCurrentConversationId] = useState<string>(initialConversation.id)
  const [showArtifact, setShowArtifact] = useState(false)
  const [currentArtifact, setCurrentArtifact] = useState<Artifact | null>(null)

  const currentConversation =
    conversations.find((c) => c.id === currentConversationId) ?? conversations[0]

  const handleNewChat = () => {
    const newConv = buildConversation()
    setConversations((prev) => [newConv, ...prev])
    setCurrentConversationId(newConv.id)
    setShowArtifact(false)
    setCurrentArtifact(null)
    return newConv.id
  }

  const addMessageToConversation = (conversationId: string, message: Message) => {
    setConversations((prev) =>
      prev.map((conv) => {
        if (conv.id === conversationId) {
          const updatedMessages = [...conv.messages, message]
          return {
            ...conv,
            messages: updatedMessages,
            updatedAt: new Date(),
            title:
              conv.title === "New Chat" && message.role === "user"
                ? message.content.slice(0, 50)
                : conv.title,
          }
        }
        return conv
      }),
    )

    if (message.artifact) {
      setCurrentArtifact(message.artifact)
      setShowArtifact(true)
    }
  }

  const handleSendMessage = (message: Message) => {
    // Ensure we have a conversation to add messages to
    let targetConversationId = currentConversationId
    if (!targetConversationId) {
      targetConversationId = handleNewChat()
      // Wait for state update before adding message
      setTimeout(() => {
        addMessageToConversation(targetConversationId, message)
      }, 10)
    } else {
      // Add immediately if conversation exists
      addMessageToConversation(targetConversationId, message)
    }
  }

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
    const conv = conversations.find((c) => c.id === id)
    if (!conv) {
      setShowArtifact(false)
      setCurrentArtifact(null)
      return
    }

    const lastArtifact = [...conv.messages].reverse().find((m) => m.artifact)?.artifact
    if (lastArtifact) {
      setCurrentArtifact(lastArtifact)
      setShowArtifact(true)
    } else {
      setShowArtifact(false)
      setCurrentArtifact(null)
    }
  }

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => {
      const remaining = prev.filter((c) => c.id !== id)
      if (remaining.length === 0) {
        const fresh = buildConversation()
        setCurrentConversationId(fresh.id)
        setShowArtifact(false)
        setCurrentArtifact(null)
        return [fresh]
      }
      if (currentConversationId === id) {
        setCurrentConversationId(remaining[0].id)
        setShowArtifact(false)
        setCurrentArtifact(null)
      }
      return remaining
    })
  }

  const handleTogglePin = (id: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, pinned: !c.pinned } : c)))
  }

  const handleConversationUpdate = (backendConversationId?: number) => {
    if (backendConversationId == null) return
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === currentConversationId ? { ...conv, backendConversationId } : conv,
      ),
    )
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
          onConversationUpdate={handleConversationUpdate}
        />
        {showArtifact && currentArtifact && (
          <ArtifactPanel artifact={currentArtifact} onClose={() => setShowArtifact(false)} />
        )}
      </div>
    </div>
  )
}
