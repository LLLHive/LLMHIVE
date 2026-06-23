"use client"

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
  MARKETING_OPENAI_FLAGSHIP,
} from "@/lib/marketing/featured-models"
import {
  BENCHMARK_CLAIM_PILL_TEXT,
  BENCHMARK_CLAIM_SHORT,
} from "@/lib/benchmark-claim"
import {
  OFFER_ENTERPRISE_FEATURES,
  OFFER_PREMIUM_FEATURES,
  OFFER_STANDARD_FEATURES,
} from "@/lib/marketing/pricing-offers"
import { cn } from "@/lib/utils"
import { track } from "@/lib/observability/analytics"
import Link from "next/link"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"
import { buildProductStructuredData, organizationNode } from "@/lib/marketing/structured-data"
import { sitePath } from "@/lib/site-url"

const SIGNUP_TRACKED_STORAGE_KEY = "llmhive_signup_tracked_v1"
const FRESH_SIGNUP_WINDOW_MS = 5 * 60 * 1000

/** Stripe / backend tier keys (legacy ids: lite = Standard product, pro = Premium product) */
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

// GTM April 2026: three offers — Standard ($10), Premium ($20), Enterprise (unchanged).
// Checkout still uses Stripe price IDs keyed as lite / pro for backwards compatibility.
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
      afterQuota: "Spend guard protected",
      detail: "Elite orchestration while the spend guard allows, then free orchestration",
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
    badge: "BEST VALUE",
    quotas: {
      headline: "Premium orchestration",
      afterQuota: "Spend guard protected",
      detail: BENCHMARK_CLAIM_SHORT,
    },
    features: [...OFFER_PREMIUM_FEATURES],
    cta: "Subscribe — Premium",
  },
  {
    name: "Enterprise",
    description: "Teams, SSO, and compliance",
    monthlyPrice: 35,
    annualPrice: 350,
    tier: "enterprise",
    icon: <Building2 className="h-5 w-5 text-emerald-400" />,
    badge: "Per seat",
    quotas: {
      headline: "400 Premium queries / seat",
      afterQuota: "Then unlimited Standard",
      detail: "SSO, audit logs, SLA",
    },
    features: [...OFFER_ENTERPRISE_FEATURES],
    cta: "Contact sales",
  },
]

const pricingFaq = [
  {
    question: "How does the 3-day Standard trial work?",
    answer:
      "Start a free 3-day trial on Standard (monthly). You get elite orchestration during the trial with a $3 provider spend cap. After 3 days your card is charged $10/month automatically unless you cancel in Billing. Cancel anytime during the trial to avoid charges.",
  },
  {
    question: "What is included in Standard?",
    answer:
      "Standard is $10/month and includes multi-model orchestration, knowledge base access, calculator and reranker tools, and 90-day conversation memory.",
  },
  {
    question: "What is Premium?",
    answer:
      "Premium is $20/month and uses our top orchestration stack while the spend guard allows, then switches to free orchestration for margin protection.",
  },
  {
    question: "What happens when the spend guard is reached?",
    answer:
      "LLMHive switches paid accounts to free orchestration for the rest of the billing period when provider spend reaches the protected cap.",
  },
  {
    question: "Can I change plans later?",
    answer: "Yes. Upgrade or downgrade from Billing; changes are prorated where Stripe applies proration.",
  },
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
          url: sitePath(`/pricing#${tier.tier}`),
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

export default function PricingClient() {
  const searchParams = useSearchParams()
  const { isSignedIn, isLoaded, user } = useUser()
  const { openSignUp } = useClerk()
  const [isAnnual, setIsAnnual] = useState(false)
  const [loadingTier, setLoadingTier] = useState<string | null>(null)
  const autoCheckoutAttempted = useRef(false)

  const startCheckout = useCallback(
    async (
      tier: PricingTier,
      billingCycle: "monthly" | "annual",
      opts?: { dedupeStorageKey?: string },
    ) => {
      if (tier.tier === "enterprise") {
        window.location.href = "mailto:info@llmhive.ai?subject=Enterprise Inquiry - LLMHive"
        return
      }

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
    if (tier.tier === "enterprise") {
      window.location.href = "mailto:info@llmhive.ai?subject=Enterprise Inquiry - LLMHive"
      return
    }

    if (!isSignedIn) {
      openSignUp({
        redirectUrl: `/pricing?subscribe=${tier.tier}&cycle=${isAnnual ? "annual" : "monthly"}`,
      })
      return
    }

    await startCheckout(tier, isAnnual ? "annual" : "monthly")
  }

  // Fire `signup_completed` once per Clerk user when they first land here
  // right after creating their account (Clerk redirects to /pricing with
  // ?subscribe=…). Dedup via localStorage so reloads / re-visits don't refire.
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
      // localStorage disabled — skip dedup, only fire if first effect run.
    }
    void track("signup_completed", {
      user_id: user.id,
      via: searchParams.get("subscribe") ? "pricing_redirect" : "direct",
    })
  }, [isLoaded, isSignedIn, user?.id, user?.createdAt, searchParams])

  // After Clerk sign-up/sign-in, land on /pricing?subscribe=…&cycle=… and redirect to Stripe once.
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !user?.id) return
    const sub = searchParams.get("subscribe")
    if (!sub) return

    const tier = pricingTiers.find((t) => t.tier === sub)
    if (!tier || tier.tier === "enterprise") return

    const cycle = searchParams.get("cycle") === "annual" ? "annual" : "monthly"
    const storageKey = `llmhive_pricing_autoco_v1_${user.id}_${sub}_${cycle}`
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
    // Transparent root: same reasoning as app/page.tsx — let the global
    // <AppBackground /> from app/layout.tsx (forest + warm light) show
    // through so /pricing matches /  and /app instead of painting solid
    // color over the corporate scene.
    <div className="relative min-h-screen">
      {renderPricingStructuredData()}
      {/* The shared <MarketingNav /> rendered by app/pricing/page.tsx is the
          single nav for this page. The previous internal header duplicated
          it visually and shipped a buggy "Go to App" link pointing at "/"
          instead of "/app", so it has been removed. Anonymous Sign in /
          Sign up and signed-in Sign out controls all live in MarketingNav. */}

      <main className="container mx-auto px-4 py-12">
        {/* Past-due banner is intentionally preserved: it signals a real
            billing failure to existing paying customers and is a different
            audience from the generic "Subscription required" banner that
            user-feedback asked us to remove. The amber generic variant
            previously rendered for any ?payment_required=1 hit was
            removed — see commit message for context. */}
        {searchParams.get("payment_required") === "1" &&
          searchParams.get("reason") === "past_due" && (
            <div
              role="alert"
              className="max-w-3xl mx-auto mb-8 rounded-xl border border-red-500/60 bg-red-500/10 px-5 py-4 text-sm text-red-100"
            >
              <strong className="font-semibold">Your last renewal payment failed.</strong>{" "}
              Update your payment method to restore access. We&apos;ll resume immediately
              once the new charge succeeds.
            </div>
          )}

        {/* Brand hero — copied 1:1 from app/page.tsx (which itself mirrors
            components/home-screen.tsx). Identical sphere sizing, identical
            negative-margin overlap, identical LogoText heights, identical
            metallic subtitle, identical #1 benchmark pill, and the same
            `${MARKETING_OPENAI_FLAGSHIP} · …` models pill that lives directly under the
            hero on /. Keeps /, /pricing and /app visually indistinguishable
            on the brand mark. Do not adjust here without also updating
            home-screen.tsx and app/page.tsx — kept in lockstep. */}
        <div className="llmhive-fade-in mx-auto mb-2 flex min-h-0 shrink-0 flex-col items-center text-center [@media(max-height:720px)]:scale-[0.97] [@media(max-height:640px)]:scale-[0.94]">
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
            Patented multi-agent orchestration for enhanced accuracy and performance.
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

        <div className="mb-10 flex justify-center">
          <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-amber-500/25 bg-amber-500/10 px-3.5 py-1.5 text-xs font-medium text-amber-300 backdrop-blur-sm sm:text-sm">
            <Sparkles className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="truncate">
              {MARKETING_FEATURED_LINE}
            </span>
          </div>
        </div>

        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            Premium quality from <span className="text-yellow-400">$20/mo</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-4">
            <span className="text-yellow-400 font-bold">Premium</span> uses{" "}
            <span className="text-yellow-400 font-bold">elite orchestration</span> with{" "}
            <span className="text-yellow-400 font-bold">{BENCHMARK_CLAIM_SHORT}</span> — powered by{" "}
            {MARKETING_FEATURED_ORCHESTRATION_STACK}.
          </p>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            <span className="font-semibold text-[var(--bronze)]">Standard</span> and{" "}
            <span className="font-semibold text-yellow-400">Premium</span> use elite orchestration while the
            spend guard allows, then switch to free orchestration for margin protection.
          </p>
        </div>

        {!isAnnual && (
          <div className="max-w-3xl mx-auto mb-8 rounded-2xl border-2 border-amber-500/40 bg-gradient-to-r from-amber-500/15 via-[var(--bronze)]/10 to-amber-500/15 px-6 py-5 text-center shadow-lg shadow-amber-500/10">
            <p className="text-lg font-bold text-amber-300 mb-1">Try Standard free for 3 days</p>
            <p className="text-sm text-muted-foreground max-w-xl mx-auto">
              <span className="text-foreground font-semibold">$0 today</span> — card required. Elite orchestration
              during trial (up to $3 provider spend). Then{" "}
              <span className="text-foreground font-semibold">$10/month</span> unless you cancel in Billing.
            </p>
          </div>
        )}

        <div className="max-w-4xl mx-auto mb-10 p-6 rounded-xl bg-gradient-to-r from-yellow-500/20 via-amber-500/20 to-yellow-500/20 border-2 border-yellow-500/50">
          <div className="grid md:grid-cols-2 gap-6 text-center">
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <div className="text-3xl font-black text-yellow-400 mb-2">Premium</div>
              <div className="text-lg font-bold text-yellow-300">{BENCHMARK_CLAIM_SHORT}</div>
              <div className="text-sm text-yellow-200/70 mt-1">{MARKETING_FEATURED_ORCHESTRATION_STACK}</div>
            </div>
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <div className="text-3xl font-black text-[var(--bronze)] mb-2">Standard</div>
              <div className="text-lg font-bold text-amber-300">3-day free trial on monthly</div>
              <div className="text-sm text-muted-foreground mt-1">$0 today, then $10/mo — cancel anytime</div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center gap-4 mb-10">
          <Label
            htmlFor="billing-toggle"
            className={cn(!isAnnual && "text-foreground font-semibold", isAnnual && "text-muted-foreground")}
          >
            Monthly
          </Label>
          <Switch
            id="billing-toggle"
            checked={isAnnual}
            onCheckedChange={setIsAnnual}
            className="data-[state=checked]:bg-yellow-500"
          />
          <Label
            htmlFor="billing-toggle"
            className={cn(isAnnual && "text-foreground font-semibold", !isAnnual && "text-muted-foreground")}
          >
            Annual
          </Label>
          {isAnnual && (
            <Badge className="bg-yellow-500 text-black font-bold border-0">Save ~17%</Badge>
          )}
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl mx-auto mb-16">
          {pricingTiers.map((tier) => {
            const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
            const period = isAnnual ? "/year" : "/month"
            const isPremium = tier.tier === "pro"

            return (
              <Card
                key={tier.name}
                className={cn(
                  "group relative flex flex-col bg-card/50 backdrop-blur-sm transition-all duration-300 h-[580px]",
                  isPremium
                    ? "border-2 border-yellow-500 shadow-lg shadow-yellow-500/20"
                    : "border-2 border-[var(--bronze)]/30 hover:border-[var(--bronze)]"
                )}
              >
                {tier.trialBadge && !isAnnual && tier.tier === "lite" && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
                    <Badge className="border-0 px-4 py-1.5 font-bold bg-amber-500 text-black shadow-md shadow-amber-500/30">
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
                          ? "bg-amber-600 text-white text-sm"
                          : tier.tier === "enterprise"
                            ? "bg-emerald-500 text-white"
                            : "bg-[var(--bronze)] text-white"
                      )}
                    >
                      {isPremium && <Trophy className="h-4 w-4 mr-1" />}
                      {tier.badge}
                    </Badge>
                  </div>
                )}

                <CardHeader className="pb-2 flex-shrink-0">
                  <div className="flex items-center gap-2 mb-1">
                    {tier.icon}
                    <CardTitle className="text-xl">{tier.name}</CardTitle>
                    {isPremium && (
                      <Badge className="bg-yellow-500/20 text-yellow-500 border-yellow-500/30 text-xs">
                        RECOMMENDED
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs">{tier.description}</CardDescription>
                </CardHeader>

                <CardContent className="flex-1 overflow-hidden flex flex-col py-2">
                  <div className="mb-4 flex-shrink-0">
                    {tier.tier === "lite" && !isAnnual ? (
                      <div>
                        <div className="flex items-baseline gap-2">
                          <span className="font-bold text-4xl text-amber-300">$0</span>
                          <span className="text-sm text-muted-foreground">for 3 days</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          then <span className="font-semibold text-foreground">${price.toFixed(2)}/month</span>
                        </p>
                        <p className="text-xs text-amber-400/90 mt-2 font-medium">
                          Card required · Cancel anytime before day 4 to avoid charges
                        </p>
                      </div>
                    ) : (
                      <div className="flex items-baseline gap-1">
                        <span className="font-bold text-3xl">${price.toFixed(2)}</span>
                        <span className="text-sm text-muted-foreground">{period}</span>
                      </div>
                    )}
                  </div>

                  <div
                    className={cn(
                      "mb-4 p-3 rounded-lg flex-shrink-0",
                      isPremium ? "bg-yellow-500/10 border border-yellow-500/30" : "bg-muted/30"
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          "font-bold text-sm",
                          isPremium ? "text-yellow-500" : "text-[var(--bronze)]"
                        )}
                      >
                        {isPremium ? "🏆" : "✦"} {tier.quotas.headline}
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-emerald-400">{tier.quotas.afterQuota}</div>
                    <div className="text-xs mt-1 text-muted-foreground">{tier.quotas.detail}</div>
                  </div>

                  <div className="flex-1 overflow-y-auto min-h-0">
                    <ul className="space-y-1.5 pr-1">
                      {tier.features.map((feature, index) => (
                        <li key={index} className="flex items-start gap-1.5">
                          <Check className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-green-500" />
                          <span className="text-xs">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>

                <CardFooter className="pt-3 pb-4 flex-shrink-0">
                  <Button
                    className={cn(
                      "w-full font-bold transition-all duration-300",
                      isPremium
                        ? "bg-amber-600 hover:bg-amber-700 text-white"
                        : "bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white"
                    )}
                    onClick={() => handleSubscribe(tier)}
                    disabled={loadingTier === tier.tier}
                  >
                    {loadingTier === tier.tier ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        {tier.tier === "lite" && isAnnual ? "Subscribe — Standard" : tier.cta}
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                </CardFooter>
              </Card>
            )
          })}
        </div>

        <div className="max-w-4xl mx-auto mb-16 text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-yellow-500/10 via-amber-500/10 to-yellow-500/10 border border-yellow-500/30">
            <Trophy className="h-12 w-12 text-yellow-400 mx-auto mb-4" />
            <h2 className="text-2xl font-display font-bold mb-4 text-yellow-400">
              Industry benchmarks (April 2026)
            </h2>
            <p className="text-muted-foreground mb-4 max-w-2xl mx-auto font-medium text-foreground/90">
              {BENCHMARK_CLAIM_SHORT}.
            </p>
            <p className="text-muted-foreground mb-6 max-w-2xl mx-auto text-sm">
              Our orchestration combines {MARKETING_FEATURED_ORCHESTRATION_STACK} with consensus voting,
              challenge-refine workflows, and tool integration.
            </p>
          </div>
        </div>

        <div className="max-w-3xl mx-auto mb-16 p-8 rounded-2xl bg-card/50 border border-border/50">
          <h2 className="text-2xl font-display font-bold text-center mb-6">How it works</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-yellow-400 font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold text-yellow-400">Choose Standard or Premium</h3>
                <p className="text-sm text-muted-foreground">
                  Standard ($10/mo) and Premium ($20/mo) use elite orchestration while the spend guard allows,
                  then switch to free orchestration.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-emerald-400 font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold text-emerald-400">Spend guard protection</h3>
                <p className="text-sm text-muted-foreground">
                  Provider spend is capped against subscription revenue. When that cap is reached, the account
                  uses free orchestration until the next billing period.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[var(--bronze)]/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[var(--bronze)] font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold">Need teams & compliance?</h3>
                <p className="text-sm text-muted-foreground">
                  Enterprise adds per-seat Premium quotas, SSO, and procurement-friendly controls — contact
                  sales for a quote.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-3xl mx-auto mb-16">
          <h2 className="text-2xl font-display font-bold text-center mb-8">Frequently asked questions</h2>
          <div className="space-y-4">
            {pricingFaq.map((item) => (
              <div key={item.question} className="p-6 rounded-lg bg-card/50 border border-border/50">
                <h3 className="font-semibold mb-2">{item.question}</h3>
                <p className="text-muted-foreground text-sm">{item.answer}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-600/10 to-amber-500/10 border border-amber-600/40">
            <Trophy className="h-10 w-10 text-amber-500 mx-auto mb-4" />
            <h2 className="text-3xl font-display font-bold mb-4 text-amber-500">Ready to subscribe?</h2>
            <p className="text-muted-foreground mb-6 max-w-xl mx-auto">
              Premium: $20/mo or $200/yr — elite orchestration while the spend guard allows.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Button
                size="lg"
                className="bg-amber-600 hover:bg-amber-700 text-white font-bold text-lg px-8"
                onClick={() => handleSubscribe(pricingTiers[1])}
              >
                <Trophy className="h-5 w-5 mr-2" />
                Get Premium — $20/mo
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="border-white/20 text-muted-foreground hover:bg-white/5"
              >
                <Link href="/sign-up">Create account</Link>
              </Button>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-border/50 mt-24 py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>© 2026 LLMHive. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
