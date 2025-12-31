"use client"

import { useState, useEffect, useCallback } from "react"
import { LogoText } from "@/components/branding"
import { Sidebar } from "./sidebar"
import { ChatArea } from "./chat-area"
import { HomeScreen } from "./home-screen"
import { ArtifactPanel } from "./artifact-panel"
import { UserAccountMenu } from "./user-account-menu"
import { AdvancedSettingsDrawer } from "./advanced-settings-drawer"
import { RenameChatModal } from "./rename-chat-modal"
import { MoveToProjectModal } from "./move-to-project-modal"
import { KeyboardShortcutsModal } from "./keyboard-shortcuts-modal"
import { DeleteConfirmationDialog } from "./delete-confirmation-dialog"
import { Button } from "@/components/ui/button"
import { Menu, Keyboard } from "lucide-react"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import type { Conversation, Message, Artifact, Project, OrchestratorSettings } from "@/lib/types"
import { 
  loadOrchestratorSettings, 
  saveOrchestratorSettings, 
  DEFAULT_ORCHESTRATOR_SETTINGS 
} from "@/lib/settings-storage"
import { useAuth } from "@/lib/auth-context"
import { toast } from "@/lib/toast"

// Storage keys
const CONVERSATIONS_KEY = "llmhive-conversations"
const PROJECTS_KEY = "llmhive-projects"

// Helper to sync to API (for authenticated users)
async function syncToApi(conversations: Conversation[], projects: Project[]) {
  try {
    await Promise.all([
      fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "sync", conversations }),
      }),
      fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "sync", projects }),
      }),
    ])
    console.log("[ChatInterface] Synced to API")
  } catch (e) {
    console.error("[ChatInterface] API sync failed:", e)
  }
}

// Helper to load from API
async function loadFromApi(): Promise<{ conversations: Conversation[], projects: Project[] } | null> {
  try {
    const [convRes, projRes] = await Promise.all([
      fetch("/api/conversations"),
      fetch("/api/projects"),
    ])

    if (convRes.ok && projRes.ok) {
      const convData = await convRes.json()
      const projData = await projRes.json()
      
      const conversations = (convData.conversations || []).map((c: any) => ({
        ...c,
        createdAt: new Date(c.createdAt),
        updatedAt: new Date(c.updatedAt),
        messages: (c.messages || []).map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        })),
      }))
      
      const projects = (projData.projects || []).map((p: any) => ({
        ...p,
        createdAt: new Date(p.createdAt),
      }))

      return { conversations, projects }
    }
  } catch (e) {
    console.warn("[ChatInterface] API load failed:", e)
  }
  return null
}

export function ChatInterface() {
  const auth = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [showArtifact, setShowArtifact] = useState(false)
  const [currentArtifact, setCurrentArtifact] = useState<Artifact | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [orchestratorSettings, setOrchestratorSettings] = useState<OrchestratorSettings>(DEFAULT_ORCHESTRATOR_SETTINGS)
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  
  // Rename modal state
  const [showRenameModal, setShowRenameModal] = useState(false)
  const [renameConversationId, setRenameConversationId] = useState<string | null>(null)
  
  // Move to project modal state
  const [showMoveModal, setShowMoveModal] = useState(false)
  const [moveConversationId, setMoveConversationId] = useState<string | null>(null)
  
  // Keyboard shortcuts modal state
  const [showShortcutsModal, setShowShortcutsModal] = useState(false)
  
  // Delete confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deleteConversationId, setDeleteConversationId] = useState<string | null>(null)
  
  // Load settings and data on mount
  useEffect(() => {
    const loadData = async () => {
      const savedSettings = loadOrchestratorSettings()
      setOrchestratorSettings(savedSettings)
      
      // Try to load from API first (if authenticated)
      if (auth?.isAuthenticated) {
        const apiData = await loadFromApi()
        if (apiData && (apiData.conversations.length > 0 || apiData.projects.length > 0)) {
          setConversations(apiData.conversations)
          setProjects(apiData.projects)
          // Cache to localStorage
          localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(apiData.conversations))
          localStorage.setItem(PROJECTS_KEY, JSON.stringify(apiData.projects))
          console.log(`[ChatInterface] Loaded from API: ${apiData.conversations.length} conversations, ${apiData.projects.length} projects`)
          setSettingsLoaded(true)
          return
        }
      }
      
      // Fallback to localStorage
      try {
        const savedConversations = localStorage.getItem(CONVERSATIONS_KEY)
        if (savedConversations) {
          const parsed = JSON.parse(savedConversations)
          const restored = parsed.map((c: any) => ({
            ...c,
            createdAt: new Date(c.createdAt),
            updatedAt: new Date(c.updatedAt),
            messages: (c.messages || []).map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp),
            })),
          }))
          setConversations(restored)
        }
      } catch (e) {
        console.error("Failed to load conversations:", e)
      }
      
      try {
        const savedProjects = localStorage.getItem(PROJECTS_KEY)
        if (savedProjects) {
          const parsed = JSON.parse(savedProjects)
          const restored = parsed.map((p: any) => ({
            ...p,
            createdAt: new Date(p.createdAt),
          }))
          setProjects(restored)
        }
      } catch (e) {
        console.error("Failed to load projects:", e)
      }
      
      setSettingsLoaded(true)
    }
    
    loadData()
  }, [auth?.isAuthenticated])
  
  // Persist conversations when they change
  useEffect(() => {
    if (!settingsLoaded) return
    
    // Always save to localStorage
    try {
      localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations))
    } catch (e) {
      console.error("Failed to save conversations:", e)
    }
    
    // Also sync to API if authenticated (debounced)
    if (auth?.isAuthenticated && conversations.length > 0) {
      const timeoutId = setTimeout(() => {
        syncToApi(conversations, projects)
      }, 2000) // Debounce by 2 seconds
      return () => clearTimeout(timeoutId)
    }
  }, [conversations, settingsLoaded, auth?.isAuthenticated])
  
  // Persist projects when they change
  useEffect(() => {
    if (!settingsLoaded) return
    
    // Always save to localStorage
    try {
      localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects))
    } catch (e) {
      console.error("Failed to save projects:", e)
    }
    
    // Also sync to API if authenticated (debounced)
    if (auth?.isAuthenticated) {
      const timeoutId = setTimeout(() => {
        syncToApi(conversations, projects)
      }, 2000) // Debounce by 2 seconds
      return () => clearTimeout(timeoutId)
    }
  }, [projects, settingsLoaded, auth?.isAuthenticated])

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0
      const cmdKey = isMac ? e.metaKey : e.ctrlKey
      
      // Don't trigger in input fields except for specific shortcuts
      const target = e.target as HTMLElement
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable
      
      // Cmd/Ctrl + N: New chat
      if (cmdKey && e.key === "n" && !e.shiftKey) {
        e.preventDefault()
        handleNewChat()
        toast.info("New chat created")
        return
      }
      
      // Cmd/Ctrl + /: Show shortcuts
      if (cmdKey && e.key === "/") {
        e.preventDefault()
        setShowShortcutsModal(true)
        return
      }
      
      // Escape: Close modals
      if (e.key === "Escape") {
        if (showShortcutsModal) {
          setShowShortcutsModal(false)
          return
        }
        if (showRenameModal) {
          setShowRenameModal(false)
          return
        }
        if (showMoveModal) {
          setShowMoveModal(false)
          return
        }
        if (showAdvancedSettings) {
          setShowAdvancedSettings(false)
          return
        }
        if (showArtifact) {
          setShowArtifact(false)
          return
        }
      }
      
      // Cmd/Ctrl + ,: Open settings
      if (cmdKey && e.key === "," && !isInput) {
        e.preventDefault()
        setShowAdvancedSettings(true)
        return
      }
    }
    
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [showShortcutsModal, showRenameModal, showMoveModal, showAdvancedSettings, showArtifact])

  const currentConversation = conversations.find((c) => c.id === currentConversationId)

  const handleNewChat = () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      model: "gpt-4o",
    }
    setConversations([newConv, ...conversations])
    setCurrentConversationId(newConv.id)
    setShowArtifact(false)
    setCurrentArtifact(null)
    setMobileSidebarOpen(false)
    return newConv.id
  }

  const handleStartFromTemplate = (preset: Partial<OrchestratorSettings>) => {
    const newSettings = { ...DEFAULT_ORCHESTRATOR_SETTINGS, ...preset }
    setOrchestratorSettings(newSettings)
    saveOrchestratorSettings(newSettings)
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

  const handleOpenDeleteDialog = (id: string) => {
    setDeleteConversationId(id)
    setShowDeleteDialog(true)
  }

  const handleDeleteConversation = (id: string) => {
    // Clear the delete dialog state first
    setDeleteConversationId(null)
    
    // Then update the conversations
    setConversations((prev) => prev.filter((c) => c.id !== id))
    
    if (currentConversationId === id) {
      setCurrentConversationId(null)
      setShowArtifact(false)
      setCurrentArtifact(null)
    }
    
    toast.info("Chat deleted")
  }

  const handleShareConversation = (id: string) => {
    // TODO: Implement share functionality
    const conv = conversations.find((c) => c.id === id)
    if (conv) {
      // For now, copy a shareable link to clipboard
      navigator.clipboard.writeText(`${window.location.origin}/chat/${id}`)
      toast.success("Share link copied to clipboard")
    }
  }

  const handleArchiveConversation = (id: string) => {
    // Mark conversation as archived
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, archived: true } : c))
    )
    toast.info("Chat archived")
  }

  const handleTogglePin = (id: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, pinned: !c.pinned } : c)))
  }

  const handleRenameConversation = (id: string, newTitle: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c)))
  }

  const handleMoveToProject = (conversationId: string, projectId: string) => {
    setProjects((prev) =>
      prev.map((project) => {
        if (project.id === projectId) {
          // Add conversation to project if not already there
          if (!project.conversations.includes(conversationId)) {
            return { ...project, conversations: [...project.conversations, conversationId] }
          }
        } else {
          // Remove from other projects
          return { ...project, conversations: project.conversations.filter((id) => id !== conversationId) }
        }
        return project
      })
    )
    toast.success("Moved to project successfully")
    setShowMoveModal(false)
    setMoveConversationId(null)
  }

  const handleOpenMoveModal = (conversationId: string) => {
    setMoveConversationId(conversationId)
    setShowMoveModal(true)
  }

  const handleOpenRenameModal = (conversationId: string) => {
    setRenameConversationId(conversationId)
    setShowRenameModal(true)
  }

  const handleCreateProject = (project: Omit<Project, "id" | "createdAt">) => {
    const newProject: Project = {
      ...project,
      id: `project-${Date.now()}`,
      createdAt: new Date(),
    }
    setProjects((prev) => [...prev, newProject])
    toast.success(`Project "${newProject.name}" created`)
  }

  const handleDeleteProject = (projectId: string) => {
    setProjects((prev) => prev.filter((p) => p.id !== projectId))
    toast.info("Project deleted")
  }

  const handleSelectProject = (projectId: string) => {
    const project = projects.find((p) => p.id === projectId)
    if (project && project.conversations.length > 0) {
      // Select the first conversation in the project
      setCurrentConversationId(project.conversations[0])
      toast.info(`Viewing project: ${project.name}`)
    }
  }

  const handleGoHome = () => {
    setCurrentConversationId(null)
    setShowArtifact(false)
    setCurrentArtifact(null)
    setMobileSidebarOpen(false)
  }

  const updateOrchestratorSettings = (updates: Partial<OrchestratorSettings>) => {
    setOrchestratorSettings((prev) => {
      const newSettings = { ...prev, ...updates }
      // Persist to localStorage for cross-page access
      saveOrchestratorSettings(newSettings)
      return newSettings
    })
  }

  const sidebarContent = (
    <Sidebar
      conversations={conversations.filter((c) => !c.archived)}
      currentConversationId={currentConversationId}
      onNewChat={handleNewChat}
      onSelectConversation={handleSelectConversation}
      onDeleteConversation={handleOpenDeleteDialog}
      onTogglePin={handleTogglePin}
      onRenameConversation={handleOpenRenameModal}
      onMoveToProject={handleOpenMoveModal}
      onShareConversation={handleShareConversation}
      onArchiveConversation={handleArchiveConversation}
      projects={projects}
      collapsed={sidebarCollapsed}
      onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      onGoHome={handleGoHome}
      onCreateProject={handleCreateProject}
      onDeleteProject={handleDeleteProject}
      onSelectProject={handleSelectProject}
    />
  )

  return (
    <div className="flex h-full w-full relative">
      {/* Sign In Button - Desktop Top Right (fixed position) */}
      <div className="hidden md:block fixed top-3 right-3 z-50">
        <UserAccountMenu />
      </div>

      {/* Desktop Sidebar */}
      <div className="hidden md:block h-full">{sidebarContent}</div>

      {/* Mobile Header with Hamburger - Glassmorphism */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 h-14 border-b border-white/10 llmhive-glass-sidebar flex items-center justify-between px-4">
        <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9" aria-label="Open navigation menu">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-72 llmhive-glass-sidebar border-r-0">
            <Sidebar
              conversations={conversations.filter((c) => !c.archived)}
              currentConversationId={currentConversationId}
              onNewChat={handleNewChat}
              onSelectConversation={handleSelectConversation}
              onDeleteConversation={handleOpenDeleteDialog}
              onTogglePin={handleTogglePin}
              onRenameConversation={handleOpenRenameModal}
              onMoveToProject={handleOpenMoveModal}
              onShareConversation={handleShareConversation}
              onArchiveConversation={handleArchiveConversation}
              projects={projects}
              collapsed={false}
              onToggleCollapse={() => {}}
              onGoHome={handleGoHome}
              onCreateProject={handleCreateProject}
              onDeleteProject={handleDeleteProject}
              onSelectProject={handleSelectProject}
            />
          </SheetContent>
        </Sheet>

        <LogoText height={28} />

        <UserAccountMenu />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden md:pt-0 pt-14">
        {!currentConversationId ? (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex-1 h-full overflow-auto">
              <HomeScreen onNewChat={handleNewChat} onStartFromTemplate={handleStartFromTemplate} />
            </div>
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

      {/* Rename Chat Modal */}
      <RenameChatModal
        open={showRenameModal}
        onOpenChange={setShowRenameModal}
        currentTitle={conversations.find((c) => c.id === renameConversationId)?.title ?? ""}
        onRename={(newTitle) => {
          if (renameConversationId) {
            handleRenameConversation(renameConversationId, newTitle)
            toast.success("Chat renamed successfully")
          }
          setShowRenameModal(false)
          setRenameConversationId(null)
        }}
      />

      {/* Move to Project Modal */}
      <MoveToProjectModal
        open={showMoveModal}
        onOpenChange={setShowMoveModal}
        projects={projects}
        onMove={(projectId) => {
          if (moveConversationId) {
            handleMoveToProject(moveConversationId, projectId)
          }
        }}
        onCreateProject={() => {
          setShowMoveModal(false)
          // Create a default project and then re-open
          handleCreateProject({
            name: "New Project",
            description: "Created from move dialog",
            conversations: moveConversationId ? [moveConversationId] : [],
            files: [],
          })
        }}
      />

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal
        open={showShortcutsModal}
        onOpenChange={setShowShortcutsModal}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete chat?"
        description={`This will permanently delete "${conversations.find((c) => c.id === deleteConversationId)?.title ?? "this chat"}". This action cannot be undone.`}
        onConfirm={() => {
          if (deleteConversationId) {
            handleDeleteConversation(deleteConversationId)
          }
        }}
      />
    </div>
  )
}
