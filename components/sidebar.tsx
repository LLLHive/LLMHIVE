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
  Folder,
  FolderPlus,
  Users,
  Pin,
  PinOff,
  Trash2,
  MoreHorizontal,
  Globe,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Pencil,
  FolderInput,
  Workflow,
  Clock,
  Boxes,
  Share,
  Archive,
  UserPlus,
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
  onShareConversation?: (id: string) => void
  onArchiveConversation?: (id: string) => void
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
  onShareConversation,
  onArchiveConversation,
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
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [showAllProjects, setShowAllProjects] = useState(false)
  const [showAllChats, setShowAllChats] = useState(false)

  // Helper to check if a route is active
  const isActiveRoute = (route: string) => pathname === route

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const pinnedConversations = filteredConversations.filter((c) => c.pinned)
  const unpinnedConversations = filteredConversations.filter((c) => !c.pinned)
  
  // Get conversations that are in a project
  const projectConversationIds = new Set(projects.flatMap(p => p.conversations))
  
  // Standalone chats (not in any project)
  const standaloneChats = filteredConversations.filter(c => !projectConversationIds.has(c.id))
  
  // Get conversations for a specific project
  const getProjectConversations = (projectId: string) => {
    const project = projects.find(p => p.id === projectId)
    if (!project) return []
    return conversations.filter(c => project.conversations.includes(c.id))
  }
  
  // Toggle project expansion
  const toggleProjectExpand = (projectId: string) => {
    setExpandedProjects(prev => {
      const next = new Set(prev)
      if (next.has(projectId)) {
        next.delete(projectId)
      } else {
        next.add(projectId)
      }
      return next
    })
  }
  
  // Visible projects (limited unless "See more" is clicked)
  const visibleProjects = showAllProjects ? projects : projects.slice(0, 5)
  
  // Visible standalone chats (limited unless "See All" is clicked)
  const visibleStandaloneChats = showAllChats ? standaloneChats : standaloneChats.slice(0, 5)

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
              className="flex items-center gap-0 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <div className="relative w-12 h-12">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
              </div>
              <LogoText height={35} className="-ml-1" />
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

            {/* Content - ChatGPT Style Layout */}
            <ScrollArea className="flex-1 px-3">
              {/* Projects Section */}
              <div className="py-2">
                <button
                  onClick={() => setActiveTab(activeTab === "projects" ? null : "projects")}
                  className="flex items-center justify-between w-full px-2 py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span className="font-medium">Projects</span>
                  {activeTab === "projects" ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
                
                {activeTab === "projects" && (
                  <div className="mt-1 space-y-0.5">
                    {/* New Project Button */}
                    <button
                      onClick={() => onCreateProject?.({
                        name: "New Project",
                        description: "",
                        conversations: [],
                        files: [],
                      })}
                      className="flex items-center gap-2 w-full px-2 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors"
                    >
                      <FolderPlus className="h-4 w-4" />
                      New project
                    </button>
                    
                    {/* Project List */}
                    {visibleProjects.map((project) => (
                      <div key={project.id}>
                        <ProjectItem
                          project={project}
                          isExpanded={expandedProjects.has(project.id)}
                          onToggleExpand={() => toggleProjectExpand(project.id)}
                          onSelect={() => onSelectProject?.(project.id)}
                          onDelete={() => onDeleteProject?.(project.id)}
                          hasActiveChat={getProjectConversations(project.id).some(c => c.id === currentConversationId)}
                        />
                        
                        {/* Nested Chats */}
                        {expandedProjects.has(project.id) && (
                          <div className="ml-4 border-l border-border/50 pl-2 space-y-0.5">
                            {getProjectConversations(project.id).map((conv) => (
                              <ConversationItem
                                key={conv.id}
                                conversation={conv}
                                isActive={conv.id === currentConversationId}
                                onSelect={() => onSelectConversation(conv.id)}
                                onDelete={() => onDeleteConversation(conv.id)}
                                onTogglePin={() => onTogglePin(conv.id)}
                                onRename={() => handleRename(conv.id)}
                                onMoveToProject={() => handleMoveToProjectClick(conv.id)}
                                onShare={() => onShareConversation?.(conv.id)}
                                onArchive={() => onArchiveConversation?.(conv.id)}
                                isNested
                              />
                            ))}
                            {getProjectConversations(project.id).length === 0 && (
                              <div className="text-xs text-muted-foreground py-2 px-2">
                                No chats in this project
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {/* See more link */}
                    {projects.length > 5 && (
                      <button
                        onClick={() => setShowAllProjects(!showAllProjects)}
                        className="flex items-center gap-2 w-full px-2 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                        {showAllProjects ? "Show less" : "See more"}
                      </button>
                    )}
                  </div>
                )}
              </div>
              
              {/* Your Chats Section */}
              <div className="py-2 border-t border-border/50">
                <div className="px-2 py-1 text-sm font-medium text-muted-foreground">
                  Your chats
                </div>
                
                <div className="mt-1 space-y-0.5">
                  {visibleStandaloneChats.length === 0 ? (
                    <div className="py-4 text-center text-sm text-muted-foreground">
                      No chats yet. Start a new chat!
                    </div>
                  ) : (
                    <>
                      {visibleStandaloneChats.map((conv) => (
                        <ConversationItem
                          key={conv.id}
                          conversation={conv}
                          isActive={conv.id === currentConversationId}
                          onSelect={() => onSelectConversation(conv.id)}
                          onDelete={() => onDeleteConversation(conv.id)}
                          onTogglePin={() => onTogglePin(conv.id)}
                          onRename={() => handleRename(conv.id)}
                          onMoveToProject={() => handleMoveToProjectClick(conv.id)}
                          onShare={() => onShareConversation?.(conv.id)}
                          onArchive={() => onArchiveConversation?.(conv.id)}
                        />
                      ))}
                      
                      {/* See All link */}
                      {standaloneChats.length > 5 && (
                        <button
                          onClick={() => setShowAllChats(!showAllChats)}
                          className="flex items-center gap-2 w-full px-2 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {showAllChats ? "Show less" : "See All"}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>

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

function ProjectItem({
  project,
  isExpanded,
  onToggleExpand,
  onSelect,
  onDelete,
  hasActiveChat,
}: {
  project: Project
  isExpanded: boolean
  onToggleExpand: () => void
  onSelect: () => void
  onDelete: () => void
  hasActiveChat?: boolean
}) {
  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-secondary cursor-pointer transition-all duration-200 overflow-hidden",
        (isExpanded || hasActiveChat) && "bg-secondary/50",
      )}
      onClick={onToggleExpand}
    >
      {isExpanded ? (
        <FolderOpen className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      ) : (
        <Folder className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      )}
      <span className="text-sm truncate flex-1 min-w-0">{project.name}</span>
      
      <DropdownMenu>
        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
          <Button 
            variant="ghost" 
            size="icon" 
            className={cn(
              "h-6 w-6 min-w-6 flex-shrink-0 rounded-md transition-all duration-200",
              "opacity-0 group-hover:opacity-100",
              "hover:bg-secondary-foreground/10",
              "focus:opacity-100"
            )}
            aria-label="Project options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="right" sideOffset={8} className="w-48 p-1">
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onSelect()
            }}
            className="cursor-pointer rounded-sm"
          >
            <FolderOpen className="h-4 w-4 mr-2" />
            Open project
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="text-destructive cursor-pointer rounded-sm"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete project
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
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
  onShare,
  onArchive,
  onStartGroupChat,
  isNested = false,
}: {
  conversation: Conversation
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onTogglePin: () => void
  onRename: () => void
  onMoveToProject: () => void
  onShare?: () => void
  onArchive?: () => void
  onStartGroupChat?: () => void
  isNested?: boolean
}) {
  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-secondary cursor-pointer transition-all duration-200 overflow-hidden",
        isActive && "bg-secondary ring-1 ring-[var(--bronze)]/30",
        isNested && "py-1 text-[13px]",
      )}
      onClick={onSelect}
    >
      {!isNested && (
        <MessageSquare className={cn(
          "h-4 w-4 flex-shrink-0 transition-colors",
          isActive ? "text-[var(--bronze)]" : "text-muted-foreground"
        )} />
      )}
      <span className={cn(
        "truncate flex-1 min-w-0",
        isNested ? "text-[13px]" : "text-sm"
      )}>{conversation.title}</span>
      
      {/* Pin indicator */}
      {conversation.pinned && !isNested && (
        <Pin className="h-3 w-3 text-[var(--bronze)] flex-shrink-0" />
      )}

      <DropdownMenu>
        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
          <Button 
            variant="ghost" 
            size="icon" 
            className={cn(
              "h-6 w-6 min-w-6 flex-shrink-0 rounded-md transition-all duration-200",
              "bg-[var(--bronze)]/20 hover:bg-[var(--bronze)]/40",
              "text-[var(--bronze)]",
              "focus:ring-1 focus:ring-[var(--bronze)]/50"
            )}
            aria-label="Chat options"
          >
            <MoreHorizontal className="h-4 w-4 text-current" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent 
          align="end" 
          side="right"
          sideOffset={8}
          className="w-48 p-1"
        >
          {/* Share option */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onShare?.()
            }}
            className="cursor-pointer rounded-sm"
          >
            <Share className="h-4 w-4 mr-2" />
            Share
          </DropdownMenuItem>
          
          {/* Start a group chat - Coming soon */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onStartGroupChat?.()
            }}
            className="cursor-pointer rounded-sm"
            disabled
          >
            <UserPlus className="h-4 w-4 mr-2" />
            Start a group chat
            <span className="ml-auto text-xs text-muted-foreground">Soon</span>
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          {/* Rename */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onRename()
            }}
            className="cursor-pointer rounded-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            Rename
          </DropdownMenuItem>
          
          {/* Move to Project */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onMoveToProject()
            }}
            className="cursor-pointer rounded-sm"
          >
            <FolderInput className="h-4 w-4 mr-2" />
            Move to project
          </DropdownMenuItem>
          
          {/* Pin/Unpin */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onTogglePin()
            }}
            className="cursor-pointer rounded-sm"
          >
            {conversation.pinned ? (
              <>
                <PinOff className="h-4 w-4 mr-2" />
                Unpin chat
              </>
            ) : (
              <>
                <Pin className="h-4 w-4 mr-2" />
                Pin chat
              </>
            )}
          </DropdownMenuItem>
          
          {/* Archive */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onArchive?.()
            }}
            className="cursor-pointer rounded-sm"
          >
            <Archive className="h-4 w-4 mr-2" />
            Archive
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          {/* Delete - with destructive styling */}
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="cursor-pointer rounded-sm text-destructive focus:text-destructive focus:bg-destructive/10"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
