"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ChevronDown, Zap, Brain, Rocket, Users, User, Settings2 } from "lucide-react"
import type { ReasoningMode, DomainPack, OrchestratorSettings } from "@/lib/types"

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

export function ChatToolbar({ settings, onSettingsChange, onOpenAdvanced }: ChatToolbarProps) {
  const currentReasoningMode = reasoningModes.find((m) => m.value === settings.reasoningMode) || reasoningModes[1]
  const currentDomainPack = domainPacks.find((d) => d.value === settings.domainPack) || domainPacks[0]
  const ReasoningIcon = currentReasoningMode.icon

  return (
    <div className="flex items-center gap-2 flex-wrap">
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
