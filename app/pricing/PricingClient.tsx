"use client"

import { useState } from "react"
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
      afterQuota: "Unlimited included",
      detail: "Powered by our Standard routing — strong quality vs. single-model apps",
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
      headline: "500 Premium queries / month",
      afterQuota: "Then unlimited Standard",
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
      "Standard is $10/month and includes unlimited Standard orchestration — multi-model routing tuned for cost and quality for everyday tasks.",
  },
  {
    question: "What is Premium?",
    answer:
      "Premium is $20/month and includes 500 Premium queries per month using our top orchestration stack, then unlimited Standard orchestration after the quota.",
  },
  {
    question: "What happens after I use my Premium queries?",
    answer:
      "LLMHive switches you to unlimited Standard orchestration for the rest of the billing period — no hard stop.",
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
  const { isSignedIn, isLoaded } = useUser()
  const { openSignIn } = useClerk()
  const [isAnnual, setIsAnnual] = useState(false)
  const [loadingTier, setLoadingTier] = useState<string | null>(null)

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

    setLoadingTier(tier.tier)
    try {
      const response = await fetch("/api/billing/create-checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tier: tier.tier,
          billingCycle: isAnnual ? "annual" : "monthly",
        }),
      })

      const data = await response.json()

      if (data.url) {
        window.location.href = data.url
      } else {
        console.error("Failed to create checkout session:", data.error)
        alert(`Failed to create checkout: ${data.error || "Unknown error"}`)
      }
    } catch (error) {
      console.error("Error creating checkout session:", error)
      alert(`An error occurred: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setLoadingTier(null)
    }
  }

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
            <span className="text-yellow-400 font-bold">Premium</span> includes{" "}
            <span className="text-yellow-400 font-bold">500 Premium queries</span> with{" "}
            <span className="text-yellow-400 font-bold">{BENCHMARK_CLAIM_SHORT}</span> — powered by GPT-5.2,
            Claude Opus 4.5 & Gemini 3 Pro.
          </p>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            <span className="font-semibold text-[var(--bronze)]">Standard</span> at $10/mo is unlimited{" "}
            <strong>Standard orchestration</strong>. After Premium quota, Premium subscribers get{" "}
            <span className="font-semibold text-emerald-400">unlimited Standard</span> for the rest of the
            period.
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
              <div className="text-sm text-muted-foreground mt-1">Unlimited on the Standard plan; included after Premium quota on Premium</div>
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
                  Standard ($10/mo) is unlimited Standard orchestration. Premium ($20/mo) adds 500 Premium
                  queries with {BENCHMARK_CLAIM_SHORT}, then unlimited Standard.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-emerald-400 font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold text-emerald-400">After Premium quota</h3>
                <p className="text-sm text-muted-foreground">
                  Premium subscribers keep working on unlimited Standard orchestration until the next billing
                  cycle resets Premium queries.
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
              Premium: $20/mo or $200/yr — 500 Premium queries, then unlimited Standard.
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
