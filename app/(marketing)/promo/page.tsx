"use client"

import Link from "next/link"
import Image from "next/image"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { LogoText } from "@/components/branding"
import { 
  ArrowRight,
  Check,
  Brain,
  Crown,
  Sparkles,
  Shield,
  ListOrdered,
  Briefcase,
  Database,
  RefreshCw,
  Lock,
  ChevronDown,
  ChevronUp,
  Trophy,
  Zap,
  Star,
  Rocket,
  MessageSquarePlus,
  Play,
} from "lucide-react"
import { cn } from "@/lib/utils"

// ═══════════════════════════════════════════════════════════════════════════════
// TECHNOLOGY SECTIONS - Same as home-screen.tsx
// ═══════════════════════════════════════════════════════════════════════════════
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
    icon: Briefcase,
    iconColor: "text-orange-400",
    features: [
      { name: "Medical", desc: "Clinical terminology, research" },
      { name: "Legal", desc: "Case law, contracts, compliance" },
      { name: "Finance", desc: "Risk analysis, regulations" },
      { name: "Coding", desc: "Multi-language, debugging" },
      { name: "Research", desc: "Academic sources, citations" },
      { name: "Marketing", desc: "Campaigns, copywriting" },
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

// Benchmark categories
const benchmarkCategories = [
  "GPQA Diamond", "SWE-Bench", "AIME 2024", "MMMLU", "ARC-AGI 2",
  "Tool Use", "RAG", "Multimodal", "Dialogue EQ", "Long Context"
]

export default function PromoLandingPage() {
  const [expandedSection, setExpandedSection] = useState<string | null>(null)

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Forest Background - Full page */}
      <div className="fixed inset-0 z-0">
        <Image
          src="/backgrounds/forest-bg.png"
          alt="Forest background"
          fill
          className="object-cover"
          priority
          quality={90}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/60" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Sticky Header */}
        <nav className="fixed top-0 left-0 right-0 z-50 bg-black/30 backdrop-blur-md border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <Link href="/" className="flex items-center gap-3">
                <Image src="/logo.png" alt="LLMHive" width={40} height={40} className="drop-shadow-lg" />
                <span className="text-xl font-bold text-white">LLMHive</span>
              </Link>
              <div className="flex items-center gap-3">
                <Link href="/sign-in">
                  <Button variant="ghost" size="sm" className="text-white/80 hover:text-white hover:bg-white/10">
                    Sign In
                  </Button>
                </Link>
                <Link href="/sign-up">
                  <Button size="sm" className="bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white">
                    Get Started Free
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="pt-24 pb-16 px-4 sm:px-6 lg:px-8 min-h-screen flex flex-col items-center justify-center">
          <div className="text-center max-w-5xl mx-auto">
            {/* 3D Logo */}
            <div className="relative w-48 h-48 md:w-64 md:h-64 lg:w-80 lg:h-80 mx-auto mb-4 llmhive-float">
              <Image 
                src="/logo.png" 
                alt="LLMHive" 
                fill 
                className="object-contain drop-shadow-2xl" 
                priority 
              />
            </div>
            
            {/* LLMHive Metallic Text */}
            <LogoText height={80} className="md:hidden mb-4 mx-auto" />
            <LogoText height={100} className="hidden md:block lg:hidden mb-4 mx-auto" />
            <LogoText height={120} className="hidden lg:block mb-4 mx-auto" />

            {/* Subtitle */}
            <p className="llmhive-subtitle-3d text-base md:text-lg mx-auto mb-6 whitespace-nowrap">
              Patented multi-agent orchestration for enhanced accuracy and performance.
            </p>

            {/* #1 Benchmark Badge - HUGE */}
            <div className="flex items-center justify-center gap-4 px-8 py-4 rounded-2xl bg-gradient-to-r from-yellow-500/20 via-amber-500/20 to-[var(--bronze)]/20 border-2 border-yellow-500/50 mb-8 shadow-2xl shadow-yellow-500/20 max-w-xl mx-auto">
              <div className="w-16 h-16 md:w-20 md:h-20 rounded-full bg-gradient-to-br from-yellow-400 via-amber-500 to-[var(--bronze)] flex items-center justify-center shadow-xl">
                <Trophy className="h-8 w-8 md:h-10 md:w-10 text-white" />
              </div>
              <div className="text-left">
                <p className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-yellow-300 to-amber-400 bg-clip-text text-transparent">
                  #1 in ALL 10 Industry Benchmarks
                </p>
                <p className="text-sm md:text-base text-white/70">January 2026 · Verified Rankings</p>
              </div>
            </div>

            {/* Value Proposition */}
            <h1 className="text-3xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
              The World&apos;s Best AI Quality<br />
              <span className="bg-gradient-to-r from-yellow-300 via-amber-400 to-[var(--bronze)] bg-clip-text text-transparent">
                For Just $29.99/month
              </span>
            </h1>

            <p className="text-lg md:text-xl text-white/80 mb-8 max-w-3xl mx-auto leading-relaxed">
              Get <strong className="text-yellow-400">500 ELITE queries</strong> ranked #1 in ALL categories — 
              powered by GPT-5.2, Claude Opus 4.5 & Gemini 3 Pro unified. 
              After that, enjoy <strong className="text-green-400">UNLIMITED FREE queries</strong> that still beat most single paid models.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
              <Link href="/sign-up">
                <Button size="lg" className="bg-gradient-to-r from-amber-500 to-[var(--bronze)] hover:from-amber-600 hover:to-[var(--bronze-dark)] text-white text-lg px-10 h-16 shadow-xl shadow-amber-500/30 font-bold">
                  <Trophy className="h-6 w-6 mr-2" />
                  Get Pro — $29.99/mo
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/sign-up">
                <Button size="lg" variant="outline" className="border-2 border-green-500/50 text-green-400 hover:bg-green-500/10 text-lg px-10 h-16 bg-black/30">
                  <Star className="h-6 w-6 mr-2" />
                  Try Free First
                </Button>
              </Link>
            </div>

            {/* Quick Stats */}
            <div className="flex flex-wrap items-center justify-center gap-8 text-white/60 text-sm">
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-400" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-400" />
                <span>UNLIMITED FREE queries</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-400" />
                <span>Cancel anytime</span>
              </div>
            </div>
          </div>

          {/* Scroll indicator */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
            <ChevronDown className="h-8 w-8 text-white/50" />
          </div>
        </section>

        {/* Why We're #1 Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-black/60 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
                Why We&apos;re <span className="text-yellow-400">#1 in ALL 10</span> Categories
              </h2>
              <p className="text-xl text-white/70 max-w-3xl mx-auto">
                Our patented orchestration technology combines GPT-5.2, Claude Opus 4.5, and Gemini 3 Pro 
                with consensus voting, challenge-refine workflows, and tool integration.
              </p>
            </div>

            {/* Benchmark Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-16">
              {benchmarkCategories.map((benchmark, i) => (
                <div 
                  key={benchmark}
                  className="p-4 rounded-xl bg-gradient-to-br from-yellow-500/10 to-amber-500/5 border border-yellow-500/30 text-center group hover:border-yellow-500/60 transition-all"
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 via-amber-500 to-[var(--bronze)] flex items-center justify-center mx-auto mb-3 shadow-lg group-hover:scale-110 transition-transform">
                    <span className="text-lg font-bold text-white">#1</span>
                  </div>
                  <p className="text-sm font-medium text-white">{benchmark}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Technology Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
                Patented Orchestration Technology
              </h2>
              <p className="text-xl text-white/70 max-w-3xl mx-auto">
                9 breakthrough features that no other AI platform can match.
              </p>
            </div>

            {/* Technology Accordion */}
            <div className="grid md:grid-cols-2 gap-4">
              {featureSections.map((section) => {
                const Icon = section.icon
                const isExpanded = expandedSection === section.id
                return (
                  <div 
                    key={section.id}
                    className={cn(
                      "rounded-xl border transition-all",
                      isExpanded 
                        ? "bg-white/10 border-[var(--bronze)]/50" 
                        : "bg-black/30 border-white/10 hover:border-white/30"
                    )}
                  >
                    <button
                      onClick={() => setExpandedSection(isExpanded ? null : section.id)}
                      className="w-full flex items-center gap-4 p-4 text-left"
                    >
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center",
                        isExpanded ? "bg-[var(--bronze)]/20" : "bg-white/10"
                      )}>
                        <Icon className={cn("h-5 w-5", section.iconColor)} />
                      </div>
                      <span className="flex-1 text-lg font-semibold text-white">{section.title}</span>
                      {isExpanded ? (
                        <ChevronUp className="h-5 w-5 text-white/50" />
                      ) : (
                        <ChevronDown className="h-5 w-5 text-white/50" />
                      )}
                    </button>
                    
                    {isExpanded && (
                      <div className="px-4 pb-4 space-y-2">
                        {section.features.map((feature, idx) => (
                          <div key={idx} className="flex items-start gap-3 py-2 px-3 rounded-lg bg-white/5">
                            <Check className="h-4 w-4 text-[var(--bronze)] mt-0.5 shrink-0" />
                            <div>
                              <span className="font-medium text-white">{feature.name}</span>
                              <span className="text-white/60 ml-2">— {feature.desc}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-black/60 backdrop-blur-sm">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
                How It Works
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  step: "1",
                  icon: Trophy,
                  iconColor: "text-yellow-400",
                  bgColor: "from-yellow-500/20 to-amber-500/10",
                  title: "Get 500 ELITE queries with Pro",
                  description: "Each ELITE query uses our #1 ranked orchestration with GPT-5.2, Claude Opus 4.5 & Gemini 3 Pro. Perfect for professional work."
                },
                {
                  step: "2",
                  icon: Zap,
                  iconColor: "text-green-400",
                  bgColor: "from-green-500/20 to-emerald-500/10",
                  title: "UNLIMITED FREE after",
                  description: "After your ELITE quota, you get unlimited FREE tier queries. Our FREE orchestration still beats most single paid models."
                },
                {
                  step: "3",
                  icon: Rocket,
                  iconColor: "text-purple-400",
                  bgColor: "from-purple-500/20 to-pink-500/10",
                  title: "Upgrade anytime",
                  description: "Need more #1 quality? Upgrade from Lite to Pro for 5x more ELITE queries. Or go Enterprise for team features."
                }
              ].map((item) => (
                <div 
                  key={item.step}
                  className={cn(
                    "p-6 rounded-2xl bg-gradient-to-br border border-white/10",
                    item.bgColor
                  )}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center">
                      <item.icon className={cn("h-6 w-6", item.iconColor)} />
                    </div>
                    <span className="text-4xl font-bold text-white/20">{item.step}</span>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">{item.title}</h3>
                  <p className="text-white/70">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing Comparison */}
        <section className="py-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
                Simple Pricing, Maximum Value
              </h2>
              <p className="text-xl text-white/70">
                Start free, upgrade when you&apos;re ready for #1 quality.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {/* Free */}
              <div className="p-6 rounded-2xl bg-gradient-to-b from-green-500/10 to-emerald-500/5 border border-green-500/30">
                <div className="flex items-center gap-2 mb-4">
                  <Star className="h-5 w-5 text-green-400" />
                  <h3 className="text-lg font-bold text-white">Free</h3>
                </div>
                <div className="text-3xl font-bold text-white mb-2">$0</div>
                <p className="text-sm text-white/60 mb-4">Forever free</p>
                <ul className="space-y-2 mb-6">
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-green-400" />
                    50 FREE queries/month
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-green-400" />
                    Beats most single models
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-green-400" />
                    Knowledge Base access
                  </li>
                </ul>
                <Link href="/sign-up">
                  <Button className="w-full bg-green-600 hover:bg-green-700 text-white">
                    Start Free
                  </Button>
                </Link>
              </div>

              {/* Pro - Featured */}
              <div className="p-6 rounded-2xl bg-gradient-to-b from-yellow-500/20 to-amber-500/10 border-2 border-yellow-500/50 relative scale-105 shadow-2xl shadow-yellow-500/20">
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-yellow-500 to-amber-600 rounded-full text-sm font-bold text-white">
                  BEST VALUE
                </div>
                <div className="flex items-center gap-2 mb-4">
                  <Rocket className="h-5 w-5 text-yellow-400" />
                  <h3 className="text-lg font-bold text-white">Pro</h3>
                </div>
                <div className="text-3xl font-bold text-white mb-2">$29.99</div>
                <p className="text-sm text-white/60 mb-4">/month</p>
                <ul className="space-y-2 mb-6">
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Trophy className="h-4 w-4 text-yellow-400" />
                    <strong>500 ELITE queries</strong>
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-yellow-400" />
                    #1 in ALL 10 benchmarks
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-green-400" />
                    UNLIMITED FREE after
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-yellow-400" />
                    Full API access
                  </li>
                </ul>
                <Link href="/sign-up">
                  <Button className="w-full bg-gradient-to-r from-yellow-500 to-amber-600 hover:from-yellow-600 hover:to-amber-700 text-white font-bold">
                    Get Pro Now
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {/* Enterprise */}
              <div className="p-6 rounded-2xl bg-gradient-to-b from-purple-500/10 to-pink-500/5 border border-purple-500/30">
                <div className="flex items-center gap-2 mb-4">
                  <Briefcase className="h-5 w-5 text-purple-400" />
                  <h3 className="text-lg font-bold text-white">Enterprise</h3>
                </div>
                <div className="text-3xl font-bold text-white mb-2">$35</div>
                <p className="text-sm text-white/60 mb-4">/seat/month</p>
                <ul className="space-y-2 mb-6">
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-purple-400" />
                    400 ELITE/seat
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-purple-400" />
                    SSO & SAML
                  </li>
                  <li className="flex items-center gap-2 text-sm text-white/80">
                    <Check className="h-4 w-4 text-purple-400" />
                    SOC 2 compliance
                  </li>
                </ul>
                <Link href="/contact">
                  <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white">
                    Contact Sales
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-transparent to-black/80">
          <div className="max-w-4xl mx-auto text-center">
            {/* Logo */}
            <div className="relative w-32 h-32 md:w-40 md:h-40 mx-auto mb-6 llmhive-float">
              <Image 
                src="/logo.png" 
                alt="LLMHive" 
                fill 
                className="object-contain drop-shadow-2xl" 
              />
            </div>

            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">
              Ready for <span className="text-yellow-400">#1 AI Quality</span>?
            </h2>
            <p className="text-xl text-white/70 mb-10 max-w-2xl mx-auto">
              500 ELITE queries. UNLIMITED FREE after. Full API access.<br />
              The world&apos;s best AI orchestration for just <strong className="text-yellow-400">$29.99/month</strong>.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/sign-up">
                <Button size="lg" className="bg-gradient-to-r from-amber-500 to-[var(--bronze)] hover:from-amber-600 hover:to-[var(--bronze-dark)] text-white text-lg px-10 h-16 shadow-xl shadow-amber-500/30 font-bold">
                  <Trophy className="h-6 w-6 mr-2" />
                  Get Pro — $29.99/mo
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/sign-up">
                <Button size="lg" variant="outline" className="border-2 border-white/30 text-white hover:bg-white/10 text-lg px-10 h-16">
                  Try Free First
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-8 px-4 sm:px-6 lg:px-8 bg-black/80 border-t border-white/10">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Image src="/logo.png" alt="LLMHive" width={32} height={32} />
              <span className="font-semibold text-white">LLMHive</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-white/50">
              <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
              <Link href="/terms" className="hover:text-white transition-colors">Terms</Link>
              <Link href="/contact" className="hover:text-white transition-colors">Contact</Link>
            </div>
            <p className="text-sm text-white/50">
              © 2026 LLMHive. All rights reserved.
            </p>
          </div>
        </footer>
      </div>

      {/* CSS for animations */}
      <style jsx global>{`
        .llmhive-float {
          animation: float 6s ease-in-out infinite;
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
      `}</style>
    </div>
  )
}
