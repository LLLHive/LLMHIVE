"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
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
  Zap,
  Target,
  Layers,
  Sparkles,
  Users,
  GitBranch,
  Settings2,
  DollarSign,
  Crown,
  TrendingUp,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { OrchestratorSettings, EliteStrategy } from "@/lib/types"

interface OrchestrationStudioDropdownProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

const accuracyLabels = ["Fastest", "Fast", "Balanced", "Accurate", "Most Accurate"]

const orchestrationEngines = [
  {
    key: "enableHRM" as const,
    label: "Hierarchical Roles (HRM)",
    description: "Assign specialized roles",
    icon: Layers,
  },
  {
    key: "enablePromptDiffusion" as const,
    label: "Prompt Diffusion",
    description: "Iterative refinement",
    icon: GitBranch,
  },
  {
    key: "enableDeepConsensus" as const,
    label: "Deep Consensus",
    description: "Multi-round debate",
    icon: Users,
  },
  {
    key: "enableAdaptiveEnsemble" as const,
    label: "Adaptive Ensemble",
    description: "Dynamic model weighting",
    icon: Sparkles,
  },
]

const STRATEGY_OPTIONS: { value: EliteStrategy; label: string; description: string }[] = [
  { value: "automatic", label: "Automatic", description: "System chooses best" },
  { value: "single_best", label: "Single Best", description: "Top-ranked model only" },
  { value: "parallel_race", label: "Parallel Race", description: "Race models, fastest wins" },
  { value: "best_of_n", label: "Best of N", description: "Generate N, select best" },
  { value: "quality_weighted_fusion", label: "Fusion", description: "Combine with weights" },
  { value: "expert_panel", label: "Expert Panel", description: "Specialists synthesize" },
  { value: "challenge_and_refine", label: "Challenge & Refine", description: "Models critique each other" },
]

export function OrchestrationStudioDropdown({
  settings,
  onSettingsChange,
}: OrchestrationStudioDropdownProps) {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("engines")
  
  const accuracyLevel = settings.accuracyLevel ?? 3
  const maxCostUsd = settings.maxCostUsd ?? 1.0
  const eliteStrategy = settings.eliteStrategy ?? "automatic"
  
  const activeEnginesCount = orchestrationEngines.filter((e) => settings[e.key]).length

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
        >
          <Settings2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">
            Studio {activeEnginesCount > 0 ? `(${activeEnginesCount})` : ""}
          </span>
          <span className="sm:hidden">
            {activeEnginesCount > 0 ? activeEnginesCount : "S"}
          </span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80 p-0 overflow-hidden">
        {/* Header */}
        <div className="px-3 py-2 bg-secondary/30 border-b border-border">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-[var(--bronze)]" />
              Orchestration Studio
            </span>
            {activeEnginesCount > 0 && (
              <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-[var(--bronze)]/20 text-[var(--bronze)]">
                {activeEnginesCount} active
              </span>
            )}
          </div>
        </div>
        
        <div className="p-3 space-y-3">
          {/* Accuracy vs Speed Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-medium flex items-center gap-1.5">
                <Target className="h-3 w-3 text-[var(--bronze)]" />
                Accuracy vs Speed
              </Label>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground">
                {accuracyLabels[accuracyLevel - 1]}
              </span>
            </div>

            <div className="relative">
              <Slider
                value={[accuracyLevel]}
                onValueChange={([value]) => onSettingsChange({ accuracyLevel: value })}
                min={1}
                max={5}
                step={1}
                className="w-full [&>span:first-child]:h-1.5 [&>span:first-child]:bg-secondary [&_[role=slider]]:h-4 [&_[role=slider]]:w-4 [&_[role=slider]]:border-2 [&_[role=slider]]:border-[var(--bronze)] [&_[role=slider]]:bg-background [&>span:first-child>span]:bg-gradient-to-r [&>span:first-child>span]:from-[var(--bronze)] [&>span:first-child>span]:to-[var(--gold)]"
              />
              <div className="flex justify-between mt-1">
                <span className="flex items-center gap-0.5 text-[9px] text-muted-foreground">
                  <Zap className="h-2.5 w-2.5" />
                  Faster
                </span>
                <span className="flex items-center gap-0.5 text-[9px] text-muted-foreground">
                  <Target className="h-2.5 w-2.5" />
                  Precise
                </span>
              </div>
            </div>
          </div>

          <DropdownMenuSeparator />

          {/* Tabs - Budget tab hidden for now (preserved for future tier levels) */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 h-7">
              <TabsTrigger value="engines" className="text-[10px] gap-1 px-1">
                <Layers className="h-3 w-3" />
                Engines
              </TabsTrigger>
              <TabsTrigger value="strategy" className="text-[10px] gap-1 px-1">
                <Crown className="h-3 w-3" />
                Strategy
              </TabsTrigger>
              {/* Budget tab preserved but hidden - for future account tiers
              <TabsTrigger value="budget" className="text-[10px] gap-1 px-1">
                <DollarSign className="h-3 w-3" />
                Budget
              </TabsTrigger>
              */}
            </TabsList>

            {/* Engines Tab */}
            <TabsContent value="engines" className="mt-2 space-y-1.5 max-h-48 overflow-y-auto">
              {orchestrationEngines.map((engine) => {
                const Icon = engine.icon
                const isEnabled = settings[engine.key]

                return (
                  <div
                    key={engine.key}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors",
                      isEnabled
                        ? "bg-[var(--bronze)]/10"
                        : "hover:bg-secondary/50"
                    )}
                    onClick={() => onSettingsChange({ [engine.key]: !isEnabled })}
                  >
                    <div
                      className={cn(
                        "w-6 h-6 rounded-md flex items-center justify-center shrink-0",
                        isEnabled
                          ? "bg-[var(--bronze)]/20 text-[var(--bronze)]"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      <Icon className="h-3 w-3" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <Label className={cn(
                        "text-xs font-medium cursor-pointer",
                        isEnabled && "text-[var(--bronze)]"
                      )}>
                        {engine.label}
                      </Label>
                      <p className="text-[9px] text-muted-foreground leading-tight">{engine.description}</p>
                    </div>
                    <Switch
                      checked={isEnabled}
                      onCheckedChange={(checked) => onSettingsChange({ [engine.key]: checked })}
                      className="data-[state=checked]:bg-[var(--bronze)] scale-75"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )
              })}
            </TabsContent>

            {/* Strategy Tab */}
            <TabsContent value="strategy" className="mt-2 space-y-2">
              <div className="space-y-1.5">
                <Label className="text-[10px] flex items-center gap-1.5">
                  <TrendingUp className="h-3 w-3 text-[var(--bronze)]" />
                  Elite Strategy
                </Label>
                <Select 
                  value={eliteStrategy} 
                  onValueChange={(v) => onSettingsChange({ eliteStrategy: v as EliteStrategy })}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Select strategy" />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGY_OPTIONS.map(option => (
                      <SelectItem key={option.value} value={option.value} className="text-xs">
                        <span className="font-medium">{option.label}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-[10px]">Enable Refinement</Label>
                  <Switch
                    checked={settings.orchestrationOverrides?.enableRefinement !== false}
                    onCheckedChange={(checked) => onSettingsChange({
                      orchestrationOverrides: {
                        ...settings.orchestrationOverrides,
                        enableRefinement: checked,
                      }
                    })}
                    className="data-[state=checked]:bg-[var(--bronze)] scale-75"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label className="text-[10px]">Enable Verification</Label>
                  <Switch
                    checked={settings.enableVerification !== false}
                    onCheckedChange={(checked) => onSettingsChange({ enableVerification: checked })}
                    className="data-[state=checked]:bg-[var(--bronze)] scale-75"
                  />
                </div>
              </div>
            </TabsContent>

            {/* Budget Tab - HIDDEN for now, preserved for future account tiers
            <TabsContent value="budget" className="mt-2 space-y-2">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-[10px] flex items-center gap-1.5">
                    <DollarSign className="h-3 w-3 text-[var(--bronze)]" />
                    Max Cost per Query
                  </Label>
                  <span className="text-xs font-medium text-[var(--bronze)]">
                    ${maxCostUsd.toFixed(2)}
                  </span>
                </div>
                <Slider
                  value={[maxCostUsd]}
                  onValueChange={([value]) => onSettingsChange({ maxCostUsd: value })}
                  min={0.01}
                  max={5.0}
                  step={0.01}
                  className="w-full [&>span:first-child]:h-1.5 [&>span:first-child]:bg-secondary [&_[role=slider]]:h-4 [&_[role=slider]]:w-4 [&_[role=slider]]:border-2 [&_[role=slider]]:border-[var(--bronze)] [&_[role=slider]]:bg-background [&>span:first-child>span]:bg-gradient-to-r [&>span:first-child>span]:from-emerald-500 [&>span:first-child>span]:to-emerald-400"
                />
                <div className="flex justify-between text-[9px] text-muted-foreground">
                  <span>$0.01</span>
                  <span>$5.00</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <Label className="text-[10px]">Prefer Cheaper Models</Label>
                <Switch
                  checked={settings.preferCheaper ?? false}
                  onCheckedChange={(checked) => onSettingsChange({ preferCheaper: checked })}
                  className="data-[state=checked]:bg-[var(--bronze)] scale-75"
                />
              </div>
            </TabsContent>
            */}
          </Tabs>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
