import Image from "next/image"
import Link from "next/link"
import type { Metadata } from "next"
import { auth } from "@clerk/nextjs/server"
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Brain,
  Check,
  Clock,
  Cpu,
  Layers,
  Lock,
  LogIn,
  MessageSquare,
  Network,
  Quote,
  Shield,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { getPaidEntitlementFast } from "@/lib/billing/entitlement"
import {
  OFFER_ENTERPRISE_FEATURES,
  OFFER_PREMIUM_FEATURES,
  OFFER_STANDARD_FEATURES,
} from "@/lib/marketing/pricing-offers"

export const metadata: Metadata = {
  title: "LLMHive — One AI Hive. Every Model. Always the Best Answer.",
  description:
    "LLMHive routes every request to the best AI model — GPT-5, Claude, Gemini, Grok, Llama, DeepSeek and 350+ more — for accuracy, speed and cost. Built for teams and enterprises.",
  alternates: { canonical: "https://llmhive.ai/" },
  openGraph: {
    title: "LLMHive — One AI Hive. Every Model. Always the Best Answer.",
    description:
      "Stop choosing AI models. LLMHive routes each request to the optimal one — automatically. 350+ models, enterprise security, transparent pricing.",
    type: "website",
    images: [{ url: "/logo.png" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive — One AI Hive. Every Model. Always the Best Answer.",
    description:
      "Stop choosing AI models. LLMHive routes each request to the optimal one — automatically.",
  },
}

// ---------------------------------------------------------------------------
// Content (kept top-level so the JSX below stays declarative & scannable).
// ---------------------------------------------------------------------------

const PROVIDER_LOGOS: ReadonlyArray<{ name: string; src: string }> = [
  { name: "OpenAI", src: "/logos/openai.svg" },
  { name: "Anthropic", src: "/logos/anthropic.png" },
  { name: "Google", src: "/logos/google.svg" },
  { name: "Meta", src: "/logos/meta.svg" },
  { name: "Mistral", src: "/logos/mistral.png" },
  { name: "xAI", src: "/logos/xai.png" },
  { name: "DeepSeek", src: "/logos/deepseek.svg" },
  { name: "Perplexity", src: "/logos/perplexity.svg" },
  { name: "NVIDIA", src: "/logos/nvidia.svg" },
  { name: "Cohere", src: "/logos/cohere.png" },
]

const HEADLINE_STATS = [
  { value: "350+", label: "Models routed" },
  { value: "99.9%", label: "Uptime SLA" },
  { value: "60%", label: "Avg AI cost saved" },
  { value: "150ms", label: "Median routing latency" },
]

const FEATURES = [
  {
    icon: Network,
    title: "Multi-model routing in one call",
    body: "GPT-5, Claude Opus 4.7, Gemini 3.1, Grok 4.2, Llama 4, DeepSeek V3.2 and 350+ more — accessed through one interface and one bill.",
  },
  {
    icon: Brain,
    title: "HRM intelligent selection",
    body: "Our Hive Routing Model classifies each request by task type, complexity and budget, then picks the model that delivers the best answer — not just the cheapest or the loudest.",
  },
  {
    icon: Layers,
    title: "Consensus & DeepConf strategies",
    body: "For high-stakes prompts, LLMHive runs parallel models, scores agreement, and returns the most confident answer with full attribution.",
  },
  {
    icon: BarChart3,
    title: "Spend guard, not surprise bills",
    body: "Real-time per-user budget enforcement at the orchestrator level. The guard caps spend before you exceed it, transparently — never silently.",
  },
  {
    icon: Shield,
    title: "Enterprise-grade security",
    body: "End-to-end encryption, scoped access, and clean separation of customer data. Your prompts never train anyone's model.",
  },
  {
    icon: Workflow,
    title: "Knowledge base + tools",
    body: "Retrieval-augmented chat with calculator, hosted reranker, and 90-day conversation memory on Standard and Premium.",
  },
] as const

const TIERS = [
  {
    name: "Standard",
    price: "$10",
    period: "/month",
    description: "Spend-guarded elite orchestration for individuals.",
    features: [...OFFER_STANDARD_FEATURES],
    cta: "Start with Standard",
    href: "/pricing",
    highlighted: false,
    accent: "bronze" as const,
  },
  {
    name: "Premium",
    price: "$20",
    period: "/month",
    description: "Benchmark-leading routing for power users.",
    features: [...OFFER_PREMIUM_FEATURES],
    cta: "Get Premium",
    href: "/pricing",
    highlighted: true,
    accent: "amber" as const,
  },
  {
    name: "Enterprise",
    price: "$35",
    period: "/seat/mo",
    description: "Compliance, SSO, and shared workspaces for teams.",
    features: [...OFFER_ENTERPRISE_FEATURES],
    cta: "Talk to sales",
    href: "/contact",
    highlighted: false,
    accent: "emerald" as const,
  },
] as const

const FAQ = [
  {
    q: "What does LLMHive actually do?",
    a: "LLMHive is a multi-model AI orchestration platform. You ask one question; LLMHive analyses it, picks the optimal model from a pool of 350+, and returns the best answer. You get one chat, one API, and one bill instead of juggling subscriptions.",
  },
  {
    q: "How is this different from using ChatGPT or Claude directly?",
    a: "Single-model tools commit you to one company's strengths and weaknesses. LLMHive lets the right model handle each task — GPT-5 for reasoning, Claude for writing, Gemini for long context, DeepSeek for cheap throughput — so quality goes up and cost goes down without you thinking about it.",
  },
  {
    q: "Can I trust the orchestrator to pick the right model?",
    a: "Yes. The HRM router is benchmarked continuously and every response shows the model used and the routing rationale. For high-stakes prompts, our consensus and DeepConf strategies run multiple models in parallel and return the most confident answer.",
  },
  {
    q: "How does pricing work? Will I get a surprise bill?",
    a: "No. Every plan includes a real-time spend guard enforced at the orchestrator. Once your budget is consumed for the period, traffic transparently routes to free-tier models — the bill never moves on you.",
  },
  {
    q: "Is LLMHive secure for business use?",
    a: "LLMHive uses end-to-end encryption, scoped data access, and provider-agnostic prompts — your data never trains the underlying models. Enterprise plans add SSO/SAML, audit logs, and 1-year retention controls.",
  },
  {
    q: "How quickly can I get started?",
    a: "Sign up, choose a plan, and you're in. Most users run their first multi-model query inside 60 seconds. No infrastructure to provision, no API keys to wire up.",
  },
]

const TESTIMONIAL = {
  quote:
    "LLMHive replaced four AI subscriptions and our internal router. Quality on every prompt went up, and our monthly AI spend dropped almost in half — without us changing a single workflow.",
  author: "Engineering Lead",
  role: "Mid-market SaaS company",
}

// ---------------------------------------------------------------------------
// Structured data for SEO (Organization + SoftwareApplication + FAQ).
// ---------------------------------------------------------------------------

function StructuredData() {
  const data = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        name: "LLMHive",
        url: "https://llmhive.ai",
        logo: "https://llmhive.ai/logo.png",
      },
      {
        "@type": "SoftwareApplication",
        name: "LLMHive",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        description:
          "Multi-model AI orchestration platform. One interface routes every request to the best of 350+ AI models for accuracy, speed and cost.",
        offers: {
          "@type": "Offer",
          priceCurrency: "USD",
          price: "10",
          category: "Standard",
          url: "https://llmhive.ai/pricing",
        },
        featureList: FEATURES.map((f) => f.title),
      },
      {
        "@type": "FAQPage",
        mainEntity: FAQ.map((item) => ({
          "@type": "Question",
          name: item.q,
          acceptedAnswer: { "@type": "Answer", text: item.a },
        })),
      },
    ],
  }
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function Home() {
  const { userId } = await auth()
  const isSignedIn = Boolean(userId)

  // For signed-in users we look up paid status so the primary CTA never
  // points them at a route that will bounce them right back here. Without
  // this, a signed-in unpaid user clicks "Open app" -> /app gate -> /pricing,
  // returns to /, sees "Open app" again, and ends up in a loop. The fast
  // variant has a short timeout and fails open ("no paid access"), so an
  // unreachable backend never blocks the marketing page from rendering.
  let hasPaidAccess = false
  if (isSignedIn && userId) {
    const entitlement = await getPaidEntitlementFast(userId)
    hasPaidAccess = entitlement.hasPaidAccess
  }

  const primary: { href: string; label: string } = !isSignedIn
    ? { href: "/sign-up", label: "Get started free" }
    : hasPaidAccess
      ? { href: "/app", label: "Open the app" }
      : { href: "/pricing", label: "Choose your plan" }

  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-zinc-100">
      <StructuredData />

      {/* Animated brand glow background */}
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[680px]">
        <div className="absolute left-1/2 top-[-200px] h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-amber-500/20 blur-[160px]" />
        <div className="absolute right-[-200px] top-[100px] h-[500px] w-[500px] rounded-full bg-orange-600/15 blur-[140px]" />
        <div className="absolute left-[-200px] top-[200px] h-[500px] w-[500px] rounded-full bg-amber-700/10 blur-[140px]" />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Nav                                                                 */}
      {/* ------------------------------------------------------------------ */}
      <nav className="fixed inset-x-0 top-0 z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <Image
              src="/logo.png"
              alt="LLMHive"
              width={32}
              height={32}
              priority
              className="h-8 w-8"
            />
            <Image
              src="/brand/llmhive-wordmark-nav.png"
              alt="LLMHive"
              width={140}
              height={30}
              priority
              className="hidden h-6 w-auto sm:block"
            />
          </Link>
          <div className="hidden items-center gap-7 md:flex">
            <Link href="#features" className="text-sm text-zinc-400 transition-colors hover:text-white">
              Features
            </Link>
            <Link href="#how-it-works" className="text-sm text-zinc-400 transition-colors hover:text-white">
              How it works
            </Link>
            <Link href="#pricing" className="text-sm text-zinc-400 transition-colors hover:text-white">
              Pricing
            </Link>
            <Link href="/about" className="text-sm text-zinc-400 transition-colors hover:text-white">
              About
            </Link>
            <Link href="/contact" className="text-sm text-zinc-400 transition-colors hover:text-white">
              Contact
            </Link>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            {!isSignedIn ? (
              <>
                <Link href="/sign-in">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-amber-500/40 bg-transparent font-semibold text-amber-300 hover:border-amber-500/70 hover:bg-amber-500/10 hover:text-amber-200"
                  >
                    <LogIn className="mr-1.5 h-4 w-4" />
                    Sign in
                  </Button>
                </Link>
                <Link href="/sign-up">
                  <Button
                    size="sm"
                    className="border-0 bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700"
                  >
                    Get started
                  </Button>
                </Link>
              </>
            ) : (
              <Link href={primary.href}>
                <Button
                  size="sm"
                  className="border-0 bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700"
                >
                  {primary.label}
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      </nav>

      {/* ------------------------------------------------------------------ */}
      {/* Hero                                                                */}
      {/* ------------------------------------------------------------------ */}
      <section className="relative px-4 pb-16 pt-28 sm:px-6 sm:pt-32 lg:px-8 lg:pt-36">
        <div className="mx-auto max-w-6xl">
          <div className="mx-auto max-w-4xl text-center">
            {/* Round mark + metallic wordmark — primary brand expression. */}
            <div className="flex flex-col items-center">
              <div className="relative">
                <div className="absolute inset-0 -z-10 scale-150 rounded-full bg-amber-500/20 blur-2xl" />
                <Image
                  src="/logo.png"
                  alt="LLMHive logo"
                  width={120}
                  height={120}
                  priority
                  className="h-24 w-24 drop-shadow-[0_0_30px_rgba(245,158,11,0.35)] sm:h-28 sm:w-28"
                />
              </div>
              <Image
                src="/brand/llmhive-wordmark-hero.png"
                alt="LLMHive"
                width={3000}
                height={700}
                priority
                className="mt-5 h-auto w-auto max-h-14 sm:max-h-20 md:max-h-24"
              />
            </div>

            <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-amber-500/25 bg-amber-500/10 px-3.5 py-1.5 text-xs font-medium text-amber-300 sm:text-sm">
              <Sparkles className="h-3.5 w-3.5" />
              <span>GPT-5, Claude Opus 4.7, Gemini 3.1, Grok 4.2 & 350+ more — one interface</span>
            </div>

            <h1 className="mt-6 text-balance text-4xl font-extrabold leading-[1.07] tracking-tight text-white sm:text-5xl md:text-6xl lg:text-7xl">
              Ask once.{" "}
              <span className="bg-gradient-to-r from-amber-400 via-orange-400 to-amber-300 bg-clip-text text-transparent">
                The best AI model
              </span>{" "}
              answers — every time.
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-zinc-400 sm:text-xl">
              LLMHive routes every request to the optimal model from a pool of 350+ — GPT-5, Claude, Gemini, Grok,
              Llama, DeepSeek and more — so you stop guessing, stop tab-hopping, and stop overpaying.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Link href={primary.href} className="w-full sm:w-auto">
                <Button
                  size="lg"
                  className="h-14 w-full border-0 bg-gradient-to-r from-amber-500 to-orange-600 px-8 text-base font-semibold text-white shadow-lg shadow-amber-500/20 hover:from-amber-600 hover:to-orange-700 sm:w-auto sm:text-lg"
                >
                  {primary.label}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/pricing" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="outline"
                  className="h-14 w-full border-zinc-700 bg-zinc-950/40 px-8 text-base text-white backdrop-blur hover:bg-zinc-900 sm:w-auto sm:text-lg"
                >
                  See pricing
                </Button>
              </Link>
            </div>

            {/* Secondary auth link directly under the primary CTA so users who
                already have an account never have to hunt for the login. */}
            {!isSignedIn && (
              <p className="mt-5 text-center text-sm text-zinc-400">
                Already have an account?{" "}
                <Link
                  href="/sign-in"
                  className="inline-flex items-center gap-1 font-semibold text-amber-400 underline-offset-4 hover:text-amber-300 hover:underline"
                >
                  <LogIn className="h-3.5 w-3.5" />
                  Sign in
                </Link>
              </p>
            )}

            <p className="mt-5 flex flex-wrap items-center justify-center gap-x-5 gap-y-1 text-xs text-zinc-500 sm:text-sm">
              <span className="flex items-center gap-1.5">
                <BadgeCheck className="h-4 w-4 text-emerald-400" />
                Cancel anytime
              </span>
              <span className="flex items-center gap-1.5">
                <Lock className="h-4 w-4 text-emerald-400" />
                Encrypted end-to-end
              </span>
              <span className="flex items-center gap-1.5">
                <Shield className="h-4 w-4 text-emerald-400" />
                Your data never trains models
              </span>
            </p>
          </div>

          {/* Provider strip — above-fold trust */}
          <div className="mt-16">
            <p className="text-center text-xs uppercase tracking-[0.18em] text-zinc-500">
              One subscription. Every leading model.
            </p>
            <div className="mt-6 grid grid-cols-3 items-center gap-x-8 gap-y-6 sm:grid-cols-5 md:flex md:flex-wrap md:justify-center md:gap-x-10 md:gap-y-6">
              {PROVIDER_LOGOS.map((logo) => (
                <div
                  key={logo.name}
                  className="flex h-8 items-center justify-center grayscale transition-all hover:grayscale-0 md:h-10"
                  title={logo.name}
                >
                  <Image
                    src={logo.src}
                    alt={logo.name}
                    width={120}
                    height={32}
                    className="max-h-7 w-auto object-contain opacity-70 hover:opacity-100 md:max-h-8"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div className="mt-20 grid grid-cols-2 gap-y-8 rounded-2xl border border-white/5 bg-white/[0.02] py-10 backdrop-blur md:grid-cols-4">
            {HEADLINE_STATS.map((s) => (
              <div key={s.label} className="px-6 text-center">
                <div className="bg-gradient-to-r from-amber-300 to-orange-400 bg-clip-text text-3xl font-bold text-transparent sm:text-4xl">
                  {s.value}
                </div>
                <div className="mt-1.5 text-xs uppercase tracking-wide text-zinc-500 sm:text-sm sm:normal-case sm:tracking-normal">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Problem → Solution                                                  */}
      {/* ------------------------------------------------------------------ */}
      <section className="px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-12 md:grid-cols-2 md:items-center md:gap-16">
            <div>
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">
                The single-model trap
              </span>
              <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
                You're paying for{" "}
                <span className="text-zinc-500 line-through decoration-zinc-700">four AIs</span>
                <span className="block text-white sm:inline"> and still getting the wrong one.</span>
              </h2>
              <p className="mt-6 text-lg leading-relaxed text-zinc-400">
                Every model has a strength and a blind spot. Reasoning lives in one. Long context in another. Code in a
                third. Cheap throughput in a fourth. Without orchestration, you guess — or pay for all of them and pick
                manually.
              </p>
              <ul className="mt-6 space-y-3 text-base text-zinc-300">
                {[
                  "Route by task: reasoning, code, retrieval, summarisation, vision",
                  "Score answers across providers with the consensus and DeepConf strategies",
                  "Never overspend — the spend guard enforces budgets in real time",
                  "Get the model name and rationale on every response",
                ].map((line) => (
                  <li key={line} className="flex items-start gap-3">
                    <Check className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Visual: routing diagram */}
            <div className="relative">
              <div className="relative rounded-2xl border border-white/10 bg-gradient-to-br from-zinc-900/80 to-zinc-950/80 p-8 shadow-2xl backdrop-blur">
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                    <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                    <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-xs text-zinc-500">llmhive.ai</span>
                </div>

                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                  <div className="text-xs uppercase tracking-wider text-amber-300/70">Your prompt</div>
                  <div className="mt-1.5 text-sm text-white">
                    "Explain attention mechanisms and write a PyTorch implementation."
                  </div>
                </div>

                <div className="my-5 flex items-center justify-center">
                  <div className="rounded-full border border-amber-500/30 bg-gradient-to-r from-amber-500/15 to-orange-600/15 px-4 py-1.5 text-xs font-semibold text-amber-300">
                    HRM router · classified reasoning + code
                  </div>
                </div>

                <div className="space-y-2.5">
                  {[
                    { name: "Claude Opus 4.7", note: "Pedagogical clarity", pick: false },
                    { name: "GPT-5", note: "Best reasoning + code", pick: true },
                    { name: "Gemini 3.1", note: "Long-context fallback", pick: false },
                  ].map((m) => (
                    <div
                      key={m.name}
                      className={`flex items-center justify-between rounded-lg border px-3.5 py-2.5 text-sm ${
                        m.pick
                          ? "border-amber-500/40 bg-amber-500/10 text-white"
                          : "border-white/5 bg-white/[0.02] text-zinc-400"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Cpu className={`h-4 w-4 ${m.pick ? "text-amber-400" : "text-zinc-500"}`} />
                        <span className={m.pick ? "font-medium text-white" : ""}>{m.name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span>{m.note}</span>
                        {m.pick && (
                          <span className="rounded-full bg-amber-500/20 px-2 py-0.5 font-semibold text-amber-300">
                            chosen
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-emerald-300">
                  Routed in 142ms · saved $0.014 vs running all three
                </div>
              </div>
              <div className="absolute -inset-3 -z-10 rounded-3xl bg-gradient-to-br from-amber-500/20 via-transparent to-orange-600/20 blur-2xl" />
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Features                                                            */}
      {/* ------------------------------------------------------------------ */}
      <section id="features" className="border-t border-white/5 bg-zinc-950/40 px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-16 text-center">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">
              The platform
            </span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
              Built for serious AI work, not demos.
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-400">
              Everything you need to ship AI features safely — without committing to a single provider.
            </p>
          </div>

          <div className="grid gap-5 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = f.icon
              return (
                <div
                  key={f.title}
                  className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-6 transition-all hover:-translate-y-0.5 hover:border-amber-500/30 hover:bg-white/[0.04]"
                >
                  <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/10 ring-1 ring-amber-500/20 transition-colors group-hover:bg-amber-500/20">
                    <Icon className="h-5 w-5 text-amber-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-400">{f.body}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* How it works                                                        */}
      {/* ------------------------------------------------------------------ */}
      <section id="how-it-works" className="px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-16 text-center">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">
              How it works
            </span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
              Three steps. No knobs.
            </h2>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {[
              {
                step: "01",
                title: "Send your prompt",
                body: "Use the chat or the API. No model selection required.",
                icon: MessageSquare,
              },
              {
                step: "02",
                title: "HRM picks the model",
                body: "The router classifies the request and chooses the best of 350+ models for your task and budget.",
                icon: Network,
              },
              {
                step: "03",
                title: "Get the best answer",
                body: "Optional: run consensus across multiple providers. Always: full transparency on which model ran and why.",
                icon: Zap,
              },
            ].map((s, i) => {
              const Icon = s.icon
              return (
                <div key={s.step} className="relative">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-7">
                    <div className="flex items-baseline gap-3">
                      <div className="text-5xl font-bold text-zinc-800">{s.step}</div>
                      <Icon className="h-5 w-5 text-amber-400" />
                    </div>
                    <h3 className="mt-4 text-xl font-semibold text-white">{s.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-zinc-400">{s.body}</p>
                  </div>
                  {i < 2 && (
                    <div className="absolute right-[-22px] top-1/2 hidden h-px w-8 -translate-y-1/2 bg-gradient-to-r from-amber-500/40 to-transparent md:block" />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Distributed social proof                                            */}
      {/* ------------------------------------------------------------------ */}
      <section className="px-4 pb-12 pt-2 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-zinc-900/80 to-zinc-950/80 p-8 sm:p-12">
            <Quote className="absolute right-8 top-8 h-12 w-12 text-amber-500/10" />
            <p className="text-xl leading-relaxed text-zinc-200 sm:text-2xl">
              &ldquo;{TESTIMONIAL.quote}&rdquo;
            </p>
            <div className="mt-6 flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-amber-500 to-orange-600" />
              <div>
                <div className="text-sm font-semibold text-white">{TESTIMONIAL.author}</div>
                <div className="text-xs text-zinc-500">{TESTIMONIAL.role}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Pricing teaser                                                      */}
      {/* ------------------------------------------------------------------ */}
      <section id="pricing" className="border-t border-white/5 bg-zinc-950/40 px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 text-center">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">
              Pricing
            </span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
              Transparent. Spend-guarded. No surprise bills.
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-400">
              Pick a plan, set a budget, and let LLMHive do the rest. Annual billing saves about 17%.
            </p>
          </div>

          <div className="mx-auto grid max-w-5xl gap-5 sm:gap-6 md:grid-cols-3">
            {TIERS.map((t) => (
              <div
                key={t.name}
                className={`relative flex flex-col rounded-2xl p-6 ${
                  t.highlighted
                    ? "border-2 border-amber-500/60 bg-gradient-to-b from-amber-500/12 to-orange-600/5 shadow-xl shadow-amber-500/10"
                    : t.accent === "bronze"
                      ? "border border-amber-700/40 bg-zinc-900/50"
                      : "border border-emerald-700/40 bg-zinc-900/50"
                }`}
              >
                {t.highlighted && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-amber-500 to-orange-600 px-3 py-1 text-xs font-semibold text-white">
                    Most popular
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white">{t.name}</h3>
                <div className="mt-2 flex items-baseline gap-1.5">
                  <span className="text-4xl font-bold text-white">{t.price}</span>
                  <span className="text-sm text-zinc-500">{t.period}</span>
                </div>
                <p className="mt-2 text-sm text-zinc-400">{t.description}</p>
                <ul className="mt-5 flex-1 space-y-2.5">
                  {t.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2 text-sm text-zinc-300">
                      <Check
                        className={`mt-0.5 h-4 w-4 flex-shrink-0 ${
                          t.highlighted
                            ? "text-amber-400"
                            : t.accent === "emerald"
                              ? "text-emerald-400"
                              : "text-amber-500"
                        }`}
                      />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
                <Link href={t.href} className="mt-6 block">
                  <Button
                    className={`w-full ${
                      t.highlighted
                        ? "border-0 bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700"
                        : t.accent === "emerald"
                          ? "bg-emerald-700 text-white hover:bg-emerald-600"
                          : "bg-zinc-800 text-white hover:bg-zinc-700"
                    }`}
                  >
                    {t.cta}
                  </Button>
                </Link>
              </div>
            ))}
          </div>

          <p className="mt-8 text-center text-sm text-zinc-500">
            Need something custom? <Link href="/contact" className="text-amber-400 hover:text-amber-300">Talk to us</Link>.
          </p>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Trust badges                                                        */}
      {/* ------------------------------------------------------------------ */}
      <section className="px-4 py-14 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-x-12 gap-y-4 text-zinc-400">
          <div className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            <span className="text-sm">SOC 2 controls</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <span className="text-sm">GDPR / CCPA aware</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            <span className="text-sm">99.9% uptime SLA</span>
          </div>
          <div className="flex items-center gap-2">
            <BadgeCheck className="h-5 w-5" />
            <span className="text-sm">Stripe-secured billing</span>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* FAQ                                                                 */}
      {/* ------------------------------------------------------------------ */}
      <section className="border-t border-white/5 px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-12 text-center">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">
              Questions
            </span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
              Everything you'd ask in a sales call.
            </h2>
          </div>
          <div className="space-y-3">
            {FAQ.map((item) => (
              <details
                key={item.q}
                className="group rounded-2xl border border-white/10 bg-white/[0.02] open:border-amber-500/30"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-6 py-5">
                  <span className="text-base font-semibold text-white sm:text-lg">{item.q}</span>
                  <span className="ml-2 inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white/5 text-zinc-400 transition-transform group-open:rotate-45">
                    <span className="text-lg leading-none">+</span>
                  </span>
                </summary>
                <p className="px-6 pb-6 text-sm leading-relaxed text-zinc-400 sm:text-base">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Final CTA                                                           */}
      {/* ------------------------------------------------------------------ */}
      <section className="relative px-4 pb-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="relative overflow-hidden rounded-3xl border border-amber-500/20 bg-gradient-to-br from-amber-500/10 via-zinc-950 to-orange-600/10 p-10 text-center sm:p-16">
            <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,rgba(245,158,11,0.18),transparent_60%)]" />
            <h2 className="text-balance text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
              Stop choosing models. Start shipping answers.
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg text-zinc-300">
              Subscribe in under a minute. Cancel anytime. Your spend is guarded — your output isn't.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Link href={primary.href}>
                <Button
                  size="lg"
                  className="h-14 border-0 bg-gradient-to-r from-amber-500 to-orange-600 px-9 text-base font-semibold text-white shadow-lg shadow-amber-500/20 hover:from-amber-600 hover:to-orange-700 sm:text-lg"
                >
                  {primary.label}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/pricing">
                <Button
                  size="lg"
                  variant="outline"
                  className="h-14 border-zinc-700 bg-zinc-950/40 px-9 text-base text-white hover:bg-zinc-900 sm:text-lg"
                >
                  Compare plans
                </Button>
              </Link>
            </div>
            {!isSignedIn && (
              <p className="mt-6 text-center text-sm text-zinc-400">
                Already have an account?{" "}
                <Link
                  href="/sign-in"
                  className="font-semibold text-amber-400 underline-offset-4 hover:text-amber-300 hover:underline"
                >
                  Sign in
                </Link>
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Footer                                                              */}
      {/* ------------------------------------------------------------------ */}
      <footer className="border-t border-white/5 bg-black/40 px-4 py-14 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <div>
              <h4 className="text-sm font-semibold text-white">Product</h4>
              <ul className="mt-4 space-y-2 text-sm text-zinc-400">
                <li><Link href="#features" className="hover:text-white">Features</Link></li>
                <li><Link href="#pricing" className="hover:text-white">Pricing</Link></li>
                <li><Link href="/comparisons" className="hover:text-white">Comparisons</Link></li>
                <li><Link href="/case-studies" className="hover:text-white">Case studies</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">Company</h4>
              <ul className="mt-4 space-y-2 text-sm text-zinc-400">
                <li><Link href="/about" className="hover:text-white">About</Link></li>
                <li><Link href="/contact" className="hover:text-white">Contact</Link></li>
                <li><Link href="/demo" className="hover:text-white">Demo</Link></li>
                <li><Link href="/press" className="hover:text-white">Press</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">Legal</h4>
              <ul className="mt-4 space-y-2 text-sm text-zinc-400">
                <li><Link href="/privacy" className="hover:text-white">Privacy</Link></li>
                <li><Link href="/terms" className="hover:text-white">Terms</Link></li>
                <li><Link href="/cookies" className="hover:text-white">Cookies</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">Account</h4>
              <ul className="mt-4 space-y-2 text-sm text-zinc-400">
                {isSignedIn ? (
                  <li>
                    <Link href={primary.href} className="hover:text-white">
                      {primary.label}
                    </Link>
                  </li>
                ) : (
                  <>
                    <li><Link href="/sign-in" className="hover:text-white">Sign in</Link></li>
                    <li><Link href="/sign-up" className="hover:text-white">Create account</Link></li>
                  </>
                )}
                <li><Link href="/help" className="hover:text-white">Help center</Link></li>
                <li><Link href="/faq" className="hover:text-white">FAQ</Link></li>
                <li>
                  <a href="mailto:info@llmhive.ai" className="hover:text-white">
                    info@llmhive.ai
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/5 pt-8 sm:flex-row">
            <Link href="/" className="flex items-center gap-2.5">
              <Image src="/logo.png" alt="LLMHive" width={28} height={28} className="h-7 w-7" />
              <span className="text-sm font-semibold text-white">LLMHive</span>
            </Link>
            <p className="text-xs text-zinc-500">© 2026 LLMHive. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
