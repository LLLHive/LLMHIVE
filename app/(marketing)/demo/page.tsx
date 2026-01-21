"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { LogoText } from "@/components/branding"
import { 
  Play, 
  Pause,
  Brain, 
  Zap, 
  Shield, 
  Layers, 
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  MessageSquare,
  Code,
  FileSearch,
  Lightbulb,
  BarChart3,
  Users,
  Clock,
  Award,
} from "lucide-react"

// Demo sections with timestamps
const DEMO_SECTIONS = [
  { id: "intro", title: "Introduction", timestamp: "0:00", icon: Play },
  { id: "chat", title: "Starting a Chat", timestamp: "0:45", icon: MessageSquare },
  { id: "orchestration", title: "Orchestration Modes", timestamp: "2:15", icon: Brain },
  { id: "elite", title: "ELITE Mode Deep Dive", timestamp: "4:30", icon: Zap },
  { id: "templates", title: "Templates & Presets", timestamp: "6:00", icon: Lightbulb },
  { id: "analytics", title: "Analytics & Usage", timestamp: "7:30", icon: BarChart3 },
]

// Key features highlighted in the demo
const KEY_FEATURES = [
  {
    icon: Brain,
    title: "Multi-Model Orchestration",
    description: "See how LLMHive intelligently combines GPT-4, Claude, Gemini, and more for superior results.",
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
  },
  {
    icon: Zap,
    title: "ELITE Mode Performance",
    description: "Watch our advanced reasoning methods (HRM, DeepConf, Adaptive Ensemble) in action.",
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description: "Learn how PII redaction and content filtering protect your sensitive data.",
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
  },
  {
    icon: Layers,
    title: "Accuracy Levels",
    description: "Understand the difference between Standard, High, and Maximum accuracy modes.",
    color: "text-green-400",
    bgColor: "bg-green-400/10",
  },
]

// Use case examples
const USE_CASES = [
  { icon: Code, title: "Code Generation", description: "Complex multi-file code with best practices" },
  { icon: FileSearch, title: "Research Analysis", description: "Deep analysis with source citations" },
  { icon: MessageSquare, title: "Content Creation", description: "Marketing copy, blog posts, documentation" },
  { icon: BarChart3, title: "Data Analysis", description: "Insights from structured and unstructured data" },
]

export default function DemoPage() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [activeSection, setActiveSection] = useState("intro")

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="border-b border-[#262626] bg-[#0a0a0a]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <LogoText className="h-8" />
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/pricing">
              <Button variant="ghost" size="sm">Pricing</Button>
            </Link>
            <Link href="/sign-up">
              <Button size="sm" className="bronze-gradient text-[#0a0a0a]">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 border-b border-[#262626]">
        <div className="container mx-auto px-4">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#C48E48]/10 border border-[#C48E48]/20 text-[#C48E48] text-sm mb-6">
              <Play className="h-4 w-4" />
              Product Demo
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
              See LLMHive in Action
            </h1>
            <p className="text-xl text-muted-foreground">
              Watch how our multi-model orchestration delivers consistently superior AI results
              across coding, research, analysis, and more.
            </p>
          </div>

          {/* Video Player Placeholder */}
          <div className="max-w-4xl mx-auto">
            <div 
              className="relative aspect-video rounded-2xl overflow-hidden border border-[#262626] bg-[#171717]"
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {/* Video Placeholder - Replace with actual video embed */}
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-[#171717] to-[#0a0a0a]">
                {/* Decorative background */}
                <div className="absolute inset-0 opacity-20">
                  <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-[#C48E48] blur-[100px]" />
                  <div className="absolute bottom-1/4 right-1/4 w-48 h-48 rounded-full bg-purple-500 blur-[80px]" />
                </div>

                {/* Play button */}
                <button 
                  className="relative z-10 w-24 h-24 rounded-full bg-[#C48E48] flex items-center justify-center shadow-lg shadow-[#C48E48]/20 hover:scale-105 transition-transform"
                  aria-label={isPlaying ? "Pause video" : "Play video"}
                >
                  {isPlaying ? (
                    <Pause className="h-10 w-10 text-[#0a0a0a]" />
                  ) : (
                    <Play className="h-10 w-10 text-[#0a0a0a] ml-1" />
                  )}
                </button>
                
                <p className="relative z-10 mt-6 text-muted-foreground">
                  {isPlaying ? "Demo playing..." : "Click to play demo video"}
                </p>
                
                {/* Duration badge */}
                <div className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/50 backdrop-blur-sm text-sm text-white/80">
                  <Clock className="h-4 w-4" />
                  8:30
                </div>
              </div>

              {/* Video element placeholder - uncomment when video is ready
              <video 
                className="w-full h-full object-cover"
                poster="/demo-thumbnail.jpg"
                controls
              >
                <source src="/demo-video.mp4" type="video/mp4" />
              </video>
              */}
            </div>

            {/* Video chapters */}
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {DEMO_SECTIONS.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                    activeSection === section.id
                      ? "bg-[#C48E48]/20 text-[#C48E48] border border-[#C48E48]/30"
                      : "bg-[#262626]/50 text-muted-foreground hover:bg-[#262626] hover:text-foreground"
                  }`}
                >
                  <section.icon className="h-4 w-4" />
                  <span>{section.title}</span>
                  <span className="text-xs opacity-60">{section.timestamp}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Key Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              What You'll Learn
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              This demo covers all the key features that make LLMHive the most powerful
              AI orchestration platform available.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {KEY_FEATURES.map((feature, index) => (
              <div
                key={feature.title}
                className="flex gap-4 p-6 rounded-xl bg-[#171717] border border-[#262626] hover:border-[#333] transition-colors"
              >
                <div className={`flex-shrink-0 w-12 h-12 rounded-xl ${feature.bgColor} flex items-center justify-center`}>
                  <feature.icon className={`h-6 w-6 ${feature.color}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 border-t border-[#262626] bg-[#0d0d0d]">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Real-World Use Cases
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              See how professionals across industries use LLMHive to accelerate their work.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-5xl mx-auto">
            {USE_CASES.map((useCase) => (
              <div
                key={useCase.title}
                className="p-5 rounded-xl bg-[#171717] border border-[#262626] text-center hover:border-[#C48E48]/30 transition-colors group"
              >
                <div className="w-12 h-12 rounded-xl bg-[#C48E48]/10 flex items-center justify-center mx-auto mb-4 group-hover:bg-[#C48E48]/20 transition-colors">
                  <useCase.icon className="h-6 w-6 text-[#C48E48]" />
                </div>
                <h3 className="font-semibold text-foreground mb-1">
                  {useCase.title}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {useCase.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 border-t border-[#262626]">
        <div className="container mx-auto px-4">
          <div className="grid sm:grid-cols-3 gap-8 max-w-3xl mx-auto text-center">
            <div>
              <div className="flex items-center justify-center gap-2 mb-2">
                <Award className="h-6 w-6 text-[#C48E48]" />
                <span className="text-4xl font-bold text-foreground">#1</span>
              </div>
              <p className="text-muted-foreground">Ranked in 10/10 Categories</p>
            </div>
            <div>
              <div className="flex items-center justify-center gap-2 mb-2">
                <Zap className="h-6 w-6 text-[#C48E48]" />
                <span className="text-4xl font-bold text-foreground">5x</span>
              </div>
              <p className="text-muted-foreground">Faster Than Manual Selection</p>
            </div>
            <div>
              <div className="flex items-center justify-center gap-2 mb-2">
                <Users className="h-6 w-6 text-[#C48E48]" />
                <span className="text-4xl font-bold text-foreground">10k+</span>
              </div>
              <p className="text-muted-foreground">Active Users</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 border-t border-[#262626]">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Ready to Experience ELITE AI?
            </h2>
            <p className="text-muted-foreground mb-8">
              Join thousands of professionals who've upgraded their AI workflow with LLMHive.
              Start free, no credit card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/sign-up">
                <Button size="lg" className="bronze-gradient text-[#0a0a0a] font-semibold w-full sm:w-auto">
                  Get Started Free
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/pricing">
                <Button size="lg" variant="outline" className="w-full sm:w-auto">
                  View Pricing
                  <ChevronRight className="ml-1 h-5 w-5" />
                </Button>
              </Link>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              ✓ 100 free queries · ✓ No credit card · ✓ Cancel anytime
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#262626] py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <LogoText className="h-5 opacity-50" />
              <span>© {new Date().getFullYear()} LLMHive</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy</Link>
              <Link href="/terms" className="hover:text-foreground transition-colors">Terms</Link>
              <Link href="/contact" className="hover:text-foreground transition-colors">Contact</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
