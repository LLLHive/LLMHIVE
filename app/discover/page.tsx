"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Globe,
  BookOpen,
  Sparkles,
  Search,
  Video,
  Code,
  Lightbulb,
  PenTool,
  BarChart,
  Mail,
  Users,
  Check,
  ArrowRight,
  ExternalLink,
} from "lucide-react"
import { Sidebar } from "@/components/sidebar"
import { UserAccountMenu } from "@/components/user-account-menu"
import { ROUTES } from "@/lib/routes"
import { useAuth } from "@/lib/auth-context"
import { useConversationsContext } from "@/lib/conversations-context"
import { toast } from "@/lib/toast"

// Card data matching home page template card style
const discoverCards = [
  {
    id: "web-search",
    title: "Web Search",
    description: "Search the web with AI-powered intelligence",
    icon: Globe,
    color: "from-blue-500 to-cyan-500",
  },
  {
    id: "knowledge-base",
    title: "Knowledge Base",
    description: "Explore AI prompts, guides and documentation",
    icon: BookOpen,
    color: "from-purple-500 to-pink-500",
  },
  {
    id: "ai-templates",
    title: "AI Templates",
    description: "Pre-built prompts for common tasks",
    icon: Sparkles,
    color: "from-orange-500 to-red-500",
  },
]

// Knowledge base categories with actual content/URLs
const knowledgeCategories = [
  { 
    id: "getting-started", 
    label: "Getting Started", 
    icon: Lightbulb, 
    count: 12,
    prompt: "Help me get started with LLMHive. What are the key features and how do I use them effectively?"
  },
  { 
    id: "prompting-guides", 
    label: "Prompting Guides", 
    icon: PenTool, 
    count: 24,
    prompt: "Teach me advanced prompting techniques. How can I write better prompts to get more accurate and useful responses?"
  },
  { 
    id: "api-docs", 
    label: "API Documentation", 
    icon: Code, 
    count: 18,
    prompt: "Explain the LLMHive API. What endpoints are available and how do I integrate with external applications?"
  },
  { 
    id: "tutorials", 
    label: "Video Tutorials", 
    icon: Video, 
    count: 8,
    prompt: "Guide me through a step-by-step tutorial on using LLMHive's multi-agent orchestration features."
  },
  { 
    id: "case-studies", 
    label: "Case Studies", 
    icon: BarChart, 
    count: 15,
    prompt: "Show me real-world case studies of how LLMHive has been used to solve complex problems in enterprise settings."
  },
]

// AI Templates with actual prompt content
const aiTemplates = [
  { 
    id: "email-writer", 
    label: "Email Writer", 
    description: "Professional email composition", 
    icon: Mail,
    prompt: "You are an expert professional email writer. Help me compose a clear, professional email. I'll describe the situation and recipient, and you'll craft the perfect email with appropriate tone, structure, and call-to-action. What email would you like me to help you write?"
  },
  { 
    id: "code-reviewer", 
    label: "Code Reviewer", 
    description: "Analyze and improve code quality", 
    icon: Code,
    prompt: "You are an expert senior software engineer and code reviewer. Analyze code for bugs, security vulnerabilities, performance issues, and adherence to best practices. Provide specific, actionable feedback with examples. Share the code you'd like me to review."
  },
  { 
    id: "meeting-summary", 
    label: "Meeting Summary", 
    description: "Summarize meeting notes", 
    icon: Users,
    prompt: "You are an expert at creating clear, actionable meeting summaries. Extract key decisions, action items with owners and deadlines, and important discussion points. Format the summary for easy scanning. Paste your meeting notes and I'll create a structured summary."
  },
  { 
    id: "content-creator", 
    label: "Content Creator", 
    description: "Generate blog posts and articles", 
    icon: PenTool,
    prompt: "You are an expert content strategist and writer. Help create engaging, SEO-optimized blog posts, articles, and marketing content. I'll maintain your brand voice while maximizing readability and impact. What topic would you like me to write about?"
  },
  { 
    id: "data-analyst", 
    label: "Data Analyst", 
    description: "Analyze and visualize data", 
    icon: BarChart,
    prompt: "You are an expert data analyst. Help analyze data, identify trends and patterns, suggest visualizations, and provide actionable insights. I can work with CSV data, describe statistical findings, and recommend next steps. Share your data or describe what you'd like to analyze."
  },
  { 
    id: "research-assistant", 
    label: "Research Assistant", 
    description: "Deep research and analysis", 
    icon: Lightbulb,
    prompt: "You are an expert research assistant with deep knowledge across multiple domains. Help conduct thorough research on any topic, synthesize information from multiple perspectives, and provide well-cited, comprehensive analysis. What topic would you like me to research?"
  },
]

type DrawerId = "web-search" | "knowledge-base" | "ai-templates" | null

export default function DiscoverPage() {
  const router = useRouter()
  const auth = useAuth()
  const { conversations, projects, deleteConversation, updateConversation } = useConversationsContext()
  const [activeDrawer, setActiveDrawer] = useState<DrawerId>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([])

  const toggleCategory = (id: string) => {
    setSelectedCategories((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]))
  }

  const toggleTemplate = (id: string) => {
    setSelectedTemplates((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]))
  }

  const getCount = (id: string) => {
    switch (id) {
      case "knowledge-base":
        return selectedCategories.length
      case "ai-templates":
        return selectedTemplates.length
      default:
        return 0
    }
  }

  // Handle web search - navigate to home with query
  const handleWebSearch = () => {
    if (!searchQuery.trim()) {
      toast.error("Please enter a search query")
      return
    }
    // Navigate to home page with the search query pre-filled
    // The query will be passed as a URL parameter and auto-submitted
    const encodedQuery = encodeURIComponent(`Search the web for: ${searchQuery}`)
    router.push(`${ROUTES.HOME}?q=${encodedQuery}`)
    setActiveDrawer(null)
    toast.success("Starting AI-powered web search...")
  }

  // Handle knowledge base category - use the category's prompt
  const handleExploreKnowledge = (categoryId: string) => {
    const category = knowledgeCategories.find(c => c.id === categoryId)
    if (!category) return
    
    const encodedQuery = encodeURIComponent(category.prompt)
    router.push(`${ROUTES.HOME}?q=${encodedQuery}`)
    setActiveDrawer(null)
    toast.success(`Loading ${category.label}...`)
  }

  // Handle AI template - use the template's prompt
  const handleUseTemplate = (templateId: string) => {
    const template = aiTemplates.find(t => t.id === templateId)
    if (!template) return
    
    const encodedQuery = encodeURIComponent(template.prompt)
    router.push(`${ROUTES.HOME}?q=${encodedQuery}`)
    setActiveDrawer(null)
    toast.success(`Starting ${template.label} session...`)
  }

  // Handle exploring all selected categories
  const handleExploreAllSelected = () => {
    if (selectedCategories.length === 0) {
      toast.error("Please select at least one category")
      return
    }
    
    const selectedLabels = selectedCategories
      .map(id => knowledgeCategories.find(c => c.id === id)?.label)
      .filter(Boolean)
      .join(", ")
    
    const combinedPrompt = `Help me explore these knowledge areas: ${selectedLabels}. Provide an overview of each topic and how they relate to using LLMHive effectively.`
    const encodedQuery = encodeURIComponent(combinedPrompt)
    router.push(`${ROUTES.HOME}?q=${encodedQuery}`)
    setActiveDrawer(null)
    toast.success("Exploring selected topics...")
  }

  return (
    <div className="flex h-screen overflow-hidden relative">
      {/* Sign In Button - Top Right (fixed position) */}
      <div className="hidden md:block fixed top-3 right-3 z-50">
        <UserAccountMenu />
      </div>

      {/* Glassmorphism Sidebar */}
      <div className="llmhive-glass-sidebar h-full">
      <Sidebar
        conversations={conversations}
        currentConversationId={null}
        onNewChat={() => router.push(ROUTES.HOME)}
        onSelectConversation={(id) => router.push(`${ROUTES.HOME}?chat=${id}`)}
        onDeleteConversation={(id) => deleteConversation(id)}
        onTogglePin={(id) => {
          const conv = conversations.find(c => c.id === id)
          if (conv) updateConversation(id, { pinned: !conv.pinned })
        }}
        onRenameConversation={() => {}}
        onMoveToProject={() => {}}
        projects={projects}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onGoHome={() => router.push(ROUTES.HOME)}
      />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Main Content in scrollable container */}
        <div className="flex-1 h-full overflow-auto">
          <div className="min-h-full flex flex-col items-center justify-start px-4 pt-4 pb-20">
            {/* Hero Section with 3D Logo */}
            <div className="text-center mb-6 llmhive-fade-in">
              <div className="relative w-52 h-52 md:w-[340px] md:h-[340px] lg:w-[378px] lg:h-[378px] mx-auto -mb-14 md:-mb-24 llmhive-float">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain drop-shadow-2xl" priority />
              </div>
              <LogoText height={64} className="md:hidden mb-2 mx-auto" />
              <LogoText height={92} className="hidden md:block lg:hidden mb-2 mx-auto" />
              <LogoText height={110} className="hidden lg:block mb-2 mx-auto" />
              <h2 className="text-xl md:text-2xl lg:text-3xl llmhive-subtitle mb-2">
                Discover
              </h2>
              <p className="llmhive-subtitle-3d text-sm md:text-base mx-auto whitespace-nowrap">
                Explore AI-powered search, knowledge resources, and templates
              </p>
            </div>

            {/* Cards Grid - Glassmorphism Style */}
            <div className="w-full max-w-4xl llmhive-fade-in" style={{ animationDelay: '0.1s' }}>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
                {discoverCards.map((card, index) => {
                  const Icon = card.icon
                  const count = getCount(card.id)
                  const badgeClasses: Record<string, string> = {
                    "web-search": "icon-badge-blue",
                    "knowledge-base": "icon-badge-purple",
                    "ai-templates": "icon-badge-orange",
                  }
                  return (
                    <button
                      key={card.id}
                      onClick={() => setActiveDrawer(card.id as DrawerId)}
                      className="settings-card group llmhive-fade-in"
                      style={{ animationDelay: `${0.15 + index * 0.05}s` }}
                    >
                      {count > 0 && (
                        <Badge className="absolute top-2 right-2 bronze-gradient text-black text-xs px-1.5 py-0.5 font-semibold">
                          {count}
                        </Badge>
                      )}
                      {/* Icon Badge */}
                      <div className={`icon-badge ${badgeClasses[card.id] || 'icon-badge-blue'}`}>
                        <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
                      </div>
                      {/* Card Text */}
                      <div className="space-y-0.5 text-center">
                        <h3 className="font-semibold text-sm md:text-base text-foreground group-hover:text-[var(--gold)] transition-colors">
                          {card.title}
                        </h3>
                        <p className="text-xs text-muted-foreground leading-tight">{card.description}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Web Search Drawer */}
      <Sheet open={activeDrawer === "web-search"} onOpenChange={() => setActiveDrawer(null)}>
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Globe className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Web Search</SheetTitle>
                <p className="text-xs text-muted-foreground">AI-powered web search</p>
              </div>
            </div>
          </SheetHeader>
          <div className="p-4">
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleWebSearch()
                  }
                }}
                placeholder="Search the web..."
                className="pl-10 bg-secondary/50 border-border"
              />
            </div>
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">Popular searches</p>
              {["Latest AI news", "LLM benchmarks 2025", "Multi-agent systems", "RAG best practices"].map((query) => (
                <button
                  key={query}
                  onClick={() => {
                    setSearchQuery(query)
                    // Auto-search when clicking a suggestion
                    const encodedQuery = encodeURIComponent(`Search the web for: ${query}`)
                    router.push(`${ROUTES.HOME}?q=${encodedQuery}`)
                    setActiveDrawer(null)
                    toast.success("Starting AI-powered web search...")
                  }}
                  className="w-full p-3 rounded-lg border border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50 transition-all text-left text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Search className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{query}</span>
                  </div>
                </button>
              ))}
            </div>
            <Button 
              onClick={handleWebSearch}
              disabled={!searchQuery.trim()}
              className="w-full mt-4 bronze-gradient hover:opacity-90 disabled:opacity-50"
            >
              <Search className="h-4 w-4 mr-2" />
              Search
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Knowledge Base Drawer */}
      <Sheet open={activeDrawer === "knowledge-base"} onOpenChange={() => setActiveDrawer(null)}>
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0 flex flex-col">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Knowledge Base</SheetTitle>
                <p className="text-xs text-muted-foreground">{selectedCategories.length} categories selected</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-2">
              {knowledgeCategories.map((category) => {
                const isSelected = selectedCategories.includes(category.id)
                const Icon = category.icon
                return (
                  <div
                    key={category.id}
                    className={`w-full p-3 rounded-lg border transition-all ${
                      isSelected
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => toggleCategory(category.id)}
                        className="flex items-center gap-3 flex-1 text-left"
                      >
                        <div
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                            isSelected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                          }`}
                        >
                          {isSelected && <Check className="h-3 w-3 text-white" />}
                        </div>
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className={`text-sm block ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                          {category.label}
                        </span>
                      </button>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {category.count}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleExploreKnowledge(category.id)}
                          title={`Explore ${category.label}`}
                        >
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
          {/* Explore Selected Button */}
          <div className="p-4 border-t border-border">
            <Button 
              onClick={handleExploreAllSelected}
              disabled={selectedCategories.length === 0}
              className="w-full bronze-gradient hover:opacity-90 disabled:opacity-50"
            >
              <BookOpen className="h-4 w-4 mr-2" />
              {selectedCategories.length > 0 
                ? `Explore ${selectedCategories.length} Topic${selectedCategories.length > 1 ? 's' : ''}`
                : 'Select Topics to Explore'
              }
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* AI Templates Drawer */}
      <Sheet open={activeDrawer === "ai-templates"} onOpenChange={() => setActiveDrawer(null)}>
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0 flex flex-col">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">AI Templates</SheetTitle>
                <p className="text-xs text-muted-foreground">Click to use a template</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-2">
              {aiTemplates.map((template) => {
                const Icon = template.icon
                return (
                  <button
                    key={template.id}
                    onClick={() => handleUseTemplate(template.id)}
                    className="w-full p-3 rounded-lg border transition-all text-left border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50 group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center group-hover:from-orange-500/30 group-hover:to-red-500/30 transition-all">
                        <Icon className="h-4 w-4 text-orange-500" />
                      </div>
                      <div className="flex-1">
                        <span className="text-sm block font-medium group-hover:text-[var(--gold)] transition-colors">
                          {template.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{template.description}</span>
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-[var(--bronze)] transition-colors" />
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
          <div className="p-4 border-t border-border">
            <p className="text-xs text-muted-foreground text-center">
              Templates start a new chat with expert AI assistance
            </p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
