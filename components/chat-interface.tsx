"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { useSearchParams } from "next/navigation"
import { LogoText } from "@/components/branding"
import { Sidebar } from "./sidebar"
import { ChatArea } from "./chat-area"
import { HomeScreen } from "./home-screen"
import { ArtifactPanel } from "./artifact-panel"
import { UserAccountMenu } from "./user-account-menu"
import { AdvancedSettingsDrawer } from "./advanced-settings-drawer"
import { RenameChatModal } from "./rename-chat-modal"
import { RenameProjectModal } from "./rename-project-modal"
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
import { useConversationsContext } from "@/lib/conversations-context"
import { toast } from "@/lib/toast"

export function ChatInterface() {
  // URL search params for deep linking (e.g., from Discover page)
  const searchParams = useSearchParams()
  
  // Use shared context for conversations and projects
  const {
    conversations,
    projects,
    currentConversation,
    setCurrentConversation,
    createConversation,
    updateConversation,
    deleteConversation,
    createProject,
    updateProject,
    deleteProject,
    addConversationToProject,
    removeConversationFromProject,
  } = useConversationsContext()
  
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [showArtifact, setShowArtifact] = useState(false)
  const [currentArtifact, setCurrentArtifact] = useState<Artifact | null>(null)
  const [orchestratorSettings, setOrchestratorSettings] = useState<OrchestratorSettings>(DEFAULT_ORCHESTRATOR_SETTINGS)
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  
  // Rename chat modal state
  const [showRenameModal, setShowRenameModal] = useState(false)
  const [renameConversationId, setRenameConversationId] = useState<string | null>(null)
  
  // Rename project modal state
  const [showRenameProjectModal, setShowRenameProjectModal] = useState(false)
  const [renameProjectId, setRenameProjectId] = useState<string | null>(null)
  
  // Move to project modal state
  const [showMoveModal, setShowMoveModal] = useState(false)
  const [moveConversationId, setMoveConversationId] = useState<string | null>(null)
  
  // Keyboard shortcuts modal state
  const [showShortcutsModal, setShowShortcutsModal] = useState(false)
  
  // Delete confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deleteConversationId, setDeleteConversationId] = useState<string | null>(null)
  
  // Initial query from URL (for deep linking from Discover, templates, etc.)
  const [initialQuery, setInitialQuery] = useState<string | null>(null)
  const queryProcessedRef = useRef(false)
  
  // Load orchestrator settings on mount
  useEffect(() => {
    const savedSettings = loadOrchestratorSettings()
    setOrchestratorSettings(savedSettings)
  }, [])
  
  // Handle URL query parameter (e.g., ?q=search+query)
  useEffect(() => {
    const queryParam = searchParams.get('q')
    if (queryParam && !queryProcessedRef.current) {
      queryProcessedRef.current = true
      setInitialQuery(queryParam)
      // Clear the URL parameter without triggering a navigation
      if (typeof window !== 'undefined') {
        const url = new URL(window.location.href)
        url.searchParams.delete('q')
        window.history.replaceState({}, '', url.toString())
      }
    }
  }, [searchParams])

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

  // Get current conversation from context or by ID
  const currentConv = currentConversation || conversations.find((c) => c.id === currentConversationId)

  const handleNewChat = async () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      model: "gpt-4o",
    }
    await createConversation(newConv)
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

  const handleSendMessage = async (message: Message) => {
    let targetConversationId = currentConversationId

    if (!targetConversationId) {
      targetConversationId = await handleNewChat()
    }

    const conv = conversations.find(c => c.id === targetConversationId)
    if (conv) {
      const updatedMessages = [...conv.messages, message]
      const newTitle = conv.title === "New Chat" && message.role === "user" 
        ? message.content.slice(0, 50) 
        : conv.title
      
      await updateConversation(targetConversationId, {
        messages: updatedMessages,
        title: newTitle,
      })
    }

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
    // Close mobile sidebar first to prevent focus trap issues
    setMobileSidebarOpen(false)
    // Small delay to let sidebar close before opening dialog
    setTimeout(() => {
      setDeleteConversationId(id)
      setShowDeleteDialog(true)
    }, 100)
  }

  const handleDeleteConversation = async (id: string) => {
    // Clear the delete dialog state first
    setDeleteConversationId(null)
    
    // Delete from context (handles localStorage and API sync)
    await deleteConversation(id)
    
    if (currentConversationId === id) {
      setCurrentConversationId(null)
      setShowArtifact(false)
      setCurrentArtifact(null)
    }
    
    toast.info("Chat deleted")
  }

  const handleShareConversation = (id: string) => {
    // Close mobile sidebar
    setMobileSidebarOpen(false)
    
    // TODO: Implement share functionality
    const conv = conversations.find((c) => c.id === id)
    if (conv) {
      // For now, copy a shareable link to clipboard
      navigator.clipboard.writeText(`${window.location.origin}/chat/${id}`)
      toast.success("Share link copied to clipboard")
    }
  }

  const handleArchiveConversation = async (id: string) => {
    // Close mobile sidebar
    setMobileSidebarOpen(false)
    
    // Mark conversation as archived
    await updateConversation(id, { archived: true })
    toast.info("Chat archived")
  }

  const handleTogglePin = async (id: string) => {
    const conv = conversations.find(c => c.id === id)
    if (conv) {
      await updateConversation(id, { pinned: !conv.pinned })
    }
  }

  const handleRenameConversation = async (id: string, newTitle: string) => {
    await updateConversation(id, { title: newTitle })
  }

  const handleMoveToProject = async (conversationId: string, projectId: string) => {
    // Remove from all other projects first
    for (const project of projects) {
      if (project.id !== projectId && project.conversations.includes(conversationId)) {
        await removeConversationFromProject(conversationId, project.id)
      }
    }
    // Add to target project
    await addConversationToProject(conversationId, projectId)
    
    toast.success("Moved to project successfully")
    setShowMoveModal(false)
    setMoveConversationId(null)
  }

  const handleOpenMoveModal = (conversationId: string) => {
    // Close mobile sidebar first to prevent focus trap issues
    setMobileSidebarOpen(false)
    setTimeout(() => {
      setMoveConversationId(conversationId)
      setShowMoveModal(true)
    }, 100)
  }

  const handleOpenRenameModal = (conversationId: string) => {
    // Close mobile sidebar first to prevent focus trap issues
    setMobileSidebarOpen(false)
    setTimeout(() => {
      setRenameConversationId(conversationId)
      setShowRenameModal(true)
    }, 100)
  }

  const handleOpenRenameProjectModal = (projectId: string) => {
    // Close mobile sidebar first to prevent focus trap issues
    setMobileSidebarOpen(false)
    setTimeout(() => {
      setRenameProjectId(projectId)
      setShowRenameProjectModal(true)
    }, 100)
  }

  const handleRenameProject = async (projectId: string, newName: string) => {
    await updateProject(projectId, { name: newName })
    toast.success("Project renamed")
  }

  const handleCreateProject = async (project: Omit<Project, "id" | "createdAt">) => {
    const newProject: Project = {
      ...project,
      id: `project-${Date.now()}`,
      createdAt: new Date(),
    }
    await createProject(newProject)
    toast.success(`Project "${newProject.name}" created`)
  }

  const handleDeleteProject = async (projectId: string) => {
    await deleteProject(projectId)
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
      onRenameProject={handleOpenRenameProjectModal}
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
              onRenameProject={handleOpenRenameProjectModal}
            />
          </SheetContent>
        </Sheet>

        <LogoText height={28} />

        <UserAccountMenu />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden md:pt-0 pt-14">
        {!currentConversationId && !initialQuery ? (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex-1 h-full overflow-auto">
              <HomeScreen onNewChat={handleNewChat} onStartFromTemplate={handleStartFromTemplate} />
            </div>
          </div>
        ) : (
          <>
            <ChatArea
              conversation={currentConv}
              onSendMessage={handleSendMessage}
              onShowArtifact={(artifact) => {
                setCurrentArtifact(artifact)
                setShowArtifact(true)
              }}
              orchestratorSettings={orchestratorSettings}
              onOrchestratorSettingsChange={updateOrchestratorSettings}
              onOpenAdvancedSettings={() => setShowAdvancedSettings(true)}
              initialQuery={initialQuery}
              onInitialQueryProcessed={() => setInitialQuery(null)}
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

      {/* Rename Project Modal */}
      <RenameProjectModal
        open={showRenameProjectModal}
        onOpenChange={setShowRenameProjectModal}
        currentName={projects.find((p) => p.id === renameProjectId)?.name ?? ""}
        onRename={(newName) => {
          if (renameProjectId) {
            handleRenameProject(renameProjectId, newName)
          }
          setShowRenameProjectModal(false)
          setRenameProjectId(null)
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
