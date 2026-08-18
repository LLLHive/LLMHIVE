"use client"

import Link from "next/link"
import {
  Brain,
  Zap,
  Shield,
  Layers,
  ArrowRight,
  ChevronRight,
  MessageSquare,
  Code,
  FileSearch,
  Lightbulb,
  BarChart3,
  Award,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { LogoText } from "@/components/branding"
import ProductDemoPlayer from "@/components/marketing/product-demo-player"
import { MARKETING_FEATURED_LINE } from "@/lib/marketing/featured-models"
import { BENCHMARK_CLAIM_SHORT } from "@/lib/benchmark-claim"
import { DEMO_VIDEO } from "@/lib/marketing/demo-video"

const KEY_FEATURES = [
  {
    icon: Brain,
    title: "Multi-model orchestration",
    description: `Watch one question route across ${MARKETING_FEATURED_LINE}.`,
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
  },
  {
    icon: Zap,
    title: "Premium orchestration",
    description: "See how consensus, challenge-refine, and spend-aware routing produce a single best answer.",
    color: "text-yellow-400",
    bgColor: "bg-yellow-400/10",
  },
  {
    icon: Shield,
    title: "Built for real work",
    description: "Encryption in transit and at rest. Your data is not used to train our models.",
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
  },
  {
    icon: Layers,
    title: "Plans that stay simple",
    description: "Standard $10/month or Premium $20/month. Start Standard free for 7 days.",
    color: "text-green-400",
    bgColor: "bg-green-400/10",
  },
]

const USE_CASES = [
  { icon: Code, title: "Code Generation", description: "Complex multi-file code with best practices" },
  { icon: FileSearch, title: "Research Analysis", description: "Deep analysis with source citations" },
  { icon: MessageSquare, title: "Content Creation", description: "Marketing copy, blog posts, documentation" },
  { icon: BarChart3, title: "Data Analysis", description: "Insights from structured and unstructured data" },
]

export default function DemoClient() {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <header className="sticky top-0 z-40 border-b border-[#262626] bg-[#0a0a0a]/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2" aria-label="LLMHive home">
            <LogoText className="h-8" />
          </Link>
          <div className="flex items-center gap-4">
            <Button asChild variant="ghost" size="sm">
              <Link href="/pricing">Pricing</Link>
            </Button>
            <Button asChild size="sm" className="bronze-gradient text-[#0a0a0a]">
              <Link href="/landing/grandmother-free">Start free trial</Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="border-b border-[#262626] py-16">
        <div className="container mx-auto px-4">
          <div className="mx-auto mb-10 max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#C48E48]/20 bg-[#C48E48]/10 px-4 py-2 text-sm text-[#C48E48]">
              Product demo · {DEMO_VIDEO.duration}s
            </div>
            <h1 className="mb-4 text-4xl font-bold text-foreground md:text-5xl">See LLMHive in action</h1>
            <p className="text-xl text-muted-foreground">
              One question. Frontier models. One best answer. Watch the 60-second walkthrough, then start a 7-day
              Standard trial — no card required.
            </p>
          </div>

          <div className="mx-auto max-w-5xl">
            <ProductDemoPlayer />
            <p className="mt-4 text-center text-sm text-zinc-500">
              Use this film in ads and sales decks.{" "}
              <a
                href={DEMO_VIDEO.src}
                download="llmhive-product-demo.mp4"
                className="text-amber-400 hover:underline"
              >
                Download MP4
              </a>
              {" · "}
              <a href={DEMO_VIDEO.poster} download="llmhive-product-demo.jpg" className="text-amber-400 hover:underline">
                Poster
              </a>
            </p>
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold text-foreground">What you will see</h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              The same story we use in ads and sales conversations: why stacked subscriptions fail, how the hive
              routes, and how to start.
            </p>
          </div>
          <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-2">
            {KEY_FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="flex gap-4 rounded-xl border border-[#262626] bg-[#171717] p-6 transition-colors hover:border-[#333]"
              >
                <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl ${feature.bgColor}`}>
                  <feature.icon className={`h-6 w-6 ${feature.color}`} />
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-foreground">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-[#262626] bg-[#0d0d0d] py-20">
        <div className="container mx-auto px-4">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold text-foreground">Real-world use cases</h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              The same orchestration stack for code, research, content, and analysis.
            </p>
          </div>
          <div className="mx-auto grid max-w-5xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {USE_CASES.map((useCase) => (
              <div
                key={useCase.title}
                className="group rounded-xl border border-[#262626] bg-[#171717] p-5 text-center transition-colors hover:border-[#C48E48]/30"
              >
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#C48E48]/10 group-hover:bg-[#C48E48]/20">
                  <useCase.icon className="h-6 w-6 text-[#C48E48]" />
                </div>
                <h3 className="mb-1 font-semibold text-foreground">{useCase.title}</h3>
                <p className="text-xs text-muted-foreground">{useCase.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-[#262626] py-20">
        <div className="container mx-auto px-4">
          <div className="mx-auto grid max-w-3xl gap-8 text-center sm:grid-cols-3">
            <div>
              <div className="mb-2 flex items-center justify-center gap-2">
                <Award className="h-6 w-6 text-[#C48E48]" />
                <span className="text-4xl font-bold text-foreground">#1</span>
              </div>
              <p className="text-muted-foreground">{BENCHMARK_CLAIM_SHORT.replace("#1 ", "")}</p>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-center gap-2">
                <Zap className="h-6 w-6 text-[#C48E48]" />
                <span className="text-4xl font-bold text-foreground">350+</span>
              </div>
              <p className="text-muted-foreground">Models available to route</p>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-center gap-2">
                <Lightbulb className="h-6 w-6 text-[#C48E48]" />
                <span className="text-4xl font-bold text-foreground">$20</span>
              </div>
              <p className="text-muted-foreground">Premium / month — or Standard at $10</p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-[#262626] py-20">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="mb-4 text-3xl font-bold text-foreground">Ready to try it?</h2>
            <p className="mb-8 text-muted-foreground">
              Start Standard free for 7 days with no card, or go Premium at $20/month.
            </p>
            <div className="flex flex-col justify-center gap-4 sm:flex-row">
              <Button asChild size="lg" className="bronze-gradient w-full font-semibold text-[#0a0a0a] sm:w-auto">
                <Link href="/landing/grandmother-free">
                  Start 7-day trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="w-full sm:w-auto">
                <Link href="/pricing">
                  View pricing
                  <ChevronRight className="ml-1 h-5 w-5" />
                </Link>
              </Button>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              ✓ No card for the Standard trial · ✓ Premium from $20/mo · ✓ Cancel anytime
            </p>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#262626] py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <LogoText className="h-5 opacity-50" />
              <span>© {new Date().getFullYear()} LLMHive</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="/privacy" className="transition-colors hover:text-foreground">
                Privacy
              </Link>
              <Link href="/terms" className="transition-colors hover:text-foreground">
                Terms
              </Link>
              <Link href="/contact" className="transition-colors hover:text-foreground">
                Contact
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
