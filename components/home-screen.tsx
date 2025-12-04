"use client"

import { useState } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Switch } from "@/components/ui/switch"
import { 
  MessageSquarePlus, 
  Brain, 
  Code, 
  Briefcase, 
  Sparkles,
  Check,
  ArrowRight,
  Scale,
  Stethoscope,
  Megaphone,
  GraduationCap,
  Building2,
  Landmark,
  Lightbulb,
  Shield,
  Zap,
  Bug,
  FileCode,
  BookOpen,
  Users,
  Target,
} from "lucide-react"
import type { OrchestratorSettings, DomainPack } from "@/lib/types"

interface HomeScreenProps {
  onNewChat: () => void
  onStartFromTemplate: (preset: Partial<OrchestratorSettings>) => void
}

// Industry pack options
const industryPacks: Array<{
  id: DomainPack
  label: string
  description: string
  icon: typeof Scale
}> = [
  { id: "legal", label: "Legal", description: "Contract analysis, case research", icon: Scale },
  { id: "medical", label: "Medical", description: "Clinical documentation, research", icon: Stethoscope },
  { id: "marketing", label: "Marketing", description: "Campaigns, copywriting, SEO", icon: Megaphone },
  { id: "education", label: "Education", description: "Curriculum, tutoring, grading", icon: GraduationCap },
  { id: "finance", label: "Finance", description: "Analysis, reports, compliance", icon: Landmark },
  { id: "real_estate", label: "Real Estate", description: "Listings, valuations, contracts", icon: Building2 },
]

// Research features
const researchFeatures = [
  { id: "deep_reasoning", label: "Deep Reasoning", description: "Extended chain-of-thought", icon: Brain },
  { id: "multi_perspective", label: "Multi-Perspective", description: "Multiple agent viewpoints", icon: Users },
  { id: "fact_verification", label: "Fact Verification", description: "Cross-reference claims", icon: Check },
  { id: "source_citation", label: "Source Citation", description: "Include references", icon: BookOpen },
]

// Code features  
const codeFeatures = [
  { id: "code_review", label: "Code Review", description: "Analyze code quality", icon: FileCode },
  { id: "debugging", label: "Debugging", description: "Find and fix bugs", icon: Bug },
  { id: "optimization", label: "Optimization", description: "Performance improvements", icon: Zap },
  { id: "best_practices", label: "Best Practices", description: "Industry standards", icon: Shield },
]

// General assistant modes
const generalModes = [
  { id: "quick", label: "Quick Response", description: "Fast, concise answers", icon: Zap },
  { id: "detailed", label: "Detailed", description: "Comprehensive explanations", icon: BookOpen },
  { id: "creative", label: "Creative", description: "Brainstorming and ideas", icon: Lightbulb },
  { id: "focused", label: "Focused", description: "Task-specific assistance", icon: Target },
]

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

type DrawerId = "general" | "research" | "code" | "industry" | null

export function HomeScreen({ onNewChat, onStartFromTemplate }: HomeScreenProps) {
  const [activeDrawer, setActiveDrawer] = useState<DrawerId>(null)
  const [selectedIndustry, setSelectedIndustry] = useState<DomainPack | null>(null)
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([])
  const [selectedMode, setSelectedMode] = useState<string>("quick")

  const openDrawer = (templateId: string) => {
    console.log("Opening drawer:", templateId)
    setActiveDrawer(templateId as DrawerId)
    // Reset selections when opening a new drawer
    setSelectedFeatures([])
    setSelectedMode("quick")
    setSelectedIndustry(null)
  }

  const closeDrawer = () => {
    console.log("Closing drawer")
    setActiveDrawer(null)
  }

  const toggleFeature = (featureId: string) => {
    setSelectedFeatures(prev => 
      prev.includes(featureId) 
        ? prev.filter(f => f !== featureId) 
        : [...prev, featureId]
    )
  }

  const handleStartChat = (template: typeof templates[0]) => {
    let finalPreset: Partial<OrchestratorSettings> = { ...template.preset }
    
    // Apply selected options based on template type
    if (activeDrawer === "industry" && selectedIndustry) {
      finalPreset.domainPack = selectedIndustry
    }
    
    if (activeDrawer === "research") {
      if (selectedFeatures.includes("deep_reasoning")) {
        finalPreset.reasoningMode = "deep"
      }
      if (selectedFeatures.includes("multi_perspective")) {
        finalPreset.agentMode = "team"
        finalPreset.enableDeepConsensus = true
      }
      if (selectedFeatures.includes("fact_verification")) {
        finalPreset.outputValidation = true
      }
    }
    
    if (activeDrawer === "code") {
      finalPreset.domainPack = "coding"
      if (selectedFeatures.includes("optimization")) {
        finalPreset.promptOptimization = true
      }
      if (selectedFeatures.includes("code_review")) {
        finalPreset.outputValidation = true
      }
    }
    
    if (activeDrawer === "general") {
      if (selectedMode === "detailed") {
        finalPreset.reasoningMode = "deep"
      } else if (selectedMode === "creative") {
        finalPreset.domainPack = "creative" as DomainPack
      }
    }
    
    console.log("Starting chat with preset:", finalPreset)
    closeDrawer()
    onStartFromTemplate(finalPreset)
  }

  const currentTemplate = templates.find(t => t.id === activeDrawer)

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
                onClick={() => openDrawer(template.id)}
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

      {/* General Assistant Drawer */}
      <Sheet open={activeDrawer === "general"} onOpenChange={(open) => !open && closeDrawer()}>
        <SheetContent side="right" className="w-[320px] sm:w-[380px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
              <div>
                <SheetTitle className="text-lg font-semibold">General Assistant</SheetTitle>
                <p className="text-sm text-muted-foreground">Configure your assistant mode</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-180px)]">
            <div className="p-4 space-y-4">
              <p className="text-sm font-medium text-muted-foreground">Select response style</p>
              <div className="space-y-2">
                {generalModes.map((mode) => {
                  const Icon = mode.icon
                  const isSelected = selectedMode === mode.id
                  return (
                    <button
                      key={mode.id}
                      onClick={() => setSelectedMode(mode.id)}
                      className={`w-full p-4 rounded-lg border transition-all text-left ${
                        isSelected
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                          : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                            isSelected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                          }`}
                        >
                          {isSelected && <Check className="h-3 w-3 text-white" />}
                        </div>
                        <Icon className={`h-5 w-5 ${isSelected ? "text-[var(--bronze)]" : "text-muted-foreground"}`} />
                        <div>
                          <span className={`text-sm font-medium block ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                            {mode.label}
                          </span>
                          <span className="text-xs text-muted-foreground">{mode.description}</span>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </ScrollArea>
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-card/95">
            <Button 
              className="w-full bronze-gradient gap-2" 
              onClick={() => currentTemplate && handleStartChat(currentTemplate)}
            >
              Start Chat
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Research & Deep Reasoning Drawer */}
      <Sheet open={activeDrawer === "research"} onOpenChange={(open) => !open && closeDrawer()}>
        <SheetContent side="right" className="w-[320px] sm:w-[380px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg">
                <Brain className="h-6 w-6 text-white" />
              </div>
              <div>
                <SheetTitle className="text-lg font-semibold">Research & Deep Reasoning</SheetTitle>
                <p className="text-sm text-muted-foreground">Configure analysis features</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-180px)]">
            <div className="p-4 space-y-4">
              <p className="text-sm font-medium text-muted-foreground">Enable features</p>
              <div className="space-y-2">
                {researchFeatures.map((feature) => {
                  const Icon = feature.icon
                  const isSelected = selectedFeatures.includes(feature.id)
                  return (
                    <button
                      key={feature.id}
                      onClick={() => toggleFeature(feature.id)}
                      className={`w-full p-4 rounded-lg border transition-all text-left ${
                        isSelected
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                          : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Icon className={`h-5 w-5 ${isSelected ? "text-[var(--bronze)]" : "text-muted-foreground"}`} />
                          <div>
                            <span className={`text-sm font-medium block ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                              {feature.label}
                            </span>
                            <span className="text-xs text-muted-foreground">{feature.description}</span>
                          </div>
                        </div>
                        <Switch checked={isSelected} onCheckedChange={() => toggleFeature(feature.id)} />
                      </div>
                    </button>
                  )
                })}
              </div>
              {selectedFeatures.length > 0 && (
                <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  <p className="text-xs text-purple-400">
                    {selectedFeatures.length} feature{selectedFeatures.length > 1 ? 's' : ''} enabled for deeper analysis
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-card/95">
            <Button 
              className="w-full bronze-gradient gap-2" 
              onClick={() => currentTemplate && handleStartChat(currentTemplate)}
            >
              Start Research
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Code & Debug Drawer */}
      <Sheet open={activeDrawer === "code"} onOpenChange={(open) => !open && closeDrawer()}>
        <SheetContent side="right" className="w-[320px] sm:w-[380px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-lg">
                <Code className="h-6 w-6 text-white" />
              </div>
              <div>
                <SheetTitle className="text-lg font-semibold">Code & Debug</SheetTitle>
                <p className="text-sm text-muted-foreground">Configure coding assistance</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-180px)]">
            <div className="p-4 space-y-4">
              <p className="text-sm font-medium text-muted-foreground">Enable features</p>
              <div className="space-y-2">
                {codeFeatures.map((feature) => {
                  const Icon = feature.icon
                  const isSelected = selectedFeatures.includes(feature.id)
                  return (
                    <button
                      key={feature.id}
                      onClick={() => toggleFeature(feature.id)}
                      className={`w-full p-4 rounded-lg border transition-all text-left ${
                        isSelected
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                          : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Icon className={`h-5 w-5 ${isSelected ? "text-[var(--bronze)]" : "text-muted-foreground"}`} />
                          <div>
                            <span className={`text-sm font-medium block ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                              {feature.label}
                            </span>
                            <span className="text-xs text-muted-foreground">{feature.description}</span>
                          </div>
                        </div>
                        <Switch checked={isSelected} onCheckedChange={() => toggleFeature(feature.id)} />
                      </div>
                    </button>
                  )
                })}
              </div>
              {selectedFeatures.length > 0 && (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <p className="text-xs text-emerald-400">
                    {selectedFeatures.length} coding feature{selectedFeatures.length > 1 ? 's' : ''} enabled
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-card/95">
            <Button 
              className="w-full bronze-gradient gap-2" 
              onClick={() => currentTemplate && handleStartChat(currentTemplate)}
            >
              Start Coding
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Industry Packs Drawer */}
      <Sheet open={activeDrawer === "industry"} onOpenChange={(open) => !open && closeDrawer()}>
        <SheetContent side="right" className="w-[320px] sm:w-[380px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
                <Briefcase className="h-6 w-6 text-white" />
              </div>
              <div>
                <SheetTitle className="text-lg font-semibold">Industry Packs</SheetTitle>
                <p className="text-sm text-muted-foreground">Select your industry</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-180px)]">
            <div className="p-4 space-y-4">
              <p className="text-sm font-medium text-muted-foreground">Choose an industry pack</p>
              <div className="space-y-2">
                {industryPacks.map((pack) => {
                  const Icon = pack.icon
                  const isSelected = selectedIndustry === pack.id
                  return (
                    <button
                      key={pack.id}
                      onClick={() => setSelectedIndustry(pack.id)}
                      className={`w-full p-4 rounded-lg border transition-all text-left ${
                        isSelected
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                          : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
                            isSelected 
                              ? "bg-gradient-to-br from-blue-500 to-cyan-500" 
                              : "bg-secondary"
                          }`}
                        >
                          <Icon className={`h-5 w-5 ${isSelected ? "text-white" : "text-muted-foreground"}`} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className={`text-sm font-medium block ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                              {pack.label}
                            </span>
                            {isSelected && (
                              <Badge className="bronze-gradient text-white text-xs">Selected</Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">{pack.description}</span>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
              {selectedIndustry && (
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <p className="text-xs text-blue-400">
                    {industryPacks.find(p => p.id === selectedIndustry)?.label} pack selected with specialized prompts and terminology
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-card/95">
            <Button 
              className="w-full bronze-gradient gap-2" 
              onClick={() => currentTemplate && handleStartChat(currentTemplate)}
              disabled={!selectedIndustry}
            >
              {selectedIndustry ? `Start ${industryPacks.find(p => p.id === selectedIndustry)?.label} Chat` : 'Select an Industry'}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
