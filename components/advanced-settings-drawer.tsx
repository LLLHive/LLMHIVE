"use client"
import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Lightbulb, CheckCircle, ListTree, Database, GraduationCap, SpellCheck, Type } from "lucide-react"
import type { OrchestratorSettings } from "@/lib/types"

interface AdvancedSettingsDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

// Answer structure formats
const answerFormats = [
  { value: "default", label: "Default", description: "Natural conversational format" },
  { value: "structured", label: "Structured", description: "With headers and sections" },
  { value: "bullet-points", label: "Bullet Points", description: "Concise bullet list format" },
  { value: "step-by-step", label: "Step by Step", description: "Numbered instructions" },
  { value: "academic", label: "Academic", description: "Formal with citations" },
  { value: "concise", label: "Concise", description: "Brief, to-the-point answers" },
]

const toggleOptions = [
  {
    key: "promptOptimization" as const,
    label: "Prompt Optimization",
    description: "Automatically enhance your prompts for better results",
    icon: Lightbulb,
  },
  {
    key: "outputValidation" as const,
    label: "Output Validation",
    description: "Verify and fact-check AI responses",
    icon: CheckCircle,
  },
  {
    key: "answerStructure" as const,
    label: "Answer Structure",
    description: "Format responses with clear sections and examples",
    icon: ListTree,
    hasSubOption: true,
  },
  {
    key: "sharedMemory" as const,
    label: "Shared Memory",
    description: "Access context from previous conversations",
    icon: Database,
  },
  {
    key: "learnFromChat" as const,
    label: "Learn from Chat",
    description: "Improve responses based on this conversation",
    icon: GraduationCap,
  },
  {
    key: "enableSpellCheck" as const,
    label: "Spell Check",
    description: "Auto-correct spelling in your messages",
    icon: SpellCheck,
  },
  {
    key: "enableClarificationQuestions" as const,
    label: "Clarification Questions",
    description: "AI asks follow-up questions for better answers",
    icon: Type,
  },
]

export function AdvancedSettingsDrawer({
  open,
  onOpenChange,
  settings,
  onSettingsChange,
}: AdvancedSettingsDrawerProps) {
  // Get answer format from settings, with type assertion
  const answerFormat = (settings as any).answerFormat || "default"
  
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[300px] sm:w-[340px] bg-card border-l border-border overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle className="text-lg font-semibold">Advanced Tuning</SheetTitle>
        </SheetHeader>

        <div className="space-y-4">
          {toggleOptions.map((option) => {
            const Icon = option.icon
            const isEnabled = (settings as any)[option.key]
            const hasSubOption = (option as any).hasSubOption

            return (
              <div key={option.key}>
                <div
                  className="flex items-start gap-3 p-3 rounded-lg border border-border bg-secondary/30 hover:bg-secondary/50 transition-colors"
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                    isEnabled ? "bg-[var(--bronze)]/20 text-[var(--bronze)]" : "bg-muted text-muted-foreground"
                  }`}
                >
                    <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <Label htmlFor={option.key} className="text-sm font-medium cursor-pointer">
                    {option.label}
                  </Label>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{option.description}</p>
                </div>
                <Switch
                  id={option.key}
                  checked={isEnabled}
                  onCheckedChange={(checked) => onSettingsChange({ [option.key]: checked })}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
                </div>
                
                {/* Answer Format Selector - shown when answerStructure is enabled */}
                {hasSubOption && option.key === "answerStructure" && isEnabled && (
                  <div className="ml-12 mt-2 p-3 rounded-lg bg-secondary/20 border border-border/50">
                    <Label className="text-xs font-medium text-muted-foreground mb-2 block">
                      Response Format
                    </Label>
                    <Select 
                      value={answerFormat} 
                      onValueChange={(value) => onSettingsChange({ answerFormat: value } as any)}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Select format" />
                      </SelectTrigger>
                      <SelectContent>
                        {answerFormats.map((format) => (
                          <SelectItem key={format.value} value={format.value} className="text-xs">
                            <div>
                              <span className="font-medium">{format.label}</span>
                              <span className="text-muted-foreground ml-2">- {format.description}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="mt-6 p-3 rounded-lg bg-[var(--bronze)]/5 border border-[var(--bronze)]/20">
          <p className="text-xs text-[var(--bronze)] font-medium">Settings Active</p>
          <p className="text-[10px] text-muted-foreground mt-1">
            These settings are applied to your current and future chats automatically.
        </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
