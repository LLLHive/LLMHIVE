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
  tier: "free" | "lite" | "pro" | "enterprise"
  badge?: string
  icon: React.ReactNode
  highlight?: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// 4-TIER PRICING STRUCTURE WITH FREE TIER (January 2026)
// Marketing: "Our patented orchestration makes our FREE tier beat top models"
// ═══════════════════════════════════════════════════════════════════════════════
const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    description: "Forever free - BEATS most paid models",
    monthlyPrice: 0,
    annualPrice: 0,
    tier: "free",
    icon: <Star className="h-5 w-5 text-green-500" />,
    badge: "No Credit Card",
    highlight: "Our patented multi-model orchestration makes FREE outperform most paid models!",
    quotas: {
      eliteQueries: "FREE Orchestration",
      afterQuota: "Always free models",
      totalQueries: "50 queries/month",
    },
    features: [
      "BEATS most single model performance",
      "Patented multi-model orchestration",
      "Knowledge Base access",
      "Calculator & Reranker tools",
      "3-day memory retention",
      "Community support",
    ],
    cta: "Get Started Free",
  },
  {
    name: "Lite",
    description: "Unlock #1 quality AI performance",
    monthlyPrice: 14.99,
    annualPrice: 149.99,
    tier: "lite",
    icon: <Zap className="h-5 w-5 text-blue-500" />,
    quotas: {
      eliteQueries: "100 ELITE",
      afterQuota: "→ FREE tier",
      totalQueries: "500 total",
    },
    features: [
      "100 ELITE queries (#1 in ALL categories)",
      "400 more queries (throttled to FREE)",
      "Knowledge Base access",
      "7-day memory retention",
      "Consensus voting",
      "Calculator & Reranker tools",
      "Email support",
    ],
    cta: "Upgrade to Lite",
  },
  {
    name: "Pro",
    description: "Full power for professionals",
    monthlyPrice: 29.99,
    annualPrice: 299.99,
    tier: "pro",
    popular: true,
    icon: <Rocket className="h-5 w-5 text-[var(--bronze)]" />,
    badge: "Most Popular",
    quotas: {
      eliteQueries: "500 ELITE",
      afterQuota: "→ FREE tier",
      totalQueries: "2,000 total",
    },
    features: [
      "500 ELITE queries (#1 in ALL)",
      "1,500 more queries (throttled to FREE)",
      "Full API access",
      "All advanced features",
      "DeepConf debate system",
      "Prompt Diffusion",
      "Web research & fact-checking",
      "30-day memory retention",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
  },
  {
    name: "Enterprise",
    description: "For organizations with compliance needs",
    monthlyPrice: 35,
    annualPrice: 350,
    tier: "enterprise",
    icon: <Building2 className="h-5 w-5 text-emerald-500" />,
    badge: "Min 5 Seats",
    quotas: {
      eliteQueries: "400 ELITE/seat",
      afterQuota: "→ FREE tier/seat",
      totalQueries: "800/seat",
    },
    features: [
      "Minimum 5 seats ($175+/mo)",
      "400 ELITE per seat/month",
      "SSO / SAML authentication",
      "SOC 2 Type II compliance",
      "Audit logs & admin dashboard",
      "99.5% SLA guarantee",
      "1-year memory retention",
      "Team workspace & projects",
      "Dedicated support manager",
    ],
    cta: "Contact Sales",
  },
]

export default function PricingPage() {
  const { isSignedIn, isLoaded } = useUser()
  const { openSignIn } = useClerk()
  const [isAnnual, setIsAnnual] = useState(false)
  const [loadingTier, setLoadingTier] = useState<string | null>(null)

  const handleSubscribe = async (tier: PricingTier) => {
    // FREE tier just needs sign-up
    if (tier.tier === "free") {
      if (!isSignedIn) {
        openSignIn({
          redirectUrl: "/",
        })
      } else {
        window.location.href = "/"
      }
      return
    }

    // Enterprise goes to contact sales
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

  // Split tiers for display - 4 tiers (Free, Lite, Pro, Enterprise)
  const mainTiers = pricingTiers.slice(0, 4)
  const enterpriseTiers: PricingTier[] = [] // Enterprise is now in main tiers

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
        {/* Hero - Updated Messaging for FREE Tier */}
        <div className="text-center mb-16">
          <Badge className="mb-4 bg-green-500/10 text-green-500 border-green-500/20">
            <Crown className="h-3 w-3 mr-1" />
            Patented Orchestration Technology
          </Badge>
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            Our FREE Tier Beats Most Paid Models
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-6">
            Because of our advanced patented orchestration of several models, 
            our free tier delivers performance that surpasses most single paid models.
          </p>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Upgrade to Lite for $14.99/mo to unlock <span className="text-green-500 font-semibold">#1 quality in ALL 10 categories</span> — 
            or try our powerful FREE tier forever at no cost.
          </p>
        </div>

        {/* Quality Explanation - Updated for FREE Tier */}
        <div className="max-w-4xl mx-auto mb-12 p-6 rounded-xl bg-gradient-to-r from-green-500/10 via-[var(--bronze)]/10 to-purple-500/10 border border-green-500/20">
          <div className="grid md:grid-cols-2 gap-6 text-center">
            <div>
              <div className="text-2xl font-bold text-green-500 mb-1">🆓 FREE Orchestration</div>
              <div className="text-sm font-medium">BEATS Most Paid Models</div>
              <div className="text-xs text-muted-foreground mt-1">Patented AI ensemble technology at $0</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-[var(--bronze)] mb-1">🟢 ELITE Orchestration</div>
              <div className="text-sm font-medium">#1 in ALL 10 Categories</div>
              <div className="text-xs text-muted-foreground mt-1">GPT-5, Claude 4.5 & Gemini 3 unified</div>
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

        {/* Main Pricing Cards (Free, Lite, Pro, Enterprise) */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 max-w-6xl mx-auto mb-16">
          {mainTiers.map((tier) => {
            const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
            const period = isAnnual ? "/year" : "/month"

            return (
              <Card
                key={tier.name}
                className={cn(
                  "group relative flex flex-col bg-card/50 backdrop-blur-sm transition-all duration-300",
                  "h-[580px]",
                  tier.tier === "free"
                    ? "border-2 border-green-500 shadow-lg shadow-green-500/10"
                    : tier.popular 
                    ? "border-2 border-[var(--bronze)] shadow-lg shadow-[var(--bronze)]/10" 
                    : "border-2 border-[var(--bronze)]/30 hover:border-[var(--bronze)]"
                )}
              >
                {(tier.popular || tier.badge) && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className={cn(
                      "border-0 px-4 py-1",
                      tier.tier === "free" ? "bg-green-500 text-white" :
                      "bg-[var(--bronze)] text-white"
                    )}>
                      {tier.tier === "free" ? <Star className="h-3 w-3 mr-1" /> : <Zap className="h-3 w-3 mr-1" />}
                      {tier.badge || "Most Popular"}
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
                      tier.tier === "free"
                        ? "bg-green-500 hover:bg-green-600 text-white"
                        : tier.popular
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


        {/* How It Works */}
        <div className="max-w-3xl mx-auto mb-16 p-8 rounded-2xl bg-card/50 border border-border/50">
          <h2 className="text-2xl font-display font-bold text-center mb-6">
            How Our Pricing Works
          </h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-green-500 font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold">Start FREE - Beat most paid models</h3>
                <p className="text-sm text-muted-foreground">
                  Our patented multi-model orchestration makes even our FREE tier outperform most single paid models. 
                  No credit card required, 50 queries/month.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[var(--bronze)]/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[var(--bronze)] font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold">Upgrade for #1 quality in ALL categories</h3>
                <p className="text-sm text-muted-foreground">
                  For just $14.99/mo (Lite), unlock ELITE orchestration — ranked #1 in ALL 10 AI benchmark categories.
                  100 ELITE queries, then throttle back to FREE tier.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-amber-500 font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold">Scale up for more power</h3>
                <p className="text-sm text-muted-foreground">
                  Pro ($29.99/mo) gives you 500 ELITE queries + full API access. 
                  Enterprise ($35/seat) for teams with compliance needs.
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
              <h3 className="font-semibold mb-2">How does the FREE tier beat paid models?</h3>
              <p className="text-muted-foreground text-sm">
                Our patented multi-model orchestration combines 3 free models in consensus, plus our Calculator 
                and Pinecone Reranker tools. This ensemble approach outperforms most single paid models 
                while costing us $0 per query — savings we pass to you!
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What happens when I run out of ELITE queries?</h3>
              <p className="text-muted-foreground text-sm">
                You're automatically throttled to our FREE tier orchestration. You'll see a notification 
                offering to upgrade. The FREE tier still beats most single models, so you continue 
                getting great quality — just not #1 in all categories.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What's the difference between FREE and ELITE?</h3>
              <p className="text-muted-foreground text-sm">
                FREE uses only free models from OpenRouter in a 3-model consensus — excellent quality at $0.
                ELITE uses premium models (GPT-5, Claude Opus, Gemini Pro) to rank #1 in ALL 10 benchmark categories.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">Can I upgrade or downgrade anytime?</h3>
              <p className="text-muted-foreground text-sm">
                Yes! You can upgrade to unlock more ELITE queries anytime, or downgrade if needed. 
                Your billing will be prorated automatically. You always keep access to our FREE tier.
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-24 text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-green-500/10 via-[var(--bronze)]/10 to-purple-500/10 border border-green-500/20">
            <h2 className="text-2xl font-display font-bold mb-4">
              Start FREE — No Credit Card Required
            </h2>
            <p className="text-muted-foreground mb-6">
              Our FREE tier beats most paid models. Experience the power of patented orchestration at no cost.
              Upgrade anytime for #1 quality in ALL categories.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link href="/sign-up">
                <Button size="lg" className="bg-green-500 hover:bg-green-600 text-white">
                  Get Started Free
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
              <Link href="/sign-up">
                <Button size="lg" variant="outline" className="border-[var(--bronze)] text-[var(--bronze)] hover:bg-[var(--bronze)]/10">
                  See All Plans
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            </div>
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
