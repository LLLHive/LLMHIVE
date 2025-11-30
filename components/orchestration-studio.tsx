"use client"

import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
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
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { OrchestratorSettings } from "@/lib/types"

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

export function OrchestrationStudio({
  settings,
  onSettingsChange,
  className,
}: OrchestrationStudioProps) {
  const [isOpen, setIsOpen] = useState(false)
  const accuracyLevel = settings.accuracyLevel ?? 3

  const activeEnginesCount = orchestrationEngines.filter((e) => settings[e.key]).length

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
        <div className="mt-3 p-4 rounded-xl border border-border bg-card/50 backdrop-blur-sm space-y-5">
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

          {/* Orchestration Engine Toggles */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Orchestration Engines</Label>
            <div className="grid gap-2">
              {orchestrationEngines.map((engine) => {
                const Icon = engine.icon
                const isEnabled = settings[engine.key]

                return (
                  <div
                    key={engine.key}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg border transition-all duration-200",
                      isEnabled
                        ? "bg-[var(--bronze)]/5 border-[var(--bronze)]/30"
                        : "bg-secondary/30 border-border hover:border-border/80"
                    )}
                  >
                    <div
                      className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200",
                        isEnabled
                          ? `bg-gradient-to-br ${engine.color} text-white shadow-lg shadow-${engine.color.split("-")[1]}-500/20`
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <Label
                        htmlFor={engine.key}
                        className={cn(
                          "text-sm font-medium cursor-pointer transition-colors",
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
                      className="data-[state=checked]:bg-[var(--bronze)]"
                    />
                  </div>
                )
              })}
            </div>
          </div>

          {/* Hint */}
          <p className="text-[10px] text-muted-foreground text-center">
            Enable multiple engines for enhanced orchestration capabilities
          </p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

