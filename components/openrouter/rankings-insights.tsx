"use client"

/**
 * Rankings & Insights Component
 * 
 * Interactive rankings display with:
 * - Dynamic categories from OpenRouter (source of truth)
 * - Multiple ranking dimensions
 * - Time range selection
 * - Clear data provenance labels
 * 
 * Data Source: OpenRouter Rankings (synced to local DB)
 * Rankings reflect OpenRouter's global usage data, NOT internal telemetry.
 */

import * as React from "react"
import { 
  TrendingUp, BarChart3, DollarSign, MessageSquare, Zap, Image, Clock, Shield, Info, ChevronRight, ExternalLink,
  Code, Users, Megaphone, Search, Cpu, FlaskConical, Languages, Scale, Landmark, Heart, GraduationCap, PieChart, Wrench, RefreshCw, CheckCircle, AlertCircle
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"

import type { RankingDimension, TimeRange, RankingResult, RankedModel, OpenRouterModel } from "@/lib/openrouter/types"
import { formatPrice, formatContextLength, formatLatency } from "@/lib/openrouter/types"
import { 
  getRankings, 
  listRankingDimensions,
  listCategories,
  getCategoryRankings,
  getRankingsStatus,
  triggerRankingsSync,
  type OpenRouterCategory,
  type CategoryRankingsResponse,
  type OpenRouterRankingEntry,
} from "@/lib/openrouter/api"

// =============================================================================
// Category Icons Mapping
// =============================================================================

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
  'tool-use': Wrench,
  'vision': Image,
  'reasoning': FlaskConical,
}

const CATEGORY_COLORS: Record<string, string> = {
  'programming': 'text-violet-500',
  'science': 'text-cyan-500',
  'health': 'text-red-500',
  'legal': 'text-gray-500',
  'marketing': 'text-orange-500',
  'marketing/seo': 'text-teal-500',
  'technology': 'text-slate-500',
  'finance': 'text-emerald-500',
  'academia': 'text-amber-600',
  'roleplay': 'text-pink-500',
  'creative-writing': 'text-purple-500',
  'translation': 'text-sky-500',
}

// Fallback for legacy dimension-based tabs (internal telemetry)
const LEGACY_DIMENSION_CONFIG: Record<string, {
  icon: React.ElementType
  name: string
  description: string
  color: string
}> = {
  leaderboard: {
    icon: BarChart3,
    name: "Leaderboard",
    description: "Token usage across all models",
    color: "text-blue-500",
  },
  trending: {
    icon: TrendingUp,
    name: "Trending",
    description: "Models with growing usage",
    color: "text-green-500",
  },
  best_value: {
    icon: DollarSign,
    name: "Best Value",
    description: "Quality/cost ratio",
    color: "text-amber-500",
  },
  fastest: {
    icon: Clock,
    name: "Fastest",
    description: "Lowest latency",
    color: "text-cyan-500",
  },
}

const VIEW_LABELS: Record<string, string> = {
  "day": "Today",
  "week": "This Week",
  "month": "This Month",
  "all": "All Time",
}

// Import shared provider logo resolver
import { resolveProviderLogo, type LogoResult } from "@/lib/provider-logos"

function getProviderLogo(author: string | undefined): LogoResult {
  return resolveProviderLogo(author || '')
}

// =============================================================================
// OpenRouter Ranking Entry Row Component
// =============================================================================

interface RankingEntryRowProps {
  entry: OpenRouterRankingEntry
  onSelect?: (modelId: string) => void
}

function RankingEntryRow({ entry, onSelect }: RankingEntryRowProps) {
  const getRankBadgeColor = (r: number) => {
    if (r === 1) return "bg-yellow-500 text-yellow-950"
    if (r === 2) return "bg-gray-400 text-gray-950"
    if (r === 3) return "bg-amber-700 text-amber-100"
    return "bg-muted text-muted-foreground"
  }
  
  const logo = getProviderLogo(entry.author)
  
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/50"
      onClick={() => onSelect?.(entry.model_id)}
    >
      <CardContent className="flex items-center gap-4 p-4">
        {/* Rank */}
        <Badge className={cn("w-8 h-8 flex items-center justify-center text-sm font-bold shrink-0", getRankBadgeColor(entry.rank))}>
          {entry.rank}
        </Badge>
        
        {/* Provider Logo with Fallback */}
        <div className="w-8 h-8 shrink-0 flex items-center justify-center">
          {logo.src ? (
            <img 
              src={logo.src} 
              alt={entry.author || ''} 
              className="w-6 h-6 object-contain" 
              onError={(e) => {
                // Hide the image on error and show fallback
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : (
            <div className={cn(
              "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white",
              logo.fallbackColor
            )}>
              {logo.fallbackInitials}
            </div>
          )}
        </div>
        
        {/* Model info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold truncate">{entry.model_name}</h4>
          <p className="text-sm text-muted-foreground truncate">
            {entry.model_id || entry.author}
          </p>
        </div>
        
        {/* Usage metrics */}
        <div className="text-right shrink-0">
          {entry.share_pct != null && (
            <div className="font-mono text-sm font-medium">
              {entry.share_pct.toFixed(1)}%
            </div>
          )}
          {entry.tokens_display && (
            <div className="text-xs text-muted-foreground">
              {entry.tokens_display} tokens
            </div>
          )}
          {entry.tokens && !entry.tokens_display && (
            <div className="text-xs text-muted-foreground">
              {entry.tokens >= 1_000_000_000 
                ? `${(entry.tokens / 1_000_000_000).toFixed(1)}B` 
                : entry.tokens >= 1_000_000
                ? `${(entry.tokens / 1_000_000).toFixed(1)}M`
                : entry.tokens.toLocaleString()
              } tokens
            </div>
          )}
        </div>
        
        {/* Capabilities badges */}
        {entry.model_metadata && (
          <div className="hidden md:flex gap-1 shrink-0">
            {entry.model_metadata.supports_tools && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Badge variant="secondary" className="h-6 w-6 p-0 flex items-center justify-center">
                      <Zap className="w-3 h-3" />
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>Tool calling</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            {entry.model_metadata.multimodal_input && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Badge variant="secondary" className="h-6 w-6 p-0 flex items-center justify-center">
                      <Image className="w-3 h-3" />
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>Vision</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        )}
        
        {/* Price */}
        {entry.model_metadata?.pricing?.prompt != null && (
          <div className="text-right shrink-0 w-24 hidden lg:block">
            <div className="text-sm font-medium">
              {formatPrice(entry.model_metadata.pricing.prompt)}
            </div>
          </div>
        )}
        
        <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Legacy Ranked Model Row Component (for internal telemetry)
// =============================================================================

interface RankedModelRowProps {
  rankedModel: RankedModel
  onSelect?: (model: OpenRouterModel) => void
}

function RankedModelRow({ rankedModel, onSelect }: RankedModelRowProps) {
  // Handle both nested format (model: {...}) and flat format (id, name directly on rankedModel)
  const model = rankedModel.model || rankedModel as unknown as OpenRouterModel
  const rank = rankedModel.rank || (rankedModel as unknown as {rank?: number}).rank
  const score = rankedModel.score
  const metrics = rankedModel.metrics || {}
  
  // Defensive: skip rendering if essential data is missing
  if (!model || (!model.id && !(rankedModel as unknown as {id?: string}).id)) {
    return null
  }
  
  // Handle flat format - get id/name from rankedModel directly
  const modelId = model.id || (rankedModel as unknown as {id: string}).id
  const modelName = model.name || (rankedModel as unknown as {name: string}).name
  
  const getRankBadgeColor = (r: number) => {
    if (r === 1) return "bg-yellow-500 text-yellow-950"
    if (r === 2) return "bg-gray-400 text-gray-950"
    if (r === 3) return "bg-amber-700 text-amber-100"
    return "bg-muted text-muted-foreground"
  }
  
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/50"
      onClick={() => onSelect?.(model)}
    >
      <CardContent className="flex items-center gap-4 p-4">
        {/* Rank */}
        <Badge className={cn("w-8 h-8 flex items-center justify-center text-sm font-bold shrink-0", getRankBadgeColor(rank || 0))}>
          {rank || '-'}
        </Badge>
        
        {/* Model info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold truncate">{modelName}</h4>
          <p className="text-sm text-muted-foreground truncate">{modelId}</p>
        </div>
        
        {/* Score/metrics */}
        <div className="text-right shrink-0">
          <div className="font-mono text-sm font-medium">
            {typeof score === 'number' 
              ? score >= 1000 
                ? score.toLocaleString()
                : score.toFixed(2)
              : score
            }
          </div>
          {metrics?.usage_count && (
            <div className="text-xs text-muted-foreground">
              {(metrics.usage_count as number).toLocaleString()} requests
            </div>
          )}
        </div>
        
        {/* Capabilities badges */}
        <div className="hidden md:flex gap-1 shrink-0">
          {model.capabilities?.supports_tools && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="h-6 w-6 p-0 flex items-center justify-center">
                    <Zap className="w-3 h-3" />
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>Tool calling</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {model.capabilities?.multimodal_input && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="h-6 w-6 p-0 flex items-center justify-center">
                    <Image className="w-3 h-3" />
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>Vision</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        
        {/* Price */}
        <div className="text-right shrink-0 w-24 hidden lg:block">
          <div className="text-sm font-medium">
            {model.pricing?.per_1m_prompt != null 
              ? formatPrice(model.pricing.per_1m_prompt)
              : "N/A"}
          </div>
        </div>
        
        <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Main Component
// =============================================================================

interface RankingsInsightsProps {
  onSelectModel?: (model: OpenRouterModel) => void
  defaultCategory?: string
  showDataProvenance?: boolean
}

export function RankingsInsights({
  onSelectModel,
  defaultCategory = "programming",
  showDataProvenance = true,
}: RankingsInsightsProps) {
  // State
  const [categories, setCategories] = React.useState<OpenRouterCategory[]>([])
  const [selectedCategory, setSelectedCategory] = React.useState<string>(defaultCategory)
  const [view, setView] = React.useState<'week' | 'month' | 'day' | 'all'>('week')
  const [rankings, setRankings] = React.useState<CategoryRankingsResponse | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [categoriesLoading, setCategoriesLoading] = React.useState(true)
  const [error, setError] = React.useState<string>()
  const [syncing, setSyncing] = React.useState(false)
  
  // Fetch categories on mount
  React.useEffect(() => {
    const fetchCategories = async () => {
      setCategoriesLoading(true)
      try {
        const data = await listCategories({ group: 'usecase' })
        setCategories(data.categories)
        
        // Set default category if not in list
        if (!data.categories.find(c => c.slug === selectedCategory)) {
          setSelectedCategory(data.categories[0]?.slug || 'programming')
        }
      } catch (e) {
        console.error('Failed to load categories:', e)
        // Use seed categories as fallback
        setCategories([
          { id: 1, slug: 'programming', display_name: 'Programming', group: 'usecase', depth: 0, is_active: true },
          { id: 2, slug: 'science', display_name: 'Science', group: 'usecase', depth: 0, is_active: true },
          { id: 3, slug: 'health', display_name: 'Health', group: 'usecase', depth: 0, is_active: true },
          { id: 4, slug: 'legal', display_name: 'Legal', group: 'usecase', depth: 0, is_active: true },
          { id: 5, slug: 'marketing', display_name: 'Marketing', group: 'usecase', depth: 0, is_active: true },
          { id: 6, slug: 'technology', display_name: 'Technology', group: 'usecase', depth: 0, is_active: true },
          { id: 7, slug: 'finance', display_name: 'Finance', group: 'usecase', depth: 0, is_active: true },
          { id: 8, slug: 'academia', display_name: 'Academia', group: 'usecase', depth: 0, is_active: true },
          { id: 9, slug: 'roleplay', display_name: 'Roleplay', group: 'usecase', depth: 0, is_active: true },
        ])
      } finally {
        setCategoriesLoading(false)
      }
    }
    
    fetchCategories()
  }, [])
  
  // Fetch rankings when category changes
  React.useEffect(() => {
    const fetchRankings = async () => {
      if (!selectedCategory) return
      
      setLoading(true)
      setError(undefined)
      
      try {
        const data = await getCategoryRankings(selectedCategory, { view, limit: 10 })
        setRankings(data)
      } catch (e) {
        console.error('Failed to load rankings:', e)
        setError(e instanceof Error ? e.message : "Failed to load rankings")
      } finally {
        setLoading(false)
      }
    }
    
    fetchRankings()
  }, [selectedCategory, view])
  
  // Handle sync
  const handleSync = async () => {
    setSyncing(true)
    try {
      await triggerRankingsSync({ full: false, categories: [selectedCategory] })
      // Refresh rankings after sync
      const data = await getCategoryRankings(selectedCategory, { view, limit: 10 })
      setRankings(data)
    } catch (e) {
      console.error('Sync failed:', e)
    } finally {
      setSyncing(false)
    }
  }
  
  const CategoryIcon = CATEGORY_ICONS[selectedCategory] || BarChart3
  const categoryColor = CATEGORY_COLORS[selectedCategory] || 'text-blue-500'
  const currentCategory = categories.find(c => c.slug === selectedCategory)
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <BarChart3 className="w-6 h-6" />
              OpenRouter Rankings
            </h2>
            <p className="text-muted-foreground mt-1">
              Top models by category from OpenRouter
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            {/* View selector */}
            <Select value={view} onValueChange={(v) => setView(v as 'week' | 'month' | 'day' | 'all')}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(VIEW_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {/* Sync button */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="outline" 
                    size="icon"
                    onClick={handleSync}
                    disabled={syncing}
                  >
                    <RefreshCw className={cn("w-4 h-4", syncing && "animate-spin")} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Sync rankings from OpenRouter</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
        
        {/* Data provenance notice */}
        {showDataProvenance && (
          <Alert className="bg-blue-500/10 border-blue-500/30">
            <ExternalLink className="h-4 w-4 text-blue-500" />
            <AlertTitle className="text-blue-500">OpenRouter Rankings</AlertTitle>
            <AlertDescription>
              Rankings synced from OpenRouter. Data reflects global usage patterns.
              {rankings?.last_synced && (
                <span className="block text-xs mt-1">
                  Last synced: {new Date(rankings.last_synced).toLocaleString()}
                </span>
              )}
            </AlertDescription>
          </Alert>
        )}
      </div>
      
      {/* Category tabs */}
      <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="flex-1 flex flex-col">
        <div className="border-b px-4">
          <ScrollArea className="w-full">
            <TabsList className="inline-flex h-12 w-max p-1">
              {categoriesLoading ? (
                <div className="flex gap-2 p-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-24" />
                  ))}
                </div>
              ) : (
                categories.map((category) => {
                  const Icon = CATEGORY_ICONS[category.slug] || BarChart3
                  const color = CATEGORY_COLORS[category.slug] || 'text-blue-500'
                  return (
                    <TabsTrigger
                      key={category.slug}
                      value={category.slug}
                      className="gap-2 data-[state=active]:bg-background"
                    >
                      <Icon className={cn("w-4 h-4", color)} />
                      <span className="hidden sm:inline">{category.display_name}</span>
                    </TabsTrigger>
                  )
                })
              )}
            </TabsList>
          </ScrollArea>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <TabsContent value={selectedCategory} className="h-full mt-0">
            <ScrollArea className="h-full">
              <div className="p-4 space-y-4">
                {/* Category header */}
                <div className="flex items-center gap-3">
                  <CategoryIcon className={cn("w-8 h-8", categoryColor)} />
                  <div>
                    <h3 className="text-xl font-semibold">
                      {currentCategory?.display_name || selectedCategory}
                    </h3>
                    <p className="text-muted-foreground">
                      Top models for {currentCategory?.display_name?.toLowerCase() || selectedCategory} tasks
                    </p>
                  </div>
                </div>
                
                {/* Rankings list */}
                {error ? (
                  <div className="text-center py-12">
                    <AlertCircle className="w-12 h-12 mx-auto text-destructive mb-4" />
                    <p className="text-destructive">{error}</p>
                    <Button variant="outline" className="mt-4" onClick={() => setSelectedCategory(selectedCategory)}>
                      Retry
                    </Button>
                  </div>
                ) : loading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 10 }).map((_, i) => (
                      <Card key={i}>
                        <CardContent className="flex items-center gap-4 p-4">
                          <Skeleton className="w-8 h-8 rounded-full" />
                          <Skeleton className="w-8 h-8 rounded-full" />
                          <div className="flex-1 space-y-2">
                            <Skeleton className="h-5 w-1/3" />
                            <Skeleton className="h-4 w-1/2" />
                          </div>
                          <Skeleton className="h-6 w-16" />
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (!rankings?.entries || rankings.entries.length === 0) ? (
                  <div className="text-center py-12">
                    <BarChart3 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                    <h3 className="text-lg font-medium">No rankings available</h3>
                    <p className="text-muted-foreground mt-1">
                      {rankings?.error || "Run a sync to populate rankings"}
                    </p>
                    <Button variant="outline" className="mt-4" onClick={handleSync} disabled={syncing}>
                      <RefreshCw className={cn("w-4 h-4 mr-2", syncing && "animate-spin")} />
                      Sync Now
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {rankings.entries.map((entry, index) => (
                      <RankingEntryRow
                        key={entry.model_id || `entry-${index}`}
                        entry={entry}
                        onSelect={(modelId) => {
                          // Create a minimal model object for selection
                          const model: OpenRouterModel = {
                            id: modelId,
                            name: entry.model_name,
                            context_length: entry.model_metadata?.context_length || 0,
                            architecture: {},
                            pricing: {
                              per_1m_prompt: entry.model_metadata?.pricing?.prompt || 0,
                              per_1m_completion: entry.model_metadata?.pricing?.completion || 0,
                            },
                            capabilities: {
                              supports_tools: entry.model_metadata?.supports_tools || false,
                              supports_structured: entry.model_metadata?.supports_structured || false,
                              supports_streaming: true,
                              multimodal_input: entry.model_metadata?.multimodal_input || false,
                              multimodal_output: false,
                            },
                            is_free: false,
                            is_active: true,
                            availability_score: entry.model_metadata?.availability_score || 0,
                          }
                          onSelectModel?.(model)
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}

export default RankingsInsights

