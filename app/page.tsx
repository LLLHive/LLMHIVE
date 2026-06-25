import Image from "next/image"
import Link from "next/link"
import { redirect } from "next/navigation"
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
import { MarketingNav } from "@/components/marketing/MarketingNav"
import LogoText from "@/components/branding/LogoText"
import { getPaidEntitlementFast } from "@/lib/billing/entitlement"
import { BENCHMARK_CLAIM_PILL_TEXT } from "@/lib/benchmark-claim"
import {
  OFFER_ENTERPRISE_FEATURES,
  OFFER_PREMIUM_FEATURES,
  OFFER_STANDARD_FEATURES,
} from "@/lib/marketing/pricing-offers"
import {
  buildProductStructuredData,
  organizationNode,
  PRODUCT_IMAGE_URL,
} from "@/lib/marketing/structured-data"
import { sitePath } from "@/lib/site-url"
import {
  MARKETING_FEATURED_LINE,
  MARKETING_META_DESCRIPTION_MODELS,
  MARKETING_OPENAI_FLAGSHIP,
} from "@/lib/marketing/featured-models"

export const metadata: Metadata = {
  title: "LLMHive — One AI Hive. Every Model. Always the Best Answer.",
  description:
    `LLMHive routes every request to the best AI model — ${MARKETING_META_DESCRIPTION_MODELS} — for accuracy, speed and cost. Built for teams and enterprises.`,
  alternates: { canonical: sitePath('/') },
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
    body: `${MARKETING_FEATURED_LINE} — accessed through one interface and one bill.`,
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
    a: `Single-model tools commit you to one company's strengths and weaknesses. LLMHive lets the right model handle each task — ${MARKETING_OPENAI_FLAGSHIP} for reasoning, Claude Sonnet 4.6 for writing, Gemini 3.1 Pro for long context, DeepSeek V3.2 for cheap throughput — so quality goes up and cost goes down without you thinking about it.`,
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
      organizationNode(),
      buildProductStructuredData({
        description:
          "Multi-model AI orchestration platform. One interface routes every request to the best of 350+ AI models for accuracy, speed and cost.",
        offers: [
          { name: "Standard", price: "10", url: sitePath('/pricing#lite') },
          { name: "Premium", price: "20", url: sitePath('/pricing#pro') },
        ],
      }),
      {
        "@type": "SoftwareApplication",
        name: "LLMHive",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        image: PRODUCT_IMAGE_URL,
        description:
          "Multi-model AI orchestration platform. One interface routes every request to the best of 350+ AI models for accuracy, speed and cost.",
        offers: {
          "@type": "Offer",
          priceCurrency: "USD",
          price: "10",
          category: "Standard",
          url: sitePath('/pricing'),
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

  // Signed-in: paid or provisioned free tier -> app; otherwise pricing CTA.
  let hasAppAccess = false
  if (isSignedIn && userId) {
    const entitlement = await getPaidEntitlementFast(userId)
    hasAppAccess = entitlement.hasAppAccess
  }

  // Auto-route signed-in users with app access (paid or free orchestration) into /app.
  if (isSignedIn && hasAppAccess) {
    redirect("/app")
  }

  const primary: { href: string; label: string } = !isSignedIn
    ? { href: "/sign-up", label: "Get started free" }
    : hasAppAccess
      ? { href: "/app", label: "Open the app" }
      : { href: "/pricing", label: "Choose your plan" }

  return (
    // Transparent root: the global <AppBackground /> rendered by
    // app/layout.tsx paints the redwoods + warm light scene used across
    // /app and /pricing. We were wrapping the whole landing in `bg-black`,
    // which painted over that scene — that's why /  looked nothing like
    // the rest of the build. Removing the solid fill lets the same
    // forest backdrop come through here too.
    <div className="relative min-h-screen overflow-hidden text-zinc-100">
      <StructuredData />

      {/* Shared site-wide nav: Signup/Signin top-right until logged in. */}
      <MarketingNav />

      {/* ------------------------------------------------------------------ */}
      {/* Hero — mirrors the /app home composition (round honeycomb sphere   */}
      {/* + metallic LLMHive wordmark + aluminum subtitle + #1 benchmark     */}
      {/* pill) so visitors see the same brand the moment they land,        */}
      {/* whether on /, /pricing, or /app.                                   */}
      {/* ------------------------------------------------------------------ */}
      <section className="relative px-4 pb-16 pt-24 sm:px-6 sm:pt-28 lg:px-8 lg:pt-32">
        <div className="mx-auto max-w-6xl">
          <div className="mx-auto max-w-4xl text-center">
            {/* Hero composition copied 1:1 from components/home-screen.tsx
                (the /app home screen) so the round sphere, the metallic
                LLMHive wordmark, the aluminum subtitle and the #1
                benchmark pill render at IDENTICAL sizes, spacing and
                negative-margin overlap on / as they do on /app. The
                only thing the landing wraps around it is the marketing
                section padding above (so the fixed MarketingNav does
                not occlude the sphere). Do not adjust these sizes here
                without also updating home-screen.tsx — they are kept
                in lockstep on purpose. */}
            <div className="llmhive-fade-in flex min-h-0 shrink-0 flex-col items-center text-center [@media(max-height:720px)]:scale-[0.97] [@media(max-height:640px)]:scale-[0.94]">
              <div className="relative mx-auto h-[min(66.3vh,24.25rem)] w-[min(66.3vh,24.25rem)] sm:h-[min(61.2vh,26.75rem)] sm:w-[min(61.2vh,26.75rem)] md:h-[min(56.1vh,29.25rem)] md:w-[min(56.1vh,29.25rem)] lg:h-[min(51vh,31.875rem)] lg:w-[min(51vh,31.875rem)] -mb-[5.5rem] sm:-mb-[6rem] md:-mb-[6.5rem] lg:-mb-[6.75rem] llmhive-float">
                <Image
                  src="/logo.png"
                  alt="LLMHive"
                  fill
                  className="object-contain drop-shadow-2xl"
                  priority
                />
              </div>

              <LogoText height={66} className="relative z-10 -mt-1 mx-auto mb-0 md:hidden" />
              <LogoText height={84} className="relative z-10 -mt-1.5 mx-auto mb-0 hidden md:block lg:hidden" />
              <LogoText height={102} className="relative z-10 -mt-2 mx-auto mb-0 hidden lg:block" />

              <p className="llmhive-subtitle-3d mx-auto mb-0 w-full max-w-[min(100%,calc(100vw-1.5rem))] whitespace-nowrap overflow-x-auto overflow-y-hidden px-2 text-center text-[clamp(0.65rem,2vw,0.9375rem)] leading-normal [-ms-overflow-style:none] [scrollbar-width:none] sm:text-sm md:text-base [&::-webkit-scrollbar]:hidden">
                Patent Pending multi-agent orchestration for enhanced accuracy and performance.
              </p>

              <div className="my-3 mx-auto inline-flex w-fit max-w-[calc(100vw-2rem)] items-center justify-center gap-1.5 rounded-full border-2 border-yellow-500/40 bg-gradient-to-r from-yellow-500/15 via-amber-500/15 to-[var(--bronze)]/15 px-2 py-[0.2rem] shadow-lg shadow-yellow-500/10 sm:gap-2 sm:px-2.5 sm:py-1 md:gap-2.5 md:px-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-yellow-400 via-amber-500 to-[var(--bronze)] shadow-lg sm:h-10 sm:w-10 md:h-11 md:w-11">
                  <span className="text-sm font-bold text-white sm:text-base md:text-lg">#1</span>
                </div>
                <p className="shrink-0 whitespace-nowrap bg-gradient-to-r from-yellow-300 to-amber-400 bg-clip-text text-left text-[19.8px] font-semibold leading-[1.1] text-transparent sm:text-[23.4px] md:text-[25.2px] lg:text-[27px]">
                  {BENCHMARK_CLAIM_PILL_TEXT}
                </p>
              </div>
            </div>

            <div className="mt-4 inline-flex max-w-full items-center gap-2 rounded-full border border-amber-500/25 bg-amber-500/10 px-3.5 py-1.5 text-xs font-medium text-amber-300 backdrop-blur-sm sm:text-sm">
              <Sparkles className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="truncate">
                {MARKETING_FEATURED_LINE}
              </span>
            </div>

            <h1 className="mt-6 text-balance text-4xl font-extrabold leading-[1.07] tracking-tight text-white drop-shadow-[0_4px_30px_rgba(0,0,0,0.7)] sm:text-5xl md:text-6xl lg:text-7xl">
              Ask once.{" "}
              <span className="bg-gradient-to-r from-amber-400 via-orange-400 to-amber-300 bg-clip-text text-transparent">
                The best AI model
              </span>{" "}
              answers — every time.
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-zinc-100/90 drop-shadow-[0_2px_18px_rgba(0,0,0,0.7)] sm:text-xl">
              LLMHive routes every request to the optimal model — {MARKETING_FEATURED_LINE} — so you stop guessing, stop tab-hopping, and stop overpaying.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Button
                asChild
                size="lg"
                className="h-14 w-full border-0 bg-gradient-to-r from-amber-500 to-orange-600 px-8 text-base font-semibold text-white shadow-lg shadow-amber-500/20 hover:from-amber-600 hover:to-orange-700 sm:w-auto sm:text-lg"
              >
                <Link href={primary.href} className="w-full sm:w-auto">
                  {primary.label}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-14 w-full border-zinc-700 bg-zinc-950/40 px-8 text-base text-white backdrop-blur hover:bg-zinc-900 sm:w-auto sm:text-lg"
              >
                <Link href="/pricing" className="w-full sm:w-auto">
                  See pricing
                </Link>
              </Button>
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

          {/* Provider strip — above-fold trust.
              Each logo sits on a subtle white-tinted card so it's always
              legible regardless of native colour (most provider marks are
              dark, which becomes invisible on a black page). Pattern used
              by Stripe / Linear / Vercel landing pages. */}
          <div className="mt-16">
            <p className="text-center text-xs uppercase tracking-[0.2em] text-zinc-500">
              One subscription. Every leading model.
            </p>
            <div className="mx-auto mt-7 grid max-w-5xl grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
              {PROVIDER_LOGOS.map((logo) => (
                <div
                  key={logo.name}
                  className="group flex h-16 items-center justify-center rounded-xl border border-white/10 bg-white/95 px-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-amber-500/40 hover:shadow-amber-500/10 sm:h-[68px]"
                  title={logo.name}
                >
                  <Image
                    src={logo.src}
                    alt={logo.name}
                    width={140}
                    height={36}
                    className="max-h-7 w-auto object-contain sm:max-h-8"
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
                You&apos;re paying for{" "}
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
                    &ldquo;Explain attention mechanisms and write a PyTorch implementation.&rdquo;
                  </div>
                </div>

                <div className="my-5 flex items-center justify-center">
                  <div className="rounded-full border border-amber-500/30 bg-gradient-to-r from-amber-500/15 to-orange-600/15 px-4 py-1.5 text-xs font-semibold text-amber-300">
                    HRM router · classified reasoning + code
                  </div>
                </div>

                <div className="space-y-2.5">
                  {[
                    { name: "Claude Sonnet 4.6", note: "Pedagogical clarity", pick: false },
                    { name: MARKETING_OPENAI_FLAGSHIP, note: "Best reasoning + code", pick: true },
                    { name: "Gemini 3.1 Pro", note: "Long-context fallback", pick: false },
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
                <Button
                  asChild
                  className={`mt-6 w-full ${
                    t.highlighted
                      ? "border-0 bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700"
                      : t.accent === "emerald"
                        ? "bg-emerald-700 text-white hover:bg-emerald-600"
                        : "bg-zinc-800 text-white hover:bg-zinc-700"
                  }`}
                >
                  <Link href={t.href}>{t.cta}</Link>
                </Button>
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
              Everything you&apos;d ask in a sales call.
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
              Subscribe in under a minute. Cancel anytime. Your spend is guarded — your output isn&apos;t.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Button
                asChild
                size="lg"
                className="h-14 border-0 bg-gradient-to-r from-amber-500 to-orange-600 px-9 text-base font-semibold text-white shadow-lg shadow-amber-500/20 hover:from-amber-600 hover:to-orange-700 sm:text-lg"
              >
                <Link href={primary.href}>
                  {primary.label}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-14 border-zinc-700 bg-zinc-950/40 px-9 text-base text-white hover:bg-zinc-900 sm:text-lg"
              >
                <Link href="/pricing">Compare plans</Link>
              </Button>
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
