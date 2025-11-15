"use client"

import Image from "next/image"
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
import { CriteriaEqualizer } from "./criteria-equalizer"
import { Checkbox } from "@/components/ui/checkbox"

type OrchestrationEngine = "hrm" | "prompt-diffusion" | "deep-conf" | "adaptive-ensemble"
type AdvancedFeature = "vector-db" | "rag" | "shared-memory" | "loop-back" | "live-data"

export function ChatHeader({
  selectedModels,
  onToggleModel,
  reasoningMode,
  onReasoningModeChange,
  orchestrationEngine,
  onOrchestrationChange,
  advancedFeatures,
  onToggleFeature,
  criteriaSettings,
  onCriteriaChange,
}: {
  selectedModels: string[]
  onToggleModel: (model: string) => void
  reasoningMode: "deep" | "standard" | "fast"
  onReasoningModeChange: (mode: "deep" | "standard" | "fast") => void
  orchestrationEngine: OrchestrationEngine
  onOrchestrationChange: (engine: OrchestrationEngine) => void
  advancedFeatures: AdvancedFeature[]
  onToggleFeature: (feature: AdvancedFeature) => void
  criteriaSettings: CriteriaSettings
  onCriteriaChange: (settings: CriteriaSettings) => void
}) {
  return (
    <header className="border-b border-border p-3 flex items-center justify-between bg-card/50 backdrop-blur-xl sticky top-0 z-50">
      <div className="flex items-center justify-between gap-4 flex-1 px-8">
        {/* AI Agents Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300">
              <span>AI Agents</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300">
            {["openai", "anthropic", "google", "xai", "meta"].map((provider) => (
              <div key={provider}>
                <DropdownMenuLabel className="text-[9px] uppercase tracking-wider opacity-60">
                  {provider}
                </DropdownMenuLabel>
                {AVAILABLE_MODELS.filter((m) => m.provider === provider).map((model) => (
                  <DropdownMenuItem
                    key={model.id}
                    onClick={() => onToggleModel(model.id)}
                    className="gap-2 py-1.5 hover-lift"
                  >
                    <Checkbox
                      checked={selectedModels.includes(model.id)}
                      className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]"
                    />
                    <Image
                      src={getModelLogo(model.provider) || "/placeholder.svg"}
                      alt={`${model.name} logo`}
                      width={14}
                      height={14}
                      className="h-3.5 w-3.5 object-contain"
                    />
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
            <Button variant="outline" size="sm" className="gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300">
              <span>Tuning</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="start"
            className="w-44 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300"
          >
            <DropdownMenuItem onClick={() => onReasoningModeChange("deep")} className="gap-2 py-1.5 hover-lift">
              <Checkbox 
                checked={reasoningMode === "deep"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              <span className="text-[11px]">Deep Reasoning</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onReasoningModeChange("standard")} className="gap-2 py-1.5 hover-lift">
              <Checkbox 
                checked={reasoningMode === "standard"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              <span className="text-[11px]">Standard</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onReasoningModeChange("fast")} className="gap-2 py-1.5 hover-lift">
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
            <Button variant="outline" size="sm" className="gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300">
              <span>Orchestration</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-60 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300">
            <DropdownMenuItem onClick={() => onOrchestrationChange("hrm")} className="gap-2 py-2 hover-lift text-xs">
              <Checkbox 
                checked={orchestrationEngine === "hrm"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              Hierarchical Role Management (HRM)
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onOrchestrationChange("prompt-diffusion")}
              className="gap-2 py-2 hover-lift text-xs"
            >
              <Checkbox 
                checked={orchestrationEngine === "prompt-diffusion"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              Prompt Diffusion and Refinement
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onOrchestrationChange("deep-conf")} className="gap-2 py-2 hover-lift text-xs">
              <Checkbox 
                checked={orchestrationEngine === "deep-conf"} 
                className="pointer-events-none border-[var(--bronze)] data-[state=checked]:bg-[var(--bronze)] data-[state=checked]:border-[var(--bronze)]" 
              />
              DeepConf (Deep Consensus Framework)
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onOrchestrationChange("adaptive-ensemble")}
              className="gap-2 py-2 hover-lift text-xs"
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
            <Button variant="outline" size="sm" className="gap-1.5 h-7 px-2.5 text-[11px] bg-transparent hover:bronze-gradient hover:text-primary-foreground hover:border-transparent transition-all duration-300">
              <span>Advanced</span>
              <ChevronDown className="h-2.5 w-2.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48 z-[600] glass-effect animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-300">
            {(["vector-db", "rag", "shared-memory", "loop-back", "live-data"] as AdvancedFeature[]).map((feature) => (
              <DropdownMenuItem key={feature} onClick={() => onToggleFeature(feature)} className="gap-2 py-2 hover-lift">
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

        <div className="flex items-center gap-2">
          <div className="hidden md:flex items-center gap-1 text-[11px] text-muted-foreground uppercase tracking-wide">
            <span>Models:</span>
            <span className="font-semibold text-foreground">{selectedModels.length}</span>
          </div>
          <CriteriaEqualizer settings={criteriaSettings} onChange={onCriteriaChange} />
        </div>
      </div>

    </header>
  )
}
