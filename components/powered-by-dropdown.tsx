"use client"

import { useState } from "react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { 
  ChevronDown, 
  Brain, 
  Sparkles, 
  Shield, 
  Calculator, 
  Code, 
  Search, 
  CheckCircle,
  MessageSquare,
  ListOrdered,
  Zap,
  Database,
  RefreshCw,
  TrendingUp,
  Building2,
  Heart,
  Scale,
  Landmark,
  GraduationCap,
  Megaphone,
  Home,
  Palette,
  FlaskConical,
  Link,
  Clock,
  Globe,
  Lock,
  FileText,
  Cpu,
  Crown
} from "lucide-react"
import { cn } from "@/lib/utils"

// Feature sections data
const featureSections = [
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
  {
    id: "industry",
    title: "Industry Packs",
    icon: Building2,
    iconColor: "text-amber-400",
    features: [
      { name: "Medical", desc: "Clinical terminology, research", icon: Heart },
      { name: "Legal", desc: "Case law, contracts, compliance", icon: Scale },
      { name: "Finance", desc: "Risk analysis, regulations", icon: Landmark },
      { name: "Coding", desc: "Multi-language, debugging", icon: Code },
      { name: "Research", desc: "Academic sources, citations", icon: FlaskConical },
      { name: "Marketing", desc: "Campaigns, copywriting", icon: Megaphone },
      { name: "Education", desc: "Curriculum, tutoring", icon: GraduationCap },
      { name: "Real Estate", desc: "Market analysis, contracts", icon: Home },
      { name: "Creative", desc: "Writing, ideation", icon: Palette },
    ]
  },
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

export function PoweredByDropdown() {
  const [open, setOpen] = useState(false)
  const [expandedSection, setExpandedSection] = useState<string | null>(null)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-8 px-3 text-xs bg-gradient-to-r from-purple-500/20 to-amber-500/20 border border-purple-500/30 rounded-lg hover:from-purple-500/30 hover:to-amber-500/30 hover:border-purple-400/50 transition-all"
        >
          <Cpu className="h-3.5 w-3.5 text-purple-400" />
          <span className="hidden sm:inline font-medium bg-gradient-to-r from-purple-300 to-amber-300 bg-clip-text text-transparent">
            LLMHive Technology
          </span>
          <span className="sm:hidden font-medium bg-gradient-to-r from-purple-300 to-amber-300 bg-clip-text text-transparent">
            Tech
          </span>
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        align="start" 
        className="w-80 max-h-[80vh] overflow-y-auto p-0 bg-gradient-to-b from-background to-background/95"
      >
        {/* Header */}
        <div className="px-4 py-3 bg-gradient-to-r from-purple-500/10 to-amber-500/10 border-b border-border/50">
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
        </div>

        {/* Feature Sections */}
        <div className="p-2">
          {featureSections.map((section, idx) => {
            const SectionIcon = section.icon
            const isExpanded = expandedSection === section.id
            
            return (
              <div key={section.id}>
                {/* Section Header - Clickable to expand */}
                <div
                  className={cn(
                    "flex items-center gap-2.5 px-2 py-2 rounded-md cursor-pointer transition-all",
                    isExpanded 
                      ? "bg-secondary/80" 
                      : "hover:bg-secondary/50"
                  )}
                  onClick={() => setExpandedSection(isExpanded ? null : section.id)}
                >
                  <div className={cn(
                    "w-6 h-6 rounded-md flex items-center justify-center shrink-0",
                    isExpanded ? "bg-[var(--bronze)]/20" : "bg-muted"
                  )}>
                    <SectionIcon className={cn("h-3.5 w-3.5", section.iconColor)} />
                  </div>
                  <span className="flex-1 text-sm font-medium">{section.title}</span>
                  <ChevronDown className={cn(
                    "h-3.5 w-3.5 text-muted-foreground transition-transform",
                    isExpanded && "rotate-180"
                  )} />
                </div>
                
                {/* Expanded Features */}
                {isExpanded && (
                  <div className="ml-4 pl-4 border-l border-border/50 py-1 space-y-1">
                    {section.features.map((feature, fIdx) => {
                      const FeatureIcon = (feature as any).icon || CheckCircle
                      return (
                        <div 
                          key={fIdx}
                          className="flex items-start gap-2 py-1.5 px-2 rounded text-xs"
                        >
                          <FeatureIcon className="h-3 w-3 text-[var(--bronze)] mt-0.5 shrink-0" />
                          <div>
                            <span className="font-medium">{feature.name}</span>
                            <span className="text-muted-foreground ml-1">— {feature.desc}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
                
                {idx < featureSections.length - 1 && !isExpanded && (
                  <div className="my-1" />
                )}
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 bg-gradient-to-r from-purple-500/5 to-amber-500/5 border-t border-border/50">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">
              Patented orchestration technology
            </span>
            <div className="flex items-center gap-1 text-[10px] text-[var(--bronze)]">
              <TrendingUp className="h-3 w-3" />
              <span>Always optimizing</span>
            </div>
          </div>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
