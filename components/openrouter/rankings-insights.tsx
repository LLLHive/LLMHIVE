"use client"

/**
 * Rankings & Insights Component
 * 
 * Interactive rankings display with:
 * - Multiple ranking dimensions (trending, most used, best value, etc.)
 * - Time range selection
 * - Filters
 * - Clear data provenance labels
 * 
 * Compliance: Rankings are built from our internal telemetry,
 * NOT scraped from OpenRouter.
 */

import * as React from "react"
import { TrendingUp, BarChart3, DollarSign, MessageSquare, Zap, Image, Clock, Shield, Info, ChevronRight, ExternalLink } from "lucide-react"
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
import { getRankings, listRankingDimensions } from "@/lib/openrouter/api"

// =============================================================================
// Constants
// =============================================================================

const DIMENSION_CONFIG: Record<RankingDimension, {
  icon: React.ElementType
  name: string
  description: string
  color: string
}> = {
  trending: {
    icon: TrendingUp,
    name: "Trending",
    description: "Models with growing usage",
    color: "text-green-500",
  },
  most_used: {
    icon: BarChart3,
    name: "Most Used",
    description: "Highest usage volume",
    color: "text-blue-500",
  },
  best_value: {
    icon: DollarSign,
    name: "Best Value",
    description: "Quality/cost ratio",
    color: "text-amber-500",
  },
  long_context: {
    icon: MessageSquare,
    name: "Long Context",
    description: "Largest context windows",
    color: "text-purple-500",
  },
  tools_agents: {
    icon: Zap,
    name: "Tools & Agents",
    description: "Best for function calling",
    color: "text-orange-500",
  },
  multimodal: {
    icon: Image,
    name: "Multimodal",
    description: "Image/audio support",
    color: "text-pink-500",
  },
  fastest: {
    icon: Clock,
    name: "Fastest",
    description: "Lowest latency",
    color: "text-cyan-500",
  },
  most_reliable: {
    icon: Shield,
    name: "Most Reliable",
    description: "Highest success rate",
    color: "text-emerald-500",
  },
  lowest_cost: {
    icon: DollarSign,
    name: "Lowest Cost",
    description: "Most affordable",
    color: "text-lime-500",
  },
}

const TIME_RANGE_LABELS: Record<TimeRange, string> = {
  "24h": "Last 24 Hours",
  "7d": "Last 7 Days",
  "30d": "Last 30 Days",
  "all": "All Time",
}

// =============================================================================
// Ranked Model Row Component
// =============================================================================

interface RankedModelRowProps {
  rankedModel: RankedModel
  onSelect?: (model: OpenRouterModel) => void
}

function RankedModelRow({ rankedModel, onSelect }: RankedModelRowProps) {
  const { model, rank, score, metrics } = rankedModel
  
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
        <Badge className={cn("w-8 h-8 flex items-center justify-center text-sm font-bold shrink-0", getRankBadgeColor(rank))}>
          {rank}
        </Badge>
        
        {/* Model info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold truncate">{model.name}</h4>
          <p className="text-sm text-muted-foreground truncate">{model.id}</p>
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
          {metrics.usage_count && (
            <div className="text-xs text-muted-foreground">
              {(metrics.usage_count as number).toLocaleString()} requests
            </div>
          )}
        </div>
        
        {/* Capabilities badges */}
        <div className="hidden md:flex gap-1 shrink-0">
          {model.capabilities.supports_tools && (
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
          {model.capabilities.multimodal_input && (
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
            {formatPrice(model.pricing.per_1m_prompt)}
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
  defaultDimension?: RankingDimension
  showDataProvenance?: boolean
}

export function RankingsInsights({
  onSelectModel,
  defaultDimension = "trending",
  showDataProvenance = true,
}: RankingsInsightsProps) {
  const [dimension, setDimension] = React.useState<RankingDimension>(defaultDimension)
  const [timeRange, setTimeRange] = React.useState<TimeRange>("7d")
  const [result, setResult] = React.useState<RankingResult>()
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string>()
  
  // Fetch rankings
  React.useEffect(() => {
    const fetchRankings = async () => {
      setLoading(true)
      setError(undefined)
      
      try {
        const data = await getRankings(dimension, { timeRange, limit: 20 })
        setResult(data)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load rankings")
      } finally {
        setLoading(false)
      }
    }
    
    fetchRankings()
  }, [dimension, timeRange])
  
  const DimensionIcon = DIMENSION_CONFIG[dimension].icon
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <BarChart3 className="w-6 h-6" />
              Rankings & Insights
            </h2>
            <p className="text-muted-foreground mt-1">
              Discover top models based on real usage data
            </p>
          </div>
          
          {/* Time range selector */}
          <Select value={timeRange} onValueChange={(v) => setTimeRange(v as TimeRange)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TIME_RANGE_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {/* Data provenance notice */}
        {showDataProvenance && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Data Source</AlertTitle>
            <AlertDescription>
              Rankings are derived from our internal usage telemetry through the LLMHive gateway.
              Last updated: {result?.generated_at 
                ? new Date(result.generated_at).toLocaleString()
                : "Loading..."}
            </AlertDescription>
          </Alert>
        )}
      </div>
      
      {/* Dimension tabs */}
      <Tabs value={dimension} onValueChange={(v) => setDimension(v as RankingDimension)} className="flex-1 flex flex-col">
        <div className="border-b px-4">
          <ScrollArea className="w-full">
            <TabsList className="inline-flex h-12 w-max p-1">
              {Object.entries(DIMENSION_CONFIG).map(([key, config]) => {
                const Icon = config.icon
                return (
                  <TabsTrigger
                    key={key}
                    value={key}
                    className="gap-2 data-[state=active]:bg-background"
                  >
                    <Icon className={cn("w-4 h-4", config.color)} />
                    <span className="hidden sm:inline">{config.name}</span>
                  </TabsTrigger>
                )
              })}
            </TabsList>
          </ScrollArea>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <TabsContent value={dimension} className="h-full mt-0">
            <ScrollArea className="h-full">
              <div className="p-4 space-y-4">
                {/* Dimension header */}
                <div className="flex items-center gap-3">
                  <DimensionIcon className={cn("w-8 h-8", DIMENSION_CONFIG[dimension].color)} />
                  <div>
                    <h3 className="text-xl font-semibold">{DIMENSION_CONFIG[dimension].name}</h3>
                    <p className="text-muted-foreground">
                      {DIMENSION_CONFIG[dimension].description}
                    </p>
                  </div>
                </div>
                
                {/* Metric definitions */}
                {result?.metric_definitions && Object.keys(result.metric_definitions).length > 0 && (
                  <div className="bg-muted/50 rounded-lg p-3 text-sm">
                    <strong>How it's measured:</strong>{" "}
                    {result.metric_definitions[Object.keys(result.metric_definitions)[0]]}
                  </div>
                )}
                
                {/* Rankings list */}
                {error ? (
                  <div className="text-center py-12">
                    <p className="text-destructive">{error}</p>
                    <Button variant="outline" className="mt-4" onClick={() => setDimension(dimension)}>
                      Retry
                    </Button>
                  </div>
                ) : loading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 10 }).map((_, i) => (
                      <Card key={i}>
                        <CardContent className="flex items-center gap-4 p-4">
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
                ) : (!result?.models || result.models.length === 0) && (!result?.data || (result.data as unknown[]).length === 0) ? (
                  <div className="text-center py-12">
                    <BarChart3 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                    <h3 className="text-lg font-medium">No data available</h3>
                    <p className="text-muted-foreground mt-1">
                      Not enough usage data for this ranking dimension
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {(result?.models || (result?.data as RankedModel[]) || []).map((rankedModel) => (
                      <RankedModelRow
                        key={rankedModel.model?.id || rankedModel.id}
                        rankedModel={rankedModel}
                        onSelect={onSelectModel}
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

