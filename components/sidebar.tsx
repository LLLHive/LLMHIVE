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
  CreditCard,
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
import { CollaborationPanel } from "./collaboration-panel"

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
  onRenameProject?: (id: string) => void
  onTogglePinProject?: (id: string) => void
  onArchiveProject?: (id: string) => void
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
  onRenameProject,
  onTogglePinProject,
  onArchiveProject,
}: SidebarProps) {
  const pathname = usePathname()
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState<"chats" | "projects" | "discover" | null>("chats")
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [showAllProjects, setShowAllProjects] = useState(false)
  const [showAllChats, setShowAllChats] = useState(false)
  const [chatsExpanded, setChatsExpanded] = useState(true)
  const [collaborateExpanded, setCollaborateExpanded] = useState(false)

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
          "llmhive-glass-sidebar flex flex-col transition-all duration-300 relative h-full overflow-visible",
          collapsed ? "w-16" : "w-60",
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
              <LogoText height={40} className="-ml-2" />
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

            {/* Navigation Links */}
            <div className="px-3 pb-2 space-y-1">
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
                    className="pl-9 bg-transparent border-transparent hover:bg-secondary hover:border-border focus:bg-secondary focus:border-border transition-all duration-200"
                  />
                </div>
              </div>
            )}

            {/* Content - Scrollable container with extra right padding for 3-dot menu */}
            <div 
              className="flex-1 overflow-y-auto overflow-x-visible pl-2 pr-3 pb-4" 
              style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.3) transparent' }}
            >
              {/* Inner wrapper with relative positioning for dropdown portal */}
              <div className="relative">
              {/* Collaborate Section - Links to Settings/Collaboration */}
              <div className="py-2">
                <button
                  onClick={() => setCollaborateExpanded(!collaborateExpanded)}
                  className="flex items-center justify-between w-full px-2 py-1 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg"
                  aria-expanded={collaborateExpanded}
                  aria-label={collaborateExpanded ? "Collapse collaborate section" : "Expand collaborate section"}
                >
                  <span className="font-medium flex items-center gap-2">
                    <Users className="h-4 w-4 flex-shrink-0" />
                    Collaborate
                  </span>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <Clock className="h-3 w-3 text-muted-foreground" />
                    {collaborateExpanded ? (
                      <ChevronUp className="h-4 w-4 text-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-foreground" />
                    )}
                  </div>
                </button>
                
                {collaborateExpanded && (
                  <div className="mt-1">
                    <CollaborationPanel />
                  </div>
                )}
              </div>
              
              {/* Projects Section */}
              <div className="py-2 border-t border-border/50">
                <button
                  onClick={() => setActiveTab(activeTab === "projects" ? null : "projects")}
                  className="flex items-center justify-between w-full px-2 py-1 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg"
                  aria-expanded={activeTab === "projects"}
                  aria-label={activeTab === "projects" ? "Collapse projects section" : "Expand projects section"}
                >
                  <span className="font-medium">Projects</span>
                  {activeTab === "projects" ? (
                    <ChevronUp className="h-4 w-4 flex-shrink-0 text-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 flex-shrink-0 text-foreground" />
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
                          onRename={() => onRenameProject?.(project.id)}
                          onTogglePin={() => onTogglePinProject?.(project.id)}
                          onArchive={() => onArchiveProject?.(project.id)}
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
              
              {/* Chats Section */}
              <div className="py-2 border-t border-border/50">
                <button
                  onClick={() => setChatsExpanded(!chatsExpanded)}
                  className="flex items-center justify-between w-full px-2 py-1 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg"
                  aria-expanded={chatsExpanded}
                  aria-label={chatsExpanded ? "Collapse chats section" : "Expand chats section"}
                >
                  <span className="font-medium">Chats</span>
                  {chatsExpanded ? (
                    <ChevronUp className="h-4 w-4 flex-shrink-0 text-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 flex-shrink-0 text-foreground" />
                  )}
                </button>
                
                {chatsExpanded && (
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
                )}
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
              </div>{/* Close inner wrapper */}
            </div>{/* Close scrollable container */}
            
            {/* Settings at the bottom */}
            <div className="px-3 py-3 border-t border-border/50 mt-auto">
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
          </>
        )}

        {collapsed && (
          <div className="flex-1 flex flex-col items-center py-4">
            {/* Top section icons */}
            <div className="flex flex-col items-center gap-4">
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
              {/* Collapsed Collaborate - links to Settings */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link href={ROUTES.SETTINGS}>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="w-10 h-10 hover:text-[var(--bronze)]"
                      >
                        <Users className="h-5 w-5" />
                      </Button>
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">Collaborate (Coming Soon) - Go to Settings</TooltipContent>
                </Tooltip>
              </TooltipProvider>
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
            </div>
            
            {/* Spacer to push Settings to bottom */}
            <div className="flex-1" />
            
            {/* Settings at bottom */}
            <div className="border-t border-border/50 pt-4 flex flex-col gap-2">
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
  onRename,
  onTogglePin,
  onArchive,
  hasActiveChat,
}: {
  project: Project
  isExpanded: boolean
  onToggleExpand: () => void
  onSelect: () => void
  onDelete: () => void
  onRename?: () => void
  onTogglePin?: () => void
  onArchive?: () => void
  hasActiveChat?: boolean
}) {
  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-xl px-2 py-2 hover:bg-secondary cursor-pointer transition-all duration-200",
        (isExpanded || hasActiveChat) && "bg-secondary/50",
        // Ensure the rounded corners are not clipped
        "overflow-visible"
      )}
      onClick={onToggleExpand}
    >
      {isExpanded ? (
        <FolderOpen className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      ) : (
        <Folder className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      )}
      <span className="text-sm truncate flex-1 min-w-0">{project.name}</span>
      
      {/* Pin indicator */}
      {(project as any).pinned && (
        <Pin className="h-3 w-3 text-[var(--bronze)] flex-shrink-0" />
      )}
      
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={(e) => e.stopPropagation()}
            className="h-6 w-6 min-w-[24px] flex-shrink-0 rounded-md bg-secondary/50 opacity-100 hover:bg-secondary-foreground/20 focus:bg-secondary-foreground/20"
            aria-label="Project options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent 
          align="end" 
          side="bottom" 
          sideOffset={4} 
          className="w-52 p-1 z-[9999]"
          forceMount
        >
          <DropdownMenuItem
            onClick={() => { onSelect() }}
            className="cursor-pointer rounded-sm"
          >
            <FolderOpen className="h-4 w-4 mr-2" />
            Open project
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          {/* Rename */}
          <DropdownMenuItem
            onClick={() => { onRename?.() }}
            className="cursor-pointer rounded-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            Rename
          </DropdownMenuItem>
          
          {/* Move to Collaboration - Coming Soon */}
          <DropdownMenuItem
            className="cursor-pointer rounded-sm"
            disabled
          >
            <Users className="h-4 w-4 mr-2" />
            Move to Collaboration
            <span className="ml-auto text-xs text-muted-foreground">Soon</span>
          </DropdownMenuItem>
          
          {/* Pin/Unpin Project */}
          <DropdownMenuItem
            onClick={() => { onTogglePin?.() }}
            className="cursor-pointer rounded-sm"
          >
            {(project as any).pinned ? (
              <>
                <PinOff className="h-4 w-4 mr-2" />
                Unpin project
              </>
            ) : (
              <>
                <Pin className="h-4 w-4 mr-2" />
                Pin project
              </>
            )}
          </DropdownMenuItem>
          
          {/* Archive */}
          <DropdownMenuItem
            onClick={() => { onArchive?.() }}
            className="cursor-pointer rounded-sm"
          >
            <Archive className="h-4 w-4 mr-2" />
            Archive
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          {/* Delete */}
          <DropdownMenuItem
            onClick={() => { onDelete() }}
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
        "group relative flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-secondary cursor-pointer transition-all duration-200",
        // Active state: fully rounded pill with bronze accent border (not ring to avoid clipping)
        isActive && "bg-secondary/80 border border-[var(--bronze)]/40",
        !isActive && "border border-transparent",
        isNested && "py-1 text-[13px]"
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

      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={(e) => e.stopPropagation()}
            className="h-6 w-6 min-w-[24px] flex-shrink-0 rounded-md bg-secondary/50 opacity-100 hover:bg-secondary-foreground/20 focus:bg-secondary-foreground/20"
            aria-label="Chat options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent 
          align="end" 
          side="bottom"
          sideOffset={4}
          className="w-48 p-1 z-[9999]"
          forceMount
        >
          {/* Share option */}
          <DropdownMenuItem
            onClick={() => { onShare?.() }}
            className="cursor-pointer rounded-sm"
          >
            <Share className="h-4 w-4 mr-2" />
            Share
          </DropdownMenuItem>
          
          {/* Start a group chat - Coming soon */}
          <DropdownMenuItem
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
            onClick={() => { onRename() }}
            className="cursor-pointer rounded-sm"
          >
            <Pencil className="h-4 w-4 mr-2" />
            Rename
          </DropdownMenuItem>
          
          {/* Move to Project */}
          <DropdownMenuItem
            onClick={() => { onMoveToProject() }}
            className="cursor-pointer rounded-sm"
          >
            <FolderInput className="h-4 w-4 mr-2" />
            Move to project
          </DropdownMenuItem>
          
          {/* Pin/Unpin */}
          <DropdownMenuItem
            onClick={() => { onTogglePin() }}
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
            onClick={() => { onArchive?.() }}
            className="cursor-pointer rounded-sm"
          >
            <Archive className="h-4 w-4 mr-2" />
            Archive
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          {/* Delete - with destructive styling */}
          <DropdownMenuItem
            onClick={() => { onDelete() }}
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
