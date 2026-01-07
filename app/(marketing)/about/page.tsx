"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { 
  ArrowLeft, 
  Sparkles,
  Target,
  Heart,
  Lightbulb,
  Users,
  Zap,
  Shield
} from "lucide-react"

const values = [
  {
    icon: Target,
    title: "Mission First",
    description: "We're on a mission to democratize access to the world's best AI models. Everyone deserves powerful AI tools."
  },
  {
    icon: Heart,
    title: "User-Centric",
    description: "Every feature we build starts with a real user need. We listen, iterate, and deliver solutions that matter."
  },
  {
    icon: Lightbulb,
    title: "Innovation",
    description: "We push the boundaries of what's possible with AI orchestration, constantly exploring new approaches."
  },
  {
    icon: Shield,
    title: "Trust & Security",
    description: "Your data is sacred. We implement the highest security standards and never compromise on privacy."
  }
]

const team = [
  {
    name: "Founding Team",
    role: "Building the Future",
    bio: "A passionate team of AI researchers, engineers, and designers dedicated to making AI accessible to everyone."
  }
]

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--bronze)]/10 border border-[var(--bronze)]/20 text-[var(--bronze)] text-sm mb-8">
            <Sparkles className="h-4 w-4" />
            <span>Our Story</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            Building the Future of AI
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            LLMHive was born from a simple frustration: why should anyone have to choose 
            between AI models when they can have the best of all worlds?
          </p>
        </div>
      </section>

      {/* Story */}
      <section className="py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="prose prose-invert max-w-none">
            <h2 className="text-2xl font-semibold mb-6">The Problem We Solve</h2>
            <p className="text-muted-foreground leading-relaxed mb-6">
              The AI landscape is fragmented. GPT-4 excels at creative writing, Claude shines in 
              analysis, Gemini dominates in multimodal tasks, and DeepSeek offers incredible value. 
              But switching between these tools is tedious, expensive, and time-consuming.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-6">
              We built LLMHive to solve this problem. Our intelligent orchestration layer 
              automatically routes your queries to the best AI model for each specific task. 
              You get optimal results without the cognitive overhead of model selection.
            </p>
            <h2 className="text-2xl font-semibold mb-6 mt-12">Our Approach</h2>
            <p className="text-muted-foreground leading-relaxed mb-6">
              LLMHive uses advanced techniques like Hierarchical Routing Matrices (HRM), 
              Prompt Diffusion, and Deep Confidence scoring to analyze your queries and match 
              them with the ideal AI model. The result? Better answers, faster responses, and 
              lower costs.
            </p>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-16 px-4 bg-card/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Our Values</h2>
          <div className="grid sm:grid-cols-2 gap-8">
            {values.map((value) => (
              <div key={value.title} className="flex gap-4">
                <div className="w-12 h-12 rounded-xl bg-[var(--bronze)]/10 flex items-center justify-center flex-shrink-0">
                  <value.icon className="h-6 w-6 text-[var(--bronze)]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-1">{value.title}</h3>
                  <p className="text-sm text-muted-foreground">{value.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-[var(--bronze)] mb-2">100+</div>
              <div className="text-sm text-muted-foreground">AI Models</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-[var(--bronze)] mb-2">10M+</div>
              <div className="text-sm text-muted-foreground">Queries Processed</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-[var(--bronze)] mb-2">99.9%</div>
              <div className="text-sm text-muted-foreground">Uptime</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-[var(--bronze)] mb-2">60%</div>
              <div className="text-sm text-muted-foreground">Cost Savings</div>
            </div>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="py-16 px-4 bg-card/30">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">The Team</h2>
          <p className="text-muted-foreground mb-12 max-w-2xl mx-auto">
            We&apos;re a diverse team of engineers, researchers, and designers united by 
            our passion for making AI accessible and powerful.
          </p>
          <div className="inline-flex items-center gap-4 p-6 rounded-2xl bg-card border border-border">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--bronze)] to-orange-600 flex items-center justify-center">
              <Users className="h-8 w-8 text-white" />
            </div>
            <div className="text-left">
              <h3 className="font-semibold">Growing Team</h3>
              <p className="text-sm text-muted-foreground">
                We&apos;re always looking for talented people to join us.
              </p>
              <Link href="/contact" className="text-sm text-[var(--bronze)] hover:underline">
                Get in touch →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-muted-foreground mb-8">
            Join thousands of users who are already supercharging their AI workflow.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/sign-up">
              <Button size="lg" className="bg-[var(--bronze)] hover:bg-[var(--bronze)]/90 text-white">
                <Zap className="h-5 w-5 mr-2" />
                Start for Free
              </Button>
            </Link>
            <Link href="/contact">
              <Button size="lg" variant="outline">
                Contact Us
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

