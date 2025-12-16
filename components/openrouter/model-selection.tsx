"use client"

import * as React from "react"
import { Check, Crown, Lock, Plus, Settings2, Sparkles, Star, X, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { type OpenRouterModel } from "@/lib/openrouter/types"
import {
  type UserTier,
  type SelectedModelConfig,
  type UserModelPreferences,
  getModelRequiredTier,
  canAccessModel,
  getTierBadgeColor,
  getTierDisplayName,
  TIER_CONFIGS,
  STORAGE_KEYS,
} from "@/lib/openrouter/tiers"

// =============================================================================
// Types
// =============================================================================

interface ModelSelectionProps {
  models: OpenRouterModel[]
  userTier: UserTier
  onSelectionChange?: (selectedModels: SelectedModelConfig[]) => void
  maxSelectableModels?: number
  className?: string
}

interface SelectedModelCardProps {
  model: OpenRouterModel
  config: SelectedModelConfig
  userTier: UserTier
  onUpdate: (config: SelectedModelConfig) => void
  onRemove: () => void
}

// =============================================================================
// Hooks
// =============================================================================

function useModelPreferences(userId: string = 'default') {
  const [preferences, setPreferences] = React.useState<UserModelPreferences | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)

  // Load preferences from localStorage
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER_MODEL_PREFERENCES)
      if (stored) {
        const parsed = JSON.parse(stored) as UserModelPreferences
        if (parsed.userId === userId) {
          setPreferences(parsed)
        }
      }
    } catch (e) {
      console.error('Failed to load model preferences:', e)
    } finally {
      setIsLoading(false)
    }
  }, [userId])

  // Save preferences to localStorage
  const savePreferences = React.useCallback((newPrefs: UserModelPreferences) => {
    try {
      localStorage.setItem(STORAGE_KEYS.USER_MODEL_PREFERENCES, JSON.stringify(newPrefs))
      setPreferences(newPrefs)
    } catch (e) {
      console.error('Failed to save model preferences:', e)
    }
  }, [])

  return { preferences, savePreferences, isLoading }
}

// =============================================================================
// Selected Model Card Component
// =============================================================================

function SelectedModelCard({ model, config, userTier, onUpdate, onRemove }: SelectedModelCardProps) {
  const [showSettings, setShowSettings] = React.useState(false)
  const requiredTier = getModelRequiredTier(model.id)

  return (
    <Card className="relative group">
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={onRemove}
      >
        <X className="h-4 w-4" />
      </Button>

      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="font-medium text-sm truncate">{model.name}</h4>
              <Badge 
                variant="outline" 
                className={cn("text-[10px] px-1.5", getTierBadgeColor(requiredTier))}
              >
                {getTierDisplayName(requiredTier)}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {model.id}
            </p>
          </div>

          <Switch
            checked={config.enabled}
            onCheckedChange={(enabled) => onUpdate({ ...config, enabled })}
          />
        </div>

        {/* Role selector */}
        <div className="mt-3 flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">Role:</Label>
          <Select
            value={config.preferredRole || 'primary'}
            onValueChange={(value) => onUpdate({ 
              ...config, 
              preferredRole: value as SelectedModelConfig['preferredRole'] 
            })}
          >
            <SelectTrigger className="h-7 text-xs flex-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="primary">Primary</SelectItem>
              <SelectItem value="validator">Validator</SelectItem>
              <SelectItem value="specialist">Specialist</SelectItem>
              <SelectItem value="fallback">Fallback</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings2 className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Advanced settings */}
        {showSettings && (
          <div className="mt-3 pt-3 border-t space-y-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Temperature</Label>
                <span className="text-xs text-muted-foreground">
                  {config.customSettings?.temperature ?? 0.7}
                </span>
              </div>
              <Slider
                value={[config.customSettings?.temperature ?? 0.7]}
                onValueChange={([v]) => onUpdate({
                  ...config,
                  customSettings: { ...config.customSettings, temperature: v }
                })}
                min={0}
                max={2}
                step={0.1}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Max Tokens</Label>
                <span className="text-xs text-muted-foreground">
                  {config.customSettings?.maxTokens ?? 4096}
                </span>
              </div>
              <Slider
                value={[config.customSettings?.maxTokens ?? 4096]}
                onValueChange={([v]) => onUpdate({
                  ...config,
                  customSettings: { ...config.customSettings, maxTokens: v }
                })}
                min={256}
                max={model.context_length || 32000}
                step={256}
                className="w-full"
              />
            </div>
          </div>
        )}

        {/* Capability badges */}
        <div className="mt-2 flex flex-wrap gap-1">
          {model.capabilities?.supports_tools && (
            <Badge variant="secondary" className="text-[10px] h-5">Tools</Badge>
          )}
          {model.capabilities?.supports_streaming && (
            <Badge variant="secondary" className="text-[10px] h-5">Stream</Badge>
          )}
          {model.capabilities?.multimodal_input && (
            <Badge variant="secondary" className="text-[10px] h-5">Vision</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Model Selection Component
// =============================================================================

export function ModelSelection({
  models,
  userTier,
  onSelectionChange,
  maxSelectableModels,
  className,
}: ModelSelectionProps) {
  const { preferences, savePreferences, isLoading } = useModelPreferences()
  const [selectedModels, setSelectedModels] = React.useState<SelectedModelConfig[]>([])
  const [isAddDialogOpen, setIsAddDialogOpen] = React.useState(false)
  const [searchQuery, setSearchQuery] = React.useState('')

  const tierConfig = TIER_CONFIGS[userTier]
  const maxModels = maxSelectableModels ?? tierConfig.maxModelsInTeam

  // Load selected models from preferences
  React.useEffect(() => {
    if (preferences?.selectedModels) {
      setSelectedModels(preferences.selectedModels)
    }
  }, [preferences])

  // Notify parent of changes
  React.useEffect(() => {
    onSelectionChange?.(selectedModels)
  }, [selectedModels, onSelectionChange])

  // Get selected model objects
  const selectedModelObjects = React.useMemo(() => {
    return selectedModels.map(config => ({
      config,
      model: models.find(m => m.id === config.modelId),
    })).filter(item => item.model != null) as { config: SelectedModelConfig; model: OpenRouterModel }[]
  }, [selectedModels, models])

  // Available models for selection (not already selected and accessible)
  const availableModels = React.useMemo(() => {
    const selectedIds = new Set(selectedModels.map(m => m.modelId))
    return models.filter(m => 
      !selectedIds.has(m.id) && 
      canAccessModel(userTier, m.id)
    )
  }, [models, selectedModels, userTier])

  // Filtered models for search
  const filteredModels = React.useMemo(() => {
    if (!searchQuery) return availableModels.slice(0, 50)
    const query = searchQuery.toLowerCase()
    return availableModels.filter(m => 
      m.name.toLowerCase().includes(query) ||
      m.id.toLowerCase().includes(query) ||
      m.description?.toLowerCase().includes(query)
    ).slice(0, 50)
  }, [availableModels, searchQuery])

  // Locked models (require higher tier)
  const lockedModels = React.useMemo(() => {
    return models.filter(m => !canAccessModel(userTier, m.id)).slice(0, 10)
  }, [models, userTier])

  const handleAddModel = (model: OpenRouterModel) => {
    if (selectedModels.length >= maxModels) {
      toast.error(`Maximum ${maxModels} models allowed for ${tierConfig.displayName} tier`)
      return
    }

    const newConfig: SelectedModelConfig = {
      modelId: model.id,
      enabled: true,
      preferredRole: 'primary',
      addedAt: new Date().toISOString(),
    }

    const newSelectedModels = [...selectedModels, newConfig]
    setSelectedModels(newSelectedModels)
    
    if (preferences) {
      savePreferences({
        ...preferences,
        selectedModels: newSelectedModels,
        updatedAt: new Date().toISOString(),
      })
    } else {
      savePreferences({
        userId: 'default',
        tier: userTier,
        selectedModels: newSelectedModels,
        preferredTeamSize: maxModels,
        autoSelectEnabled: false,
        updatedAt: new Date().toISOString(),
      })
    }

    toast.success(`Added ${model.name} to orchestration`)
    setIsAddDialogOpen(false)
  }

  const handleUpdateModel = (index: number, config: SelectedModelConfig) => {
    const newSelectedModels = [...selectedModels]
    newSelectedModels[index] = config
    setSelectedModels(newSelectedModels)

    if (preferences) {
      savePreferences({
        ...preferences,
        selectedModels: newSelectedModels,
        updatedAt: new Date().toISOString(),
      })
    }
  }

  const handleRemoveModel = (index: number) => {
    const removed = selectedModels[index]
    const newSelectedModels = selectedModels.filter((_, i) => i !== index)
    setSelectedModels(newSelectedModels)

    if (preferences) {
      savePreferences({
        ...preferences,
        selectedModels: newSelectedModels,
        updatedAt: new Date().toISOString(),
      })
    }

    const model = models.find(m => m.id === removed.modelId)
    toast.success(`Removed ${model?.name || removed.modelId} from orchestration`)
  }

  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <div className="animate-pulse text-muted-foreground">Loading preferences...</div>
      </div>
    )
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Your Orchestration Models</h3>
          <p className="text-sm text-muted-foreground">
            Select up to {maxModels} models for your AI team ({selectedModels.length}/{maxModels} selected)
          </p>
        </div>

        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button 
              disabled={selectedModels.length >= maxModels}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Add Model
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle>Add Model to Orchestration</DialogTitle>
              <DialogDescription>
                Select a model to add to your AI team. Models are filtered based on your {tierConfig.displayName} tier.
              </DialogDescription>
            </DialogHeader>

            {/* Search */}
            <div className="relative">
              <input
                type="text"
                placeholder="Search models..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm"
              />
            </div>

            {/* Available models list */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-2">
              {filteredModels.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No models found matching your search.
                </p>
              ) : (
                filteredModels.map((model) => {
                  const requiredTier = getModelRequiredTier(model.id)
                  return (
                    <Card
                      key={model.id}
                      className="cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => handleAddModel(model)}
                    >
                      <CardContent className="p-3 flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm truncate">{model.name}</span>
                            <Badge 
                              variant="outline" 
                              className={cn("text-[10px] shrink-0", getTierBadgeColor(requiredTier))}
                            >
                              {getTierDisplayName(requiredTier)}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground truncate">{model.id}</p>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {model.capabilities?.supports_tools && (
                            <Badge variant="secondary" className="text-[10px]">Tools</Badge>
                          )}
                          {model.capabilities?.multimodal_input && (
                            <Badge variant="secondary" className="text-[10px]">Vision</Badge>
                          )}
                        </div>
                        <Button size="sm" variant="ghost">
                          <Plus className="h-4 w-4" />
                        </Button>
                      </CardContent>
                    </Card>
                  )
                })
              )}

              {/* Locked models section */}
              {lockedModels.length > 0 && (
                <div className="pt-4 border-t mt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Lock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-muted-foreground">
                      Upgrade to access premium models
                    </span>
                  </div>
                  {lockedModels.map((model) => {
                    const requiredTier = getModelRequiredTier(model.id)
                    return (
                      <Card key={model.id} className="opacity-50 cursor-not-allowed mb-2">
                        <CardContent className="p-3 flex items-center gap-3">
                          <Lock className="h-4 w-4 text-muted-foreground shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm truncate">{model.name}</span>
                              <Badge 
                                variant="outline" 
                                className={cn("text-[10px] shrink-0", getTierBadgeColor(requiredTier))}
                              >
                                {getTierDisplayName(requiredTier)} required
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground truncate">{model.id}</p>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Tier info banner */}
      <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
        <CardContent className="p-4 flex items-center gap-4">
          <div className="p-2 rounded-full bg-primary/10">
            {userTier === 'enterprise' ? (
              <Crown className="h-5 w-5 text-primary" />
            ) : userTier === 'pro' ? (
              <Sparkles className="h-5 w-5 text-primary" />
            ) : userTier === 'starter' ? (
              <Star className="h-5 w-5 text-primary" />
            ) : (
              <Zap className="h-5 w-5 text-primary" />
            )}
          </div>
          <div className="flex-1">
            <h4 className="font-medium">{tierConfig.displayName} Tier</h4>
            <p className="text-sm text-muted-foreground">
              {tierConfig.description} • Up to {tierConfig.maxModelsInTeam} models in teams
            </p>
          </div>
          {userTier !== 'enterprise' && (
            <Button variant="outline" size="sm">
              Upgrade
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Selected models grid */}
      {selectedModels.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-8 text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
              <Plus className="h-6 w-6 text-muted-foreground" />
            </div>
            <h4 className="font-medium mb-1">No models selected</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Add models to create your AI orchestration team
            </p>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              Add Your First Model
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {selectedModelObjects.map(({ config, model }, index) => (
            <SelectedModelCard
              key={config.modelId}
              model={model}
              config={config}
              userTier={userTier}
              onUpdate={(newConfig) => handleUpdateModel(index, newConfig)}
              onRemove={() => handleRemoveModel(index)}
            />
          ))}

          {/* Add more card */}
          {selectedModels.length < maxModels && (
            <Card 
              className="border-dashed cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => setIsAddDialogOpen(true)}
            >
              <CardContent className="p-4 flex flex-col items-center justify-center h-full min-h-[120px]">
                <Plus className="h-8 w-8 text-muted-foreground mb-2" />
                <span className="text-sm text-muted-foreground">Add Model</span>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

export default ModelSelection

