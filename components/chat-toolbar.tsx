"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ChevronDown, Zap, Brain, Rocket, Users, User, Settings2, Cpu, Sparkles, Check } from "lucide-react"
import type { ReasoningMode, DomainPack, OrchestratorSettings, AdvancedReasoningMethod } from "@/lib/types"
import { AVAILABLE_MODELS, getModelLogo } from "@/lib/models"
import Image from "next/image"

interface ChatToolbarProps {
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
  onOpenAdvanced: () => void
}

const reasoningModes: { value: ReasoningMode; label: string; icon: React.ElementType }[] = [
  { value: "fast", label: "Fast", icon: Zap },
  { value: "standard", label: "Standard", icon: Brain },
  { value: "deep", label: "Deep", icon: Rocket },
]

const domainPacks: { value: DomainPack; label: string }[] = [
  { value: "default", label: "Default" },
  { value: "medical", label: "Medical" },
  { value: "legal", label: "Legal" },
  { value: "marketing", label: "Marketing" },
  { value: "coding", label: "Coding" },
  { value: "research", label: "Research" },
  { value: "finance", label: "Finance" },
]

const advancedReasoningMethods: { value: AdvancedReasoningMethod; label: string; description: string }[] = [
  { value: "chain-of-thought", label: "Chain of Thought", description: "Step-by-step reasoning" },
  { value: "tree-of-thought", label: "Tree of Thought", description: "Explore multiple paths" },
  { value: "self-consistency", label: "Self Consistency", description: "Multiple samples, vote" },
  { value: "react", label: "ReAct", description: "Reason + Act iteratively" },
  { value: "reflexion", label: "Reflexion", description: "Self-reflection loop" },
  { value: "least-to-most", label: "Least to Most", description: "Decompose problems" },
  { value: "plan-and-solve", label: "Plan and Solve", description: "Plan then execute" },
]

export function ChatToolbar({ settings, onSettingsChange, onOpenAdvanced }: ChatToolbarProps) {
  const currentReasoningMode = reasoningModes.find((m) => m.value === settings.reasoningMode) || reasoningModes[1]
  const currentDomainPack = domainPacks.find((d) => d.value === settings.domainPack) || domainPacks[0]
  const ReasoningIcon = currentReasoningMode.icon

  const toggleModel = (modelId: string) => {
    const currentModels = settings.selectedModels || []
    if (currentModels.includes(modelId)) {
      if (currentModels.length > 1) {
        onSettingsChange({ selectedModels: currentModels.filter((id) => id !== modelId) })
      }
    } else {
      onSettingsChange({ selectedModels: [...currentModels, modelId] })
    }
  }

  const toggleReasoningMethod = (method: AdvancedReasoningMethod) => {
    const currentMethods = settings.advancedReasoningMethods || []
    if (currentMethods.includes(method)) {
      onSettingsChange({ advancedReasoningMethods: currentMethods.filter((m) => m !== method) })
    } else {
      onSettingsChange({ advancedReasoningMethods: [...currentMethods, method] })
    }
  }

  const selectedModels = settings.selectedModels || ["gpt-5"]
  const selectedReasoningMethods = settings.advancedReasoningMethods || []

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <Cpu className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Models ({selectedModels.length})</span>
            <span className="sm:hidden">{selectedModels.length}</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56 max-h-80 overflow-y-auto">
          {AVAILABLE_MODELS.map((model) => {
            const isSelected = selectedModels.includes(model.id)
            return (
              <DropdownMenuItem key={model.id} onClick={() => toggleModel(model.id)} className="gap-2 cursor-pointer">
                <div className="w-5 h-5 relative flex-shrink-0">
                  <Image
                    src={getModelLogo(model.provider) || "/placeholder.svg"}
                    alt={model.provider}
                    fill
                    className="object-contain"
                  />
                </div>
                <span className="flex-1">{model.name}</span>
                {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              Reasoning {selectedReasoningMethods.length > 0 ? `(${selectedReasoningMethods.length})` : ""}
            </span>
            <span className="sm:hidden">
              {selectedReasoningMethods.length > 0 ? selectedReasoningMethods.length : "R"}
            </span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {advancedReasoningMethods.map((method) => {
            const isSelected = selectedReasoningMethods.includes(method.value)
            return (
              <DropdownMenuItem
                key={method.value}
                onClick={() => toggleReasoningMethod(method.value)}
                className="flex flex-col items-start gap-0.5 cursor-pointer"
              >
                <div className="flex items-center w-full gap-2">
                  <span className="flex-1 font-medium">{method.label}</span>
                  {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                </div>
                <span className="text-[10px] text-muted-foreground">{method.description}</span>
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Reasoning Mode */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <ReasoningIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{currentReasoningMode.label}</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-40">
          {reasoningModes.map((mode) => {
            const Icon = mode.icon
            return (
              <DropdownMenuItem
                key={mode.value}
                onClick={() => onSettingsChange({ reasoningMode: mode.value })}
                className="gap-2"
              >
                <Icon className="h-4 w-4" />
                <span>{mode.label}</span>
                {settings.reasoningMode === mode.value && <span className="ml-auto text-[var(--bronze)]">•</span>}
              </DropdownMenuItem>
            )
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Domain Pack */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <span className="hidden sm:inline">{currentDomainPack.label}</span>
            <span className="sm:hidden">Domain</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-40">
          {domainPacks.map((pack) => (
            <DropdownMenuItem
              key={pack.value}
              onClick={() => onSettingsChange({ domainPack: pack.value })}
              className="gap-2"
            >
              <span>{pack.label}</span>
              {settings.domainPack === pack.value && <span className="ml-auto text-[var(--bronze)]">•</span>}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Agent Mode Toggle */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          onSettingsChange({
            agentMode: settings.agentMode === "single" ? "team" : "single",
          })
        }
        className={`gap-1.5 h-8 px-3 text-xs border rounded-lg transition-colors ${
          settings.agentMode === "team"
            ? "bg-[var(--bronze)]/20 border-[var(--bronze)] text-[var(--bronze)]"
            : "bg-secondary/50 border-border hover:bg-secondary hover:border-[var(--bronze)]"
        }`}
      >
        {settings.agentMode === "team" ? <Users className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
        <span className="hidden sm:inline">{settings.agentMode === "team" ? "Team" : "Single"}</span>
      </Button>

      {/* Advanced Settings */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onOpenAdvanced}
        className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
      >
        <Settings2 className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Tuning</span>
      </Button>
    </div>
  )
}
