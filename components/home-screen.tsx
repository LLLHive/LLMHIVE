"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { LogoText } from "@/components/branding"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
  Home,
  Users,
  Target,
  X,
} from "lucide-react"
import type { OrchestratorSettings, DomainPack } from "@/lib/types"

interface HomeScreenProps {
  onNewChat: () => void
  onStartFromTemplate: (preset: Partial<OrchestratorSettings>) => void
}

// Industry pack options - matches chat-area.tsx domainPacks
const industryPacks: Array<{
  id: DomainPack
  label: string
  description: string
  icon: typeof Scale
  color: string
}> = [
  { id: "default", label: "General Assistant", description: "Versatile AI for everyday tasks", icon: Sparkles, color: "text-amber-400" },
  { id: "medical", label: "Medical Pack", description: "Clinical documentation, research", icon: Stethoscope, color: "text-red-400" },
  { id: "legal", label: "Legal Pack", description: "Contract analysis, case research", icon: Scale, color: "text-purple-400" },
  { id: "marketing", label: "Marketing Pack", description: "Campaigns, copywriting, SEO", icon: Megaphone, color: "text-pink-400" },
  { id: "coding", label: "Coding Pack", description: "Development, debugging, reviews", icon: Code, color: "text-emerald-400" },
  { id: "research", label: "Research Mode", description: "Deep analysis, citations", icon: Brain, color: "text-blue-400" },
  { id: "finance", label: "Finance Pack", description: "Analysis, reports, compliance", icon: Landmark, color: "text-yellow-400" },
  { id: "education", label: "Education Pack", description: "Curriculum, tutoring, grading", icon: GraduationCap, color: "text-cyan-400" },
  { id: "real_estate", label: "Real Estate Pack", description: "Listings, valuations, contracts", icon: Home, color: "text-orange-400" },
]

// Research features
const researchFeatures = [
  { id: "deep_reasoning", label: "Deep Reasoning", description: "Extended chain-of-thought", icon: Brain, color: "text-purple-400" },
  { id: "multi_perspective", label: "Multi-Perspective", description: "Multiple agent viewpoints", icon: Users, color: "text-blue-400" },
  { id: "fact_verification", label: "Fact Verification", description: "Cross-reference claims", icon: Check, color: "text-green-400" },
  { id: "source_citation", label: "Source Citation", description: "Include references", icon: BookOpen, color: "text-cyan-400" },
]

// Code features  
const codeFeatures = [
  { id: "code_review", label: "Code Review", description: "Analyze code quality", icon: FileCode, color: "text-emerald-400" },
  { id: "debugging", label: "Debugging", description: "Find and fix bugs", icon: Bug, color: "text-red-400" },
  { id: "optimization", label: "Optimization", description: "Performance improvements", icon: Zap, color: "text-yellow-400" },
  { id: "best_practices", label: "Best Practices", description: "Industry standards", icon: Shield, color: "text-blue-400" },
]

// General assistant modes
const generalModes = [
  { id: "quick", label: "Quick Response", description: "Fast, concise answers", icon: Zap, color: "text-amber-400" },
  { id: "detailed", label: "Detailed", description: "Comprehensive explanations", icon: BookOpen, color: "text-blue-400" },
  { id: "creative", label: "Creative", description: "Brainstorming and ideas", icon: Lightbulb, color: "text-yellow-400" },
  { id: "focused", label: "Focused", description: "Task-specific assistance", icon: Target, color: "text-pink-400" },
]

const templates = [
  {
    id: "general",
    title: "General Assistant",
    description: "Versatile AI helper for everyday tasks",
    icon: Sparkles,
    badgeClass: "icon-badge-orange",
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
    badgeClass: "icon-badge-purple",
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
    badgeClass: "icon-badge-emerald",
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
    badgeClass: "icon-badge-blue",
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
    setActiveDrawer(templateId as DrawerId)
    setSelectedFeatures([])
    setSelectedMode("quick")
    setSelectedIndustry(null)
  }

  const closeDrawer = () => {
    setActiveDrawer(null)
  }

  const toggleFeature = (featureId: string) => {
    setSelectedFeatures(prev => 
      prev.includes(featureId) 
        ? prev.filter(f => f !== featureId) 
        : [...prev, featureId]
    )
  }

  const handleStartChat = () => {
    const template = templates.find(t => t.id === activeDrawer)
    if (!template) return
    
    let finalPreset: Partial<OrchestratorSettings> = { ...template.preset }
    
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
    
    closeDrawer()
    onStartFromTemplate(finalPreset)
  }

  const currentTemplate = templates.find(t => t.id === activeDrawer)

  return (
    <div className="min-h-full flex flex-col items-center justify-start px-4 pt-4 pb-20 overflow-y-auto relative">
      {/* Hero Section with 3D Logo */}
      <div className="text-center mb-6 llmhive-fade-in">
        <div className="relative w-52 h-52 md:w-[340px] md:h-[340px] lg:w-[378px] lg:h-[378px] mx-auto -mb-14 md:-mb-24 llmhive-float">
          <Image 
            src="/logo.png" 
            alt="LLMHive" 
            fill 
            className="object-contain drop-shadow-2xl" 
            priority 
          />
        </div>
        
        {/* 3D Metallic Title - Using actual rendered image for exact match */}
        <LogoText height={64} className="md:hidden mb-2 mx-auto" />
        <LogoText height={92} className="hidden md:block lg:hidden mb-2 mx-auto" />
        <LogoText height={110} className="hidden lg:block mb-2 mx-auto" />
        
        <p className="llmhive-subtitle-3d text-sm md:text-base mx-auto mb-4 whitespace-nowrap">
          Multi-agent AI orchestration for enhanced accuracy and deeper insights
        </p>
      </div>

      {/* Main CTA Button */}
      <Button
        onClick={onNewChat}
        size="lg"
        className="bronze-gradient mb-6 md:mb-8 h-12 md:h-14 px-8 md:px-10 text-base md:text-lg gap-2 shadow-lg hover:shadow-xl transition-shadow"
      >
        <MessageSquarePlus className="h-5 w-5 md:h-6 md:w-6" />
        Start Chatting
      </Button>

      {/* Template Cards - Glass Cards */}
      <div className="w-full max-w-3xl mx-auto llmhive-fade-in" style={{ animationDelay: '0.1s' }}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          {templates.map((template, index) => {
            const Icon = template.icon
            const cardContent = (
              <>
                {/* Icon Badge */}
                <div className={`icon-badge ${template.badgeClass}`}>
                  <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
                </div>
                
                {/* Card Text */}
                <div className="space-y-0.5 text-center">
                  <h3 className="font-semibold text-sm md:text-base text-foreground group-hover:text-[var(--gold)] transition-colors">
                    {template.title}
                  </h3>
                  <p className="text-xs text-muted-foreground leading-tight line-clamp-2">
                    {template.description}
                  </p>
                </div>
              </>
            )
            
            // Render as button that opens drawer
            return (
              <button
                key={template.id}
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  openDrawer(template.id)
                }}
                className="settings-card group llmhive-fade-in"
                style={{ animationDelay: `${0.15 + index * 0.05}s` }}
              >
                {cardContent}
              </button>
            )
          })}
        </div>
      </div>

      {/* Overlay and Drawer */}
      {activeDrawer && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] animate-in fade-in-0"
            onClick={closeDrawer}
          />
          
          {/* Drawer Panel - Glassmorphism */}
          <div className="fixed inset-y-0 right-0 w-[320px] sm:w-[380px] llmhive-glass border-l-0 rounded-l-2xl z-[101] animate-in slide-in-from-right duration-300 flex flex-col">
            {/* Header */}
            <div className="p-4 pb-3 border-b border-white/10 flex items-center gap-3">
              {currentTemplate && (
                <>
                  <div className={`icon-badge ${currentTemplate.badgeClass}`}>
                    <currentTemplate.icon className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <h2 className="text-lg font-semibold">{currentTemplate.title}</h2>
                    <p className="text-sm text-muted-foreground">Configure your settings</p>
                  </div>
                </>
              )}
              <button 
                onClick={closeDrawer}
                className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                aria-label="Close drawer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <ScrollArea className="flex-1 p-4">
              {/* General Assistant Options */}
              {activeDrawer === "general" && (
                <div className="space-y-4">
                  <p className="text-sm font-medium text-muted-foreground">Select response style</p>
                  <div className="space-y-2">
                    {generalModes.map((mode) => {
                      const Icon = mode.icon
                      const isSelected = selectedMode === mode.id
                      return (
                        <button
                          key={mode.id}
                          type="button"
                          onClick={() => setSelectedMode(mode.id)}
                          className={`w-full p-4 rounded-lg border transition-all text-left ${
                            isSelected
                              ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                              : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                                isSelected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                              }`}
                            >
                              {isSelected && <Check className="h-3 w-3 text-black" />}
                            </div>
                            <Icon className={`h-5 w-5 ${mode.color}`} />
                            <div>
                              <span className={`text-sm font-medium block ${isSelected ? "text-[var(--gold)]" : ""}`}>
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
              )}

              {/* Research Options */}
              {activeDrawer === "research" && (
                <div className="space-y-4">
                  <p className="text-sm font-medium text-muted-foreground">Enable features</p>
                  <div className="space-y-2">
                    {researchFeatures.map((feature) => {
                      const Icon = feature.icon
                      const isSelected = selectedFeatures.includes(feature.id)
                      return (
                        <button
                          key={feature.id}
                          type="button"
                          onClick={() => toggleFeature(feature.id)}
                          className={`w-full p-4 rounded-lg border transition-all text-left ${
                            isSelected
                              ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                              : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Icon className={`h-5 w-5 ${feature.color}`} />
                              <div>
                                <span className={`text-sm font-medium block ${isSelected ? "text-[var(--gold)]" : ""}`}>
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
                    <div className="p-3 rounded-lg glass-card border-purple-500/20">
                      <p className="text-xs text-purple-400">
                        {selectedFeatures.length} feature{selectedFeatures.length > 1 ? 's' : ''} enabled for deeper analysis
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Code Options */}
              {activeDrawer === "code" && (
                <div className="space-y-4">
                  <p className="text-sm font-medium text-muted-foreground">Enable features</p>
                  <div className="space-y-2">
                    {codeFeatures.map((feature) => {
                      const Icon = feature.icon
                      const isSelected = selectedFeatures.includes(feature.id)
                      return (
                        <button
                          key={feature.id}
                          type="button"
                          onClick={() => toggleFeature(feature.id)}
                          className={`w-full p-4 rounded-lg border transition-all text-left ${
                            isSelected
                              ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                              : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Icon className={`h-5 w-5 ${feature.color}`} />
                              <div>
                                <span className={`text-sm font-medium block ${isSelected ? "text-[var(--gold)]" : ""}`}>
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
                    <div className="p-3 rounded-lg glass-card border-emerald-500/20">
                      <p className="text-xs text-emerald-400">
                        {selectedFeatures.length} coding feature{selectedFeatures.length > 1 ? 's' : ''} enabled
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Industry Options */}
              {activeDrawer === "industry" && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">Choose an industry pack</p>
                  <div className="space-y-1">
                    {industryPacks.map((pack) => {
                      const Icon = pack.icon
                      const isSelected = selectedIndustry === pack.id
                      return (
                        <button
                          key={pack.id}
                          type="button"
                          onClick={() => setSelectedIndustry(pack.id)}
                          className={`w-full p-2 rounded-lg border transition-all text-left ${
                            isSelected
                              ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                              : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className={`w-7 h-7 rounded-md flex items-center justify-center transition-all shrink-0 ${
                                isSelected 
                                  ? "bg-[var(--bronze)]/20 border border-[var(--bronze)]/50" 
                                  : "bg-white/10"
                              }`}
                            >
                              <Icon className={`h-3.5 w-3.5 ${pack.color}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className={`text-xs font-medium block ${isSelected ? "text-[var(--gold)]" : ""}`}>
                                {pack.label}
                              </span>
                              <span className="text-[10px] text-muted-foreground truncate block">{pack.description}</span>
                            </div>
                            {isSelected && (
                              <Check className="h-4 w-4 text-[var(--bronze)] shrink-0" />
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </ScrollArea>

            {/* Footer */}
            <div className="p-4 border-t border-white/10">
              <Button 
                className="w-full bronze-gradient gap-2" 
                onClick={handleStartChat}
                disabled={activeDrawer === "industry" && !selectedIndustry}
              >
                {activeDrawer === "general" && "Start Chat"}
                {activeDrawer === "research" && "Start Research"}
                {activeDrawer === "code" && "Start Coding"}
                {activeDrawer === "industry" && (selectedIndustry ? `Start ${industryPacks.find(p => p.id === selectedIndustry)?.label} Chat` : "Select an Industry")}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
