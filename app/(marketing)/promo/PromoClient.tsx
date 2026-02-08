"use client"

import Link from "next/link"
import Image from "next/image"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import LogoText from "@/components/branding/LogoText"
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
} from "lucide-react"
import { cn } from "@/lib/utils"

// ═══════════════════════════════════════════════════════════════════════════════
// TECHNOLOGY SECTIONS - Organized in rows of 3 for synchronized expansion
// ═══════════════════════════════════════════════════════════════════════════════
const featureRows = [
  // Row 1
  [
    {
      id: "orchestration",
      title: "Intelligent Orchestration",
      icon: Brain,
      iconColor: "text-purple-400",
      features: [
        { name: "Multi-Model Ensemble", desc: "Routes to optimal AI models" },
        { name: "Deep Consensus", desc: "Models debate for accuracy" },
        { name: "Adaptive Ensemble", desc: "Dynamic model weighting" },
      ],
    },
    {
      id: "strategy",
      title: "Strategy & Coordination",
      icon: Crown,
      iconColor: "text-amber-400",
      features: [
        { name: "Parallel Race", desc: "First good answer wins" },
        { name: "Quality Fusion", desc: "Combine with quality weighting" },
        { name: "Challenge & Refine", desc: "Generate → Critique → Improve" },
      ],
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
      ],
    },
  ],
  // Row 2
  [
    {
      id: "accuracy",
      title: "Accuracy & Verification",
      icon: Shield,
      iconColor: "text-green-400",
      features: [
        { name: "Tool-Based Verification", desc: "Catches hallucinations" },
        { name: "Calculator Math", desc: "100% accurate calculations" },
        { name: "Fact-Check Pipeline", desc: "Web search for claims" },
      ],
    },
    {
      id: "formatting",
      title: "Smart Formatting",
      icon: ListOrdered,
      iconColor: "text-blue-400",
      features: [
        { name: "7 Output Formats", desc: "Bullet, Step-by-Step, Academic..." },
        { name: "Answer Refinement", desc: "Always-on polishing" },
        { name: "Auto Detection", desc: "AI selects optimal format" },
      ],
    },
    {
      id: "industry",
      title: "Industry Packs",
      icon: Briefcase,
      iconColor: "text-orange-400",
      features: [
        { name: "Medical & Legal", desc: "Specialized terminology" },
        { name: "Finance & Coding", desc: "Technical precision" },
        { name: "Research & Marketing", desc: "Domain expertise" },
      ],
    },
  ],
  // Row 3
  [
    {
      id: "memory",
      title: "Memory & Context",
      icon: Database,
      iconColor: "text-cyan-400",
      features: [
        { name: "1M Token Context", desc: "Largest API context window" },
        { name: "Cross-Session Learning", desc: "Insights persist" },
        { name: "RAG Integration", desc: "Your data, augmented" },
      ],
    },
    {
      id: "uptodate",
      title: "Always Up-to-Date",
      icon: RefreshCw,
      iconColor: "text-emerald-400",
      features: [
        { name: "Live Model Rankings", desc: "Real-time benchmarks" },
        { name: "Auto-Optimization", desc: "Best models selected" },
        { name: "New Models Added", desc: "Always latest models" },
      ],
    },
    {
      id: "enterprise",
      title: "Enterprise-Grade",
      icon: Lock,
      iconColor: "text-rose-400",
      features: [
        { name: "Multi-Tenant Isolation", desc: "Your data stays yours" },
        { name: "99.9% Uptime", desc: "Redundant infrastructure" },
        { name: "Audit Logging", desc: "Full traceability" },
      ],
    },
  ],
]

// Benchmark categories
const benchmarkCategories = [
  "GPQA Diamond",
  "SWE-Bench",
  "AIME 2024",
  "MMMLU",
  "ARC-AGI 2",
  "Tool Use",
  "RAG",
  "Multimodal",
  "Dialogue EQ",
  "Long Context",
]

export default function PromoClient() {
  // Track which ROW is expanded (0, 1, 2, or null)
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  return (
    <div className="min-h-screen relative">
      {/* Sticky Header */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-black/40 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-3">
              <Image src="/logo.png" alt="LLMHive" width={36} height={36} className="drop-shadow-lg" />
              <LogoText height={28} variant="nav" />
            </Link>
            <div className="flex items-center gap-3">
              <Link href="/business-ops">
                <Button variant="ghost" size="sm" className="text-white/80 hover:text-white hover:bg-white/10">
                  Business Ops
                </Button>
              </Link>
              <Link href="/sign-in">
                <Button variant="ghost" size="sm" className="text-white/80 hover:text-white hover:bg-white/10">
                  Sign In
                </Button>
              </Link>
              <Link href="/sign-up">
                <Button size="sm" className="bronze-gradient text-white">
                  Start Free
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-20 pb-8 px-4 sm:px-6 lg:px-8 min-h-screen flex flex-col items-center justify-center">
        <div className="text-center max-w-5xl mx-auto llmhive-fade-in">
          {/* 3D Logo */}
          <div className="relative w-52 h-52 md:w-[340px] md:h-[340px] lg:w-[378px] lg:h-[378px] mx-auto -mb-14 md:-mb-24 llmhive-float">
            <Image src="/logo.png" alt="LLMHive" fill className="object-contain drop-shadow-2xl" priority />
          </div>

          {/* LLMHive Metallic Text */}
          <LogoText height={64} className="md:hidden mb-2 mx-auto" />
          <LogoText height={92} className="hidden md:block lg:hidden mb-2 mx-auto" />
          <LogoText height={110} className="hidden lg:block mb-2 mx-auto" />

          {/* Subtitle */}
          <p className="llmhive-subtitle-3d text-sm md:text-base mx-auto mb-4 whitespace-nowrap">
            Patented multi-agent orchestration for enhanced accuracy and performance.
          </p>

          {/* #1 Benchmark Badge */}
          <div className="flex items-center justify-center gap-3 px-6 py-3 rounded-full bg-gradient-to-r from-yellow-500/15 via-amber-500/15 to-[var(--bronze)]/15 border-2 border-yellow-500/40 mb-6 shadow-lg shadow-yellow-500/10">
            <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-gradient-to-br from-yellow-400 via-amber-500 to-[var(--bronze)] flex items-center justify-center shadow-lg">
              <span className="text-base md:text-lg font-bold text-white">#1</span>
            </div>
            <p className="text-sm md:text-lg font-semibold bg-gradient-to-r from-yellow-300 to-amber-400 bg-clip-text text-transparent">
              #1 in ALL 10 Industry Benchmarks · January 2026
            </p>
          </div>

          {/* Value Hook */}
          <h1 className="text-2xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
            GPT-5.2 + Claude Opus 4.5 + Gemini 3 Pro
            <br />
            <span className="bg-gradient-to-r from-yellow-300 via-amber-400 to-[var(--bronze)] bg-clip-text text-transparent">
              Unified. For $29.99/month.
            </span>
          </h1>

          <p className="text-base md:text-lg text-white/80 mb-6 max-w-2xl mx-auto">
            <strong className="text-yellow-400">500 ELITE queries</strong> ranked #1 in ALL benchmarks.
            Then <strong className="text-green-400">UNLIMITED FREE</strong> queries that still beat most
            paid models.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            <Link href="/sign-up">
              <Button size="lg" className="bronze-gradient text-white text-lg px-8 h-14 shadow-xl font-bold">
                <Trophy className="h-5 w-5 mr-2" />
                Get Pro — $29.99/mo
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button
                size="lg"
                variant="outline"
                className="border-2 border-green-500/50 text-green-400 hover:bg-green-500/10 text-lg px-8 h-14"
              >
                <Star className="h-5 w-5 mr-2" />
                Try Free
              </Button>
            </Link>
          </div>

          {/* Trust signals */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-white/60 text-sm">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-400" />
              <span>No credit card required</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-400" />
              <span>Cancel anytime</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-400" />
              <span>SOC 2 compliant</span>
            </div>
          </div>
        </div>
      </section>

      {/* Technology Section */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          {/* Technology Grid - Rows expand together */}
          <div className="text-center mb-8">
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-2">Patented Technology</h2>
            <p className="text-white/60">9 breakthrough features no other AI platform can match</p>
          </div>

          <div className="space-y-3">
            {featureRows.map((row, rowIndex) => {
              const isRowExpanded = expandedRow === rowIndex
              return (
                <div key={rowIndex} className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {row.map((section) => {
                    const Icon = section.icon
                    return (
                      <div
                        key={section.id}
                        className={cn(
                          "rounded-xl border transition-all llmhive-glass",
                          isRowExpanded ? "border-[var(--bronze)]/50" : "border-white/10"
                        )}
                      >
                        <button
                          onClick={() => setExpandedRow(isRowExpanded ? null : rowIndex)}
                          className="w-full flex items-center gap-3 p-3 text-left"
                        >
                          <div
                            className={cn(
                              "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                              isRowExpanded ? "bg-[var(--bronze)]/20" : "bg-white/10"
                            )}
                          >
                            <Icon className={cn("h-4 w-4", section.iconColor)} />
                          </div>
                          <span className="flex-1 text-sm font-semibold text-white">{section.title}</span>
                          {isRowExpanded ? (
                            <ChevronUp className="h-4 w-4 text-white/50" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-white/50" />
                          )}
                        </button>

                        {isRowExpanded && (
                          <div className="px-3 pb-3 space-y-1">
                            {section.features.map((feature, idx) => (
                              <div key={idx} className="flex items-start gap-2 py-1 px-2 rounded bg-white/5 text-xs">
                                <Check className="h-3 w-3 text-[var(--bronze)] mt-0.5 shrink-0" />
                                <span className="text-white/80">{feature.name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Pricing - All 4 Tiers with more info and aligned buttons */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Free */}
            <div className="p-4 rounded-xl llmhive-glass border border-[var(--bronze)]/30 flex flex-col">
              <div className="flex items-center gap-2 mb-2">
                <Star className="h-4 w-4 text-[var(--bronze)]" />
                <h3 className="text-base font-bold text-white">Free</h3>
              </div>
              <div className="text-xl font-bold text-white mb-0.5">$0</div>
              <p className="text-[10px] text-white/60 mb-2">Forever free</p>

              {/* Quota highlight */}
              <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/30 mb-2">
                <div className="flex items-center gap-1.5 text-green-400 text-[11px] font-semibold">
                  <span>🆓</span> UNLIMITED FREE queries
                </div>
              </div>

              <ul className="space-y-1 mb-3 text-[11px] flex-1">
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-green-400" />
                  Multi-model orchestration
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-green-400" />
                  Beats most single models
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-green-400" />
                  Knowledge Base access
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-green-400" />
                  3-day memory
                </li>
              </ul>
              <Link href="/sign-up" className="mt-auto">
                <Button className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white text-xs h-9">
                  Start Free <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            </div>

            {/* Lite */}
            <div className="p-4 rounded-xl llmhive-glass border border-[var(--bronze)]/30 flex flex-col">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-4 w-4 text-blue-400" />
                <h3 className="text-base font-bold text-white">Lite</h3>
              </div>
              <div className="text-xl font-bold text-white mb-0.5">$14.99</div>
              <p className="text-[10px] text-white/60 mb-2">/month</p>

              {/* Quota highlight */}
              <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30 mb-2">
                <div className="flex items-center gap-1.5 text-blue-400 text-[11px] font-semibold">
                  <Zap className="h-3 w-3" /> 100 ELITE queries
                </div>
                <div className="text-green-400 text-[10px]">Then UNLIMITED FREE</div>
              </div>

              <ul className="space-y-1 mb-3 text-[11px] flex-1">
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-blue-400" />
                  #1 quality when using ELITE
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-blue-400" />
                  7-day memory retention
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-blue-400" />
                  Consensus voting
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-blue-400" />
                  Email support
                </li>
              </ul>
              <Link href="/sign-up" className="mt-auto">
                <Button className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white text-xs h-9">
                  Get Lite <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            </div>

            {/* Pro - Featured */}
            <div className="p-4 rounded-xl llmhive-glass border-2 border-yellow-500/50 relative shadow-lg shadow-yellow-500/10 flex flex-col">
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-gradient-to-r from-yellow-500 to-amber-600 rounded-full text-[10px] font-bold text-white">
                BEST VALUE
              </div>
              <div className="flex items-center gap-2 mb-2 mt-1">
                <Rocket className="h-4 w-4 text-yellow-400" />
                <h3 className="text-base font-bold text-white">Pro</h3>
              </div>
              <div className="text-xl font-bold text-white mb-0.5">$29.99</div>
              <p className="text-[10px] text-white/60 mb-2">/month</p>

              {/* Quota highlight */}
              <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30 mb-2">
                <div className="flex items-center gap-1.5 text-yellow-400 text-[11px] font-semibold">
                  <Trophy className="h-3 w-3" /> 500 ELITE queries
                </div>
                <div className="text-green-400 text-[10px]">Then UNLIMITED FREE</div>
              </div>

              <ul className="space-y-1 mb-3 text-[11px] flex-1">
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-yellow-400" />
                  #1 in ALL 10 benchmarks
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-yellow-400" />
                  Full API access
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-yellow-400" />
                  30-day memory
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-yellow-400" />
                  Priority support
                </li>
              </ul>
              <Link href="/sign-up" className="mt-auto">
                <Button className="w-full bronze-gradient text-white text-xs h-9 font-bold">
                  Get Pro — Best Value <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            </div>

            {/* Enterprise */}
            <div className="p-4 rounded-xl llmhive-glass border border-emerald-500/30 flex flex-col">
              <div className="flex items-center gap-2 mb-2">
                <Briefcase className="h-4 w-4 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Enterprise</h3>
              </div>
              <div className="text-xl font-bold text-white mb-0.5">$35</div>
              <p className="text-[10px] text-white/60 mb-2">/seat/month</p>

              {/* Quota highlight */}
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 mb-2">
                <div className="flex items-center gap-1.5 text-emerald-400 text-[11px] font-semibold">
                  <Zap className="h-3 w-3" /> 400 ELITE/seat
                </div>
                <div className="text-green-400 text-[10px]">Then UNLIMITED FREE</div>
              </div>

              <ul className="space-y-1 mb-3 text-[11px] flex-1">
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-emerald-400" />
                  Min 5 seats ($175+/mo)
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-emerald-400" />
                  SSO / SAML auth
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-emerald-400" />
                  SOC 2 Type II
                </li>
                <li className="flex items-center gap-1.5 text-white/80">
                  <Check className="h-2.5 w-2.5 text-emerald-400" />
                  1-year memory
                </li>
              </ul>
              <Link href="/contact" className="mt-auto">
                <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-9">
                  Contact Sales <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <div className="relative w-24 h-24 mx-auto mb-4 llmhive-float">
            <Image src="/logo.png" alt="LLMHive" fill className="object-contain drop-shadow-2xl" />
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
            Ready for <span className="text-yellow-400">#1 AI Quality</span>?
          </h2>
          <p className="text-white/70 mb-6">
            500 ELITE queries. UNLIMITED FREE after. Just{" "}
            <strong className="text-yellow-400">$29.99/month</strong>.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/sign-up">
              <Button size="lg" className="bronze-gradient text-white text-lg px-8 h-12 font-bold">
                <Trophy className="h-5 w-5 mr-2" />
                Get Pro
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button
                size="lg"
                variant="outline"
                className="border-white/30 text-white hover:bg-white/10 text-lg px-8 h-12"
              >
                Try Free
              </Button>
            </Link>
          </div>

          {/* Benchmark Grid - #1 in ALL 10 Categories */}
          <div className="grid grid-cols-5 md:grid-cols-10 gap-2 mt-12">
            {benchmarkCategories.map((benchmark) => (
              <div
                key={benchmark}
                className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-center"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 flex items-center justify-center mx-auto mb-1">
                  <span className="text-xs font-bold text-white">#1</span>
                </div>
                <p className="text-[10px] font-medium text-white/80 truncate">{benchmark}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 px-4 border-t border-white/10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="LLMHive" width={28} height={28} />
            <LogoText height={20} variant="nav" />
          </div>
          <div className="flex items-center gap-4 text-xs text-white/50">
            <Link href="/privacy" className="hover:text-white">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-white">
              Terms
            </Link>
            <Link href="/contact" className="hover:text-white">
              Contact
            </Link>
            <Link href="/business-ops" className="hover:text-white">
              Business Ops
            </Link>
          </div>
          <p className="text-xs text-white/50">© 2026 LLMHive</p>
        </div>
      </footer>
    </div>
  )
}
