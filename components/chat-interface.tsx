"use client"

import { useState } from "react"
import { Sidebar } from "./sidebar"
import { ChatArea } from "./chat-area"
import { HomeScreen } from "./home-screen"
import { ArtifactPanel } from "./artifact-panel"
import { UserAccountMenu } from "./user-account-menu"
import { AdvancedSettingsDrawer } from "./advanced-settings-drawer"
import { Button } from "@/components/ui/button"
import { Menu } from "lucide-react"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import type { Conversation, Message, Artifact, Project, OrchestratorSettings } from "@/lib/types"

const defaultOrchestratorSettings: OrchestratorSettings = {
  reasoningMode: "standard",
  domainPack: "default",
  agentMode: "single",
  promptOptimization: false,
  outputValidation: false,
  answerStructure: false,
  sharedMemory: false,
  learnFromChat: false,
  selectedModels: ["gpt-5"],
  advancedReasoningMethods: [],
}

export function ChatInterface() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [showArtifact, setShowArtifact] = useState(false)
  const [currentArtifact, setCurrentArtifact] = useState<Artifact | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [orchestratorSettings, setOrchestratorSettings] = useState<OrchestratorSettings>(defaultOrchestratorSettings)
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  // TODO: Wire this to your auth system (GITHUB_ID/GITHUB_SECRET, AUTH_SECRET)
  const [user, setUser] = useState<{ name?: string; email?: string; image?: string } | null>(null)

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
    setMobileSidebarOpen(false)
    return newConv.id
  }

  const handleStartFromTemplate = (preset: Partial<OrchestratorSettings>) => {
    setOrchestratorSettings({ ...defaultOrchestratorSettings, ...preset })
    handleNewChat()
  }

  const handleSendMessage = (message: Message) => {
    let targetConversationId = currentConversationId

    if (!targetConversationId) {
      targetConversationId = handleNewChat()
    }

    setConversations((prev) =>
      prev.map((conv) => {
        if (conv.id === targetConversationId) {
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

    if (message.artifact) {
      setCurrentArtifact(message.artifact)
      setShowArtifact(true)
    }
  }

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
    setMobileSidebarOpen(false)
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

  const handleRenameConversation = (id: string, newTitle: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c)))
  }

  const handleMoveToProject = (conversationId: string, projectId: string) => {
    // TODO: Implement move to project logic with your backend
    console.log(`Moving conversation ${conversationId} to project ${projectId}`)
  }

  const handleSignIn = () => {
    // TODO: Integrate with your GitHub OAuth using GITHUB_ID/GITHUB_SECRET
    console.log("Sign in triggered")
  }

  const handleSignOut = () => {
    setUser(null)
  }

  const handleGoHome = () => {
    setCurrentConversationId(null)
    setShowArtifact(false)
    setCurrentArtifact(null)
    setMobileSidebarOpen(false)
  }

  const updateOrchestratorSettings = (updates: Partial<OrchestratorSettings>) => {
    setOrchestratorSettings((prev) => ({ ...prev, ...updates }))
  }

  const sidebarContent = (
    <Sidebar
      conversations={conversations}
      currentConversationId={currentConversationId}
      onNewChat={handleNewChat}
      onSelectConversation={handleSelectConversation}
      onDeleteConversation={handleDeleteConversation}
      onTogglePin={handleTogglePin}
      onRenameConversation={handleRenameConversation}
      onMoveToProject={handleMoveToProject}
      projects={projects}
      collapsed={sidebarCollapsed}
      onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      onGoHome={handleGoHome}
    />
  )

  return (
    <div className="flex h-full w-full bg-background relative">
      {/* Desktop Sidebar */}
      <div className="hidden md:block h-full">{sidebarContent}</div>

      {/* Mobile Header with Hamburger */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 h-14 border-b border-border bg-card/95 backdrop-blur-xl flex items-center justify-between px-4">
        <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-72">
            <Sidebar
              conversations={conversations}
              currentConversationId={currentConversationId}
              onNewChat={handleNewChat}
              onSelectConversation={handleSelectConversation}
              onDeleteConversation={handleDeleteConversation}
              onTogglePin={handleTogglePin}
              onRenameConversation={handleRenameConversation}
              onMoveToProject={handleMoveToProject}
              projects={projects}
              collapsed={false}
              onToggleCollapse={() => {}}
              onGoHome={handleGoHome}
            />
          </SheetContent>
        </Sheet>

        <span className="text-lg font-bold bg-gradient-to-r from-orange-500 to-[var(--gold)] bg-clip-text text-transparent">
          LLMHive
        </span>

        <UserAccountMenu user={user} onSignIn={handleSignIn} onSignOut={handleSignOut} />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden md:pt-0 pt-14">
        {!currentConversationId ? (
          <div className="flex-1 flex flex-col">
            {/* Desktop User Account Menu */}
            <div className="hidden md:flex items-center justify-end p-3 border-b border-border bg-card/50">
              <UserAccountMenu user={user} onSignIn={handleSignIn} onSignOut={handleSignOut} />
            </div>
            <HomeScreen onNewChat={handleNewChat} onStartFromTemplate={handleStartFromTemplate} />
          </div>
        ) : (
          <>
            <ChatArea
              conversation={currentConversation}
              onSendMessage={handleSendMessage}
              onShowArtifact={(artifact) => {
                setCurrentArtifact(artifact)
                setShowArtifact(true)
              }}
              orchestratorSettings={orchestratorSettings}
              onOrchestratorSettingsChange={updateOrchestratorSettings}
              onOpenAdvancedSettings={() => setShowAdvancedSettings(true)}
              userAccountMenu={
                <div className="hidden md:block">
                  <UserAccountMenu user={user} onSignIn={handleSignIn} onSignOut={handleSignOut} />
                </div>
              }
            />
            {showArtifact && currentArtifact && (
              <ArtifactPanel artifact={currentArtifact} onClose={() => setShowArtifact(false)} />
            )}
          </>
        )}
      </div>

      {/* Advanced Settings Drawer */}
      <AdvancedSettingsDrawer
        open={showAdvancedSettings}
        onOpenChange={setShowAdvancedSettings}
        settings={orchestratorSettings}
        onSettingsChange={updateOrchestratorSettings}
      />
    </div>
  )
}
