"use client"

import { useState, useEffect } from "react"
import type React from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent, DropdownMenuSeparator, DropdownMenuLabel } from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, Zap, Brain, Rocket, Users, User, Settings2, Cpu, Sparkles, Check, Wrench, ArrowLeft, BarChart3, TrendingUp, DollarSign, Code, PieChart, MessageSquare, Image as ImageIcon, Wrench as ToolIcon, Languages, Clock, ChevronRight, Crown, Lock, FlaskConical, Heart, Scale, Megaphone, Search, Landmark, GraduationCap, Loader2 } from "lucide-react"
import type {
  ReasoningMode,
  DomainPack,
  OrchestratorSettings,
  AdvancedReasoningMethod,
  AdvancedFeature,
} from "@/lib/types"
import { AVAILABLE_MODELS, getModelLogo } from "@/lib/models"
import { CriteriaEqualizer } from "./criteria-equalizer"
import Image from "next/image"
import type { OpenRouterModel } from "@/lib/openrouter/types"
import { canAccessModel, type UserTier, getTierBadgeColor, getTierDisplayName, getModelRequiredTier, STORAGE_KEYS, type SelectedModelConfig } from "@/lib/openrouter/tiers"
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
  onOpenAdvanced: () => void
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
  const [featuresOpen, setFeaturesOpen] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [myTeamModels, setMyTeamModels] = useState<string[]>([])
  
  // TODO: Get from auth context
  const userTier: UserTier = 'pro'
  
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
      if (currentModels.length > 1) {
        onSettingsChange({ selectedModels: currentModels.filter((id) => id !== modelId) })
      }
    } else {
      onSettingsChange({ selectedModels: [...currentModels, modelId] })
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

  const toggleFeature = (feature: AdvancedFeature) => {
    const currentFeatures = settings.advancedFeatures || []
    if (currentFeatures.includes(feature)) {
      onSettingsChange({ advancedFeatures: currentFeatures.filter((f) => f !== feature) })
    } else {
      onSettingsChange({ advancedFeatures: [...currentFeatures, feature] })
    }
  }

  const selectedModels = settings.selectedModels || ["automatic"]
  const selectedReasoningMethods = settings.advancedReasoningMethods || []
  const selectedFeatures = settings.advancedFeatures || []

  return (
    <div className="flex items-center gap-2 flex-wrap">
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
                        entry.rank === 1 ? "bg-amber-500 text-black" :
                        entry.rank === 2 ? "bg-gray-300 text-black" :
                        entry.rank === 3 ? "bg-orange-400 text-black" :
                        "bg-muted text-muted-foreground"
                      )}>
                        {entry.rank}
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
              
              <DropdownMenuSeparator />
              
              {/* Built-in Models */}
              <DropdownMenuLabel className="text-muted-foreground text-xs">
                Built-in Models
              </DropdownMenuLabel>
              {AVAILABLE_MODELS.map((model) => {
                const isSelected = selectedModels.includes(model.id)
                return (
                  <DropdownMenuItem
                    key={model.id}
                    onSelect={(e) => {
                      e.preventDefault()
                      toggleModel(model.id)
                    }}
                    className="gap-2 cursor-pointer"
                  >
                    <div className="w-5 h-5 relative flex-shrink-0">
                      <Image
                        src={getModelLogo(model.provider) || "/placeholder.svg"}
                        alt={model.provider}
                        fill
                        className="object-contain"
                      />
                    </div>
                    <span className="flex-1">{model.name}</span>
                    {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                  </DropdownMenuItem>
                )
              })}
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

      <DropdownMenu open={featuresOpen} onOpenChange={setFeaturesOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <Wrench className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              Features {selectedFeatures.length > 0 ? `(${selectedFeatures.length})` : ""}
            </span>
            <span className="sm:hidden">{selectedFeatures.length > 0 ? selectedFeatures.length : "F"}</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56 max-h-80 overflow-y-auto">
          {advancedFeatures.map((feature) => {
            const isSelected = selectedFeatures.includes(feature.value)
            return (
              <DropdownMenuItem
                key={feature.value}
                onSelect={(e) => {
                  e.preventDefault()
                  toggleFeature(feature.value)
                }}
                className="flex flex-col items-start gap-0.5 cursor-pointer"
              >
                <div className="flex items-center w-full gap-2">
                  <span className="flex-1 font-medium">{feature.label}</span>
                  {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                </div>
                <span className="text-[10px] text-muted-foreground">{feature.description}</span>
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Reasoning Mode */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <ReasoningIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{currentReasoningMode.label}</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-40">
          {reasoningModes.map((mode) => {
            const Icon = mode.icon
            return (
              <DropdownMenuItem
                key={mode.value}
                onClick={() => onSettingsChange({ reasoningMode: mode.value })}
                className="gap-2"
              >
                <Icon className="h-4 w-4" />
                <span>{mode.label}</span>
                {settings.reasoningMode === mode.value && <span className="ml-auto text-[var(--bronze)]">•</span>}
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Domain Pack */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <span className="hidden sm:inline">{currentDomainPack.label}</span>
            <span className="sm:hidden">Domain</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-40">
          {domainPacks.map((pack) => (
            <DropdownMenuItem
              key={pack.value}
              onClick={() => onSettingsChange({ domainPack: pack.value })}
              className="gap-2"
            >
              <span>{pack.label}</span>
              {settings.domainPack === pack.value && <span className="ml-auto text-[var(--bronze)]">•</span>}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

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

      {/* Criteria Equalizer */}
      <CriteriaEqualizer
        settings={settings.criteria || { accuracy: 70, speed: 70, creativity: 50 }}
        onChange={(criteria) => onSettingsChange({ criteria })}
      />

      {/* Advanced Settings */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onOpenAdvanced}
        className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
      >
        <Settings2 className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Advanced</span>
      </Button>
    </div>
  )
}
