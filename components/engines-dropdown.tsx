"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Layers, Sparkles, Users, GitBranch, ChevronDown, Check } from "lucide-react"
import type { OrchestratorSettings } from "@/lib/types"
import { cn } from "@/lib/utils"

interface EnginesDropdownProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

const orchestrationEngines = [
  {
    key: "enableHRM" as const,
    label: "Hierarchical Roles (HRM)",
    description: "Assign specialized roles to models",
    icon: Layers,
  },
  {
    key: "enablePromptDiffusion" as const,
    label: "Prompt Diffusion",
    description: "Iterative refinement for better outputs",
    icon: GitBranch,
  },
  {
    key: "enableDeepConsensus" as const,
    label: "Deep Consensus",
    description: "Multi-round debate for accuracy",
    icon: Users,
  },
  {
    key: "enableAdaptiveEnsemble" as const,
    label: "Adaptive Ensemble",
    description: "Dynamic model weighting",
    icon: Sparkles,
  },
]

export function EnginesDropdown({
  settings,
  onSettingsChange,
}: EnginesDropdownProps) {
  const [open, setOpen] = useState(false)
  
  // Check if in automatic mode (default)
  const isAutomaticMode = settings.enginesMode !== "manual"
  
  // Count manually enabled engines (only shown when in manual mode)
  const activeEnginesCount = orchestrationEngines.filter((e) => settings[e.key]).length
  
  // Display text for button
  const displayText = isAutomaticMode ? "Auto" : (activeEnginesCount > 0 ? `(${activeEnginesCount})` : "")

  const handleSelectAutomatic = () => {
    onSettingsChange({ 
      enginesMode: "automatic",
      // Reset manual selections when switching to automatic
      enableHRM: false,
      enablePromptDiffusion: false,
      enableDeepConsensus: false,
      enableAdaptiveEnsemble: false,
    })
  }

  const handleToggleEngine = (engineKey: string, enabled: boolean) => {
    // Switching to manual mode when toggling individual engines
    onSettingsChange({ 
      enginesMode: "manual",
      [engineKey]: enabled 
    })
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
          <span className="hidden sm:inline">
            Engines {displayText}
          </span>
          <span className="sm:hidden">
            {isAutomaticMode ? "A" : (activeEnginesCount > 0 ? activeEnginesCount : "E")}
          </span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80 p-2">
        {/* Header */}
        <div className="px-2 py-1.5 mb-1">
          <span className="text-sm font-medium">Orchestration Engines</span>
          <p className="text-[10px] text-muted-foreground">Select how models collaborate on your queries</p>
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Automatic Option - Always at top */}
        <div
          className={cn(
            "flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-colors mt-1",
            isAutomaticMode 
              ? "bg-gradient-to-r from-[var(--bronze)]/15 to-[var(--gold)]/10 border border-[var(--bronze)]/30" 
              : "hover:bg-secondary/50"
          )}
          onClick={handleSelectAutomatic}
        >
          {/* Icon with gradient background */}
          <div className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
            isAutomaticMode 
              ? "bg-gradient-to-br from-[var(--bronze)] to-amber-600" 
              : "bg-muted"
          )}>
            <Sparkles className={cn(
              "h-4 w-4",
              isAutomaticMode ? "text-white" : "text-muted-foreground"
            )} />
          </div>
          
          {/* Label and Description */}
          <div className="flex-1 min-w-0">
            <span className={cn(
              "text-sm font-medium",
              isAutomaticMode && "text-[var(--bronze)]"
            )}>
              Automatic
            </span>
            <p className="text-[10px] text-muted-foreground leading-tight">
              AI selects the best engine(s) for each query
            </p>
          </div>
          
          {/* Check mark */}
          {isAutomaticMode && <Check className="h-5 w-5 text-[var(--bronze)] shrink-0" />}
        </div>
        
        <DropdownMenuSeparator className="my-2" />
        
        {/* Manual Engine Options */}
        <div className="px-2 py-1">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
            Manual Selection
          </span>
        </div>
        
        <div className="space-y-1 py-1">
          {orchestrationEngines.map((engine) => {
            const Icon = engine.icon
            const isEnabled = settings[engine.key] && !isAutomaticMode

            return (
              <div
                key={engine.key}
                className={cn(
                  "flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-colors",
                  isEnabled 
                    ? "bg-[var(--bronze)]/10" 
                    : "hover:bg-secondary/50",
                  isAutomaticMode && "opacity-50"
                )}
                onClick={() => handleToggleEngine(engine.key, !settings[engine.key])}
              >
                {/* Icon */}
                <div
                  className={cn(
                    "w-7 h-7 rounded-md flex items-center justify-center shrink-0 transition-colors",
                    isEnabled 
                      ? "bg-[var(--bronze)]/20 text-[var(--bronze)]" 
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                </div>
                
                {/* Label and Description */}
                <div className="flex-1 min-w-0">
                  <Label className={cn(
                    "text-sm font-medium cursor-pointer",
                    isEnabled && "text-[var(--bronze)]"
                  )}>
                    {engine.label}
                  </Label>
                  <p className="text-[10px] text-muted-foreground leading-tight">
                    {engine.description}
                  </p>
                </div>
                
                {/* Switch */}
                <Switch
                  checked={isEnabled}
                  onCheckedChange={(checked) => handleToggleEngine(engine.key, checked)}
                  className="data-[state=checked]:bg-[var(--bronze)] scale-90"
                  onClick={(e) => e.stopPropagation()}
                  disabled={isAutomaticMode}
                />
              </div>
            )
          })}
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Footer */}
        <div className="px-2 py-1.5">
          <p className="text-[10px] text-muted-foreground">
            {isAutomaticMode 
              ? "🤖 Engine selection optimized per query" 
              : `${activeEnginesCount} engine${activeEnginesCount !== 1 ? 's' : ''} manually selected`
            }
          </p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
