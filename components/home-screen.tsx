"use client"

import { useState } from "react"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
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
  Landmark,
  Home,
  X,
  Cpu,
  ListTree,
  Crown,
  Shield,
  Database,
  RefreshCw,
  Lock,
  MessageSquare,
  LayoutGrid,
  List,
  ListOrdered,
  Zap,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import type { OrchestratorSettings, DomainPack, AnswerFormat } from "@/lib/types"

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

// LLMHive Technology feature sections - MUST MATCH powered-by-dropdown.tsx
const featureSections = [
  // 1. Intelligent Orchestration
  {
    id: "orchestration",
    title: "Intelligent Orchestration",
    icon: Brain,
    iconColor: "text-purple-400",
    features: [
      { name: "Multi-Model Ensemble", desc: "Routes to optimal AI models" },
      { name: "Hierarchical Role Management", desc: "Decomposes complex tasks" },
      { name: "Deep Consensus", desc: "Models debate for accuracy" },
      { name: "Adaptive Ensemble", desc: "Dynamic model weighting" },
      { name: "Prompt Diffusion", desc: "Iterative refinement" },
    ]
  },
  // 2. Strategy & Coordination
  {
    id: "strategy",
    title: "Strategy & Coordination",
    icon: Crown,
    iconColor: "text-amber-400",
    features: [
      { name: "Single Best", desc: "Top-ranked model (fastest)" },
      { name: "Parallel Race", desc: "Multiple models, first good answer wins" },
      { name: "Best of N", desc: "Generate N responses, pick the best" },
      { name: "Quality Fusion", desc: "Combine with quality weighting" },
      { name: "Expert Panel", desc: "Specialists synthesize insights" },
      { name: "Challenge & Refine", desc: "Generate → Critique → Improve" },
    ]
  },
  // 3. Advanced Reasoning
  {
    id: "reasoning",
    title: "Advanced Reasoning",
    icon: Sparkles,
    iconColor: "text-yellow-400",
    features: [
      { name: "Chain of Thought", desc: "Step-by-step logic" },
      { name: "Tree of Thoughts", desc: "Multiple solution paths" },
      { name: "Self-Consistency", desc: "Samples & votes on best" },
      { name: "Challenge & Refine", desc: "Models critique each other" },
    ]
  },
  // 4. Accuracy & Verification
  {
    id: "accuracy",
    title: "Accuracy & Verification",
    icon: Shield,
    iconColor: "text-green-400",
    features: [
      { name: "Tool-Based Verification", desc: "Catches hallucinations" },
      { name: "Calculator-Authoritative Math", desc: "100% accurate calculations" },
      { name: "Code Syntax Verification", desc: "Multi-language validation" },
      { name: "Fact-Check Pipeline", desc: "Web search for claims" },
      { name: "Self-Consistency Voting", desc: "Best answer wins" },
    ]
  },
  // 5. Smart Formatting
  {
    id: "formatting",
    title: "Smart Formatting",
    icon: ListOrdered,
    iconColor: "text-blue-400",
    features: [
      { name: "Automatic Format Detection", desc: "AI selects optimal structure" },
      { name: "7 Output Formats", desc: "Bullet, Step-by-Step, Academic..." },
      { name: "Answer Refinement Engine", desc: "Always-on polishing" },
      { name: "Spell Check", desc: "Auto-corrects prompts" },
    ]
  },
  // 6. Industry Packs
  {
    id: "industry-section",
    title: "Industry Packs",
    icon: Briefcase,
    iconColor: "text-orange-400",
    features: [
      { name: "Medical", desc: "Clinical terminology, research" },
      { name: "Legal", desc: "Case law, contracts, compliance" },
      { name: "Finance", desc: "Risk analysis, regulations" },
      { name: "Coding", desc: "Multi-language, debugging" },
      { name: "Research", desc: "Academic sources, citations" },
      { name: "Marketing", desc: "Campaigns, copywriting" },
      { name: "Education", desc: "Curriculum, tutoring" },
      { name: "Real Estate", desc: "Market analysis, contracts" },
      { name: "Creative", desc: "Writing, ideation" },
    ]
  },
  // 7. Memory & Context
  {
    id: "memory",
    title: "Memory & Context",
    icon: Database,
    iconColor: "text-cyan-400",
    features: [
      { name: "Shared Memory", desc: "Remembers across sessions" },
      { name: "Cross-Session Learning", desc: "Insights persist" },
      { name: "1M Token Context", desc: "Largest API context window" },
      { name: "RAG Integration", desc: "Your data, augmented" },
    ]
  },
  // 8. Always Up-to-Date
  {
    id: "uptodate",
    title: "Always Up-to-Date",
    icon: RefreshCw,
    iconColor: "text-emerald-400",
    features: [
      { name: "Live Model Rankings", desc: "Real-time benchmarks" },
      { name: "Auto-Optimization Engine", desc: "Best models selected" },
      { name: "New Model Integration", desc: "Latest models added" },
      { name: "Cost Optimization", desc: "Best performance, lowest cost" },
    ]
  },
  // 9. Enterprise-Grade
  {
    id: "enterprise",
    title: "Enterprise-Grade",
    icon: Lock,
    iconColor: "text-rose-400",
    features: [
      { name: "Multi-Tenant Isolation", desc: "Your data stays yours" },
      { name: "Guardrails & Safety", desc: "Content filtering" },
      { name: "Audit Logging", desc: "Full traceability" },
      { name: "99.9% Uptime", desc: "Redundant infrastructure" },
    ]
  },
]

// Model options
const modelOptions = [
  { id: "automatic", label: "Automatic", description: "Best model per task", icon: Sparkles, color: "text-amber-400" },
  { id: "gpt-4", label: "GPT-4", description: "OpenAI's flagship model", icon: Cpu, color: "text-green-400" },
  { id: "claude-3", label: "Claude 3", description: "Anthropic's latest", icon: Cpu, color: "text-orange-400" },
  { id: "gemini", label: "Gemini", description: "Google's multimodal AI", icon: Cpu, color: "text-blue-400" },
  { id: "llama", label: "Llama 3", description: "Meta's open model", icon: Cpu, color: "text-purple-400" },
]

// Format options
const formatOptions = [
  { id: "automatic", label: "Automatic", description: "AI selects optimal format", icon: Sparkles, color: "text-amber-400" },
  { id: "conversational", label: "Conversational", description: "Natural flowing paragraphs", icon: MessageSquare, color: "text-blue-400" },
  { id: "structured", label: "Structured", description: "Headers, sections & emphasis", icon: LayoutGrid, color: "text-purple-400" },
  { id: "bullet-points", label: "Bullet Points", description: "Quick-scan lists", icon: List, color: "text-green-400" },
  { id: "step-by-step", label: "Step-by-Step", description: "Numbered instructions", icon: ListOrdered, color: "text-orange-400" },
  { id: "academic", label: "Academic", description: "Formal with citations", icon: GraduationCap, color: "text-cyan-400" },
  { id: "concise", label: "Concise", description: "Brief, direct answers", icon: Zap, color: "text-yellow-400" },
]


const templates = [
  {
    id: "technology",
    title: "LLMHive Technology",
    description: "Our patented orchestration features",
    icon: Cpu,
    badgeClass: "icon-badge-purple",
  },
  {
    id: "industry",
    title: "Industry Packs",
    description: "Legal, Medical, Marketing & more",
    icon: Briefcase,
    badgeClass: "icon-badge-orange",
  },
  {
    id: "models",
    title: "Models",
    description: "Choose AI models for your tasks",
    icon: Cpu,
    badgeClass: "icon-badge-cyan",
  },
  {
    id: "format",
    title: "Format",
    description: "How your answers are structured",
    icon: ListTree,
    badgeClass: "icon-badge-pink",
  },
]

type DrawerId = "technology" | "industry" | "models" | "format" | null

export function HomeScreen({ onNewChat, onStartFromTemplate }: HomeScreenProps) {
  const [activeDrawer, setActiveDrawer] = useState<DrawerId>(null)
  const [selectedIndustry, setSelectedIndustry] = useState<DomainPack | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>("automatic")
  const [selectedFormat, setSelectedFormat] = useState<string>("automatic")
  const [expandedSection, setExpandedSection] = useState<string | null>(null)

  const openDrawer = (templateId: string) => {
    setActiveDrawer(templateId as DrawerId)
    if (templateId === "industry") setSelectedIndustry(null)
  }

  const closeDrawer = () => {
    setActiveDrawer(null)
    setExpandedSection(null)
  }

  const handleStartChat = () => {
    let finalPreset: Partial<OrchestratorSettings> = {}
    
    if (activeDrawer === "industry" && selectedIndustry) {
      finalPreset.domainPack = selectedIndustry
    }
    
    if (activeDrawer === "models") {
      finalPreset.selectedModels = selectedModel === "automatic" ? ["automatic"] : [selectedModel]
    }
    
    if (activeDrawer === "format") {
      finalPreset.answerFormat = selectedFormat as AnswerFormat
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
            {/* Header - Different for Technology vs Others */}
            {activeDrawer === "technology" ? (
              <div className="p-4 pb-3 border-b border-white/10">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-400 via-amber-500 to-[var(--bronze)] flex items-center justify-center shadow-lg">
                      <span className="text-lg font-bold text-white">#1</span>
                    </div>
                    <div>
                      <h3 className="font-bold text-base bg-gradient-to-r from-yellow-300 to-amber-400 bg-clip-text text-transparent">
                        #1 in ALL 10 Industry Benchmarks
                      </h3>
                      <p className="text-[10px] text-muted-foreground">January 2026 Rankings</p>
                    </div>
                  </div>
                  <button 
                    onClick={closeDrawer}
                    className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    aria-label="Close drawer"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 pb-3 border-b border-white/10 flex items-center gap-3">
                {currentTemplate && (
                  <>
                    <div className={`icon-badge ${currentTemplate.badgeClass}`}>
                      <currentTemplate.icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <h2 className="text-lg font-semibold">{currentTemplate.title}</h2>
                      <p className="text-sm text-muted-foreground">Select an option</p>
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
            )}

            {/* Content */}
            <ScrollArea className="flex-1 p-4">
              {/* LLMHive Technology - Read-only showcase - MATCHES powered-by-dropdown.tsx */}
              {activeDrawer === "technology" && (
                <div className="space-y-1">
                  {featureSections.map((section, idx) => {
                    const Icon = section.icon
                    const isExpanded = expandedSection === section.id
                    return (
                      <div key={section.id}>
                        {/* Section Header - Clickable to expand */}
                        <button
                          type="button"
                          onClick={() => setExpandedSection(isExpanded ? null : section.id)}
                          className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-md cursor-pointer transition-all text-left ${
                            isExpanded 
                              ? "bg-white/10" 
                              : "hover:bg-white/5"
                          }`}
                        >
                          <div className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 ${
                            isExpanded ? "bg-[var(--bronze)]/20" : "bg-white/10"
                          }`}>
                            <Icon className={`h-3.5 w-3.5 ${section.iconColor}`} />
                          </div>
                          <span className="flex-1 text-sm font-medium">{section.title}</span>
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />}
                        </button>
                        
                        {/* Expanded Features */}
                        {isExpanded && (
                          <div className="ml-4 pl-4 border-l border-white/10 py-1 space-y-1">
                            {section.features.map((feature, fIdx) => (
                              <div 
                                key={fIdx}
                                className="flex items-start gap-2 py-1.5 px-2 rounded text-xs"
                              >
                                <Check className="h-3 w-3 text-[var(--bronze)] mt-0.5 shrink-0" />
                                <div>
                                  <span className="font-medium">{feature.name}</span>
                                  <span className="text-muted-foreground ml-1">— {feature.desc}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {idx < featureSections.length - 1 && !isExpanded && (
                          <div className="my-0.5" />
                        )}
                      </div>
                    )
                  })}
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

              {/* Models Options */}
              {activeDrawer === "models" && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">Select AI model</p>
                  <div className="space-y-1">
                    {modelOptions.map((model) => {
                      const Icon = model.icon
                      const isSelected = selectedModel === model.id
                      return (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => setSelectedModel(model.id)}
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
                              <Icon className={`h-3.5 w-3.5 ${model.color}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className={`text-xs font-medium block ${isSelected ? "text-[var(--gold)]" : ""}`}>
                                {model.label}
                              </span>
                              <span className="text-[10px] text-muted-foreground truncate block">{model.description}</span>
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

              {/* Format Options */}
              {activeDrawer === "format" && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">Choose answer format</p>
                  <div className="space-y-1">
                    {formatOptions.map((format) => {
                      const Icon = format.icon
                      const isSelected = selectedFormat === format.id
                      return (
                        <button
                          key={format.id}
                          type="button"
                          onClick={() => setSelectedFormat(format.id)}
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
                              <Icon className={`h-3.5 w-3.5 ${format.color}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className={`text-xs font-medium block ${isSelected ? "text-[var(--gold)]" : ""}`}>
                                {format.label}
                              </span>
                              <span className="text-[10px] text-muted-foreground truncate block">{format.description}</span>
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
              {activeDrawer === "technology" ? (
                <div className="space-y-3">
                  {/* Patented tech footer - matches dropdown */}
                  <div className="flex items-center justify-between px-2">
                    <span className="text-[10px] text-yellow-400 font-medium">
                      Patented orchestration technology
                    </span>
                    <div className="flex items-center gap-1 text-[10px] text-[var(--bronze)]">
                      <RefreshCw className="h-3 w-3" />
                      <span>Always optimizing</span>
                    </div>
                  </div>
                  <Button 
                    className="w-full bronze-gradient gap-2" 
                    onClick={closeDrawer}
                  >
                    Close
                  </Button>
                </div>
              ) : (
                <Button 
                  className="w-full bronze-gradient gap-2" 
                  onClick={handleStartChat}
                  disabled={activeDrawer === "industry" && !selectedIndustry}
                >
                  {activeDrawer === "industry" && (selectedIndustry ? `Start ${industryPacks.find(p => p.id === selectedIndustry)?.label} Chat` : "Select an Industry")}
                  {activeDrawer === "models" && `Start with ${modelOptions.find(m => m.id === selectedModel)?.label}`}
                  {activeDrawer === "format" && `Start with ${formatOptions.find(f => f.id === selectedFormat)?.label} Format`}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
