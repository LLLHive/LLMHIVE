"use client"

import { useState } from "react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { 
  ChevronDown, 
  Check, 
  Sparkles, 
  Layers, 
  GitBranch, 
  Users, 
  Crown,
  Zap,
  Brain,
  TreeDeciduous
} from "lucide-react"
import type { OrchestratorSettings, EliteStrategy, AdvancedReasoningMethod } from "@/lib/types"
import { cn } from "@/lib/utils"

interface OrchestrationDropdownProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

// Engines
const orchestrationEngines = [
  { key: "enableHRM" as const, label: "Hierarchical Roles (HRM)", icon: Layers },
  { key: "enablePromptDiffusion" as const, label: "Prompt Diffusion", icon: GitBranch },
  { key: "enableDeepConsensus" as const, label: "Deep Consensus", icon: Users },
  { key: "enableAdaptiveEnsemble" as const, label: "Adaptive Ensemble", icon: Sparkles },
]

// Strategies
const STRATEGY_OPTIONS: { value: EliteStrategy; label: string }[] = [
  { value: "automatic", label: "Automatic" },
  { value: "single_best", label: "Single Best" },
  { value: "parallel_race", label: "Parallel Race" },
  { value: "best_of_n", label: "Best of N" },
  { value: "quality_weighted_fusion", label: "Fusion" },
  { value: "expert_panel", label: "Expert Panel" },
  { value: "challenge_and_refine", label: "Challenge & Refine" },
]

// Reasoning methods
const REASONING_METHODS: { value: AdvancedReasoningMethod; label: string }[] = [
  { value: "automatic", label: "Automatic" },
  { value: "chain-of-thought", label: "Chain of Thought" },
  { value: "tree-of-thought", label: "Tree of Thought" },
  { value: "self-consistency", label: "Self Consistency" },
]

export function OrchestrationDropdown({
  settings,
  onSettingsChange,
}: OrchestrationDropdownProps) {
  const [open, setOpen] = useState(false)
  
  // Engines state
  const isAutomaticEngines = settings.enginesMode !== "manual"
  const activeEnginesCount = orchestrationEngines.filter((e) => settings[e.key]).length
  
  // Strategy state
  const eliteStrategy = settings.eliteStrategy ?? "automatic"
  const currentStrategy = STRATEGY_OPTIONS.find(s => s.value === eliteStrategy) || STRATEGY_OPTIONS[0]
  
  // Reasoning state
  const selectedReasoningMethods = settings.advancedReasoningMethods || ["automatic"]
  const currentReasoning = REASONING_METHODS.find(m => selectedReasoningMethods.includes(m.value)) || REASONING_METHODS[0]
  
  // Build display text
  const getDisplayText = () => {
    const parts = []
    if (isAutomaticEngines) {
      parts.push("Auto")
    } else if (activeEnginesCount > 0) {
      parts.push(`${activeEnginesCount} Engines`)
    }
    return parts.length > 0 ? parts.join(" · ") : "Orchestration"
  }

  const handleSelectAutomaticEngines = () => {
    onSettingsChange({ 
      enginesMode: "automatic",
      enableHRM: false,
      enablePromptDiffusion: false,
      enableDeepConsensus: false,
      enableAdaptiveEnsemble: false,
    })
  }

  const handleToggleEngine = (engineKey: string, enabled: boolean) => {
    onSettingsChange({ 
      enginesMode: "manual",
      [engineKey]: enabled 
    })
  }

  const handleSelectReasoning = (method: AdvancedReasoningMethod) => {
    if (method === "automatic") {
      onSettingsChange({ advancedReasoningMethods: ["automatic"] })
    } else {
      // Toggle the method
      const current = settings.advancedReasoningMethods || []
      const withoutAutomatic = current.filter(m => m !== "automatic")
      if (withoutAutomatic.includes(method)) {
        const newMethods = withoutAutomatic.filter(m => m !== method)
        onSettingsChange({ advancedReasoningMethods: newMethods.length > 0 ? newMethods : ["automatic"] })
      } else {
        onSettingsChange({ advancedReasoningMethods: [...withoutAutomatic, method] })
      }
    }
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
        >
          <Layers className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Orchestration</span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 max-h-[80vh] overflow-y-auto p-2">
        
        {/* ========== ENGINES SECTION ========== */}
        <DropdownMenuLabel className="text-xs text-muted-foreground flex items-center gap-1.5">
          <Layers className="h-3 w-3" />
          Engines
        </DropdownMenuLabel>
        
        {/* Automatic Option */}
        <div
          className={cn(
            "flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors",
            isAutomaticEngines 
              ? "bg-[var(--bronze)]/10" 
              : "hover:bg-secondary/50"
          )}
          onClick={handleSelectAutomaticEngines}
        >
          <div className={cn(
            "w-5 h-5 rounded-full flex items-center justify-center",
            isAutomaticEngines ? "bg-gradient-to-br from-[var(--bronze)] to-amber-600" : "bg-muted"
          )}>
            <Sparkles className={cn("h-3 w-3", isAutomaticEngines ? "text-white" : "text-muted-foreground")} />
          </div>
          <span className={cn("flex-1 text-sm", isAutomaticEngines && "font-medium text-[var(--bronze)]")}>
            Automatic
          </span>
          {isAutomaticEngines && <Check className="h-4 w-4 text-[var(--bronze)]" />}
        </div>
        
        {/* Manual Engines */}
        {orchestrationEngines.map((engine) => {
          const Icon = engine.icon
          const isEnabled = settings[engine.key] && !isAutomaticEngines
          return (
            <div
              key={engine.key}
              className={cn(
                "flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors",
                isEnabled ? "bg-[var(--bronze)]/10" : "hover:bg-secondary/50",
                isAutomaticEngines && "opacity-50"
              )}
              onClick={() => !isAutomaticEngines && handleToggleEngine(engine.key, !settings[engine.key])}
            >
              <div className={cn(
                "w-5 h-5 rounded flex items-center justify-center",
                isEnabled ? "bg-[var(--bronze)]/20 text-[var(--bronze)]" : "bg-muted text-muted-foreground"
              )}>
                <Icon className="h-3 w-3" />
              </div>
              <span className={cn("flex-1 text-sm", isEnabled && "font-medium text-[var(--bronze)]")}>
                {engine.label}
              </span>
              <Switch
                checked={isEnabled}
                onCheckedChange={(checked) => handleToggleEngine(engine.key, checked)}
                className="data-[state=checked]:bg-[var(--bronze)] scale-75"
                disabled={isAutomaticEngines}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          )
        })}
        
        <DropdownMenuSeparator className="my-2" />
        
        {/* ========== STRATEGY SECTION ========== */}
        <DropdownMenuLabel className="text-xs text-muted-foreground flex items-center gap-1.5">
          <Crown className="h-3 w-3" />
          Strategy
        </DropdownMenuLabel>
        
        <div className="grid grid-cols-2 gap-1">
          {STRATEGY_OPTIONS.map((option) => {
            const isSelected = eliteStrategy === option.value
            return (
              <div
                key={option.value}
                className={cn(
                  "p-2 rounded-md cursor-pointer transition-colors text-center text-xs",
                  isSelected 
                    ? "bg-[var(--bronze)]/10 text-[var(--bronze)] font-medium" 
                    : "hover:bg-secondary/50"
                )}
                onClick={() => onSettingsChange({ eliteStrategy: option.value })}
              >
                {option.label}
                {isSelected && <Check className="h-3 w-3 inline ml-1" />}
              </div>
            )
          })}
        </div>
        
        <DropdownMenuSeparator className="my-2" />
        
        {/* ========== REASONING SECTION ========== */}
        <DropdownMenuLabel className="text-xs text-muted-foreground flex items-center gap-1.5">
          <Brain className="h-3 w-3" />
          Reasoning
        </DropdownMenuLabel>
        
        {REASONING_METHODS.map((method) => {
          const isSelected = selectedReasoningMethods.includes(method.value) || 
            (method.value === "automatic" && selectedReasoningMethods.length === 0)
          const isAutomatic = method.value === "automatic"
          
          return (
            <div
              key={method.value}
              className={cn(
                "flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors",
                isSelected 
                  ? isAutomatic 
                    ? "bg-[var(--bronze)]/10" 
                    : "bg-[var(--bronze)]/10"
                  : "hover:bg-secondary/50"
              )}
              onClick={() => handleSelectReasoning(method.value)}
            >
              <div className={cn(
                "w-5 h-5 rounded flex items-center justify-center",
                isSelected 
                  ? isAutomatic 
                    ? "bg-gradient-to-br from-[var(--bronze)] to-amber-600" 
                    : "bg-[var(--bronze)]/20 text-[var(--bronze)]"
                  : "bg-muted text-muted-foreground"
              )}>
                {isAutomatic 
                  ? <Sparkles className={cn("h-3 w-3", isSelected ? "text-white" : "text-muted-foreground")} />
                  : method.value === "chain-of-thought" 
                    ? <Zap className="h-3 w-3" />
                    : method.value === "tree-of-thought"
                      ? <TreeDeciduous className="h-3 w-3" />
                      : <Brain className="h-3 w-3" />
                }
              </div>
              <span className={cn("flex-1 text-sm", isSelected && "font-medium text-[var(--bronze)]")}>
                {method.label}
              </span>
              {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
            </div>
          )
        })}
        
        <DropdownMenuSeparator className="my-2" />
        
        {/* Footer Summary */}
        <div className="px-2 py-1">
          <p className="text-[10px] text-muted-foreground">
            {isAutomaticEngines ? "🤖 Auto" : `${activeEnginesCount} engines`} · {currentStrategy.label} · {currentReasoning.label}
          </p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
