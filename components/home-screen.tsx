"use client"

import Image from "next/image"
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
      enableDeepConsensus: true,
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
      domainPack: "legal" as const,
      agentMode: "team" as const,
      outputValidation: true,
      answerStructure: true,
    },
  },
]

export function HomeScreen({ onNewChat, onStartFromTemplate }: HomeScreenProps) {
  return (
    <div className="min-h-full flex flex-col items-center justify-start px-4 pt-0 pb-20 overflow-y-auto">
      {/* Hero Section */}
      <div className="text-center mb-0">
        {/* Logo Container */}
        <div className="relative w-40 h-40 md:w-[280px] md:h-[280px] lg:w-[320px] lg:h-[320px] mx-auto mb-0 -mt-4 md:-mt-8 lg:-mt-10">
          <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
        </div>
        {/* Title */}
        <h1 className="-mt-6 md:-mt-8 lg:-mt-10 text-[1.75rem] md:text-[2.85rem] lg:text-[3.4rem] font-bold mb-1 bg-gradient-to-r from-[var(--bronze)] via-[var(--gold)] to-[var(--bronze)] bg-clip-text text-transparent">
          Welcome to LLMHive
        </h1>
        {/* Subtitle */}
        <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto mb-0">
          Multi-agent AI orchestration for enhanced accuracy and deeper insights
        </p>
      </div>

      {/* Separator Line */}
      <div className="w-16 h-px bg-border my-2" />

      {/* New Chat Button */}
      <Button
        onClick={onNewChat}
        size="lg"
        className="bronze-gradient mb-4 md:mb-6 h-12 md:h-14 px-8 md:px-10 text-base md:text-lg gap-2 shadow-lg hover:shadow-xl transition-shadow"
      >
        <MessageSquarePlus className="h-5 w-5 md:h-6 md:w-6" />
        New Chat
      </Button>

      {/* Template Cards */}
      <div className="w-full max-w-4xl">
        <p className="text-sm text-muted-foreground text-center mb-2">Or start from a template</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {templates.map((template) => {
            const Icon = template.icon
            return (
              <button
                key={template.id}
                onClick={() => onStartFromTemplate(template.preset)}
                className="group flex flex-col items-center gap-2 p-3 md:p-4 rounded-xl border border-border hover:border-[var(--bronze)] bg-card/50 hover:bg-card/80 transition-all duration-300 cursor-pointer text-left"
              >
                <div
                  className={`w-10 h-10 md:w-12 md:h-12 rounded-xl bg-gradient-to-br ${template.color} flex items-center justify-center shadow-lg group-hover:scale-110 group-hover:shadow-xl transition-all duration-300`}
                >
                  <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
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
