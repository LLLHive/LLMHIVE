"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Lightbulb, CheckCircle, ListTree, GraduationCap, SpellCheck, Settings2, ChevronDown } from "lucide-react"
import type { OrchestratorSettings } from "@/lib/types"
import { cn } from "@/lib/utils"

interface AdvancedSettingsDropdownProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

// Note: Shared Memory and Clarification Questions are always enabled in the backend
// so their toggles have been removed (they were non-functional UI toggles)
const toggleOptions = [
  {
    key: "promptOptimization" as const,
    label: "Prompt Optimization",
    description: "Enhance prompts for better results",
    icon: Lightbulb,
  },
  {
    key: "outputValidation" as const,
    label: "Output Validation",
    description: "Verify and fact-check responses",
    icon: CheckCircle,
  },
  {
    key: "answerStructure" as const,
    label: "Answer Structure",
    description: "Format with clear sections",
    icon: ListTree,
  },
  {
    key: "learnFromChat" as const,
    label: "Learn from Chat",
    description: "Improve based on conversation",
    icon: GraduationCap,
  },
  {
    key: "enableSpellCheck" as const,
    label: "Spell Check",
    description: "Auto-correct spelling in prompts",
    icon: SpellCheck,
  },
]

export function AdvancedSettingsDropdown({
  settings,
  onSettingsChange,
}: AdvancedSettingsDropdownProps) {
  const [open, setOpen] = useState(false)
  
  // Count enabled settings
  const enabledCount = toggleOptions.filter(
    (option) => (settings as any)[option.key]
  ).length

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
            Advanced {enabledCount > 0 ? `(${enabledCount})` : ""}
          </span>
          <span className="sm:hidden">
            {enabledCount > 0 ? enabledCount : "A"}
          </span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72 max-h-[70vh] overflow-y-auto p-2">
        {/* Header */}
        <div className="px-2 py-1.5 mb-1">
          <span className="text-sm font-medium">Advanced Tuning</span>
          <p className="text-[10px] text-muted-foreground">Fine-tune orchestration behavior</p>
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Toggle Options */}
        <div className="space-y-1 py-1">
          {toggleOptions.map((option) => {
            const Icon = option.icon
            const isEnabled = (settings as any)[option.key]

            return (
              <div
                key={option.key}
                className={cn(
                  "flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-colors",
                  isEnabled 
                    ? "bg-[var(--bronze)]/10" 
                    : "hover:bg-secondary/50"
                )}
                onClick={() => onSettingsChange({ [option.key]: !isEnabled })}
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
                  <Label className="text-sm font-medium cursor-pointer">
                    {option.label}
                  </Label>
                  <p className="text-[10px] text-muted-foreground leading-tight">
                    {option.description}
                  </p>
                </div>
                
                {/* Switch */}
                <Switch
                  checked={isEnabled}
                  onCheckedChange={(checked) => onSettingsChange({ [option.key]: checked })}
                  className="data-[state=checked]:bg-[var(--bronze)] scale-90"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            )
          })}
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Footer */}
        <div className="px-2 py-1.5 mt-1">
          <p className="text-[10px] text-muted-foreground">
            {enabledCount} of {toggleOptions.length} enabled • Applied automatically
          </p>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
