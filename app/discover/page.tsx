"use client"
import { useState } from "react"
import Image from "next/image"
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
} from "lucide-react"
import { Sidebar } from "@/components/sidebar"

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

// Knowledge base categories
const knowledgeCategories = [
  { id: "getting-started", label: "Getting Started", icon: Lightbulb, count: 12 },
  { id: "prompting-guides", label: "Prompting Guides", icon: PenTool, count: 24 },
  { id: "api-docs", label: "API Documentation", icon: Code, count: 18 },
  { id: "tutorials", label: "Video Tutorials", icon: Video, count: 8 },
  { id: "case-studies", label: "Case Studies", icon: BarChart, count: 15 },
]

// AI Templates
const aiTemplates = [
  { id: "email-writer", label: "Email Writer", description: "Professional email composition", icon: Mail },
  { id: "code-reviewer", label: "Code Reviewer", description: "Analyze and improve code quality", icon: Code },
  { id: "meeting-summary", label: "Meeting Summary", description: "Summarize meeting notes", icon: Users },
  { id: "content-creator", label: "Content Creator", description: "Generate blog posts and articles", icon: PenTool },
  { id: "data-analyst", label: "Data Analyst", description: "Analyze and visualize data", icon: BarChart },
  { id: "research-assistant", label: "Research Assistant", description: "Deep research and analysis", icon: Lightbulb },
]

type DrawerId = "web-search" | "knowledge-base" | "ai-templates" | null

export default function DiscoverPage() {
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

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar
        conversations={[]}
        currentConversationId={null}
        onNewChat={() => {}}
        onSelectConversation={() => {}}
        onDeleteConversation={() => {}}
        onTogglePin={() => {}}
        onRenameConversation={() => {}}
        onMoveToProject={() => {}}
        projects={[]}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onGoHome={() => (window.location.href = "/")}
      />

      <main className="flex-1 min-h-full flex flex-col items-center justify-start px-4 pt-8 md:pt-12 pb-20 overflow-y-auto">
        {/* Hero Section - identical structure to home page and orchestration */}
        <div className="text-center mb-0">
          {/* Logo Container - Same size as home page */}
          <div className="relative w-40 h-40 md:w-[280px] md:h-[280px] lg:w-[320px] lg:h-[320px] mx-auto mb-0">
            <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
          </div>
          <h1 className="-mt-6 md:-mt-8 lg:-mt-10 text-[1.75rem] md:text-[2.85rem] lg:text-[3.4rem] font-bold mb-1 bg-gradient-to-r from-[var(--bronze)] via-[var(--gold)] to-[var(--bronze)] bg-clip-text text-transparent">
            Discover
          </h1>
          {/* Subtitle */}
          <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto mb-0">
            Explore AI-powered search, knowledge resources, and templates
          </p>
        </div>

        {/* Separator Line - Same as Home Page */}
        <div className="w-16 h-px bg-border my-2" />

        {/* Cards Grid - matching home page template cards */}
        <div className="w-full max-w-4xl">
          <p className="text-sm text-muted-foreground text-center mb-2">Select a category to explore</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
            {discoverCards.map((card) => {
              const Icon = card.icon
              const count = getCount(card.id)
              return (
                <button
                  key={card.id}
                  onClick={() => setActiveDrawer(card.id as DrawerId)}
                  className="group relative p-4 md:p-5 rounded-xl border border-border bg-card hover:bg-secondary/50 transition-all duration-300 hover:border-[var(--bronze)]/50 hover:shadow-lg hover:shadow-[var(--bronze)]/5 text-left"
                >
                  {count > 0 && (
                    <Badge className="absolute top-2 right-2 bronze-gradient text-white text-xs px-1.5 py-0.5">
                      {count}
                    </Badge>
                  )}
                  <div
                    className={`w-10 h-10 md:w-12 md:h-12 rounded-lg bg-gradient-to-br ${card.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300`}
                  >
                    <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
                  </div>
                  <h3 className="font-semibold text-sm md:text-base mb-1 group-hover:text-[var(--bronze)] transition-colors">
                    {card.title}
                  </h3>
                  <p className="text-xs md:text-sm text-muted-foreground">{card.description}</p>
                </button>
              )
            })}
          </div>
        </div>
      </main>

      {/* Web Search Drawer */}
      <Sheet open={activeDrawer === "web-search"} onOpenChange={() => setActiveDrawer(null)}>
        <SheetContent className="w-[340px] sm:w-[400px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
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
                placeholder="Search the web..."
                className="pl-10 bg-secondary/50 border-border"
              />
            </div>
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">Popular searches</p>
              {["Latest AI news", "LLM benchmarks 2025", "Multi-agent systems", "RAG best practices"].map((query) => (
                <button
                  key={query}
                  onClick={() => setSearchQuery(query)}
                  className="w-full p-3 rounded-lg border border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50 transition-all text-left text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Search className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{query}</span>
                  </div>
                </button>
              ))}
            </div>
            <Button className="w-full mt-4 bronze-gradient hover:opacity-90">
              <Search className="h-4 w-4 mr-2" />
              Search
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Knowledge Base Drawer */}
      <Sheet open={activeDrawer === "knowledge-base"} onOpenChange={() => setActiveDrawer(null)}>
        <SheetContent className="w-[340px] sm:w-[400px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
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
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-2">
              {knowledgeCategories.map((category) => {
                const isSelected = selectedCategories.includes(category.id)
                const Icon = category.icon
                return (
                  <button
                    key={category.id}
                    onClick={() => toggleCategory(category.id)}
                    className={`w-full p-3 rounded-lg border transition-all text-left ${
                      isSelected
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
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
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        {category.count}
                      </Badge>
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* AI Templates Drawer */}
      <Sheet open={activeDrawer === "ai-templates"} onOpenChange={() => setActiveDrawer(null)}>
        <SheetContent className="w-[340px] sm:w-[400px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">AI Templates</SheetTitle>
                <p className="text-xs text-muted-foreground">{selectedTemplates.length} templates selected</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-2">
              {aiTemplates.map((template) => {
                const isSelected = selectedTemplates.includes(template.id)
                const Icon = template.icon
                return (
                  <button
                    key={template.id}
                    onClick={() => toggleTemplate(template.id)}
                    className={`w-full p-3 rounded-lg border transition-all text-left ${
                      isSelected
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isSelected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3 text-white" />}
                      </div>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <span className={`text-sm block ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                          {template.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{template.description}</span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  )
}
