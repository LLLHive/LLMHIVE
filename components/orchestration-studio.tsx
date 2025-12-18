"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ChevronDown,
  ChevronUp,
  Zap,
  Target,
  Layers,
  Sparkles,
  Users,
  GitBranch,
  Settings2,
  DollarSign,
  BarChart3,
  Crown,
  TrendingUp,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { OrchestratorSettings, EliteStrategy } from "@/lib/types"

interface OrchestrationStudioProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
  className?: string
}

const accuracyLabels = ["Fastest", "Fast", "Balanced", "Accurate", "Most Accurate"]

const orchestrationEngines = [
  {
    key: "enableHRM" as const,
    label: "Hierarchical Roles (HRM)",
    description: "Assign specialized roles to different models",
    icon: Layers,
    color: "from-blue-500 to-indigo-600",
  },
  {
    key: "enablePromptDiffusion" as const,
    label: "Prompt Diffusion",
    description: "Iterative refinement for better outputs",
    icon: GitBranch,
    color: "from-purple-500 to-pink-600",
  },
  {
    key: "enableDeepConsensus" as const,
    label: "Deep Consensus",
    description: "Multi-round debate for accuracy",
    icon: Users,
    color: "from-emerald-500 to-teal-600",
  },
  {
    key: "enableAdaptiveEnsemble" as const,
    label: "Adaptive Ensemble",
    description: "Dynamic model weighting",
    icon: Sparkles,
    color: "from-orange-500 to-amber-600",
  },
]

// PR6: Strategy options
const STRATEGY_OPTIONS: { value: EliteStrategy; label: string; description: string }[] = [
  { value: "automatic", label: "Automatic", description: "Let the system choose the best strategy" },
  { value: "single_best", label: "Single Best", description: "Use the top-ranked model only" },
  { value: "parallel_race", label: "Parallel Race", description: "Race multiple models, return fastest quality response" },
  { value: "best_of_n", label: "Best of N", description: "Generate N responses, select the best" },
  { value: "quality_weighted_fusion", label: "Fusion", description: "Combine responses with quality weights" },
  { value: "expert_panel", label: "Expert Panel", description: "Multiple specialists synthesize insights" },
  { value: "challenge_and_refine", label: "Challenge & Refine", description: "Models critique and improve each other" },
]

export function OrchestrationStudio({
  settings,
  onSettingsChange,
  className,
}: OrchestrationStudioProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("engines")
  const accuracyLevel = settings.accuracyLevel ?? 3
  const maxCostUsd = settings.maxCostUsd ?? 1.0
  const eliteStrategy = settings.eliteStrategy ?? "automatic"

  const activeEnginesCount = orchestrationEngines.filter((e) => settings[e.key]).length
  const hasAdvancedSettings = settings.maxCostUsd !== undefined || 
                              settings.preferCheaper || 
                              (settings.eliteStrategy && settings.eliteStrategy !== "automatic")

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={cn("w-full", className)}>
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "w-full justify-between gap-2 h-9 px-3 text-xs border rounded-lg transition-all duration-300",
            isOpen
              ? "bg-[var(--bronze)]/10 border-[var(--bronze)]/30 text-[var(--bronze)]"
              : "bg-secondary/50 border-border hover:bg-secondary hover:border-[var(--bronze)]/50"
          )}
        >
          <div className="flex items-center gap-2">
            <Settings2 className="h-3.5 w-3.5" />
            <span className="font-medium">Orchestration Studio</span>
            {activeEnginesCount > 0 && (
              <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-[var(--bronze)]/20 text-[var(--bronze)]">
                {activeEnginesCount} active
              </span>
            )}
          </div>
          {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="animate-in slide-in-from-top-2 duration-200">
        <div className="mt-3 p-4 rounded-xl border border-border bg-card/50 backdrop-blur-sm space-y-4">
          {/* Accuracy vs Speed Slider */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium flex items-center gap-2">
                <Target className="h-4 w-4 text-[var(--bronze)]" />
                Accuracy vs Speed
              </Label>
              <span className="text-xs px-2 py-1 rounded-full bg-secondary text-muted-foreground">
                {accuracyLabels[accuracyLevel - 1]}
              </span>
            </div>

            <div className="relative pt-1">
              <Slider
                value={[accuracyLevel]}
                onValueChange={([value]) => onSettingsChange({ accuracyLevel: value })}
                min={1}
                max={5}
                step={1}
                className="w-full [&>span:first-child]:h-2 [&>span:first-child]:bg-secondary [&_[role=slider]]:h-5 [&_[role=slider]]:w-5 [&_[role=slider]]:border-2 [&_[role=slider]]:border-[var(--bronze)] [&_[role=slider]]:bg-background [&>span:first-child>span]:bg-gradient-to-r [&>span:first-child>span]:from-[var(--bronze)] [&>span:first-child>span]:to-[var(--gold)]"
              />
              <div className="flex justify-between mt-2">
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Zap className="h-3 w-3" />
                  Faster
                </span>
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Target className="h-3 w-3" />
                  Precise
                </span>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="h-px bg-border" />

          {/* PR6: Tabbed Settings */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3 h-8">
              <TabsTrigger value="engines" className="text-xs gap-1">
                <Layers className="h-3 w-3" />
                Engines
              </TabsTrigger>
              <TabsTrigger value="strategy" className="text-xs gap-1">
                <Crown className="h-3 w-3" />
                Strategy
              </TabsTrigger>
              <TabsTrigger value="budget" className="text-xs gap-1">
                <DollarSign className="h-3 w-3" />
                Budget
              </TabsTrigger>
            </TabsList>

            {/* Engines Tab */}
            <TabsContent value="engines" className="mt-3 space-y-2">
              {orchestrationEngines.map((engine) => {
                const Icon = engine.icon
                const isEnabled = settings[engine.key]

                return (
                  <div
                    key={engine.key}
                    className={cn(
                      "flex items-center gap-3 p-2.5 rounded-lg border transition-all duration-200",
                      isEnabled
                        ? "bg-[var(--bronze)]/5 border-[var(--bronze)]/30"
                        : "bg-secondary/30 border-border hover:border-border/80"
                    )}
                  >
                    <div
                      className={cn(
                        "w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200",
                        isEnabled
                          ? `bg-gradient-to-br ${engine.color} text-white shadow-lg`
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <Label
                        htmlFor={engine.key}
                        className={cn(
                          "text-xs font-medium cursor-pointer transition-colors",
                          isEnabled && "text-[var(--bronze)]"
                        )}
                      >
                        {engine.label}
                      </Label>
                      <p className="text-[10px] text-muted-foreground truncate">{engine.description}</p>
                    </div>
                    <Switch
                      id={engine.key}
                      checked={isEnabled}
                      onCheckedChange={(checked) => onSettingsChange({ [engine.key]: checked })}
                      className="data-[state=checked]:bg-[var(--bronze)] scale-90"
                    />
                  </div>
                )
              })}
            </TabsContent>

            {/* PR6: Strategy Tab */}
            <TabsContent value="strategy" className="mt-3 space-y-3">
              <div className="space-y-2">
                <Label className="text-xs flex items-center gap-2">
                  <TrendingUp className="h-3 w-3 text-[var(--bronze)]" />
                  Elite Strategy
                </Label>
                <Select 
                  value={eliteStrategy} 
                  onValueChange={(v) => onSettingsChange({ eliteStrategy: v as EliteStrategy })}
                >
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="Select strategy" />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGY_OPTIONS.map(option => (
                      <SelectItem key={option.value} value={option.value} className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium">{option.label}</span>
                          <span className="text-[10px] text-muted-foreground">{option.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Refinement Controls */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Enable Refinement</Label>
                  <Switch
                    checked={settings.orchestrationOverrides?.enableRefinement !== false}
                    onCheckedChange={(checked) => onSettingsChange({
                      orchestrationOverrides: {
                        ...settings.orchestrationOverrides,
                        enableRefinement: checked,
                      }
                    })}
                    className="data-[state=checked]:bg-[var(--bronze)] scale-90"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Enable Verification</Label>
                  <Switch
                    checked={settings.enableVerification !== false}
                    onCheckedChange={(checked) => onSettingsChange({ enableVerification: checked })}
                    className="data-[state=checked]:bg-[var(--bronze)] scale-90"
                  />
                </div>
              </div>

              {/* Max Iterations */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Max Iterations</Label>
                  <Badge variant="secondary" className="text-[10px]">
                    {settings.orchestrationOverrides?.maxIterations ?? 3}
                  </Badge>
                </div>
                <Slider
                  value={[settings.orchestrationOverrides?.maxIterations ?? 3]}
                  onValueChange={([value]) => onSettingsChange({
                    orchestrationOverrides: {
                      ...settings.orchestrationOverrides,
                      maxIterations: value,
                    }
                  })}
                  min={1}
                  max={5}
                  step={1}
                  className="w-full"
                />
              </div>
            </TabsContent>

            {/* PR6: Budget Tab */}
            <TabsContent value="budget" className="mt-3 space-y-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs flex items-center gap-2">
                    <DollarSign className="h-3 w-3 text-green-500" />
                    Max Cost per Request
                  </Label>
                  <Badge variant="secondary" className="text-[10px]">
                    ${maxCostUsd.toFixed(2)}
                  </Badge>
                </div>
                <Slider
                  value={[maxCostUsd]}
                  onValueChange={([value]) => onSettingsChange({ maxCostUsd: value })}
                  min={0.01}
                  max={5.0}
                  step={0.05}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>$0.01 (budget)</span>
                  <span>$5.00 (premium)</span>
                </div>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/30 border border-border">
                <div>
                  <Label className="text-xs">Prefer Cheaper Models</Label>
                  <p className="text-[10px] text-muted-foreground">
                    Prioritize cost savings when quality is comparable
                  </p>
                </div>
                <Switch
                  checked={settings.preferCheaper ?? false}
                  onCheckedChange={(checked) => onSettingsChange({ preferCheaper: checked })}
                  className="data-[state=checked]:bg-green-500 scale-90"
                />
              </div>

              {/* Cost Summary */}
              <div className="p-2.5 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
                  <BarChart3 className="h-3 w-3" />
                  <span className="font-medium">Budget-Aware Routing Active</span>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Models exceeding ${maxCostUsd.toFixed(2)} will be deprioritized
                </p>
              </div>
            </TabsContent>
          </Tabs>

          {/* Hint */}
          <p className="text-[10px] text-muted-foreground text-center">
            {activeEnginesCount > 0 ? `${activeEnginesCount} engine${activeEnginesCount > 1 ? 's' : ''} active` : 'Configure orchestration for enhanced responses'}
            {hasAdvancedSettings && ' • Advanced settings enabled'}
          </p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

