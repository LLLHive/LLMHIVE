"use client"

import { useState, useEffect } from "react"
import type React from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent, DropdownMenuSeparator, DropdownMenuLabel } from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, Zap, Brain, Rocket, Users, User, Settings2, Cpu, Sparkles, Check, Wrench, ArrowLeft, BarChart3, TrendingUp, DollarSign, Code, PieChart, MessageSquare, Image as ImageIcon, Wrench as ToolIcon, Languages, Clock, ChevronRight, Crown, Lock, FlaskConical, Heart, Scale, Megaphone, Search, Landmark, GraduationCap, Loader2, ListTree, List, ListOrdered, LayoutGrid } from "lucide-react"
import type {
  ReasoningMode,
  DomainPack,
  OrchestratorSettings,
  AdvancedReasoningMethod,
  AdvancedFeature,
} from "@/lib/types"
import { getModelLogo } from "@/lib/models"
import { CriteriaEqualizer } from "./criteria-equalizer"
import { AdvancedSettingsDropdown } from "./advanced-settings-dropdown"
import Image from "next/image"
import type { OpenRouterModel } from "@/lib/openrouter/types"
import { canAccessModel, getTierBadgeColor, getTierDisplayName, getModelRequiredTier, STORAGE_KEYS, type SelectedModelConfig } from "@/lib/openrouter/tiers"
import { useUserTier } from "@/lib/hooks/use-user-tier"
import { cn } from "@/lib/utils"
import { 
  useOpenRouterCategories, 
  useCategoryRankings, 
  CATEGORY_ICON_MAP,
  CATEGORY_COLOR_MAP,
  type CategoryWithIcon,
} from "@/hooks/use-openrouter-categories"
import type { OpenRouterRankingEntry } from "@/lib/openrouter/api"

interface ChatToolbarProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
  onOpenAdvanced?: () => void  // Optional - kept for backwards compatibility
}

// Category icon resolver using Lucide components
const CATEGORY_ICONS: Record<string, React.ElementType> = {
  'programming': Code,
  'science': FlaskConical,
  'health': Heart,
  'legal': Scale,
  'marketing': Megaphone,
  'marketing/seo': Search,
  'marketing/content': MessageSquare,
  'marketing/social-media': Users,
  'technology': Cpu,
  'finance': Landmark,
  'academia': GraduationCap,
  'roleplay': Users,
  'creative-writing': MessageSquare,
  'customer-support': Users,
  'translation': Languages,
  'data-analysis': BarChart3,
  'long-context': MessageSquare,
  'tool-use': ToolIcon,
  'vision': ImageIcon,
  'reasoning': FlaskConical,
}

function getCategoryIcon(slug: string): React.ElementType {
  return CATEGORY_ICONS[slug] || BarChart3
}

const reasoningModes: { value: ReasoningMode; label: string; icon: React.ElementType }[] = [
  { value: "fast", label: "Fast", icon: Zap },
  { value: "standard", label: "Standard", icon: Brain },
  { value: "deep", label: "Deep", icon: Rocket },
]

const domainPacks: { value: DomainPack; label: string }[] = [
  { value: "default", label: "Default" },
  { value: "medical", label: "Medical" },
  { value: "legal", label: "Legal" },
  { value: "marketing", label: "Marketing" },
  { value: "coding", label: "Coding" },
  { value: "research", label: "Research" },
  { value: "finance", label: "Finance" },
]

// Response format options - Enhanced with clear descriptions
const responseFormats = [
  { 
    value: "automatic", 
    label: "Automatic", 
    description: "AI selects optimal format based on your query",
    icon: "Sparkles"
  },
  { 
    value: "default", 
    label: "Conversational", 
    description: "Natural flowing paragraphs with explanations",
    icon: "MessageSquare"
  },
  { 
    value: "structured", 
    label: "Structured", 
    description: "Organized with headers, sections & emphasis",
    icon: "LayoutGrid"
  },
  { 
    value: "bullet-points", 
    label: "Bullet Points", 
    description: "Quick-scan lists for easy reading",
    icon: "List"
  },
  { 
    value: "step-by-step", 
    label: "Step-by-Step", 
    description: "Numbered instructions for how-to tasks",
    icon: "ListOrdered"
  },
  { 
    value: "academic", 
    label: "Academic", 
    description: "Formal style with citations & references",
    icon: "GraduationCap"
  },
  { 
    value: "concise", 
    label: "Concise", 
    description: "Brief, direct answers — just the essentials",
    icon: "Zap"
  },
]

const advancedReasoningMethods: { value: AdvancedReasoningMethod; label: string; description: string }[] = [
  { value: "automatic", label: "Automatic", description: "Let the orchestrator choose the best method" },
  { value: "chain-of-thought", label: "Chain of Thought", description: "Step-by-step reasoning" },
  { value: "tree-of-thought", label: "Tree of Thought", description: "Explore multiple paths" },
  { value: "graph-of-thought", label: "Graph of Thought", description: "Non-linear reasoning graph" },
  { value: "algorithm-of-thought", label: "Algorithm of Thought", description: "Algorithmic problem solving" },
  { value: "skeleton-of-thought", label: "Skeleton of Thought", description: "Parallel skeleton expansion" },
  { value: "self-consistency", label: "Self Consistency", description: "Multiple samples, vote" },
  { value: "cumulative-reasoning", label: "Cumulative Reasoning", description: "Build on prior conclusions" },
  { value: "meta-prompting", label: "Meta Prompting", description: "LLM orchestrates sub-LLMs" },
  { value: "react", label: "ReAct", description: "Reason + Act iteratively" },
  { value: "reflexion", label: "Reflexion", description: "Self-reflection loop" },
  { value: "least-to-most", label: "Least to Most", description: "Decompose problems" },
  { value: "plan-and-solve", label: "Plan and Solve", description: "Plan then execute" },
]

const advancedFeatures: { value: AdvancedFeature; label: string; description: string }[] = [
  { value: "vector-rag", label: "Vector DB + RAG", description: "Retrieval augmented generation" },
  { value: "mcp-server", label: "MCP Server + Tools", description: "Model context protocol" },
  { value: "personal-database", label: "Personal Database", description: "Your private knowledge base" },
  { value: "modular-answer-feed", label: "Modular Answer Feed", description: "Internal LLM routing" },
  { value: "memory-augmentation", label: "Memory Augmentation", description: "Long-term memory" },
  { value: "tool-use", label: "Tool Use", description: "External tool integration" },
  { value: "code-interpreter", label: "Code Interpreter", description: "Execute code in sandbox" },
]

export function ChatToolbar({ settings, onSettingsChange, onOpenAdvanced }: ChatToolbarProps) {
  const [modelsOpen, setModelsOpen] = useState(false)
  const [reasoningOpen, setReasoningOpen] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [myTeamModels, setMyTeamModels] = useState<string[]>([])
  
  // Get user tier from subscription
  const { userTier } = useUserTier()
  
  // Use shared hooks for categories and rankings
  const { categories, loading: categoriesLoading, error: categoriesError } = useOpenRouterCategories({ group: 'usecase' })
  const { rankings: rankedEntries, loading: loadingRankings, error: rankingsError } = useCategoryRankings(activeCategory, { limit: 10 })

  // Load user's team models from storage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER_MODEL_PREFERENCES)
      if (stored) {
        const prefs = JSON.parse(stored)
        if (prefs.selectedModels) {
          setMyTeamModels(prefs.selectedModels.map((m: SelectedModelConfig) => m.modelId))
        }
      }
    } catch (e) {
      console.error('Failed to load team models:', e)
    }
  }, [])

  const currentReasoningMode = reasoningModes.find((m) => m.value === settings.reasoningMode) || reasoningModes[1]
  const currentDomainPack = domainPacks.find((d) => d.value === settings.domainPack) || domainPacks[0]
  const ReasoningIcon = currentReasoningMode.icon

  const toggleModel = (modelId: string) => {
    const currentModels = settings.selectedModels || []
    if (currentModels.includes(modelId)) {
      // Removing a model
      if (currentModels.length > 1) {
        const newModels = currentModels.filter((id) => id !== modelId)
        // If only "automatic" remains, keep it; otherwise filter it out too
        onSettingsChange({ selectedModels: newModels })
      } else {
        // If removing the last model, switch back to automatic
        onSettingsChange({ selectedModels: ["automatic"] })
      }
    } else {
      // Adding a model - remove "automatic" when adding specific models
      const modelsWithoutAutomatic = currentModels.filter((id) => id !== "automatic")
      onSettingsChange({ selectedModels: [...modelsWithoutAutomatic, modelId] })
    }
  }

  const toggleReasoningMethod = (method: AdvancedReasoningMethod) => {
    const currentMethods = settings.advancedReasoningMethods || []
    if (currentMethods.includes(method)) {
      onSettingsChange({ advancedReasoningMethods: currentMethods.filter((m) => m !== method) })
    } else {
      onSettingsChange({ advancedReasoningMethods: [...currentMethods, method] })
    }
  }

  const selectedModels = settings.selectedModels || ["automatic"]
  const selectedReasoningMethods = settings.advancedReasoningMethods || []

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Agent Mode Toggle */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          onSettingsChange({
            agentMode: settings.agentMode === "single" ? "team" : "single",
          })
        }
        className={`gap-1.5 h-8 px-3 text-xs border rounded-lg transition-colors ${
          settings.agentMode === "team"
            ? "bg-[var(--bronze)]/20 border-[var(--bronze)] text-[var(--bronze)]"
            : "bg-secondary/50 border-border hover:bg-secondary hover:border-[var(--bronze)]"
        }`}
      >
        {settings.agentMode === "team" ? <Users className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
        <span className="hidden sm:inline">{settings.agentMode === "team" ? "Team" : "Single"}</span>
      </Button>

      {/* Models Dropdown with Ranking Categories */}
      <DropdownMenu open={modelsOpen} onOpenChange={(open) => {
        setModelsOpen(open)
        if (!open) setActiveCategory(null)
      }}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <Cpu className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Models ({selectedModels.length})</span>
            <span className="sm:hidden">{selectedModels.length}</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-72 max-h-[70vh] overflow-y-auto">
          {activeCategory ? (
            // Show top 10 models for selected ranking category
            <>
              <div className="flex items-center gap-2 px-2 py-1.5 border-b">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6 w-6 p-0"
                  onClick={() => setActiveCategory(null)}
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <span className="font-medium text-sm">
                  Top 10 - {categories.find(c => c.slug === activeCategory)?.displayName || activeCategory}
                </span>
              </div>
              {loadingRankings ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 animate-spin mx-auto mb-1" />
                  Loading...
                </div>
              ) : rankingsError ? (
                <div className="p-4 text-center text-sm text-destructive">
                  Failed to load rankings
                </div>
              ) : rankedEntries.length > 0 ? (
                rankedEntries.map((entry) => {
                  const modelId = entry.model_id || ''
                  const isSelected = selectedModels.includes(modelId)
                  const hasAccess = canAccessModel(userTier, modelId)
                  const requiredTier = getModelRequiredTier(modelId)
                  
                  return (
                    <DropdownMenuItem
                      key={modelId}
                      onSelect={(e) => {
                        e.preventDefault()
                        if (hasAccess) toggleModel(modelId)
                      }}
                      disabled={!hasAccess}
                      className={cn("gap-2 cursor-pointer", !hasAccess && "opacity-50")}
                    >
                      <div className={cn(
                        "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0",
                        entry.rank === 1 ? "bg-yellow-400 text-yellow-900" :  // Gold
                        entry.rank === 2 ? "bg-slate-300 text-slate-700" :    // Silver
                        entry.rank === 3 ? "bg-amber-600 text-amber-100" :    // Bronze
                        "bg-muted text-muted-foreground"
                      )}>
                        {entry.rank}
                      </div>
                      {/* Provider Logo */}
                      <div className="w-5 h-5 relative shrink-0">
                        <Image
                          src={getModelLogo(modelId)}
                          alt=""
                          fill
                          className="object-contain"
                          unoptimized
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1">
                          <span className="text-sm truncate">{entry.model_name}</span>
                          {!hasAccess && (
                            <Badge variant="outline" className={cn("text-[8px] px-1 h-4", getTierBadgeColor(requiredTier))}>
                              <Lock className="w-2 h-2 mr-0.5" />
                              {getTierDisplayName(requiredTier)}
                            </Badge>
                          )}
                        </div>
                        <span className="text-[10px] text-muted-foreground">
                          {entry.author || entry.model_id?.split('/')[0]}
                        </span>
                      </div>
                      {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                    </DropdownMenuItem>
                  )
                })
              ) : (
                <div className="p-4 text-center text-muted-foreground text-sm">No models found</div>
              )}
            </>
          ) : (
            // Show ranking categories
            <>
              {/* Automatic Option - Always at top */}
              <DropdownMenuItem
                onSelect={(e) => {
                  e.preventDefault()
                  // Set to automatic mode
                  onSettingsChange({ selectedModels: ["automatic"] })
                }}
                className="gap-2 cursor-pointer"
              >
                <div className="w-5 h-5 rounded-full bg-gradient-to-br from-[var(--bronze)] to-amber-600 flex items-center justify-center">
                  <Sparkles className="h-3 w-3 text-white" />
                </div>
                <span className="flex-1 font-medium">Automatic</span>
                <span className="text-[10px] text-muted-foreground">Best model per task</span>
                {selectedModels.includes("automatic") && <Check className="h-4 w-4 text-[var(--bronze)]" />}
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              {/* My Team Section */}
              {myTeamModels.length > 0 && (
                <>
                  <DropdownMenuLabel className="flex items-center gap-2 text-[var(--bronze)]">
                    <Crown className="h-3.5 w-3.5" />
                    My Team ({myTeamModels.length})
                  </DropdownMenuLabel>
                  {myTeamModels.slice(0, 5).map((modelId) => {
                    const isSelected = selectedModels.includes(modelId)
                    return (
                      <DropdownMenuItem
                        key={modelId}
                        onSelect={(e) => {
                          e.preventDefault()
                          toggleModel(modelId)
                        }}
                        className="gap-2 cursor-pointer pl-6"
                      >
                        <span className="flex-1 text-sm truncate">{modelId.split('/')[1] || modelId}</span>
                        {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                      </DropdownMenuItem>
                    )
                  })}
                  <DropdownMenuSeparator />
                </>
              )}
              
              {/* OpenRouter Categories (dynamic from API) */}
              <DropdownMenuLabel className="text-muted-foreground text-xs">
                Browse by Category
              </DropdownMenuLabel>
              {categoriesLoading ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 animate-spin mx-auto mb-1" />
                  Loading categories...
                </div>
              ) : categoriesError ? (
                <div className="p-4 text-center text-sm text-destructive">
                  Failed to load categories
                </div>
              ) : (
                categories.map((cat) => {
                  const Icon = getCategoryIcon(cat.slug)
                  return (
                    <DropdownMenuItem
                      key={cat.slug}
                      onSelect={(e) => {
                        e.preventDefault()
                        setActiveCategory(cat.slug)
                      }}
                      className="gap-2 cursor-pointer"
                    >
                      <Icon className={cn("h-4 w-4", CATEGORY_COLOR_MAP[cat.slug] || "text-muted-foreground")} />
                      <span className="flex-1">{cat.displayName}</span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </DropdownMenuItem>
                  )
                })
              )}
              
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu open={reasoningOpen} onOpenChange={setReasoningOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              Reasoning {selectedReasoningMethods.length > 0 ? `(${selectedReasoningMethods.length})` : ""}
            </span>
            <span className="sm:hidden">
              {selectedReasoningMethods.length > 0 ? selectedReasoningMethods.length : "R"}
            </span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56 max-h-80 overflow-y-auto">
          {advancedReasoningMethods.map((method) => {
            const isSelected = selectedReasoningMethods.includes(method.value)
            return (
              <DropdownMenuItem
                key={method.value}
                onSelect={(e) => {
                  e.preventDefault()
                  toggleReasoningMethod(method.value)
                }}
                className="flex flex-col items-start gap-0.5 cursor-pointer"
              >
                <div className="flex items-center w-full gap-2">
                  <span className="flex-1 font-medium">{method.label}</span>
                  {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                </div>
                <span className="text-[10px] text-muted-foreground">{method.description}</span>
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Features dropdown removed from chat page - available in Orchestration page */}
      {/* Speed dropdown removed from chat page - available in Orchestration page */}
      {/* Domain Pack moved to lit-up badge in chat-area.tsx */}

      {/* Response Format */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <ListTree className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Format</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          {responseFormats.map((format) => {
            const isSelected = (settings as any).answerFormat === format.value || 
              ((settings as any).answerFormat === undefined && format.value === "automatic")
            const isAutomatic = format.value === "automatic"
            
            // Map icon names to components
            const iconMap: Record<string, React.ElementType> = {
              "Sparkles": Sparkles,
              "MessageSquare": MessageSquare,
              "LayoutGrid": LayoutGrid,
              "List": List,
              "ListOrdered": ListOrdered,
              "GraduationCap": GraduationCap,
              "Zap": Zap,
            }
            const IconComponent = iconMap[format.icon] || ListTree
            
            return (
              <div key={format.value}>
                <DropdownMenuItem
                  onClick={() => onSettingsChange({ answerFormat: format.value } as any)}
                  className="flex items-center gap-2.5 py-2.5 cursor-pointer"
                >
                  {/* Icon with special styling for Automatic */}
                  <div className={cn(
                    "w-6 h-6 rounded-md flex items-center justify-center shrink-0",
                    isAutomatic 
                      ? "bg-gradient-to-br from-[var(--bronze)] to-amber-600" 
                      : "bg-muted"
                  )}>
                    <IconComponent className={cn(
                      "h-3.5 w-3.5",
                      isAutomatic ? "text-white" : "text-muted-foreground"
                    )} />
                  </div>
                  
                  {/* Label and Description */}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{format.label}</div>
                    <div className="text-[10px] text-muted-foreground leading-tight">{format.description}</div>
                  </div>
                  
                  {/* Check mark for selected */}
                  {isSelected && <Check className="h-4 w-4 text-[var(--bronze)] shrink-0" />}
                </DropdownMenuItem>
                
                {/* Separator after Automatic */}
                {isAutomatic && <DropdownMenuSeparator />}
              </div>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Criteria Equalizer */}
      <CriteriaEqualizer
        settings={settings.criteria || { accuracy: 70, speed: 70, creativity: 50 }}
        onChange={(criteria) => onSettingsChange({ criteria })}
      />

      {/* Advanced Settings - Now a dropdown menu like the others */}
      <AdvancedSettingsDropdown
        settings={settings}
        onSettingsChange={onSettingsChange}
      />
    </div>
  )
}
