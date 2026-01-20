"use client"

import { useState } from "react"
import { useUser, useClerk } from "@clerk/nextjs"
import { Check, Zap, Building2, Sparkles, ArrowRight, Loader2, Home, Crown, Users, Rocket, Star } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import Link from "next/link"

interface PricingTier {
  name: string
  description: string
  monthlyPrice: number
  annualPrice: number
  features: string[]
  quotas: {
    eliteQueries: string
    afterQuota: string
    totalQueries: string
  }
  popular?: boolean
  cta: string
  tier: "free" | "lite" | "pro" | "team" | "enterprise" | "enterprise_plus" | "maximum"
  badge?: string
  icon: React.ReactNode
}

const pricingTiers: PricingTier[] = [
  {
    name: "Free Trial",
    description: "Experience #1 AI quality free",
    monthlyPrice: 0,
    annualPrice: 0,
    tier: "free",
    icon: <Sparkles className="h-5 w-5 text-muted-foreground" />,
    quotas: {
      eliteQueries: "50 ELITE",
      afterQuota: "Trial ends",
      totalQueries: "50 total",
    },
    features: [
      "50 ELITE queries (best quality)",
      "#1 ranking in ALL 10 categories",
      "Basic orchestration",
      "Session memory",
      "Calculator & Reranker tools",
      "Community support",
    ],
    cta: "Start Free",
  },
  {
    name: "Lite",
    description: "#1 quality at just $9.99/month",
    monthlyPrice: 9.99,
    annualPrice: 99.99,
    tier: "lite",
    icon: <Zap className="h-5 w-5 text-blue-500" />,
    quotas: {
      eliteQueries: "100 ELITE",
      afterQuota: "400 BUDGET",
      totalQueries: "500 total",
    },
    features: [
      "100 ELITE queries (#1 in ALL)",
      "400 BUDGET queries (#1 in 6)",
      "Knowledge Base access",
      "Persistent memory (7 days)",
      "Consensus voting",
      "Email support",
    ],
    cta: "Get Lite",
  },
  {
    name: "Pro",
    description: "Power user with API access",
    monthlyPrice: 29.99,
    annualPrice: 299.99,
    tier: "pro",
    popular: true,
    icon: <Zap className="h-5 w-5 text-[var(--bronze)]" />,
    badge: "Most Popular",
    quotas: {
      eliteQueries: "400 ELITE",
      afterQuota: "600 STANDARD",
      totalQueries: "1,000 total",
    },
    features: [
      "400 ELITE queries (#1 in ALL)",
      "600 STANDARD queries (#1 in 8)",
      "Full API access",
      "DeepConf debate system",
      "Prompt Diffusion",
      "Web research",
      "30-day memory",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
  },
  {
    name: "Team",
    description: "Collaborative workspace for teams",
    monthlyPrice: 49.99,
    annualPrice: 499.99,
    tier: "team",
    icon: <Users className="h-5 w-5 text-purple-500" />,
    quotas: {
      eliteQueries: "500 ELITE pooled",
      afterQuota: "1,500 STANDARD",
      totalQueries: "2,000 total",
    },
    features: [
      "500 ELITE pooled for team",
      "1,500 STANDARD queries",
      "3 team members included",
      "Shared team workspace",
      "Team projects & memory",
      "Admin dashboard",
      "90-day memory retention",
    ],
    cta: "Get Team",
  },
  {
    name: "Enterprise",
    description: "For organizations with compliance needs",
    monthlyPrice: 25,
    annualPrice: 250,
    tier: "enterprise",
    icon: <Building2 className="h-5 w-5 text-emerald-500" />,
    badge: "Per Seat",
    quotas: {
      eliteQueries: "300 ELITE/seat",
      afterQuota: "200 STANDARD",
      totalQueries: "500/seat",
    },
    features: [
      "300 ELITE per seat/month",
      "SSO / SAML authentication",
      "SOC 2 compliance",
      "Audit logs",
      "99.5% SLA guarantee",
      "1-year memory retention",
      "Priority queue",
    ],
    cta: "Contact Sales",
  },
  {
    name: "Enterprise+",
    description: "Custom policies & dedicated support",
    monthlyPrice: 45,
    annualPrice: 450,
    tier: "enterprise_plus",
    icon: <Star className="h-5 w-5 text-yellow-500" />,
    badge: "Per Seat",
    quotas: {
      eliteQueries: "800 ELITE/seat",
      afterQuota: "700 STANDARD",
      totalQueries: "1,500/seat",
    },
    features: [
      "800 ELITE per seat/month",
      "Custom routing policies",
      "Dedicated support manager",
      "99.9% SLA guarantee",
      "Custom integrations",
      "Webhooks",
      "Unlimited memory",
    ],
    cta: "Contact Sales",
  },
  {
    name: "Maximum",
    description: "BEATS competition by +5%",
    monthlyPrice: 499,
    annualPrice: 4990,
    tier: "maximum",
    icon: <Crown className="h-5 w-5 text-amber-500" />,
    badge: "Mission Critical",
    quotas: {
      eliteQueries: "200 MAXIMUM + 500 ELITE",
      afterQuota: "Never throttled",
      totalQueries: "700 total",
    },
    features: [
      "200 MAXIMUM queries (beats GPT-5.2!)",
      "500 ELITE queries (#1 in ALL)",
      "5-model consensus",
      "Verification loops",
      "Reflection chains",
      "All Enterprise+ features",
      "Mission-critical support",
    ],
    cta: "Get Maximum Power",
  },
]

export default function PricingPage() {
  const { isSignedIn, isLoaded } = useUser()
  const { openSignIn } = useClerk()
  const [isAnnual, setIsAnnual] = useState(false)
  const [loadingTier, setLoadingTier] = useState<string | null>(null)

  const handleSubscribe = async (tier: PricingTier) => {
    if (tier.tier === "free") {
      if (isSignedIn) {
        window.location.href = "/"
      } else {
        window.location.href = "/sign-up"
      }
      return
    }

    // Enterprise tiers go to contact
    if (tier.tier === "enterprise" || tier.tier === "enterprise_plus") {
      window.location.href = "mailto:sales@llmhive.ai?subject=Enterprise Inquiry"
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

  // Split tiers for display - main 4 + enterprise section
  const mainTiers = pricingTiers.slice(0, 4)
  const enterpriseTiers = pricingTiers.slice(4)

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
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

      <main className="container mx-auto px-4 py-16">
        {/* Hero */}
        <div className="text-center mb-16">
          <Badge className="mb-4 bg-green-500/10 text-green-500 border-green-500/20">
            <Crown className="h-3 w-3 mr-1" />
            #1 in ALL 10 AI Categories
          </Badge>
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            All Tiers Get #1 Quality
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Every paid plan starts with ELITE orchestration — #1 ranking in all categories.
            Differs only by quota. When ELITE runs out, you're throttled to still-great quality.
          </p>
        </div>

        {/* Quality Explanation */}
        <div className="max-w-4xl mx-auto mb-12 p-6 rounded-xl bg-gradient-to-r from-[var(--bronze)]/10 to-purple-500/10 border border-[var(--bronze)]/20">
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-2xl font-bold text-green-500 mb-1">🟢 ELITE</div>
              <div className="text-sm font-medium">#1 in ALL 10 Categories</div>
              <div className="text-xs text-muted-foreground mt-1">3-model consensus, best quality</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-500 mb-1">🟡 STANDARD</div>
              <div className="text-sm font-medium">#1 in 8 Categories</div>
              <div className="text-xs text-muted-foreground mt-1">Mixed routing, great quality</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-500 mb-1">🟠 BUDGET</div>
              <div className="text-sm font-medium">#1 in 6 Categories</div>
              <div className="text-xs text-muted-foreground mt-1">Claude Sonnet, good quality</div>
            </div>
          </div>
        </div>

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-4 mb-12">
          <Label htmlFor="billing-toggle" className={cn(!isAnnual && "text-foreground", isAnnual && "text-muted-foreground")}>
            Monthly
          </Label>
          <Switch
            id="billing-toggle"
            checked={isAnnual}
            onCheckedChange={setIsAnnual}
            className="data-[state=checked]:bg-[var(--bronze)]"
          />
          <Label htmlFor="billing-toggle" className={cn(isAnnual && "text-foreground", !isAnnual && "text-muted-foreground")}>
            Annual
          </Label>
          {isAnnual && (
            <Badge variant="secondary" className="bg-green-500/10 text-green-500 border-green-500/20">
              Save 17%
            </Badge>
          )}
        </div>

        {/* Main Pricing Cards (Free, Lite, Pro, Team) */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto mb-16">
          {mainTiers.map((tier) => {
            const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
            const period = isAnnual ? "/year" : "/month"

            return (
              <Card
                key={tier.name}
                className={cn(
                  "group relative flex flex-col bg-card/50 backdrop-blur-sm transition-all duration-300",
                  "h-[580px]",
                  tier.popular 
                    ? "border-2 border-[var(--bronze)] shadow-lg shadow-[var(--bronze)]/10" 
                    : "border-2 border-[var(--bronze)]/30 hover:border-[var(--bronze)]"
                )}
              >
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className="bg-[var(--bronze)] text-white border-0 px-4 py-1">
                      <Zap className="h-3 w-3 mr-1" />
                      {tier.badge}
                    </Badge>
                  </div>
                )}

                <CardHeader className="pb-2 flex-shrink-0">
                  <div className="flex items-center gap-2 mb-1">
                    {tier.icon}
                    <CardTitle className="text-xl">{tier.name}</CardTitle>
                  </div>
                  <CardDescription className="text-xs">{tier.description}</CardDescription>
                </CardHeader>

                <CardContent className="flex-1 overflow-hidden flex flex-col py-2">
                  {/* Price */}
                  <div className="mb-4 flex-shrink-0">
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold">
                        {price === 0 ? "Free" : `$${price.toFixed(2)}`}
                      </span>
                      {price > 0 && (
                        <span className="text-muted-foreground text-sm">{period}</span>
                      )}
                    </div>
                  </div>

                  {/* Quotas */}
                  <div className="mb-4 p-3 rounded-lg bg-muted/30 flex-shrink-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-green-500 font-semibold text-sm">🟢 {tier.quotas.eliteQueries}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Then: {tier.quotas.afterQuota}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {tier.quotas.totalQueries}
                    </div>
                  </div>

                  {/* Features - scrollable */}
                  <div className="flex-1 overflow-y-auto min-h-0">
                    <ul className="space-y-1.5 pr-1">
                      {tier.features.map((feature, index) => (
                        <li key={index} className="flex items-start gap-1.5">
                          <Check className="h-3.5 w-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                          <span className="text-xs">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>

                <CardFooter className="pt-3 pb-4 flex-shrink-0">
                  <Button
                    className={cn(
                      "w-full font-semibold transition-all duration-300",
                      tier.popular
                        ? "bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white"
                        : "bg-[var(--bronze)]/50 group-hover:bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white"
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

        {/* Enterprise & Maximum Section */}
        <div className="mb-16">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-display font-bold mb-2">Enterprise & Maximum Power</h2>
            <p className="text-muted-foreground">For organizations and mission-critical applications</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {enterpriseTiers.map((tier) => {
              const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
              const period = isAnnual ? "/year" : "/month"

              return (
                <Card
                  key={tier.name}
                  className={cn(
                    "group relative flex flex-col bg-card/50 backdrop-blur-sm transition-all duration-300",
                    tier.tier === "maximum" 
                      ? "border-2 border-amber-500 shadow-lg shadow-amber-500/10"
                      : "border-2 border-[var(--bronze)]/30 hover:border-[var(--bronze)]"
                  )}
                >
                  {tier.badge && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className={cn(
                        "border-0 px-3 py-0.5 text-xs",
                        tier.tier === "maximum" 
                          ? "bg-amber-500 text-black"
                          : "bg-emerald-500/80 text-white"
                      )}>
                        {tier.badge}
                      </Badge>
                    </div>
                  )}

                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2 mb-1">
                      {tier.icon}
                      <CardTitle className="text-lg">{tier.name}</CardTitle>
                    </div>
                    <CardDescription className="text-xs">{tier.description}</CardDescription>
                  </CardHeader>

                  <CardContent className="flex-1 py-2">
                    {/* Price */}
                    <div className="mb-3">
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold">${price.toFixed(2)}</span>
                        <span className="text-muted-foreground text-xs">{period}</span>
                      </div>
                    </div>

                    {/* Quotas */}
                    <div className="mb-3 p-2 rounded-lg bg-muted/30 text-xs">
                      <div className="text-green-500 font-semibold mb-1">🟢 {tier.quotas.eliteQueries}</div>
                      <div className="text-muted-foreground">Then: {tier.quotas.afterQuota}</div>
                    </div>

                    {/* Features */}
                    <ul className="space-y-1">
                      {tier.features.slice(0, 5).map((feature, index) => (
                        <li key={index} className="flex items-start gap-1.5">
                          <Check className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                          <span className="text-xs">{feature}</span>
                        </li>
                      ))}
                      {tier.features.length > 5 && (
                        <li className="text-xs text-muted-foreground pl-4">
                          +{tier.features.length - 5} more features
                        </li>
                      )}
                    </ul>
                  </CardContent>

                  <CardFooter className="pt-2 pb-4">
                    <Button
                      className={cn(
                        "w-full text-sm",
                        tier.tier === "maximum"
                          ? "bg-amber-500 hover:bg-amber-600 text-black font-semibold"
                          : "bg-[var(--bronze)]/50 hover:bg-[var(--bronze)] text-white"
                      )}
                      onClick={() => handleSubscribe(tier)}
                      disabled={loadingTier === tier.tier}
                    >
                      {loadingTier === tier.tier ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          {tier.cta}
                          <ArrowRight className="h-4 w-4 ml-1" />
                        </>
                      )}
                    </Button>
                  </CardFooter>
                </Card>
              )
            })}
          </div>
        </div>

        {/* How Quota Works */}
        <div className="max-w-3xl mx-auto mb-16 p-8 rounded-2xl bg-card/50 border border-border/50">
          <h2 className="text-2xl font-display font-bold text-center mb-6">
            How Quota Works
          </h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-green-500 font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold">Start with ELITE quality</h3>
                <p className="text-sm text-muted-foreground">
                  Every query uses ELITE orchestration (#1 in ALL 10 categories) until your quota runs out.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-yellow-500 font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold">See your remaining quota</h3>
                <p className="text-sm text-muted-foreground">
                  Dashboard shows "ELITE queries remaining: 45/100" with warnings at 20%.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-orange-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-orange-500 font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold">Throttle to still-great quality</h3>
                <p className="text-sm text-muted-foreground">
                  When ELITE runs out, you automatically switch to STANDARD or BUDGET (still excellent!). 
                  Or upgrade anytime for more ELITE queries.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What's the difference between ELITE, STANDARD, and BUDGET?</h3>
              <p className="text-muted-foreground text-sm">
                All three deliver excellent quality, but differ in how many AI categories they're #1 in.
                ELITE uses 3-model consensus and ranks #1 in all 10 benchmark categories.
                STANDARD ranks #1 in 8 categories. BUDGET (Claude Sonnet) ranks #1 in 6 categories.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What happens when I run out of ELITE queries?</h3>
              <p className="text-muted-foreground text-sm">
                You're automatically throttled to STANDARD or BUDGET (depending on your plan) for the rest of the month.
                You still get great quality! You can also upgrade mid-month for more ELITE queries.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">Can I see how many ELITE queries I have left?</h3>
              <p className="text-muted-foreground text-sm">
                Yes! Your dashboard shows exactly how many ELITE queries remain. We also send warnings at 20% remaining.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What is MAXIMUM tier?</h3>
              <p className="text-muted-foreground text-sm">
                MAXIMUM uses 5-model consensus with GPT-5.2 + o3 + Claude Opus to actually BEAT competition by +5%.
                It's for mission-critical applications where you need the absolute best quality, like legal, healthcare, or finance.
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-24 text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-[var(--bronze)]/10 to-purple-500/10 border border-[var(--bronze)]/20">
            <h2 className="text-2xl font-display font-bold mb-4">
              Ready to experience #1 AI quality?
            </h2>
            <p className="text-muted-foreground mb-6">
              Start with 50 free ELITE queries and see the difference for yourself.
            </p>
            <Link href="/sign-up">
              <Button size="lg" className="bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white">
                Start Free Trial
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-24 py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>© 2026 LLMHive. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
