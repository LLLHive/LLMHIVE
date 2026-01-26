"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Layers, Sparkles, Users, GitBranch, ChevronDown } from "lucide-react"
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
  
  const activeEnginesCount = orchestrationEngines.filter((e) => settings[e.key]).length

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
            Engines {activeEnginesCount > 0 ? `(${activeEnginesCount})` : ""}
          </span>
          <span className="sm:hidden">
            {activeEnginesCount > 0 ? activeEnginesCount : "E"}
          </span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 p-2">
        {/* Header */}
        <div className="px-2 py-1.5 mb-1">
          <span className="text-sm font-medium">Orchestration Engines</span>
          <p className="text-[10px] text-muted-foreground">Enable advanced orchestration strategies</p>
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Engine Options */}
        <div className="space-y-1 py-1">
          {orchestrationEngines.map((engine) => {
            const Icon = engine.icon
            const isEnabled = settings[engine.key]

            return (
              <div
                key={engine.key}
                className={cn(
                  "flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-colors",
                  isEnabled 
                    ? "bg-[var(--bronze)]/10" 
                    : "hover:bg-secondary/50"
                )}
                onClick={() => onSettingsChange({ [engine.key]: !isEnabled })}
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
                  onCheckedChange={(checked) => onSettingsChange({ [engine.key]: checked })}
                  className="data-[state=checked]:bg-[var(--bronze)] scale-90"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            )
          })}
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Footer */}
        <div className="px-2 py-1.5">
          <p className="text-[10px] text-muted-foreground">
            {activeEnginesCount} of {orchestrationEngines.length} engines active
          </p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
