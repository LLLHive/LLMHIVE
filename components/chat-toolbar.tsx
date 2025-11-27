"use client"

import { useState } from "react"
import type React from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ChevronDown, Zap, Brain, Rocket, Users, User, Settings2, Cpu, Sparkles, Check, Wrench } from "lucide-react"
import type {
  ReasoningMode,
  DomainPack,
  OrchestratorSettings,
  AdvancedReasoningMethod,
  AdvancedFeature,
} from "@/lib/types"
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
  { value: "graph-of-thought", label: "Graph of Thought", description: "Non-linear reasoning graph" },
  { value: "algorithm-of-thought", label: "Algorithm of Thought", description: "Algorithmic problem solving" },
  { value: "skeleton-of-thought", label: "Skeleton of Thought", description: "Parallel skeleton expansion" },
  { value: "self-consistency", label: "Self Consistency", description: "Multiple samples, vote" },
  { value: "cumulative-reasoning", label: "Cumulative Reasoning", description: "Build on prior conclusions" },
  { value: "meta-prompting", label: "Meta Prompting", description: "LLM orchestrates sub-LLMs" },
  { value: "react", label: "ReAct", description: "Reason + Act iteratively" },
  { value: "reflexion", label: "Reflexion", description: "Self-reflection loop" },
  { value: "least-to-most", label: "Least to Most", description: "Decompose problems" },
  { value: "plan-and-solve", label: "Plan and Solve", description: "Plan then execute" },
]

const advancedFeatures: { value: AdvancedFeature; label: string; description: string }[] = [
  { value: "vector-rag", label: "Vector DB + RAG", description: "Retrieval augmented generation" },
  { value: "mcp-server", label: "MCP Server + Tools", description: "Model context protocol" },
  { value: "personal-database", label: "Personal Database", description: "Your private knowledge base" },
  { value: "modular-answer-feed", label: "Modular Answer Feed", description: "Internal LLM routing" },
  { value: "memory-augmentation", label: "Memory Augmentation", description: "Long-term memory" },
  { value: "tool-use", label: "Tool Use", description: "External tool integration" },
  { value: "code-interpreter", label: "Code Interpreter", description: "Execute code in sandbox" },
]

export function ChatToolbar({ settings, onSettingsChange, onOpenAdvanced }: ChatToolbarProps) {
  const [modelsOpen, setModelsOpen] = useState(false)
  const [reasoningOpen, setReasoningOpen] = useState(false)
  const [featuresOpen, setFeaturesOpen] = useState(false)

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

  const toggleFeature = (feature: AdvancedFeature) => {
    const currentFeatures = settings.advancedFeatures || []
    if (currentFeatures.includes(feature)) {
      onSettingsChange({ advancedFeatures: currentFeatures.filter((f) => f !== feature) })
    } else {
      onSettingsChange({ advancedFeatures: [...currentFeatures, feature] })
    }
  }

  const selectedModels = settings.selectedModels || ["gpt-5"]
  const selectedReasoningMethods = settings.advancedReasoningMethods || []
  const selectedFeatures = settings.advancedFeatures || []

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <DropdownMenu open={modelsOpen} onOpenChange={setModelsOpen}>
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
              <DropdownMenuItem
                key={model.id}
                onSelect={(e) => {
                  e.preventDefault() // Prevent dropdown from closing
                  toggleModel(model.id)
                }}
                className="gap-2 cursor-pointer"
              >
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

      <DropdownMenu open={reasoningOpen} onOpenChange={setReasoningOpen}>
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
        <DropdownMenuContent align="start" className="w-56 max-h-80 overflow-y-auto">
          {advancedReasoningMethods.map((method) => {
            const isSelected = selectedReasoningMethods.includes(method.value)
            return (
              <DropdownMenuItem
                key={method.value}
                onSelect={(e) => {
                  e.preventDefault() // Prevent dropdown from closing
                  toggleReasoningMethod(method.value)
                }}
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

      <DropdownMenu open={featuresOpen} onOpenChange={setFeaturesOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg hover:bg-secondary hover:border-[var(--bronze)]"
          >
            <Wrench className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              Features {selectedFeatures.length > 0 ? `(${selectedFeatures.length})` : ""}
            </span>
            <span className="sm:hidden">{selectedFeatures.length > 0 ? selectedFeatures.length : "F"}</span>
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56 max-h-80 overflow-y-auto">
          {advancedFeatures.map((feature) => {
            const isSelected = selectedFeatures.includes(feature.value)
            return (
              <DropdownMenuItem
                key={feature.value}
                onSelect={(e) => {
                  e.preventDefault() // Prevent dropdown from closing
                  toggleFeature(feature.value)
                }}
                className="flex flex-col items-start gap-0.5 cursor-pointer"
              >
                <div className="flex items-center w-full gap-2">
                  <span className="flex-1 font-medium">{feature.label}</span>
                  {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                </div>
                <span className="text-[10px] text-muted-foreground">{feature.description}</span>
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
