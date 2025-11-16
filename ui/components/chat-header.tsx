"use client"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import { ChevronDown } from 'lucide-react'
import { AVAILABLE_MODELS, getModelLogo } from "@/lib/models"
import type { CriteriaSettings } from "@/lib/types"
import type { CriteriaSettings } from "@/lib/types"
import { CriteriaEqualizer } from "./criteria-equalizer"
import { Checkbox } from "@/components/ui/checkbox"

type OrchestrationEngine = "hrm" | "prompt-diffusion" | "deep-conf" | "adaptive-ensemble"
type AdvancedFeature = "vector-db" | "rag" | "shared-memory" | "loop-back" | "live-data"

export function ChatHeader({
  selectedModels,
  onModelChange,
  reasoningMode,
  onReasoningModeChange,
  orchestrationEngine,
  onOrchestrationChange,
  advancedFeatures,
  onToggleFeature,
  criteriaSettings,
  onCriteriaChange,
  currentModel,
}: {
  selectedModels: string[]
  onModelChange: (models: string[]) => void
  reasoningMode: "deep" | "standard" | "fast"
  onReasoningModeChange: (mode: "deep" | "standard" | "fast") => void
  orchestrationEngine: OrchestrationEngine
  onOrchestrationChange: (engine: OrchestrationEngine) => void
  advancedFeatures: AdvancedFeature[]
  onToggleFeature: (feature: AdvancedFeature) => void
  criteriaSettings: CriteriaSettings
  onCriteriaChange: (settings: CriteriaSettings) => void
  currentModel: any
}) {
  const handleModelToggle = (modelId: string) => {
    const next = selectedModels.includes(modelId)
      ? selectedModels.filter((id) => id !== modelId)
      : [...selectedModels, modelId]
    onModelChange(next)
  }

  return (
    <header className="border-b border-border p-3 flex items-center justify-between bg-card/50 backdrop-blur-xl sticky top-0 z-50">
      <div className="flex items-center justify-between gap-4 flex-1 px-8">
        {/* AI Agents Dropdown */}
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="group gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:border-transparent transition-all duration-300"
            >
              <span className="text-foreground group-hover:text-primary-foreground transition-colors duration-300">AI Agents ({selectedModels.length})</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50 group-hover:opacity-100 transition-opacity duration-300" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300" onCloseAutoFocus={(e) => e.preventDefault()}>
            {["openai", "anthropic", "google", "xai", "meta"].map((provider) => (
              <div key={provider}>
                <DropdownMenuLabel className="text-[9px] uppercase tracking-wider opacity-60">
                  {provider}
                </DropdownMenuLabel>
                {AVAILABLE_MODELS.filter((m) => m.provider === provider).map((model) => (
                  <DropdownMenuItem
                    key={model.id}
                    onSelect={(e) => {
                      e.preventDefault()
                      handleModelToggle(model.id)
                    }}
                    className="gap-2 py-1.5 hover-lift cursor-pointer"
                  >
                    <Checkbox
                      checked={selectedModels.includes(model.id)}
                      className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]"
                    />
                    <img src={getModelLogo(model.provider) || "/placeholder.svg"} alt="" className="w-3.5 h-3.5" />
                    <span className="text-[11px]">{model.name}</span>
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
              </div>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Tuning */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="group gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300"
            >
              <span className="text-foreground group-hover:text-primary-foreground">Tuning</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="start"
            className="w-44 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300"
          >
            <DropdownMenuItem onSelect={(e) => { e.preventDefault(); onReasoningModeChange("deep"); }} className="gap-2 py-1.5 hover-lift cursor-pointer">
              <Checkbox 
                checked={reasoningMode === "deep"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              <span className="text-[11px]">Deep Reasoning</span>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={(e) => { e.preventDefault(); onReasoningModeChange("standard"); }} className="gap-2 py-1.5 hover-lift cursor-pointer">
              <Checkbox 
                checked={reasoningMode === "standard"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              <span className="text-[11px]">Standard</span>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={(e) => { e.preventDefault(); onReasoningModeChange("fast"); }} className="gap-2 py-1.5 hover-lift cursor-pointer">
              <Checkbox 
                checked={reasoningMode === "fast"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              <span className="text-[11px]">Fast</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Orchestration */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="group gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300"
            >
              <span className="text-foreground group-hover:text-primary-foreground">Orchestration</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-60 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300">
            <DropdownMenuItem onSelect={(e) => { e.preventDefault(); onOrchestrationChange("hrm"); }} className="gap-2 py-2 hover-lift text-xs cursor-pointer">
              <Checkbox 
                checked={orchestrationEngine === "hrm"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              Hierarchical Role Management (HRM)
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={(e) => { e.preventDefault(); onOrchestrationChange("prompt-diffusion"); }}
              className="gap-2 py-2 hover-lift text-xs cursor-pointer"
            >
              <Checkbox 
                checked={orchestrationEngine === "prompt-diffusion"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              Prompt Diffusion and Refinement
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={(e) => { e.preventDefault(); onOrchestrationChange("deep-conf"); }} className="gap-2 py-2 hover-lift text-xs cursor-pointer">
              <Checkbox 
                checked={orchestrationEngine === "deep-conf"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              DeepConf (Deep Consensus Framework)
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={(e) => { e.preventDefault(); onOrchestrationChange("adaptive-ensemble"); }}
              className="gap-2 py-2 hover-lift text-xs cursor-pointer"
            >
              <Checkbox 
                checked={orchestrationEngine === "adaptive-ensemble"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              Adaptive Ensemble Logic
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Advanced */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="group gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300"
            >
              <span className="text-foreground group-hover:text-primary-foreground">Advanced</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300">
            {(["vector-db", "rag", "shared-memory", "loop-back", "live-data"] as AdvancedFeature[]).map((feature) => (
              <DropdownMenuItem key={feature} onSelect={(e) => { e.preventDefault(); onToggleFeature(feature); }} className="gap-2 py-2 hover-lift cursor-pointer">
                <Checkbox 
                  checked={advancedFeatures.includes(feature)} 
                  className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
                />
                <span className="text-xs">
                  {feature
                    .split("-")
                    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                    .join(" ")}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <CriteriaEqualizer settings={criteriaSettings} onChange={onCriteriaChange} />
      </div>

    </header>
  )
}
