"use client"

/**
 * Visual campaign clone of app/pricing/PricingClient.tsx.
 * Same tiers, Stripe create-checkout, Clerk signup → auto-checkout query params.
 * Do not edit app/pricing — this file is independent.
 */

import { useState, useEffect, useRef, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import { useUser, useClerk } from "@clerk/nextjs"
import {
  Check,
  Building2,
  ArrowRight,
  Loader2,
  Crown,
  Star,
  Sparkles,
  Trophy,
  BadgeCheck,
  Wallet,
  Lock,
  Clock,
  Play,
  Zap,
  Shield,
  Brain,
  Network,
  Target,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  MARKETING_FEATURED_LINE,
  MARKETING_FEATURED_ORCHESTRATION_STACK,
} from "@/lib/marketing/featured-models"
import {
  BENCHMARK_CLAIM_BANNER,
  BENCHMARK_CLAIM_PILL_TEXT,
  BENCHMARK_CLAIM_SHORT,
} from "@/lib/benchmark-claim"
import {
  OFFER_ENTERPRISE_FEATURES,
  OFFER_PREMIUM_FEATURES,
  OFFER_STANDARD_FEATURES,
} from "@/lib/marketing/pricing-offers"
import { ENTERPRISE_SINGLE_FLAGSHIP_PICK_LABEL } from "@/lib/billing/enterprise-features"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { track } from "@/lib/observability/analytics"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"
import { buildProductStructuredData, organizationNode } from "@/lib/marketing/structured-data"
import { sitePath } from "@/lib/site-url"
import { isProductionClerkKeyOnLocalDev } from "@/lib/clerk-local-dev"

const SIGNUP_TRACKED_STORAGE_KEY = "llmhive_signup_tracked_v1"
const FRESH_SIGNUP_WINDOW_MS = 5 * 60 * 1000
/** Post-auth return path for this campaign (mirrors /pricing?subscribe=…). */
const CAMPAIGN_PATH = "/landing/spain"

const copyMuted = "text-zinc-300"
const copySubtle = "text-zinc-400"
const panelClass =
  "rounded-2xl border border-white/10 bg-zinc-950/80 backdrop-blur-md shadow-xl shadow-black/30"
const tierCardClass =
  "group relative flex flex-col rounded-2xl border bg-zinc-950/90 backdrop-blur-md shadow-lg shadow-black/30 transition-all duration-300 hover:-translate-y-1"

export type CheckoutTierKey = "lite" | "pro" | "enterprise"

interface PricingTier {
  name: string
  description: string
  monthlyPrice: number
  annualPrice: number
  features: string[]
  quotas: {
    headline: string
    afterQuota: string
    detail: string
  }
  popular?: boolean
  cta: string
  tier: CheckoutTierKey
  badge?: string
  trialBadge?: string
  icon: React.ReactNode
}

const pricingTiers: PricingTier[] = [
  {
    name: "Standard",
    description: "Standard orchestration for everyday work",
    monthlyPrice: 10,
    annualPrice: 100,
    tier: "lite",
    icon: <Star className="h-5 w-5 text-[var(--bronze)]" />,
    quotas: {
      headline: "Standard orchestration",
      afterQuota: "Included with plan",
      detail: "Premium orchestration included with your subscription",
    },
    features: [...OFFER_STANDARD_FEATURES],
    cta: "Start 3-day free trial",
    trialBadge: "3 days free",
  },
  {
    name: "Premium",
    description: "Premium orchestration for benchmark-grade answers",
    monthlyPrice: 20,
    annualPrice: 200,
    tier: "pro",
    popular: true,
    icon: <Crown className="h-5 w-5 text-yellow-500" />,
    badge: "MOST POPULAR",
    quotas: {
      headline: "Premium orchestration",
      afterQuota: "Included with plan",
      detail: BENCHMARK_CLAIM_SHORT,
    },
    features: [...OFFER_PREMIUM_FEATURES],
    cta: "Subscribe – Premium",
  },
  {
    name: "Enterprise",
    description: "Single seat or teams — SSO, compliance, flagship model pick",
    monthlyPrice: 35,
    annualPrice: 350,
    tier: "enterprise",
    icon: <Building2 className="h-5 w-5 text-sky-400" />,
    badge: "For teams",
    quotas: {
      headline: "400 Premium queries / seat",
      afterQuota: "Then unlimited Standard",
      detail: "Premium orchestration · SSO · audit logs",
    },
    features: [...OFFER_ENTERPRISE_FEATURES],
    cta: "Subscribe — Enterprise",
  },
]

const pricingFaq = [
  {
    question: "How does the 3-day Standard trial work?",
    answer:
      "Start a free 3-day trial on Standard (monthly). You get premium orchestration during the trial. After 3 days your card is charged $10/month automatically unless you cancel in Billing. Cancel anytime during the trial to avoid charges.",
  },
  {
    question: "What is included in Standard?",
    answer:
      "Standard is $10/month and includes multi-model orchestration, knowledge base access, calculator and reranker tools, and 90-day conversation memory.",
  },
  {
    question: "What is Premium?",
    answer:
      "Premium is $20/month and uses our top orchestration stack with premium routing included in your plan.",
  },
  {
    question: "What happens when premium orchestration isn't available?",
    answer:
      "If you reach your plan's premium orchestration allowance for the billing period, requests use standard orchestration until the period resets. Your subscription price does not change.",
  },
  {
    question: "Can I choose a specific flagship model?",
    answer:
      "Single flagship model pick (one explicit frontier model per request) is available on Enterprise. Standard and Premium use automatic multi-model orchestration.",
  },
  {
    question: "Can I change plans later?",
    answer: "Yes. Upgrade or downgrade from Billing; changes are prorated where Stripe applies proration.",
  },
]

const TRUST = [
  { icon: BadgeCheck, title: "Cancel Anytime", sub: "No commitments" },
  { icon: Wallet, title: "No Hidden Fees", sub: "Flat monthly pricing" },
  { icon: Lock, title: "Secure & Encrypted", sub: "256-bit protection" },
  { icon: Clock, title: "Start Free in Minutes", sub: "3-day free trial" },
]

function renderPricingStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      organizationNode(),
      buildProductStructuredData({
        description:
          "Multi-model AI orchestration platform that routes every request to the best model for accuracy, speed, and cost.",
        offers: pricingTiers.map((tier) => ({
          name: tier.name,
          price: String(tier.monthlyPrice),
          url: sitePath(`${CAMPAIGN_PATH}#${tier.tier}`),
        })),
      }),
      {
        "@type": "FAQPage",
        mainEntity: pricingFaq.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}

function SectionRule({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-8 flex items-center justify-center gap-3">
      <span className="h-px w-10 bg-gradient-to-r from-transparent to-amber-500/70 sm:w-16" />
      <span className="text-center text-xs font-bold uppercase tracking-[0.18em] text-amber-400 sm:text-sm">
        {children}
      </span>
      <span className="h-px w-10 bg-gradient-to-l from-transparent to-amber-500/70 sm:w-16" />
    </div>
  )
}

export default function SpainPricingClient() {
  const searchParams = useSearchParams()
  const { isSignedIn, isLoaded, user } = useUser()
  const { openSignUp } = useClerk()
  const [isAnnual, setIsAnnual] = useState(false)
  const [loadingTier, setLoadingTier] = useState<string | null>(null)
  const autoCheckoutAttempted = useRef(false)

  const afterAuthUrl = useCallback(
    (tier: CheckoutTierKey) =>
      `${CAMPAIGN_PATH}?subscribe=${tier}&cycle=${isAnnual ? "annual" : "monthly"}`,
    [isAnnual],
  )

  const startCheckout = useCallback(
    async (
      tier: PricingTier,
      billingCycle: "monthly" | "annual",
      opts?: { dedupeStorageKey?: string },
    ) => {
      const clearDedupe = () => {
        if (opts?.dedupeStorageKey && typeof window !== "undefined") {
          sessionStorage.removeItem(opts.dedupeStorageKey)
        }
      }

      setLoadingTier(tier.tier)
      void track("checkout_started", {
        tier: tier.tier,
        tier_name: tier.name,
        billing_cycle: billingCycle,
        source: "landing_spain",
        price_usd: billingCycle === "annual" ? tier.annualPrice : tier.monthlyPrice,
      })
      try {
        const response = await fetch("/api/billing/create-checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tier: tier.tier,
            billingCycle,
          }),
        })

        const data = await response.json()

        if (data.url) {
          if (opts?.dedupeStorageKey && typeof window !== "undefined") {
            sessionStorage.setItem(opts.dedupeStorageKey, "done")
          }
          window.location.href = data.url
        } else {
          console.error("Failed to create checkout session:", data.error)
          clearDedupe()
          alert(`Failed to create checkout: ${data.error || "Unknown error"}`)
        }
      } catch (error) {
        console.error("Error creating checkout session:", error)
        clearDedupe()
        alert(`An error occurred: ${error instanceof Error ? error.message : "Unknown error"}`)
      } finally {
        setLoadingTier(null)
      }
    },
    [],
  )

  const handleSubscribe = async (tier: PricingTier) => {
    if (!isSignedIn) {
      const dest = afterAuthUrl(tier.tier)
      // pk_live_ on localhost cannot use Clerk Account Portal with localhost redirect_url.
      if (isProductionClerkKeyOnLocalDev()) {
        window.location.assign(`/sign-up?redirect_url=${encodeURIComponent(dest)}`)
        return
      }
      // Match /pricing pattern + forceRedirect so we return to this campaign
      // even if ClerkProvider defaults sign-up to /pricing.
      openSignUp({
        redirectUrl: dest,
        forceRedirectUrl: dest,
        fallbackRedirectUrl: dest,
      })
      return
    }

    await startCheckout(tier, isAnnual ? "annual" : "monthly")
  }

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user?.id) return
    if (typeof window === "undefined") return

    const createdAtMs = user.createdAt ? new Date(user.createdAt).getTime() : NaN
    const isFreshSignup =
      Number.isFinite(createdAtMs) && Date.now() - createdAtMs < FRESH_SIGNUP_WINDOW_MS
    if (!isFreshSignup) return

    try {
      const trackedKey = `${SIGNUP_TRACKED_STORAGE_KEY}_${user.id}`
      if (window.localStorage.getItem(trackedKey)) return
      window.localStorage.setItem(trackedKey, "1")
    } catch {
      // ignore
    }
    void track("signup_completed", {
      user_id: user.id,
      via: searchParams.get("subscribe") ? "landing_spain_redirect" : "landing_spain",
    })
  }, [isLoaded, isSignedIn, user?.id, user?.createdAt, searchParams])

  // Same auto-checkout pattern as /pricing after Clerk returns with ?subscribe=
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user?.id) return
    const sub = searchParams.get("subscribe")
    if (!sub) return

    const tier = pricingTiers.find((t) => t.tier === sub)
    if (!tier) return

    const cycle = searchParams.get("cycle") === "annual" ? "annual" : "monthly"
    const storageKey = `llmhive_spain_autoco_v1_${user.id}_${sub}_${cycle}`
    if (typeof window !== "undefined") {
      if (searchParams.get("payment_required") === "1") {
        sessionStorage.removeItem(storageKey)
      }
      const state = sessionStorage.getItem(storageKey)
      if (state === "done" || state === "pending") return
      sessionStorage.setItem(storageKey, "pending")
    }
    if (autoCheckoutAttempted.current) return
    autoCheckoutAttempted.current = true

    setIsAnnual(cycle === "annual")
    void startCheckout(tier, cycle, { dedupeStorageKey: storageKey })
  }, [isLoaded, isSignedIn, user?.id, searchParams, startCheckout])

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#050505] text-zinc-100">
      {renderPricingStructuredData()}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_rgba(116,172,223,0.10),_transparent_52%),radial-gradient(ellipse_at_bottom_right,_rgba(249,115,22,0.12),_transparent_48%)]"
      />

      {/* Campaign nav (MarketingLayoutChrome skips shared nav under /landing/*) */}
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/5 bg-black/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex shrink-0 items-center gap-2.5" aria-label="LLMHive home">
            <Image src="/logo.png" alt="" width={32} height={32} priority className="h-8 w-8" />
            <LogoText height={26} variant="nav" className="hidden sm:block" />
          </Link>
          <nav className="hidden items-center gap-6 lg:flex" aria-label="Campaign">
            <a href="#features" className="text-sm font-medium text-zinc-200 hover:text-white">
              Features
            </a>
            <a href="#how-it-works" className="text-sm font-medium text-zinc-200 hover:text-white">
              How it works
            </a>
            <a href="#pricing" className="text-sm font-medium text-zinc-200 hover:text-white">
              Pricing
            </a>
            <Link href="/about" className="text-sm font-medium text-zinc-200 hover:text-white">
              About
            </Link>
            <Link href="/contact" className="text-sm font-medium text-zinc-200 hover:text-white">
              Contact
            </Link>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <Button
              size="sm"
              className="bronze-gradient border-0 font-semibold text-black hover:text-black"
              onClick={() => void handleSubscribe(pricingTiers[0])}
              disabled={loadingTier === "lite"}
            >
              Start Free Trial
            </Button>
            {isSignedIn ? (
              <Button
                asChild
                size="sm"
                variant="outline"
                className="hidden border-white/30 bg-transparent text-white hover:bg-white/10 hover:text-white sm:inline-flex"
              >
                <Link href="/app">Open app</Link>
              </Button>
            ) : (
              <Button
                asChild
                size="sm"
                variant="outline"
                className="hidden border-white/30 bg-transparent text-white hover:bg-white/10 hover:text-white sm:inline-flex"
              >
                <Link href="/sign-in">Sign In</Link>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="pt-16">
        {searchParams.get("payment_required") === "1" &&
          searchParams.get("reason") === "past_due" && (
            <div
              role="alert"
              className="mx-auto mt-6 max-w-3xl rounded-xl border border-red-500/60 bg-red-500/10 px-5 py-4 text-sm text-red-100"
            >
              <strong className="font-semibold">Your last renewal payment failed.</strong> Update your
              payment method to restore access.
            </div>
          )}

        {/* ── Hero — solid dark BG (no photo behind the card) */}
        <section className="relative overflow-hidden bg-[#050505]">
          <div className="absolute inset-0 bg-[#050505]" aria-hidden />

          <div className="relative z-10 mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6 sm:pb-20 sm:pt-12 lg:px-8">
            {/* Left copy — reserved width; image is absolutely pinned right on lg+ */}
            <div className="llmhive-fade-in relative z-20 w-full max-w-xl lg:max-w-[28rem] xl:max-w-[30rem]">
              <div className="mb-5 inline-flex max-w-full items-center gap-2 rounded-full border border-orange-400/45 bg-black/60 px-3 py-1.5 backdrop-blur-sm">
                <Trophy className="h-4 w-4 shrink-0 text-orange-400" aria-hidden />
                <p className="truncate text-xs font-semibold text-orange-300 sm:text-sm">
                  {BENCHMARK_CLAIM_BANNER}
                </p>
              </div>
              <h1 className="text-balance text-4xl font-extrabold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-[2.85rem] xl:text-[3.1rem]">
                Premium orchestration for the{" "}
                <span className="text-orange-400">best AI answers.</span>
              </h1>
              <p className="mt-5 max-w-lg text-base leading-relaxed text-zinc-200 sm:text-lg">
                Route your requests across top models instantly. Better answers, lower cost, zero
                hassle.
              </p>
              <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {TRUST.map(({ icon: Icon, title, sub }) => (
                  <div
                    key={title}
                    className="rounded-lg border border-orange-400/40 bg-black/55 px-2.5 py-2.5 backdrop-blur-sm"
                  >
                    <Icon className="mb-1.5 h-4 w-4 text-orange-400" aria-hidden />
                    <p className="text-[11px] font-semibold leading-tight text-white sm:text-xs">
                      {title}
                    </p>
                    <p className="text-[10px] leading-tight text-zinc-400">{sub}</p>
                  </div>
                ))}
              </div>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Button
                  size="lg"
                  className="bronze-gradient h-14 border-0 px-8 text-base font-bold text-black shadow-lg shadow-orange-500/35"
                  onClick={() => void handleSubscribe(pricingTiers[0])}
                  disabled={loadingTier === "lite"}
                >
                  {loadingTier === "lite" ? "Starting…" : "Start 3-day free trial"}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="h-14 border-white/30 bg-black/40 px-7 text-base text-white hover:bg-black/60 hover:text-white"
                >
                  <a href="#how-it-works">
                    <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full border border-orange-400/70">
                      <Play className="h-3 w-3 fill-orange-400 text-orange-400" />
                    </span>
                    How it works
                  </a>
                </Button>
              </div>
              <p className="mt-4 text-xs text-zinc-400 sm:text-sm">
                <span className="truncate">{MARKETING_FEATURED_LINE}</span>
              </p>
            </div>

            {/* Right: discovery scene — pinned to right edge; trial card removed */}
            <div
              className="llmhive-fade-in relative z-10 mt-10 w-full max-w-[560px] sm:max-w-[620px] lg:absolute lg:right-4 lg:top-[6.5rem] lg:mt-0 lg:w-[min(720px,calc(100%-36rem))] lg:max-w-none"
              style={{ animationDelay: "0.1s" }}
            >
              <div className="relative ml-auto h-[240px] w-full overflow-hidden rounded-2xl border border-white/10 shadow-2xl shadow-orange-500/20 sm:h-[300px] lg:h-[380px]">
                <div
                  className="pointer-events-none absolute inset-0 rounded-full bg-orange-500/15 blur-3xl"
                  aria-hidden
                />
                <Image
                  src="/campaigns/spain/hero-player.jpg"
                  alt="Fan in España jersey celebrating with LLMHive"
                  fill
                  priority
                  className="object-cover object-[70%_center]"
                  sizes="(max-width: 1024px) 620px, 700px"
                />
              </div>
            </div>
          </div>
        </section>

        {/* ── Pricing (same Stripe tiers as /pricing) ─────────────────── */}
        <section id="pricing" className="scroll-mt-20 px-4 pb-1.5 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionRule>Choose the plan that fits your goals</SectionRule>

            <div className="mb-8 flex items-center justify-center gap-4">
              <Label
                htmlFor="billing-toggle-spain"
                className={cn("text-sm", !isAnnual ? "font-semibold text-white" : copySubtle)}
              >
                Monthly
              </Label>
              <Switch
                id="billing-toggle-spain"
                checked={isAnnual}
                onCheckedChange={setIsAnnual}
                className="data-[state=checked]:bg-amber-500"
              />
              <Label
                htmlFor="billing-toggle-spain"
                className={cn("text-sm", isAnnual ? "font-semibold text-white" : copySubtle)}
              >
                Annual
              </Label>
              <Badge className="shrink-0 border-0 bg-amber-500 font-bold text-black">Save ~17%</Badge>
            </div>

            <div className="mx-auto mb-1.5 grid max-w-6xl gap-4 md:grid-cols-2 lg:grid-cols-3">
              {pricingTiers.map((tier) => {
                const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
                const period = isAnnual ? "/year" : "/month"
                const isPremium = tier.tier === "pro"

                return (
                  <Card
                    key={tier.name}
                    id={tier.tier}
                    className={cn(
                      tierCardClass,
                      "h-[580px]",
                      isPremium
                        ? "border-2 border-amber-500/70 ring-1 ring-amber-500/25 shadow-amber-500/15 md:scale-[1.03]"
                        : tier.tier === "enterprise"
                          ? "border-sky-500/35 hover:border-sky-400/50"
                          : "border-amber-700/35 hover:border-amber-500/50",
                    )}
                  >
                    {tier.trialBadge && !isAnnual && tier.tier === "lite" && (
                      <div className="absolute -top-4 left-1/2 z-10 -translate-x-1/2">
                        <Badge className="border-0 bg-amber-500 px-4 py-1.5 font-bold text-black shadow-md shadow-amber-500/30">
                          {tier.trialBadge} · $0 today
                        </Badge>
                      </div>
                    )}
                    {tier.badge && (
                      <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                        <Badge
                          className={cn(
                            "border-0 px-4 py-1.5 font-bold",
                            isPremium
                              ? "bronze-gradient text-white"
                              : tier.tier === "enterprise"
                                ? "bg-sky-500 text-white"
                                : "bg-[var(--bronze)] text-white",
                          )}
                        >
                          {isPremium && <Trophy className="mr-1 h-4 w-4" />}
                          {tier.badge}
                        </Badge>
                      </div>
                    )}

                    <CardHeader className="flex-shrink-0 pb-2">
                      <div className="mb-1 flex items-center gap-2">
                        {tier.icon}
                        <CardTitle className="text-xl text-white">{tier.name}</CardTitle>
                        {isPremium && (
                          <Badge className="border-amber-500/40 bg-amber-500/20 text-xs text-amber-300">
                            RECOMMENDED
                          </Badge>
                        )}
                      </div>
                      <CardDescription className={cn("text-sm leading-snug", copyMuted)}>
                        {tier.description}
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="flex flex-1 flex-col overflow-hidden py-2">
                      <div className="mb-4 flex-shrink-0">
                        {tier.tier === "lite" && !isAnnual ? (
                          <div>
                            <div className="flex items-baseline gap-2">
                              <span className="text-4xl font-bold text-amber-300">$0</span>
                              <span className={cn("text-sm", copyMuted)}>for 3 days</span>
                            </div>
                            <p className={cn("mt-1 text-sm", copyMuted)}>
                              then <span className="font-semibold text-white">${price.toFixed(2)}/month</span>
                            </p>
                            <p className="mt-2 text-xs font-medium text-amber-300/95">
                              Card required · Cancel before day 4 to avoid charges
                            </p>
                          </div>
                        ) : (
                          <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-bold text-white">${price.toFixed(2)}</span>
                            <span className={cn("text-sm", copySubtle)}>{period}</span>
                          </div>
                        )}
                      </div>

                      <div
                        className={cn(
                          "mb-4 flex-shrink-0 rounded-lg border p-3",
                          isPremium
                            ? "border-amber-500/25 bg-amber-500/10"
                            : "border-zinc-700/50 bg-zinc-900/80",
                        )}
                      >
                        <div className="mb-1 flex items-center gap-2">
                          <span
                            className={cn(
                              "text-sm font-bold",
                              isPremium ? "text-amber-300" : "text-[var(--bronze)]",
                            )}
                          >
                            {isPremium ? "Premium orchestration" : "Standard orchestration"}
                          </span>
                        </div>
                        <div className="text-xs font-semibold text-emerald-400">
                          {tier.quotas.afterQuota}
                        </div>
                        <div className={cn("mt-1 text-xs leading-relaxed", copyMuted)}>
                          {tier.quotas.detail}
                        </div>
                      </div>

                      <div className="min-h-0 flex-1 overflow-y-auto">
                        <ul className="space-y-2 pr-1">
                          {tier.features.map((feature, index) => (
                            <li key={index} className="flex items-start gap-2">
                              <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-400" />
                              <span className={cn("text-sm leading-snug", copyMuted)}>{feature}</span>
                            </li>
                          ))}
                        </ul>
                        {tier.tier !== "enterprise" && (
                          <p
                            className={cn(
                              "mt-3 border-t border-zinc-700/50 pt-3 text-xs leading-relaxed",
                              copySubtle,
                            )}
                          >
                            Automatic multi-model orchestration.{" "}
                            <a
                              href="#enterprise"
                              className="text-zinc-200 underline underline-offset-2 hover:text-white"
                            >
                              {ENTERPRISE_SINGLE_FLAGSHIP_PICK_LABEL}
                            </a>
                            .
                          </p>
                        )}
                      </div>
                    </CardContent>

                    <CardFooter className="flex-shrink-0 pb-4 pt-3">
                      <Button
                        className={cn(
                          "w-full font-bold transition-all duration-300",
                          isPremium
                            ? "bronze-gradient border-0 text-white"
                            : "bg-[var(--bronze)] text-white hover:bg-[var(--bronze-dark)]",
                        )}
                        onClick={() => void handleSubscribe(tier)}
                        disabled={loadingTier === tier.tier}
                      >
                        {loadingTier === tier.tier ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processing...
                          </>
                        ) : (
                          <>
                            {tier.tier === "lite" && isAnnual ? "Subscribe — Standard" : tier.cta}
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </>
                        )}
                      </Button>
                    </CardFooter>
                  </Card>
                )
              })}
            </div>
          </div>
        </section>

        {/* ── Lifestyle banner — designer asset with baked-in infographics */}
        <section className="border-t border-white/5 bg-[#050505] px-4 py-1.5 sm:px-6 lg:px-8">
          <div className="mx-auto flex max-w-6xl justify-center">
            <div className="relative w-full max-w-[1037px] overflow-hidden rounded-2xl bg-[#050505]">
              <Image
                src="/campaigns/spain/lifestyle-banner.jpg"
                alt="Less time getting things done. More time for what matters. LLM Hive made it easy."
                width={1920}
                height={887}
                className="mx-auto h-auto w-full bg-[#050505] object-contain object-center"
                sizes="(max-width: 1037px) 100vw, 1037px"
                priority={false}
              />
            </div>
          </div>
        </section>

        {/* ── Save strip — designer comparison card + right-side ball */}
        <section className="relative overflow-hidden border-t border-white/5 px-4 pb-14 pt-1.5 sm:px-6 lg:px-8">
          <div className="relative mx-auto max-w-5xl">
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-zinc-950/95 shadow-xl shadow-black/50">
              <div className="flex flex-col gap-6 p-5 sm:p-7 lg:flex-row lg:items-center lg:gap-4 lg:p-8">
                {/* Left: competitor stack */}
                <div className="min-w-0 flex-1 lg:max-w-[280px]">
                  <p className="text-sm font-bold uppercase leading-snug tracking-wide sm:text-base">
                    <span className="text-white">Stop paying for </span>
                    <span className="text-orange-400">multiple AI subscriptions</span>
                  </p>
                  <ul className="mt-4 space-y-2.5 text-sm text-zinc-200">
                    {[
                      ["ChatGPT Plus", "$20/month"],
                      ["Claude Pro", "$20/month"],
                      ["Gemini Advanced", "$20/month"],
                      ["Grok", "$30/month"],
                    ].map(([name, price]) => (
                      <li key={name} className="flex justify-between gap-4">
                        <span>{name}</span>
                        <span className="tabular-nums text-zinc-300">{price}</span>
                      </li>
                    ))}
                    <li className="flex justify-between gap-4 border-t border-white/10 pt-2.5 font-semibold">
                      <span className="text-white">TOTAL</span>
                      <span className="text-red-400 line-through decoration-red-400/80">
                        $90+ /month
                      </span>
                    </li>
                  </ul>
                </div>

                <div
                  className="hidden shrink-0 px-2 text-3xl font-black tracking-tighter text-orange-400 sm:block lg:px-4"
                  aria-hidden
                >
                  ›››
                </div>

                {/* Center: offer */}
                <div className="min-w-0 shrink-0 lg:w-[200px]">
                  <p className="text-sm font-semibold text-orange-400">LLMHive Premium</p>
                  <p className="text-xs font-semibold uppercase tracking-wider text-amber-200/90">
                    Only
                  </p>
                  <p className="mt-1 text-5xl font-extrabold leading-none text-orange-400">
                    $20
                    <span className="ml-1 text-base font-semibold text-white">/month</span>
                  </p>
                  <p className="mt-4 inline-flex rounded-md border border-orange-400/60 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-orange-300">
                    Save $70+ every month
                  </p>
                </div>

                {/* Right: ball accent — designer scale (~1/4 of card), flush right */}
                <div className="relative mx-auto h-[140px] w-[180px] shrink-0 overflow-hidden rounded-xl sm:mx-0 sm:ml-auto sm:h-[160px] sm:w-[200px] lg:h-[170px] lg:w-[220px]">
                  <div
                    className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(circle_at_35%_45%,rgba(249,115,22,0.35),transparent_55%)]"
                    aria-hidden
                  />
                  <Image
                    src="/campaigns/spain/ball-net.jpg"
                    alt=""
                    fill
                    className="object-cover object-left"
                    sizes="220px"
                  />
                </div>
              </div>
            </div>

            {/* Trust bar — product facts only (no fabricated user/volume metrics) */}
            <div className="mt-5 grid gap-3 rounded-2xl border border-white/10 bg-zinc-950/70 p-4 sm:grid-cols-2 sm:p-5 lg:grid-cols-4">
              {[
                { icon: Trophy, v: "#1 in 5/8", l: "Benchmark categories — May 2026" },
                { icon: Network, v: "350+", l: "Models available to route" },
                { icon: Clock, v: "3-day", l: "Standard free trial ($0 today)" },
                { icon: BadgeCheck, v: "Cancel anytime", l: "Flat monthly pricing, no lock-in" },
              ].map((s) => (
                <div key={s.v + s.l} className="flex items-start gap-3 px-1 py-1">
                  <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-amber-500/30 bg-amber-500/10">
                    <s.icon className="h-4 w-4 text-amber-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-lg font-bold text-white">{s.v}</p>
                    <p className="text-xs leading-snug text-zinc-400">{s.l}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Features + how it works (from pricing + mockup) ─────────── */}
        <section id="features" className="scroll-mt-20 border-t border-white/5 px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <SectionRule>Why thousands choose LLMHive</SectionRule>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {[
                { icon: Wallet, t: "Save Money", d: "One plan instead of stacked AI tools." },
                { icon: Trophy, t: "Best Answers", d: "Orchestration picks the strongest model." },
                { icon: Zap, t: "Save Time", d: "No tab-switching between providers." },
                { icon: Sparkles, t: "Zero Effort", d: "Automatic routing out of the box." },
                { icon: Shield, t: "One Subscription", d: "Billing and access in one place." },
              ].map(({ icon: Icon, t, d }) => (
                <div
                  key={t}
                  className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 transition hover:-translate-y-0.5 hover:border-amber-500/35"
                >
                  <Icon className="mb-3 h-5 w-5 text-amber-400" />
                  <p className="font-semibold text-white">{t}</p>
                  <p className="mt-1 text-sm text-zinc-400">{d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-20 px-4 pb-16 sm:px-6 lg:px-8">
          <div className={cn("mx-auto max-w-3xl p-8 md:p-10", panelClass)}>
            <h2 className="mb-8 text-center text-2xl font-bold text-white">How it works</h2>
            <ol className="grid gap-4 sm:grid-cols-2">
              {[
                { n: "1", icon: Target, t: "You Ask", d: "Submit your question in the Hive." },
                { n: "2", icon: Brain, t: "LLMHive", d: "Orchestration analyzes the request." },
                { n: "3", icon: Network, t: "Chooses Best AI", d: "Selects the strongest models." },
                { n: "4", icon: Zap, t: "Best Response", d: "You get the highest-quality answer." },
              ].map((step) => {
                const Icon = step.icon
                return (
                  <li key={step.n} className="flex items-start gap-3 rounded-xl border border-white/5 bg-black/30 p-4">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-amber-500/30 bg-amber-500/15 text-sm font-bold text-amber-300">
                      {step.n}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-amber-400" />
                        <h3 className="font-semibold text-white">{step.t}</h3>
                      </div>
                      <p className={cn("mt-1 text-sm", copyMuted)}>{step.d}</p>
                    </div>
                  </li>
                )
              })}
            </ol>
            <p className={cn("mt-6 text-center text-sm", copySubtle)}>
              Standard ($10/mo, 3-day trial on monthly) and Premium ($20/mo) include premium orchestration —
              same offers as{" "}
              <Link href="/pricing" className="text-amber-400 underline-offset-2 hover:underline">
                /pricing
              </Link>
              .
            </p>
          </div>
        </section>

        <section className="px-4 pb-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-4xl">
            <div className={cn("p-8 text-center md:p-10", panelClass)}>
              <Trophy className="mx-auto mb-4 h-10 w-10 text-amber-400" />
              <h2 className="mb-3 text-2xl font-bold text-white">Industry benchmarks (April 2026)</h2>
              <p className={cn("mx-auto mb-4 max-w-2xl font-medium", copyMuted)}>
                {BENCHMARK_CLAIM_SHORT}.
              </p>
              <p className={cn("mx-auto max-w-2xl text-sm leading-relaxed", copySubtle)}>
                Our orchestration combines {MARKETING_FEATURED_ORCHESTRATION_STACK} with consensus voting,
                challenge-refine workflows, and tool integration.
              </p>
              <p className="mt-4 text-sm text-zinc-500">
                Full pill: #1 {BENCHMARK_CLAIM_PILL_TEXT}
              </p>
            </div>
          </div>
        </section>

        <section className="px-4 pb-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl">
            <h2 className="mb-8 text-center text-2xl font-bold text-white">Frequently asked questions</h2>
            <div className="space-y-4">
              {pricingFaq.map((item) => (
                <div key={item.question} className={cn("p-6", panelClass)}>
                  <h3 className="mb-2 font-semibold text-white">{item.question}</h3>
                  <p className={cn("text-sm leading-relaxed", copyMuted)}>{item.answer}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 pb-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <div className={cn("border-amber-500/30 p-8 md:p-10", panelClass)}>
              <h2 className="mb-3 text-2xl font-bold uppercase tracking-tight text-white md:text-3xl">
                Ready to get started?
              </h2>
              <p className={cn("mb-6 leading-relaxed", copyMuted)}>
                Premium from $20/mo, or start Standard with a 3-day free trial — $0 today on monthly billing.
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <Button
                  size="lg"
                  className="bronze-gradient border-0 px-8 font-semibold text-white"
                  onClick={() => void handleSubscribe(pricingTiers[1])}
                  disabled={loadingTier === "pro"}
                >
                  <Trophy className="mr-2 h-5 w-5" />
                  Get Premium — $20/mo
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-zinc-500 text-zinc-200 hover:bg-zinc-800 hover:text-white"
                  onClick={() => void handleSubscribe(pricingTiers[0])}
                  disabled={loadingTier === "lite"}
                >
                  Start 3-day trial
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5 py-10">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/logo.png" alt="LLMHive" width={28} height={28} className="h-7 w-7" />
            <LogoText height={22} variant="nav" />
          </Link>
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-zinc-400">
            <a href="#features" className="hover:text-white">
              Features
            </a>
            <a href="#how-it-works" className="hover:text-white">
              How it works
            </a>
            <a href="#pricing" className="hover:text-white">
              Pricing
            </a>
            <Link href="/about" className="hover:text-white">
              About
            </Link>
            <Link href="/contact" className="hover:text-white">
              Contact
            </Link>
            <Link href="/pricing" className="hover:text-white">
              Full pricing
            </Link>
          </div>
        </div>
        <p className={cn("mx-auto mt-6 max-w-7xl px-4 text-center text-sm sm:px-6 lg:px-8", copySubtle)}>
          © {new Date().getFullYear()} LLMHive. All rights reserved.
        </p>
      </footer>
    </div>
  )
}
