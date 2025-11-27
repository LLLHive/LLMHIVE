"use client"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Lightbulb, CheckCircle, ListTree, Database, GraduationCap } from "lucide-react"
import type { OrchestratorSettings } from "@/lib/types"

interface AdvancedSettingsDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  settings: OrchestratorSettings
  onSettingsChange: (settings: Partial<OrchestratorSettings>) => void
}

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
]

export function AdvancedSettingsDrawer({
  open,
  onOpenChange,
  settings,
  onSettingsChange,
}: AdvancedSettingsDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:w-96 bg-card border-l border-border">
        <SheetHeader className="mb-6">
          <SheetTitle className="text-lg font-semibold">Advanced Tuning</SheetTitle>
        </SheetHeader>

        <div className="space-y-6">
          {toggleOptions.map((option) => {
            const Icon = option.icon
            const isEnabled = settings[option.key]

            return (
              <div
                key={option.key}
                className="flex items-start gap-4 p-4 rounded-lg border border-border bg-secondary/30 hover:bg-secondary/50 transition-colors"
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                    isEnabled ? "bg-[var(--bronze)]/20 text-[var(--bronze)]" : "bg-muted text-muted-foreground"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <Label htmlFor={option.key} className="text-sm font-medium cursor-pointer">
                    {option.label}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">{option.description}</p>
                </div>
                <Switch
                  id={option.key}
                  checked={isEnabled}
                  onCheckedChange={(checked) => onSettingsChange({ [option.key]: checked })}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
              </div>
            )
          })}
        </div>

        {/* TODO: Connect these settings to your orchestration backend */}
        <p className="text-xs text-muted-foreground mt-8 text-center">
          Settings are applied to your current and future chats
        </p>
      </SheetContent>
    </Sheet>
  )
}
