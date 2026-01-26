"use client"

import { useState } from "react"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import {
  ChevronDown,
  Zap,
  Target,
  Settings2,
} from "lucide-react"
import type { OrchestratorSettings } from "@/lib/types"

interface OrchestrationStudioDropdownProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

const accuracyLabels = ["Fastest", "Fast", "Balanced", "Accurate", "Most Accurate"]

export function OrchestrationStudioDropdown({
  settings,
  onSettingsChange,
}: OrchestrationStudioDropdownProps) {
  const [open, setOpen] = useState(false)
  
  const accuracyLevel = settings.accuracyLevel ?? 3

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
        >
          <Settings2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Studio</span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 p-3">
        {/* Header */}
        <div className="mb-3">
          <span className="text-sm font-medium flex items-center gap-2">
            <Target className="h-4 w-4 text-[var(--bronze)]" />
            Accuracy vs Speed
          </span>
          <p className="text-[10px] text-muted-foreground mt-0.5">Balance precision and response time</p>
        </div>
        
        {/* Accuracy Slider */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Current:</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--bronze)]/10 text-[var(--bronze)] font-medium">
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
          
          {/* Level indicators */}
          <div className="flex justify-between px-1">
            {[1, 2, 3, 4, 5].map((level) => (
              <div
                key={level}
                className={`w-6 h-1 rounded-full transition-colors ${
                  level <= accuracyLevel 
                    ? "bg-[var(--bronze)]" 
                    : "bg-muted"
                }`}
              />
            ))}
          </div>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
