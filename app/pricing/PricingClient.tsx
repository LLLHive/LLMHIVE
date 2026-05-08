"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import { useUser, useClerk } from "@clerk/nextjs"
import {
  Check,
  Building2,
  ArrowRight,
  Loader2,
  Home,
  Crown,
  Star,
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
import { BENCHMARK_CLAIM_BANNER, BENCHMARK_CLAIM_SHORT } from "@/lib/benchmark-claim"
import {
  OFFER_ENTERPRISE_FEATURES,
  OFFER_PREMIUM_FEATURES,
  OFFER_STANDARD_FEATURES,
} from "@/lib/marketing/pricing-offers"
import { cn } from "@/lib/utils"
import Link from "next/link"

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
    cta: "Subscribe — Standard",
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
      {
        "@type": "Organization",
        name: "LLMHive",
        url: "https://llmhive.ai",
        logo: "https://llmhive.ai/logo.png",
      },
      {
        "@type": "Product",
        name: "LLMHive",
        description:
          "Multi-model AI orchestration platform that routes every request to the best model for accuracy, speed, and cost.",
        brand: "LLMHive",
        offers: pricingTiers.map((tier) => ({
          "@type": "Offer",
          name: tier.name,
          priceCurrency: "USD",
          price: tier.monthlyPrice,
          url: `https://llmhive.ai/pricing#${tier.tier}`,
          availability: "https://schema.org/InStock",
        })),
      },
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
  const { openSignIn } = useClerk()
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
      openSignIn({
        redirectUrl: `/pricing?subscribe=${tier.tier}&cycle=${isAnnual ? "annual" : "monthly"}`,
      })
      return
    }

    await startCheckout(tier, isAnnual ? "annual" : "monthly")
  }

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
    <div className="min-h-screen bg-background">
      {renderPricingStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="LLMHive" className="h-8 w-8" />
            <span className="font-display text-xl font-bold text-[var(--bronze)]">LLMHive</span>
          </Link>
          <div className="flex items-center gap-4">
            {!isLoaded ? (
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            ) : isSignedIn ? (
              <Link href="/">
                <Button className="bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white">
                  <Home className="h-4 w-4 mr-2" />
                  Go to App
                </Button>
              </Link>
            ) : (
              <>
                <Link href="/sign-in">
                  <Button variant="ghost">Sign In</Button>
                </Link>
                <Link href="/sign-up">
                  <Button className="bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white">
                    Get Started
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12">
        {searchParams.get("payment_required") === "1" && (
          <div
            role="alert"
            className={
              searchParams.get("reason") === "past_due"
                ? "max-w-3xl mx-auto mb-8 rounded-xl border border-red-500/60 bg-red-500/10 px-5 py-4 text-sm text-red-100"
                : "max-w-3xl mx-auto mb-8 rounded-xl border border-amber-500/60 bg-amber-500/10 px-5 py-4 text-sm text-amber-100"
            }
          >
            {searchParams.get("reason") === "past_due" ? (
              <>
                <strong className="font-semibold">Your last renewal payment failed.</strong>{" "}
                Update your payment method to restore access. We&apos;ll resume immediately
                once the new charge succeeds.
              </>
            ) : (
              <>
                <strong className="font-semibold">Subscription required.</strong>{" "}
                Pick a plan below to start using LLMHive — you&apos;ll be redirected to
                Stripe to complete checkout.
              </>
            )}
          </div>
        )}

        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-yellow-500/30 via-amber-500/30 to-yellow-500/30 border-2 border-yellow-400 shadow-lg shadow-yellow-500/20 mb-6">
            <Trophy className="h-10 w-10 text-yellow-400" />
            <div className="text-left">
              <div className="text-2xl md:text-3xl font-black bg-gradient-to-r from-yellow-300 via-amber-400 to-yellow-300 bg-clip-text text-transparent">
                {BENCHMARK_CLAIM_BANNER}
              </div>
              <div className="text-sm md:text-base text-yellow-200/80 font-medium">
                GPQA Diamond, SWE-Bench, AIME 2024, MMMLU & more
              </div>
            </div>
          </div>
        </div>

        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            Premium quality from <span className="text-yellow-400">$20/mo</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-4">
            <span className="text-yellow-400 font-bold">Premium</span> uses{" "}
            <span className="text-yellow-400 font-bold">elite orchestration</span> with{" "}
            <span className="text-yellow-400 font-bold">{BENCHMARK_CLAIM_SHORT}</span> — powered by GPT-5.2,
            Claude Opus 4.5 & Gemini 3 Pro.
          </p>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            <span className="font-semibold text-[var(--bronze)]">Standard</span> and{" "}
            <span className="font-semibold text-yellow-400">Premium</span> use elite orchestration while the
            spend guard allows, then switch to free orchestration for margin protection.
          </p>
        </div>

        <div className="max-w-4xl mx-auto mb-10 p-6 rounded-xl bg-gradient-to-r from-yellow-500/20 via-amber-500/20 to-yellow-500/20 border-2 border-yellow-500/50">
          <div className="grid md:grid-cols-2 gap-6 text-center">
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <div className="text-3xl font-black text-yellow-400 mb-2">Premium</div>
              <div className="text-lg font-bold text-yellow-300">{BENCHMARK_CLAIM_SHORT}</div>
              <div className="text-sm text-yellow-200/70 mt-1">GPT-5.2 + Claude Opus 4.5 + Gemini 3 Pro</div>
            </div>
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <div className="text-3xl font-black text-[var(--bronze)] mb-2">Standard</div>
              <div className="text-lg font-bold text-zinc-200">Standard orchestration</div>
              <div className="text-sm text-muted-foreground mt-1">90-day memory with spend-guarded elite access</div>
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
                    <div className="flex items-baseline gap-1">
                      <span className="font-bold text-3xl">${price.toFixed(2)}</span>
                      <span className="text-sm text-muted-foreground">{period}</span>
                    </div>
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
                        {tier.cta}
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
              Our orchestration combines GPT-5.2, Claude Opus 4.5, and Gemini 3 Pro with consensus voting,
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
              <Link href="/sign-up">
                <Button size="lg" variant="outline" className="border-white/20 text-muted-foreground hover:bg-white/5">
                  Create account
                </Button>
              </Link>
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
