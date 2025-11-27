"use client"

import { Button } from "@/components/ui/button"
import { MessageSquarePlus, Brain, Code, Briefcase, Sparkles } from "lucide-react"
import type { OrchestratorSettings } from "@/lib/types"

interface HomeScreenProps {
  onNewChat: () => void
  onStartFromTemplate: (preset: Partial<OrchestratorSettings>) => void
}

const templates = [
  {
    id: "general",
    title: "General Assistant",
    description: "Versatile AI helper for everyday tasks",
    icon: Sparkles,
    color: "from-orange-500 to-amber-500",
    preset: {
      reasoningMode: "standard" as const,
      domainPack: "default" as const,
      agentMode: "single" as const,
    },
  },
  {
    id: "research",
    title: "Research & Deep Reasoning",
    description: "In-depth analysis with multiple perspectives",
    icon: Brain,
    color: "from-purple-500 to-indigo-500",
    preset: {
      reasoningMode: "deep" as const,
      domainPack: "research" as const,
      agentMode: "team" as const,
      outputValidation: true,
    },
  },
  {
    id: "code",
    title: "Code & Debug",
    description: "Expert coding assistance and debugging",
    icon: Code,
    color: "from-emerald-500 to-teal-500",
    preset: {
      reasoningMode: "standard" as const,
      domainPack: "coding" as const,
      agentMode: "team" as const,
      promptOptimization: true,
    },
  },
  {
    id: "industry",
    title: "Industry Packs",
    description: "Legal, Medical, Marketing & more",
    icon: Briefcase,
    color: "from-blue-500 to-cyan-500",
    preset: {
      reasoningMode: "deep" as const,
      agentMode: "team" as const,
      outputValidation: true,
      answerStructure: true,
    },
  },
]

export function HomeScreen({ onNewChat, onStartFromTemplate }: HomeScreenProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 md:py-12">
      {/* Hero Section */}
      <div className="text-center mb-8 md:mb-12">
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-3 bg-gradient-to-r from-[var(--bronze)] via-[var(--gold)] to-[var(--bronze)] bg-clip-text text-transparent">
          Welcome to LLMHive
        </h1>
        <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto">
          Multi-agent AI orchestration for enhanced accuracy and deeper insights
        </p>
      </div>

      {/* New Chat Button */}
      <Button
        onClick={onNewChat}
        size="lg"
        className="bronze-gradient mb-8 md:mb-12 h-12 md:h-14 px-8 md:px-10 text-base md:text-lg gap-2 shadow-lg hover:shadow-xl transition-shadow"
      >
        <MessageSquarePlus className="h-5 w-5 md:h-6 md:w-6" />
        New Chat
      </Button>

      {/* Template Cards */}
      <div className="w-full max-w-4xl">
        <p className="text-xs md:text-sm text-muted-foreground text-center mb-4">Or start from a template</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          {templates.map((template) => {
            const Icon = template.icon
            return (
              <button
                key={template.id}
                onClick={() => onStartFromTemplate(template.preset)}
                className="group flex flex-col items-center gap-3 p-4 md:p-6 rounded-xl border border-border hover:border-[var(--bronze)] bg-card/50 hover:bg-card/80 transition-all duration-300 cursor-pointer text-left"
              >
                <div
                  className={`w-12 h-12 md:w-14 md:h-14 rounded-xl bg-gradient-to-br ${template.color} flex items-center justify-center shadow-lg group-hover:scale-110 group-hover:shadow-xl transition-all duration-300`}
                >
                  <Icon className="h-6 w-6 md:h-7 md:w-7 text-white" />
                </div>
                <div className="text-center">
                  <h3 className="text-sm md:text-base font-semibold text-foreground group-hover:text-[var(--bronze)] transition-colors">
                    {template.title}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{template.description}</p>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
