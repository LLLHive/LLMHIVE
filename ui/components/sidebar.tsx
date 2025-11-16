"use client"

import { useState } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog"
import { Plus, MessageSquare, Search, Settings, Sparkles, FolderOpen, Users, Pin, Trash2, MoreHorizontal, Globe, BookOpen, ChevronLeft, ChevronRight } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import type { Conversation, Project } from "@/lib/types"
import { cn } from "@/lib/utils"
import { ProjectsPanel } from "./projects-panel"
import { SettingsPanel } from "./settings-panel"
import { CollaborationPanel } from "./collaboration-panel"
import { MetricsPanel } from "./metrics-panel"

interface SidebarProps {
  conversations: Conversation[]
  currentConversationId: string | null
  onNewChat: () => void
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => void
  onTogglePin: (id: string) => void
}

export function Sidebar({
  conversations,
  currentConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onTogglePin,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState<"chats" | "projects" | "discover">("chats")
  const [projects, setProjects] = useState<Project[]>([])
  const [showSettings, setShowSettings] = useState(false)
  const [showCollaboration, setShowCollaboration] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const pinnedConversations = filteredConversations.filter((c) => c.pinned)
  const unpinnedConversations = filteredConversations.filter((c) => !c.pinned)

  const handleCreateProject = (projectData: Omit<Project, "id" | "createdAt">) => {
    const newProject: Project = {
      ...projectData,
      id: `proj-${Date.now()}`,
      createdAt: new Date(),
    }
    setProjects([newProject, ...projects])
  }

  const handleDeleteProject = (id: string) => {
    setProjects(projects.filter((p) => p.id !== id))
  }

  return (
    <>
      <aside
        className={cn(
          "border-r border-border bg-sidebar flex flex-col transition-all duration-300 relative",
          collapsed ? "w-16" : "w-[171px]", // Increased sidebar width by 3% from 166px to 171px
        )}
      >
        {/* Logo */}
        <div className="p-4 pb-2 border-b border-border flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center gap-3">
              <div className="relative w-[84px] h-[84px] -ml-1 -mt-1">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-orange-500 to-[var(--gold)] bg-clip-text text-transparent -ml-5 mt-2">
                LLMHive
              </span>
            </div>
          )}
          {collapsed && (
            <div className="relative w-[55px] h-[55px] mx-auto">
              <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
            </div>
          )}
        </div>

        {!collapsed && (
          <>
            {/* New Chat Button */}
            <div className="p-3 pt-2">
              <Button
                onClick={onNewChat}
                className="w-full justify-start gap-2 bronze-gradient hover:opacity-90 text-primary-foreground"
              >
                <Plus className="h-4 w-4" />
                New Chat
              </Button>
            </div>

            {/* Tabs */}
            <div className="px-3 pb-2 space-y-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveTab("chats")}
                className={cn(
                  "w-full justify-start text-sm transition-all",
                  activeTab === "chats" && "bg-secondary",
                  "hover:bronze-gradient hover:text-primary-foreground"
                )}
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Chats
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveTab("projects")}
                className={cn(
                  "w-full justify-start text-sm transition-all",
                  activeTab === "projects" && "bg-secondary",
                  "hover:bronze-gradient hover:text-primary-foreground"
                )}
              >
                <FolderOpen className="h-4 w-4 mr-2" />
                Projects
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveTab("discover")}
                className={cn(
                  "w-full justify-start text-sm transition-all",
                  activeTab === "discover" && "bg-secondary",
                  "hover:bronze-gradient hover:text-primary-foreground"
                )}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Discover
              </Button>
            </div>

            {/* Search */}
            {activeTab === "chats" && (
              <div className="px-3 pb-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search conversations..."
                    className="pl-9 bg-secondary border-border"
                  />
                </div>
              </div>
            )}

            {/* Content */}
            <ScrollArea className="flex-1 px-3">
              {activeTab === "chats" && (
                <div className="space-y-4">
                  {pinnedConversations.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-2 px-2">Pinned</div>
                      <div className="space-y-1">
                        {pinnedConversations.map((conv) => (
                          <ConversationItem
                            key={conv.id}
                            conversation={conv}
                            isActive={conv.id === currentConversationId}
                            onSelect={() => onSelectConversation(conv.id)}
                            onDelete={() => onDeleteConversation(conv.id)}
                            onTogglePin={() => onTogglePin(conv.id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {unpinnedConversations.length === 0 && pinnedConversations.length === 0 ? (
                    <div className="py-8 text-center text-sm text-muted-foreground">
                      No conversations yet
                      <br />
                      Start a new chat to begin
                    </div>
                  ) : (
                    <div>
                      {pinnedConversations.length > 0 && (
                        <div className="text-xs font-medium text-muted-foreground mb-2 px-2">Recent</div>
                      )}
                      <div className="space-y-1">
                        {unpinnedConversations.map((conv) => (
                          <ConversationItem
                            key={conv.id}
                            conversation={conv}
                            isActive={conv.id === currentConversationId}
                            onSelect={() => onSelectConversation(conv.id)}
                            onDelete={() => onDeleteConversation(conv.id)}
                            onTogglePin={() => onTogglePin(conv.id)}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "projects" && (
                <ProjectsPanel
                  projects={projects}
                  onCreateProject={handleCreateProject}
                  onDeleteProject={handleDeleteProject}
                  onSelectProject={(id) => console.log("Select project:", id)}
                />
              )}

              {activeTab === "discover" && (
                <div className="space-y-3 py-4">
                  <DiscoverCard
                    icon={Globe}
                    title="Web Search"
                    description="Search the web with AI assistance"
                    color="from-blue-500 to-cyan-500"
                  />
                  <DiscoverCard
                    icon={BookOpen}
                    title="Knowledge Base"
                    description="Explore curated AI prompts and guides"
                    color="from-purple-500 to-pink-500"
                  />
                  <DiscoverCard
                    icon={Sparkles}
                    title="AI Templates"
                    description="Pre-built prompts for common tasks"
                    color="from-orange-500 to-red-500"
                  />
                  <MetricsPanel />
                </div>
              )}
            </ScrollArea>

            {/* Bottom Section */}
            <div className="p-3 border-t border-border space-y-1">
              <Dialog open={showCollaboration} onOpenChange={setShowCollaboration}>
                <DialogTrigger asChild>
                  <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
                    <Users className="h-4 w-4" />
                    Collaborate
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl h-[600px] p-0">
                  <CollaborationPanel />
                </DialogContent>
              </Dialog>

              <Dialog open={showSettings} onOpenChange={setShowSettings}>
                <DialogTrigger asChild>
                  <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
                    <Settings className="h-4 w-4" />
                    Settings
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-3xl h-[700px] p-0">
                  <SettingsPanel />
                </DialogContent>
              </Dialog>
            </div>
          </>
        )}

        {collapsed && (
          <div className="flex-1 flex flex-col items-center gap-4 py-4">
            <Button variant="ghost" size="icon" onClick={onNewChat} className="w-10 h-10">
              <Plus className="h-5 w-5" />
            </Button>
            <Button
              variant={activeTab === "chats" ? "secondary" : "ghost"}
              size="icon"
              onClick={() => setActiveTab("chats")}
              className="w-10 h-10"
            >
              <MessageSquare className="h-5 w-5" />
            </Button>
            <Button
              variant={activeTab === "projects" ? "secondary" : "ghost"}
              size="icon"
              onClick={() => setActiveTab("projects")}
              className="w-10 h-10"
            >
              <FolderOpen className="h-5 w-5" />
            </Button>
            <Button
              variant={activeTab === "discover" ? "secondary" : "ghost"}
              size="icon"
              onClick={() => setActiveTab("discover")}
              className="w-10 h-10"
            >
              <Sparkles className="h-5 w-5" />
            </Button>
          </div>
        )}

        {/* Collapse Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-1/2 -translate-y-1/2 h-6 w-6 rounded-full border border-border bg-sidebar hover:bg-secondary shadow-md z-50"
        >
          {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </Button>
      </aside>
    </>
  )
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
  onTogglePin,
}: {
  conversation: Conversation
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onTogglePin: () => void
}) {
  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-secondary cursor-pointer transition-colors",
        isActive && "bg-secondary",
      )}
      onClick={onSelect}
    >
      <MessageSquare className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      <span className="text-sm truncate flex-1">{conversation.title}</span>

      <DropdownMenu>
        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
          <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity">
            <MoreHorizontal className="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onTogglePin()
            }}
          >
            <Pin className="h-4 w-4 mr-2" />
            {conversation.pinned ? "Unpin" : "Pin"}
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="text-destructive"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

function DiscoverCard({
  icon: Icon,
  title,
  description,
  color,
}: {
  icon: any
  title: string
  description: string
  color: string
}) {
  return (
    <div className="p-4 rounded-lg border border-border bg-card hover:border-[var(--bronze)] transition-colors cursor-pointer">
      <div className="flex items-start gap-3">
        <div className={cn("w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center", color)}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-sm mb-1">{title}</h4>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  )
}
