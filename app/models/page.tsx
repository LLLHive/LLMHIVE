"use client"

/**
 * Models Page - Redesigned to match site layout
 * 
 * Features:
 * - Sidebar navigation (like all other pages)
 * - Logo and title in center
 * - Ranking categories from OpenRouter
 * - Compact model cards with cost, rankings, and selection
 */

import * as React from "react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { 
  BarChart3, TrendingUp, DollarSign, Code, Users, Megaphone, Search, Cpu, 
  FlaskConical, Languages, Scale, Landmark, Heart, GraduationCap, PieChart, 
  Wrench, MessageSquare, Image as ImageIcon, Clock, Shield, Zap, Check, Plus,
  ChevronRight, ExternalLink
} from "lucide-react"
import { Sidebar } from "@/components/sidebar"
import { UserAccountMenu } from "@/components/user-account-menu"
import { ROUTES } from "@/lib/routes"
import { useAuth } from "@/lib/auth-context"
import { listModels, getRankings } from "@/lib/openrouter/api"
import type { OpenRouterModel, RankingDimension } from "@/lib/openrouter/types"
import { 
  type UserTier, type SelectedModelConfig, 
  canAccessModel, getTierBadgeColor, getTierDisplayName, getModelRequiredTier,
  STORAGE_KEYS, TIER_CONFIGS 
} from "@/lib/openrouter/tiers"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

// Ranking categories matching OpenRouter
const RANKING_CATEGORIES: Array<{
  id: RankingDimension
  name: string
  icon: React.ElementType
  color: string
}> = [
  { id: 'leaderboard', name: 'Leaderboard', icon: BarChart3, color: 'from-blue-500 to-cyan-500' },
  { id: 'market_share', name: 'Market Share', icon: PieChart, color: 'from-indigo-500 to-purple-500' },
  { id: 'trending', name: 'Trending', icon: TrendingUp, color: 'from-green-500 to-emerald-500' },
  { id: 'programming', name: 'Programming', icon: Code, color: 'from-violet-500 to-purple-500' },
  { id: 'roleplay', name: 'Roleplay', icon: Users, color: 'from-pink-500 to-rose-500' },
  { id: 'marketing', name: 'Marketing', icon: Megaphone, color: 'from-orange-500 to-amber-500' },
  { id: 'science', name: 'Science', icon: FlaskConical, color: 'from-cyan-500 to-teal-500' },
  { id: 'translation', name: 'Translation', icon: Languages, color: 'from-sky-500 to-blue-500' },
  { id: 'legal', name: 'Legal', icon: Scale, color: 'from-gray-500 to-slate-500' },
  { id: 'finance', name: 'Finance', icon: Landmark, color: 'from-emerald-500 to-green-500' },
  { id: 'tools_agents', name: 'Tool Calls', icon: Wrench, color: 'from-orange-500 to-red-500' },
  { id: 'images', name: 'Images', icon: ImageIcon, color: 'from-fuchsia-500 to-pink-500' },
  { id: 'long_context', name: 'Long Context', icon: MessageSquare, color: 'from-purple-500 to-violet-500' },
  { id: 'fastest', name: 'Fastest', icon: Zap, color: 'from-yellow-500 to-amber-500' },
  { id: 'lowest_cost', name: 'Lowest Cost', icon: DollarSign, color: 'from-lime-500 to-green-500' },
]

interface RankedModelData {
  model: OpenRouterModel & { author?: string; tokens_used?: string }
  rank: number
  score: number
  metrics: Record<string, number | string>
}

// Compact Model Card Component
function ModelCard({ 
  model, 
  rank, 
  metrics,
  userTier,
  isSelected,
  onToggleSelect,
  onViewDetails 
}: { 
  model: OpenRouterModel & { author?: string; tokens_used?: string }
  rank?: number
  metrics?: Record<string, number | string>
  userTier: UserTier
  isSelected: boolean
  onToggleSelect: () => void
  onViewDetails: () => void
}) {
  const canAccess = canAccessModel(userTier, model.id)
  const requiredTier = getModelRequiredTier(model.id)
  const promptCost = model.pricing?.per_1m_prompt || model.pricing?.prompt || 0
  const completionCost = model.pricing?.per_1m_completion || model.pricing?.completion || 0
  
  // Extract strengths/weaknesses from model data
  const strengths: string[] = []
  const weaknesses: string[] = []
  
  if (model.context_length && model.context_length >= 100000) strengths.push('Long context')
  if (model.capabilities?.supports_tools) strengths.push('Tool calling')
  if (model.capabilities?.multimodal_input) strengths.push('Vision')
  if (model.capabilities?.supports_structured) strengths.push('JSON output')
  if (promptCost === 0) strengths.push('Free')
  else if (promptCost < 1) strengths.push('Budget-friendly')
  
  if (!model.capabilities?.supports_tools) weaknesses.push('No tools')
  if (!model.capabilities?.multimodal_input) weaknesses.push('Text only')
  if (model.context_length && model.context_length < 32000) weaknesses.push('Limited context')
  
  return (
    <Card 
      className={cn(
        "group transition-all duration-200 cursor-pointer",
        isSelected && "ring-2 ring-[var(--bronze)]",
        !canAccess && "opacity-60"
      )}
      onClick={onViewDetails}
    >
      <CardContent className="p-3">
        <div className="flex items-start gap-3">
          {/* Rank Badge */}
          {rank && rank <= 10 && (
            <div className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
              rank === 1 ? "bg-amber-500 text-black" :
              rank === 2 ? "bg-gray-300 text-black" :
              rank === 3 ? "bg-orange-400 text-black" :
              "bg-muted text-muted-foreground"
            )}>
              #{rank}
            </div>
          )}
          
          {/* Model Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{model.name}</span>
              {!canAccess && (
                <Badge variant="outline" className={cn("text-[9px] px-1", getTierBadgeColor(requiredTier))}>
                  {getTierDisplayName(requiredTier)}
                </Badge>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground truncate">{model.author || model.id.split('/')[0]}</p>
            
            {/* Cost - OTel metrics format */}
            <div className="flex items-center gap-2 mt-1 text-[10px]">
              <span className="text-muted-foreground">
                In: ${promptCost < 0.01 ? promptCost.toFixed(4) : promptCost.toFixed(2)}/1M
              </span>
              <span className="text-muted-foreground">
                Out: ${completionCost < 0.01 ? completionCost.toFixed(4) : completionCost.toFixed(2)}/1M
              </span>
            </div>
            
            {/* Metrics from ranking */}
            {metrics && Object.keys(metrics).length > 0 && (
              <div className="flex items-center gap-2 mt-1">
                {metrics.tokens && (
                  <Badge variant="secondary" className="text-[9px] h-4 px-1">
                    {metrics.tokens} tokens
                  </Badge>
                )}
                {metrics.share && (
                  <Badge variant="secondary" className="text-[9px] h-4 px-1">
                    {metrics.share}
                  </Badge>
                )}
                {metrics.change && (
                  <Badge variant="secondary" className={cn(
                    "text-[9px] h-4 px-1",
                    String(metrics.change).includes('+') ? "text-green-600" : "text-red-600"
                  )}>
                    {metrics.change}%
                  </Badge>
                )}
              </div>
            )}
            
            {/* Compact Strengths/Weaknesses */}
            <div className="flex flex-wrap gap-1 mt-1.5">
              {strengths.slice(0, 3).map((s, i) => (
                <span key={i} className="text-[9px] text-green-600 bg-green-500/10 px-1.5 rounded">
                  +{s}
                </span>
              ))}
              {weaknesses.slice(0, 2).map((w, i) => (
                <span key={i} className="text-[9px] text-orange-600 bg-orange-500/10 px-1.5 rounded">
                  -{w}
                </span>
              ))}
            </div>
          </div>
          
          {/* Selection Checkbox */}
          {canAccess && (
            <Checkbox 
              checked={isSelected}
              onCheckedChange={() => onToggleSelect()}
              onClick={(e) => e.stopPropagation()}
              className="shrink-0 mt-1"
            />
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function ModelsPage() {
  const router = useRouter()
  const auth = useAuth()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeCategory, setActiveCategory] = useState<RankingDimension | null>(null)
  const [rankedModels, setRankedModels] = useState<RankedModelData[]>([])
  const [allModels, setAllModels] = useState<OpenRouterModel[]>([])
  const [selectedModelIds, setSelectedModelIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [showDetails, setShowDetails] = useState<OpenRouterModel | null>(null)
  
  // TODO: Get from auth context
  const userTier: UserTier = 'pro'
  const tierConfig = TIER_CONFIGS[userTier]
  
  // Load all models on mount
  useEffect(() => {
    async function loadAllModels() {
      try {
        const response = await listModels({ limit: 500 })
        setAllModels(response.models || response.data || [])
      } catch (e) {
        console.error('Failed to load models:', e)
      }
    }
    loadAllModels()
    
    // Load saved selections
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER_MODEL_PREFERENCES)
      if (stored) {
        const prefs = JSON.parse(stored)
        if (prefs.selectedModels) {
          setSelectedModelIds(new Set(prefs.selectedModels.map((m: SelectedModelConfig) => m.modelId)))
        }
      }
    } catch (e) {
      console.error('Failed to load preferences:', e)
    }
  }, [])
  
  // Load rankings when category changes
  useEffect(() => {
    if (!activeCategory) {
      setRankedModels([])
      return
    }
    
    async function loadRankings() {
      setLoading(true)
      try {
        const result = await getRankings(activeCategory as RankingDimension)
        setRankedModels(result.models || [])
      } catch (e) {
        console.error('Failed to load rankings:', e)
        setRankedModels([])
      } finally {
        setLoading(false)
      }
    }
    loadRankings()
  }, [activeCategory])
  
  const toggleModelSelection = (modelId: string) => {
    const newSelected = new Set(selectedModelIds)
    if (newSelected.has(modelId)) {
      newSelected.delete(modelId)
      toast.success('Model removed from team')
    } else {
      if (newSelected.size >= tierConfig.maxModelsInTeam) {
        toast.error(`Maximum ${tierConfig.maxModelsInTeam} models allowed for ${tierConfig.displayName} tier`)
        return
      }
      newSelected.add(modelId)
      toast.success('Model added to team')
    }
    setSelectedModelIds(newSelected)
    
    // Save to localStorage
    const selectedConfigs: SelectedModelConfig[] = Array.from(newSelected).map(id => ({
      modelId: id,
      enabled: true,
      preferredRole: 'primary',
      addedAt: new Date().toISOString(),
    }))
    
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER_MODEL_PREFERENCES)
      const prefs = stored ? JSON.parse(stored) : { userId: 'default', tier: userTier }
      prefs.selectedModels = selectedConfigs
      prefs.updatedAt = new Date().toISOString()
      localStorage.setItem(STORAGE_KEYS.USER_MODEL_PREFERENCES, JSON.stringify(prefs))
    } catch (e) {
      console.error('Failed to save preferences:', e)
    }
  }
  
  // Get models to display
  const displayModels = activeCategory ? rankedModels : allModels.slice(0, 50).map(m => ({ 
    model: m, 
    rank: 0, 
    score: 0, 
    metrics: {} 
  }))
  
  return (
    <div className="flex h-screen overflow-hidden relative">
      {/* Glassmorphism Sidebar */}
      <div className="llmhive-glass-sidebar h-full">
      <Sidebar
        conversations={[]}
        currentConversationId={null}
        onNewChat={() => router.push(ROUTES.HOME)}
        onSelectConversation={() => router.push(ROUTES.HOME)}
        onDeleteConversation={() => {}}
        onTogglePin={() => {}}
        onRenameConversation={() => {}}
        onMoveToProject={() => {}}
        projects={[]}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onGoHome={() => router.push(ROUTES.HOME)}
      />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Desktop User Account Menu - Glassmorphism */}
        <div className="hidden md:flex items-center justify-end p-3 border-b border-white/5 llmhive-glass">
          <UserAccountMenu />
        </div>

        {/* Main Content */}
        <div className="flex-1 h-full overflow-auto">
          <div className="min-h-full flex flex-col items-center justify-start px-4 pt-4 pb-20">
            {/* Hero Section with 3D Logo */}
            <div className="text-center mb-6 llmhive-fade-in">
              <div className="relative w-44 h-44 md:w-72 md:h-72 lg:w-80 lg:h-80 mx-auto mb-2 llmhive-float">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain drop-shadow-2xl" priority />
              </div>
              <LogoText height={64} className="mx-auto mb-2" />
              <h2 className="text-xl md:text-2xl lg:text-3xl llmhive-subtitle mb-2">
                Models
              </h2>
              <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto">
                Browse {allModels.length}+ models by ranking category
              </p>
            </div>

            {/* Selection Status */}
            {selectedModelIds.size > 0 && (
              <div className="mb-4 flex items-center gap-2 text-sm">
                <Badge variant="outline" className="gap-1">
                  <Check className="w-3 h-3" />
                  {selectedModelIds.size}/{tierConfig.maxModelsInTeam} models selected
                </Badge>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => router.push(ROUTES.ORCHESTRATION)}
                  className="gap-1 text-[var(--bronze)]"
                >
                  Go to Orchestration
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}

            {/* Ranking Categories - Wrapped grid to prevent overflow */}
            <div className="w-full max-w-5xl mb-6">
              <p className="text-sm text-muted-foreground text-center mb-3">Select a ranking category</p>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
                {RANKING_CATEGORIES.map((cat) => {
                  const Icon = cat.icon
                  const isActive = activeCategory === cat.id
                  return (
                    <button
                      key={cat.id}
                      onClick={() => setActiveCategory(isActive ? null : cat.id)}
                      className={cn(
                        "group flex flex-col items-center gap-1.5 p-2 md:p-3 rounded-xl border transition-all duration-200",
                        isActive 
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10" 
                          : "border-border hover:border-[var(--bronze)]/50 bg-card/50 hover:bg-card/80"
                      )}
                    >
                      <div className={cn(
                        "w-8 h-8 rounded-lg bg-gradient-to-br flex items-center justify-center",
                        cat.color
                      )}>
                        <Icon className="h-4 w-4 text-white" />
                      </div>
                      <span className={cn(
                        "text-[10px] md:text-xs font-medium text-center leading-tight",
                        isActive && "text-[var(--bronze)]"
                      )}>
                        {cat.name}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Models Grid */}
            <div className="w-full max-w-5xl">
              {activeCategory && (
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">
                    Top {rankedModels.length} in {RANKING_CATEGORIES.find(c => c.id === activeCategory)?.name}
                  </h2>
                  <Badge variant="secondary" className="text-xs">
                    Click to select for orchestration
                  </Badge>
                </div>
              )}
              
              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {[...Array(6)].map((_, i) => (
                    <Card key={i} className="animate-pulse">
                      <CardContent className="p-3 h-24 bg-muted/50" />
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {displayModels.map((item) => {
                    const modelData = 'model' in item ? item.model : item
                    return (
                      <ModelCard
                        key={modelData.id}
                        model={modelData}
                        rank={item.rank}
                        metrics={item.metrics}
                        userTier={userTier}
                        isSelected={selectedModelIds.has(modelData.id)}
                        onToggleSelect={() => toggleModelSelection(modelData.id)}
                        onViewDetails={() => setShowDetails(modelData)}
                      />
                    )
                  })}
                </div>
              )}
              
              {!activeCategory && !loading && (
                <p className="text-center text-muted-foreground mt-4 text-sm">
                  Select a ranking category above to see top models
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Model Details Sheet */}
      <Sheet open={!!showDetails} onOpenChange={() => setShowDetails(null)}>
        <SheetContent side="right" className="w-[320px] sm:w-[400px]">
          {showDetails && (
            <>
              <SheetHeader>
                <SheetTitle className="text-left">{showDetails.name}</SheetTitle>
              </SheetHeader>
              <div className="mt-4 space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">{showDetails.id}</p>
                  <p className="text-sm mt-2">{showDetails.description || 'No description available'}</p>
                </div>
                
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Pricing (per 1M tokens)</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="p-2 bg-muted rounded">
                      <span className="text-muted-foreground">Input:</span>
                      <span className="ml-2 font-mono">
                        ${(showDetails.pricing?.per_1m_prompt || 0).toFixed(2)}
                      </span>
                    </div>
                    <div className="p-2 bg-muted rounded">
                      <span className="text-muted-foreground">Output:</span>
                      <span className="ml-2 font-mono">
                        ${(showDetails.pricing?.per_1m_completion || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Capabilities</h4>
                  <div className="flex flex-wrap gap-1">
                    {showDetails.capabilities?.supports_tools && (
                      <Badge variant="secondary">Tools</Badge>
                    )}
                    {showDetails.capabilities?.supports_streaming && (
                      <Badge variant="secondary">Streaming</Badge>
                    )}
                    {showDetails.capabilities?.multimodal_input && (
                      <Badge variant="secondary">Vision</Badge>
                    )}
                    {showDetails.capabilities?.supports_structured && (
                      <Badge variant="secondary">JSON</Badge>
                    )}
                    {showDetails.context_length && (
                      <Badge variant="secondary">{(showDetails.context_length / 1000).toFixed(0)}K ctx</Badge>
                    )}
                  </div>
                </div>
                
                <Button 
                  className="w-full gap-2"
                  onClick={() => {
                    toggleModelSelection(showDetails.id)
                    setShowDetails(null)
                  }}
                  disabled={!canAccessModel(userTier, showDetails.id)}
                >
                  {selectedModelIds.has(showDetails.id) ? (
                    <>Remove from Team</>
                  ) : (
                    <><Plus className="w-4 h-4" /> Add to Team</>
                  )}
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
