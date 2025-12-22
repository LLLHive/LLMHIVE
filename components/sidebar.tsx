"use client"

import { useState } from "react"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ROUTES } from "@/lib/routes"
import {
  Plus,
  MessageSquare,
  Search,
  Settings,
  Sparkles,
  FolderOpen,
  Users,
  Pin,
  Trash2,
  MoreHorizontal,
  Globe,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Pencil,
  FolderInput,
  Workflow,
  Clock,
  Boxes,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { Conversation, Project } from "@/lib/types"
import { cn } from "@/lib/utils"
import { ProjectsPanel } from "./projects-panel"
import { DiscoverCard } from "./discover-card"

interface SidebarProps {
  conversations: Conversation[]
  currentConversationId: string | null
  onNewChat: () => void
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => void
  onTogglePin: (id: string) => void
  onRenameConversation: (id: string) => void
  onMoveToProject: (conversationId: string) => void
  projects: Project[]
  collapsed: boolean
  onToggleCollapse: () => void
  onGoHome: () => void
  onCreateProject?: (project: Omit<Project, "id" | "createdAt">) => void
  onDeleteProject?: (id: string) => void
  onSelectProject?: (id: string) => void
}

export function Sidebar({
  conversations,
  currentConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onTogglePin,
  onRenameConversation,
  onMoveToProject,
  projects,
  collapsed,
  onToggleCollapse,
  onGoHome,
  onCreateProject,
  onDeleteProject,
  onSelectProject,
}: SidebarProps) {
  const pathname = usePathname()
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState<"chats" | "projects" | "discover" | null>("chats")
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)

  // Helper to check if a route is active
  const isActiveRoute = (route: string) => pathname === route

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const pinnedConversations = filteredConversations.filter((c) => c.pinned)
  const unpinnedConversations = filteredConversations.filter((c) => !c.pinned)

  const handleRename = (id: string) => {
    onRenameConversation(id)
  }

  const handleMoveToProjectClick = (id: string) => {
    onMoveToProject(id)
  }

  const handleTabChange = (tab: "chats" | "projects" | "discover") => {
    if (activeTab === tab) {
      setActiveTab(null)
    } else {
      setActiveTab(tab)
    }
  }

  return (
    <>
      <aside
        className={cn(
          "llmhive-glass-sidebar flex flex-col transition-all duration-300 relative h-full",
          collapsed ? "w-16" : "w-52",
        )}
      >
        {/* Logo */}
        <div className="p-4 pb-2 border-b border-border flex items-center justify-between">
          {!collapsed && (
            <button
              onClick={onGoHome}
              className="flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <div className="relative w-12 h-12">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
              </div>
              <LogoText height={35} />
            </button>
          )}
          {collapsed && (
            <button
              onClick={onGoHome}
              className="relative w-10 h-10 mx-auto cursor-pointer hover:opacity-80 transition-opacity"
            >
              <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
            </button>
          )}
        </div>

        {!collapsed && (
          <>
            {/* New Chat Button */}
            <div className="p-3 pt-2">
              <Button onClick={onNewChat} className="w-full justify-start gap-2 bronze-gradient hover:opacity-90">
                <Plus className="h-4 w-4" />
                New Chat
              </Button>
            </div>

            {/* Tabs */}
            <div className="px-3 pb-2 space-y-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleTabChange("chats")}
                className={cn(
                  "w-full justify-start text-sm transition-all",
                  activeTab === "chats" && "bg-secondary",
                  "hover:bg-[var(--bronze)]/20 hover:text-[var(--bronze)]",
                )}
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Chats
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleTabChange("projects")}
                className={cn(
                  "w-full justify-start text-sm transition-all",
                  activeTab === "projects" && "bg-secondary",
                  "hover:bg-[var(--bronze)]/20 hover:text-[var(--bronze)]",
                )}
              >
                <FolderOpen className="h-4 w-4 mr-2" />
                Projects
              </Button>
              <Link href={ROUTES.DISCOVER} className="w-full">
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "w-full justify-start text-sm transition-all",
                    isActiveRoute(ROUTES.DISCOVER) && "bg-secondary text-[var(--bronze)]",
                    "hover:bg-[var(--bronze)]/20 hover:text-[var(--bronze)]",
                  )}
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  Discover
                </Button>
              </Link>
              {/* Models / OpenRouter */}
              <Link href={ROUTES.MODELS} className="w-full">
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "w-full justify-start text-sm transition-all",
                    isActiveRoute(ROUTES.MODELS) && "bg-secondary text-[var(--bronze)]",
                    "hover:bg-[var(--bronze)]/20 hover:text-[var(--bronze)]",
                  )}
                >
                  <Boxes className="h-4 w-4 mr-2" />
                  Models
                </Button>
              </Link>
              {/* Collaborate - Coming Soon */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled
                      className="w-full justify-start text-sm opacity-50 cursor-not-allowed"
                    >
                      <Users className="h-4 w-4 mr-2" />
                      Collaborate
                      <Clock className="h-3 w-3 ml-auto text-muted-foreground" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Coming Soon</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              {/* Orchestration link */}
              <Link href={ROUTES.ORCHESTRATION} className="w-full">
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "w-full justify-start text-sm transition-all",
                    isActiveRoute(ROUTES.ORCHESTRATION) 
                      ? "bg-secondary text-[var(--bronze)]" 
                      : "text-[var(--bronze)]",
                    "hover:bg-[var(--bronze)]/20 hover:text-[var(--bronze)]",
                  )}
                >
                  <Workflow className="h-4 w-4 mr-2" />
                  Orchestration
                </Button>
              </Link>
              <Link href={ROUTES.SETTINGS} className="w-full">
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "w-full justify-start text-sm transition-all",
                    isActiveRoute(ROUTES.SETTINGS) && "bg-secondary text-[var(--bronze)]",
                    "hover:bg-[var(--bronze)]/20 hover:text-[var(--bronze)]",
                  )}
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Settings
                </Button>
              </Link>
            </div>

            {/* Search */}
            {activeTab === "chats" && (
              <div className="px-3 pb-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search chats..."
                    className="pl-9 bg-secondary border-border"
                  />
                </div>
              </div>
            )}

            {/* Content */}
            <ScrollArea className="px-3 h-[180px]">
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
                            onRename={() => handleRename(conv.id)}
                            onMoveToProject={() => handleMoveToProjectClick(conv.id)}
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
                            onRename={() => handleRename(conv.id)}
                            onMoveToProject={() => handleMoveToProjectClick(conv.id)}
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
                  onCreateProject={onCreateProject ?? (() => {})}
                  onDeleteProject={onDeleteProject ?? (() => {})}
                  onSelectProject={onSelectProject ?? (() => {})}
                />
              )}

              {activeTab === "discover" && (
                <div className="space-y-3 py-4">
                  <DiscoverCard
                    icon={Globe}
                    title="Web Search"
                    description="Search the web with AI"
                    color="from-blue-500 to-cyan-500"
                  />
                  <DiscoverCard
                    icon={BookOpen}
                    title="Knowledge Base"
                    description="Explore AI prompts and guides"
                    color="from-purple-500 to-pink-500"
                  />
                  <DiscoverCard
                    icon={Sparkles}
                    title="AI Templates"
                    description="Pre-built prompts"
                    color="from-orange-500 to-red-500"
                  />
                </div>
              )}
            </ScrollArea>
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
              onClick={() => handleTabChange("chats")}
              className="w-10 h-10"
            >
              <MessageSquare className="h-5 w-5" />
            </Button>
            <Button
              variant={activeTab === "projects" ? "secondary" : "ghost"}
              size="icon"
              onClick={() => handleTabChange("projects")}
              className="w-10 h-10"
            >
              <FolderOpen className="h-5 w-5" />
            </Button>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={ROUTES.DISCOVER}>
                    <Button 
                      variant={isActiveRoute(ROUTES.DISCOVER) ? "secondary" : "ghost"} 
                      size="icon" 
                      className={cn("w-10 h-10", isActiveRoute(ROUTES.DISCOVER) && "text-[var(--bronze)]")}
                    >
                      <Sparkles className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">Discover</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {/* Collapsed Models icon */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={ROUTES.MODELS}>
                    <Button 
                      variant={isActiveRoute(ROUTES.MODELS) ? "secondary" : "ghost"} 
                      size="icon" 
                      className={cn("w-10 h-10", isActiveRoute(ROUTES.MODELS) && "text-[var(--bronze)]")}
                    >
                      <Boxes className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">Models</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {/* Collapsed Orchestration icon */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={ROUTES.ORCHESTRATION}>
                    <Button 
                      variant={isActiveRoute(ROUTES.ORCHESTRATION) ? "secondary" : "ghost"} 
                      size="icon" 
                      className={cn("w-10 h-10 text-[var(--bronze)]")}
                    >
                      <Workflow className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">Orchestration</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={ROUTES.SETTINGS}>
                    <Button 
                      variant={isActiveRoute(ROUTES.SETTINGS) ? "secondary" : "ghost"} 
                      size="icon" 
                      className={cn("w-10 h-10", isActiveRoute(ROUTES.SETTINGS) && "text-[var(--bronze)]")}
                    >
                      <Settings className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">Settings</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* Collapse Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
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
  onRename,
  onMoveToProject,
}: {
  conversation: Conversation
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onTogglePin: () => void
  onRename: () => void
  onMoveToProject: () => void
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
              onRename()
            }}
          >
            <Pencil className="h-4 w-4 mr-2" />
            Rename
          </DropdownMenuItem>
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
              onMoveToProject()
            }}
          >
            <FolderInput className="h-4 w-4 mr-2" />
            Move to Project...
          </DropdownMenuItem>
          <DropdownMenuSeparator />
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
