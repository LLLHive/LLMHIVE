"use client"

/**
 * Model Explorer Component
 * 
 * Interactive model catalog browser with:
 * - Search by name, intent, capabilities
 * - Filters for context, pricing, modalities
 * - Sorting by various dimensions
 * - Model cards with plain-language descriptions
 * - Side-by-side comparison
 */

import * as React from "react"
import { Search, Filter, SlidersHorizontal, X, ChevronDown, Check, Zap, MessageSquare, Image, Code, DollarSign, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"

import type { OpenRouterModel, ModelFilters, ModelListResponse } from "@/lib/openrouter/types"
import { formatPrice, formatContextLength, getPriceTier } from "@/lib/openrouter/types"
import { listModels, searchModels } from "@/lib/openrouter/api"

// =============================================================================
// Types
// =============================================================================

interface ModelExplorerProps {
  onSelectModel?: (model: OpenRouterModel) => void
  selectedModelId?: string
  showComparison?: boolean
  maxCompare?: number
}

// =============================================================================
// Model Card Component
// =============================================================================

interface ModelCardProps {
  model: OpenRouterModel
  onSelect?: () => void
  isSelected?: boolean
  onCompare?: () => void
  isComparing?: boolean
}

function ModelCard({ model, onSelect, isSelected, onCompare, isComparing }: ModelCardProps) {
  const priceTier = getPriceTier(model.pricing.per_1m_prompt)
  
  const priceTierColors = {
    free: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
    budget: "bg-blue-500/10 text-blue-600 border-blue-500/20",
    standard: "bg-amber-500/10 text-amber-600 border-amber-500/20",
    premium: "bg-purple-500/10 text-purple-600 border-purple-500/20",
  }
  
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-200 hover:shadow-lg hover:border-primary/50",
        isSelected && "ring-2 ring-primary border-primary",
        isComparing && "ring-2 ring-blue-500 border-blue-500"
      )}
      onClick={onSelect}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold truncate">
              {model.name}
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-1">
              {model.id}
            </CardDescription>
          </div>
          <Badge variant="outline" className={cn("text-xs shrink-0", priceTierColors[priceTier])}>
            {priceTier === 'free' ? 'Free' : formatPrice(model.pricing.per_1m_prompt)}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-3">
        {/* Description */}
        {model.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {model.description}
          </p>
        )}
        
        {/* Capabilities */}
        <div className="flex flex-wrap gap-1.5">
          {model.capabilities.supports_tools && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Zap className="w-3 h-3" />
                    Tools
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  Supports function/tool calling for agents
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          
          {model.capabilities.multimodal_input && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Image className="w-3 h-3" />
                    Vision
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  Can understand images
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          
          {model.capabilities.supports_structured && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="text-xs gap-1">
                    <Code className="w-3 h-3" />
                    JSON
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  Supports structured JSON output
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          
          {(model.context_length || 0) >= 100000 && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Badge variant="secondary" className="text-xs gap-1">
                    <MessageSquare className="w-3 h-3" />
                    Long
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  {formatContextLength(model.context_length)} context window
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        
        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Context: {formatContextLength(model.context_length)}</span>
          {model.availability_score < 100 && (
            <span className={cn(
              model.availability_score < 90 ? "text-amber-600" : ""
            )}>
              {model.availability_score.toFixed(0)}% uptime
            </span>
          )}
        </div>
        
        {/* Strengths (derived) */}
        {model.strengths && model.strengths.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-1">
              Best for: <span className="text-foreground">{model.strengths[0]}</span>
            </p>
          </div>
        )}
        
        {/* Compare button */}
        {onCompare && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-2"
            onClick={(e) => {
              e.stopPropagation()
              onCompare()
            }}
          >
            {isComparing ? (
              <>
                <Check className="w-4 h-4 mr-2" />
                Comparing
              </>
            ) : (
              <>
                <SlidersHorizontal className="w-4 h-4 mr-2" />
                Compare
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Filter Panel Component
// =============================================================================

interface FilterPanelProps {
  filters: ModelFilters
  onChange: (filters: ModelFilters) => void
}

function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const updateFilter = (key: keyof ModelFilters, value: unknown) => {
    onChange({ ...filters, [key]: value })
  }
  
  return (
    <div className="space-y-6 p-4">
      {/* Price Range */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Price Range</Label>
        <p className="text-xs text-muted-foreground">
          Maximum cost per million input tokens
        </p>
        <div className="space-y-4">
          <Slider
            value={[filters.max_price_per_1m || 100]}
            onValueChange={([val]) => updateFilter('max_price_per_1m', val)}
            max={100}
            min={0}
            step={1}
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Free</span>
            <span>${filters.max_price_per_1m || 100}/M</span>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="is_free"
              checked={filters.is_free || false}
              onCheckedChange={(checked) => updateFilter('is_free', checked ? true : undefined)}
            />
            <Label htmlFor="is_free" className="text-sm">
              Free models only
            </Label>
          </div>
        </div>
      </div>
      
      {/* Context Length */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Context Window</Label>
        <p className="text-xs text-muted-foreground">
          How much text the model can process at once
        </p>
        <Select
          value={filters.min_context?.toString() || "0"}
          onValueChange={(val) => updateFilter('min_context', parseInt(val) || undefined)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Any size" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">Any size</SelectItem>
            <SelectItem value="8000">8K+ tokens (~3 pages)</SelectItem>
            <SelectItem value="32000">32K+ tokens (~12 pages)</SelectItem>
            <SelectItem value="100000">100K+ tokens (~40 pages)</SelectItem>
            <SelectItem value="200000">200K+ tokens (~80 pages)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {/* Capabilities */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Capabilities</Label>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="supports_tools"
              checked={filters.supports_tools || false}
              onCheckedChange={(checked) => updateFilter('supports_tools', checked ? true : undefined)}
            />
            <Label htmlFor="supports_tools" className="text-sm">
              <span className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Tool/Function calling
              </span>
            </Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="supports_structured"
              checked={filters.supports_structured || false}
              onCheckedChange={(checked) => updateFilter('supports_structured', checked ? true : undefined)}
            />
            <Label htmlFor="supports_structured" className="text-sm">
              <span className="flex items-center gap-2">
                <Code className="w-4 h-4" />
                Structured JSON output
              </span>
            </Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="multimodal_input"
              checked={filters.multimodal_input || false}
              onCheckedChange={(checked) => updateFilter('multimodal_input', checked ? true : undefined)}
            />
            <Label htmlFor="multimodal_input" className="text-sm">
              <span className="flex items-center gap-2">
                <Image className="w-4 h-4" />
                Image understanding
              </span>
            </Label>
          </div>
        </div>
      </div>
      
      {/* Sort */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Sort By</Label>
        <Select
          value={`${filters.sort_by || 'name'}-${filters.sort_order || 'asc'}`}
          onValueChange={(val) => {
            const [sort_by, sort_order] = val.split('-') as [ModelFilters['sort_by'], ModelFilters['sort_order']]
            onChange({ ...filters, sort_by, sort_order })
          }}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="name-asc">Name (A-Z)</SelectItem>
            <SelectItem value="name-desc">Name (Z-A)</SelectItem>
            <SelectItem value="price_per_1m_prompt-asc">Price (Low to High)</SelectItem>
            <SelectItem value="price_per_1m_prompt-desc">Price (High to Low)</SelectItem>
            <SelectItem value="context_length-desc">Context (Largest first)</SelectItem>
            <SelectItem value="context_length-asc">Context (Smallest first)</SelectItem>
            <SelectItem value="availability_score-desc">Availability (Best first)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {/* Clear filters */}
      <Button
        variant="outline"
        className="w-full"
        onClick={() => onChange({})}
      >
        Clear All Filters
      </Button>
    </div>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export function ModelExplorer({
  onSelectModel,
  selectedModelId,
  showComparison = true,
  maxCompare = 4,
}: ModelExplorerProps) {
  const [models, setModels] = React.useState<OpenRouterModel[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string>()
  const [total, setTotal] = React.useState(0)
  
  const [filters, setFilters] = React.useState<ModelFilters>({
    limit: 24,
    offset: 0,
  })
  
  const [searchQuery, setSearchQuery] = React.useState("")
  const [comparingModels, setComparingModels] = React.useState<string[]>([])
  
  // Fetch models
  React.useEffect(() => {
    const fetchModels = async () => {
      setLoading(true)
      setError(undefined)
      
      try {
        const response = searchQuery
          ? await searchModels(searchQuery, filters)
          : await listModels(filters)
        
        setModels(response.data)
        setTotal(response.total)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load models")
      } finally {
        setLoading(false)
      }
    }
    
    const debounceTimer = setTimeout(fetchModels, 300)
    return () => clearTimeout(debounceTimer)
  }, [filters, searchQuery])
  
  const toggleCompare = (modelId: string) => {
    setComparingModels((prev) => {
      if (prev.includes(modelId)) {
        return prev.filter((id) => id !== modelId)
      }
      if (prev.length >= maxCompare) {
        return prev
      }
      return [...prev, modelId]
    })
  }
  
  const activeFiltersCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== "" && v !== 24 && v !== 0
  ).length
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-col gap-4 p-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search models... (e.g., 'good for coding', 'cheap', 'GPT')"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                onClick={() => setSearchQuery("")}
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
          
          {/* Filter button */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Filter className="w-4 h-4" />
                Filters
                {activeFiltersCount > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {activeFiltersCount}
                  </Badge>
                )}
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Filter Models</SheetTitle>
                <SheetDescription>
                  Narrow down models by capabilities and pricing
                </SheetDescription>
              </SheetHeader>
              <FilterPanel filters={filters} onChange={setFilters} />
            </SheetContent>
          </Sheet>
        </div>
        
        {/* Active filters */}
        {activeFiltersCount > 0 && (
          <div className="flex flex-wrap gap-2">
            {filters.is_free && (
              <Badge variant="secondary" className="gap-1">
                Free only
                <X
                  className="w-3 h-3 cursor-pointer"
                  onClick={() => setFilters({ ...filters, is_free: undefined })}
                />
              </Badge>
            )}
            {filters.supports_tools && (
              <Badge variant="secondary" className="gap-1">
                Tool calling
                <X
                  className="w-3 h-3 cursor-pointer"
                  onClick={() => setFilters({ ...filters, supports_tools: undefined })}
                />
              </Badge>
            )}
            {filters.multimodal_input && (
              <Badge variant="secondary" className="gap-1">
                Vision
                <X
                  className="w-3 h-3 cursor-pointer"
                  onClick={() => setFilters({ ...filters, multimodal_input: undefined })}
                />
              </Badge>
            )}
            {filters.min_context && (
              <Badge variant="secondary" className="gap-1">
                {formatContextLength(filters.min_context)}+ context
                <X
                  className="w-3 h-3 cursor-pointer"
                  onClick={() => setFilters({ ...filters, min_context: undefined })}
                />
              </Badge>
            )}
          </div>
        )}
        
        {/* Results count */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {loading ? "Loading..." : `${total} models found`}
          </span>
          
          {showComparison && comparingModels.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setComparingModels([])}
            >
              Clear comparison ({comparingModels.length})
            </Button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {error ? (
            <div className="text-center py-12">
              <p className="text-destructive">{error}</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setFilters({ ...filters })}
              >
                Retry
              </Button>
            </div>
          ) : loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="h-5 w-3/4" />
                    <Skeleton className="h-4 w-1/2 mt-1" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-12 w-full" />
                    <div className="flex gap-2 mt-3">
                      <Skeleton className="h-6 w-16" />
                      <Skeleton className="h-6 w-16" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : models.length === 0 ? (
            <div className="text-center py-12">
              <Sparkles className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No models found</h3>
              <p className="text-muted-foreground mt-1">
                Try adjusting your search or filters
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {models.map((model) => (
                <ModelCard
                  key={model.id}
                  model={model}
                  onSelect={() => onSelectModel?.(model)}
                  isSelected={model.id === selectedModelId}
                  onCompare={showComparison ? () => toggleCompare(model.id) : undefined}
                  isComparing={comparingModels.includes(model.id)}
                />
              ))}
            </div>
          )}
          
          {/* Load more */}
          {!loading && models.length < total && (
            <div className="text-center mt-6">
              <Button
                variant="outline"
                onClick={() =>
                  setFilters({
                    ...filters,
                    limit: (filters.limit || 24) + 24,
                  })
                }
              >
                Load More
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

export default ModelExplorer

