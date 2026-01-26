"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Crown, ChevronDown, TrendingUp, Check } from "lucide-react"
import type { OrchestratorSettings, EliteStrategy } from "@/lib/types"
import { cn } from "@/lib/utils"

interface StrategyDropdownProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

const STRATEGY_OPTIONS: { value: EliteStrategy; label: string; description: string }[] = [
  { value: "automatic", label: "Automatic", description: "System chooses best strategy" },
  { value: "single_best", label: "Single Best", description: "Top-ranked model only" },
  { value: "parallel_race", label: "Parallel Race", description: "Race models, fastest wins" },
  { value: "best_of_n", label: "Best of N", description: "Generate N, select best" },
  { value: "quality_weighted_fusion", label: "Fusion", description: "Combine with quality weights" },
  { value: "expert_panel", label: "Expert Panel", description: "Specialists synthesize insights" },
  { value: "challenge_and_refine", label: "Challenge & Refine", description: "Models critique each other" },
]

export function StrategyDropdown({
  settings,
  onSettingsChange,
}: StrategyDropdownProps) {
  const [open, setOpen] = useState(false)
  
  const eliteStrategy = settings.eliteStrategy ?? "automatic"
  const currentStrategy = STRATEGY_OPTIONS.find(s => s.value === eliteStrategy) || STRATEGY_OPTIONS[0]
  
  // Count active features
  const activeFeatures = [
    settings.orchestrationOverrides?.enableRefinement !== false,
    settings.enableVerification !== false,
  ].filter(Boolean).length

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
        >
          <Crown className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Strategy</span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 p-2">
        {/* Header */}
        <div className="px-2 py-1.5 mb-1">
          <span className="text-sm font-medium">Elite Strategy</span>
          <p className="text-[10px] text-muted-foreground">Choose how models work together</p>
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Strategy Selection */}
        <div className="space-y-3 py-2">
          <div className="space-y-1.5 px-1">
            <Label className="text-xs flex items-center gap-1.5">
              <TrendingUp className="h-3 w-3 text-[var(--bronze)]" />
              Strategy Mode
            </Label>
            {/* Strategy Options as clickable items */}
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {STRATEGY_OPTIONS.map((option) => {
                const isSelected = eliteStrategy === option.value
                return (
                  <div
                    key={option.value}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors",
                      isSelected 
                        ? "bg-[var(--bronze)]/10" 
                        : "hover:bg-secondary/50"
                    )}
                    onClick={() => onSettingsChange({ eliteStrategy: option.value })}
                  >
                    <div className="flex-1 min-w-0">
                      <span className={cn(
                        "text-sm font-medium",
                        isSelected && "text-[var(--bronze)]"
                      )}>
                        {option.label}
                      </span>
                      <p className="text-[10px] text-muted-foreground leading-tight">
                        {option.description}
                      </p>
                    </div>
                    {isSelected && <Check className="h-4 w-4 text-[var(--bronze)] shrink-0" />}
                  </div>
                )
              })}
            </div>
          </div>
          
          <DropdownMenuSeparator />
          
          {/* Refinement Controls */}
          <div className="space-y-2 px-1">
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
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Footer */}
        <div className="px-2 py-1.5">
          <p className="text-[10px] text-muted-foreground">
            Active: {currentStrategy.label}
          </p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
