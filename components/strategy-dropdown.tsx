"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Crown, ChevronDown, TrendingUp, Check, RefreshCw, ShieldCheck } from "lucide-react"
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
      <DropdownMenuContent align="start" className="w-80 p-3">
        {/* Header */}
        <div className="mb-2">
          <span className="text-sm font-medium">Elite Strategy</span>
          <p className="text-[10px] text-muted-foreground">Configure how models collaborate</p>
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Refinement & Verification - NOW AT TOP */}
        <div className="py-3 space-y-3">
          <div className="flex items-center justify-between p-2 rounded-md bg-secondary/30">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-[var(--bronze)]" />
              <div>
                <Label className="text-sm font-medium">Enable Refinement</Label>
                <p className="text-[10px] text-muted-foreground">Iteratively improve responses</p>
              </div>
            </div>
            <Switch
              checked={settings.orchestrationOverrides?.enableRefinement !== false}
              onCheckedChange={(checked) => onSettingsChange({
                orchestrationOverrides: {
                  ...settings.orchestrationOverrides,
                  enableRefinement: checked,
                }
              })}
              className="data-[state=checked]:bg-[var(--bronze)]"
            />
          </div>
          
          <div className="flex items-center justify-between p-2 rounded-md bg-secondary/30">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[var(--bronze)]" />
              <div>
                <Label className="text-sm font-medium">Enable Verification</Label>
                <p className="text-[10px] text-muted-foreground">Cross-check for accuracy</p>
              </div>
            </div>
            <Switch
              checked={settings.enableVerification !== false}
              onCheckedChange={(checked) => onSettingsChange({ enableVerification: checked })}
              className="data-[state=checked]:bg-[var(--bronze)]"
            />
          </div>
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Strategy Mode Section */}
        <div className="py-3">
          <Label className="text-xs flex items-center gap-1.5 mb-2 px-1">
            <TrendingUp className="h-3 w-3 text-[var(--bronze)]" />
            Strategy Mode
          </Label>
          
          {/* Strategy Options - No scrolling, all visible */}
          <div className="space-y-1">
            {STRATEGY_OPTIONS.map((option) => {
              const isSelected = eliteStrategy === option.value
              const isAutomatic = option.value === "automatic"
              
              return (
                <div
                  key={option.value}
                  className={cn(
                    "flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors",
                    isSelected 
                      ? isAutomatic 
                        ? "bg-gradient-to-r from-[var(--bronze)]/15 to-[var(--gold)]/10 border border-[var(--bronze)]/30"
                        : "bg-[var(--bronze)]/10" 
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
        
        {/* Footer */}
        <div className="pt-2 px-1">
          <p className="text-[10px] text-muted-foreground">
            Active: {currentStrategy.label}
          </p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
