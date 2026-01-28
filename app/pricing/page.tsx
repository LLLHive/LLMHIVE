"use client"

import { useState } from "react"
import { useUser, useClerk } from "@clerk/nextjs"
import { Check, Zap, Building2, Sparkles, ArrowRight, Loader2, Home, Crown, Users, Rocket, Star, Trophy } from "lucide-react"
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
// 4-TIER PRICING - PRO IS THE HERO (January 2026)
// Sales Psychology: Pro should pop, Free should be an entry point only
// ═══════════════════════════════════════════════════════════════════════════════
const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    description: "Try our orchestration technology",
    monthlyPrice: 0,
    annualPrice: 0,
    tier: "free",
    icon: <Star className="h-5 w-5 text-muted-foreground" />,
    quotas: {
      eliteQueries: "FREE Orchestration",
      afterQuota: "50 queries/month",
      totalQueries: "Basic features",
    },
    features: [
      "Multi-model orchestration",
      "Beats most single models",
      "Knowledge Base access",
      "Calculator & Reranker",
      "3-day memory",
      "Community support",
    ],
    cta: "Start Free",
  },
  {
    name: "Lite",
    description: "Unlock #1 AI quality",
    monthlyPrice: 14.99,
    annualPrice: 149.99,
    tier: "lite",
    icon: <Zap className="h-5 w-5 text-blue-400" />,
    quotas: {
      eliteQueries: "100 ELITE queries",
      afterQuota: "Then UNLIMITED FREE",
      totalQueries: "#1 in ALL categories",
    },
    features: [
      "100 ELITE queries/month",
      "Then UNLIMITED FREE queries",
      "#1 quality when using ELITE",
      "Knowledge Base access",
      "7-day memory retention",
      "Consensus voting",
      "Email support",
    ],
    cta: "Get Lite",
  },
  {
    name: "Pro",
    description: "Maximum power for professionals",
    monthlyPrice: 29.99,
    annualPrice: 299.99,
    tier: "pro",
    popular: true,
    icon: <Rocket className="h-5 w-5 text-yellow-400" />,
    badge: "BEST VALUE",
    quotas: {
      eliteQueries: "500 ELITE queries",
      afterQuota: "Then UNLIMITED FREE",
      totalQueries: "#1 in ALL + Full API",
    },
    features: [
      "500 ELITE queries/month",
      "Then UNLIMITED FREE queries",
      "#1 quality when using ELITE",
      "Full API access",
      "DeepConf debate system",
      "Prompt Diffusion",
      "Web research & fact-checking",
      "30-day memory retention",
      "Priority support",
    ],
    cta: "Get Pro — Best Value",
  },
  {
    name: "Enterprise",
    description: "Teams & compliance",
    monthlyPrice: 35,
    annualPrice: 350,
    tier: "enterprise",
    icon: <Building2 className="h-5 w-5 text-emerald-400" />,
    badge: "Per Seat",
    quotas: {
      eliteQueries: "400 ELITE/seat",
      afterQuota: "Then UNLIMITED FREE",
      totalQueries: "SSO + Compliance",
    },
    features: [
      "400 ELITE per seat/month",
      "Then UNLIMITED FREE queries",
      "Min 5 seats ($175+/mo)",
      "SSO / SAML authentication",
      "SOC 2 Type II compliance",
      "Audit logs & dashboard",
      "99.5% SLA guarantee",
      "1-year memory retention",
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

  const mainTiers = pricingTiers

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

      <main className="container mx-auto px-4 py-12">
        
        {/* ══════════════════════════════════════════════════════════════════════
            #1 BENCHMARK HERO BADGE - HUGE, YELLOW, PROMINENT
            This is what builds credibility - it MUST pop
        ══════════════════════════════════════════════════════════════════════ */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-yellow-500/30 via-amber-500/30 to-yellow-500/30 border-2 border-yellow-400 shadow-lg shadow-yellow-500/20 mb-6">
            <Trophy className="h-10 w-10 text-yellow-400" />
            <div className="text-left">
              <div className="text-3xl md:text-4xl font-black bg-gradient-to-r from-yellow-300 via-amber-400 to-yellow-300 bg-clip-text text-transparent">
                #1 IN ALL 10 BENCHMARKS
              </div>
              <div className="text-sm md:text-base text-yellow-200/80 font-medium">
                January 2026 Industry Rankings — GPQA Diamond, SWE-Bench, AIME 2024 & more
              </div>
            </div>
          </div>
        </div>

        {/* Hero - SELL PRO, not give away Free */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            The World's Best AI Quality at <span className="text-yellow-400">$29.99/mo</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-4">
            Our Pro plan gives you <span className="text-yellow-400 font-bold">500 ELITE queries</span> ranked 
            <span className="text-yellow-400 font-bold"> #1 in ALL categories</span> — powered by 
            GPT-5.2, Claude Opus 4.5 & Gemini 3 Pro unified.
          </p>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            After your ELITE queries, enjoy <span className="font-semibold text-green-400">UNLIMITED FREE queries</span> — 
            our patented orchestration still beats most single paid models.
          </p>
        </div>

        {/* Quality Explanation Banner - PRO FOCUSED */}
        <div className="max-w-4xl mx-auto mb-10 p-6 rounded-xl bg-gradient-to-r from-yellow-500/20 via-amber-500/20 to-yellow-500/20 border-2 border-yellow-500/50">
          <div className="grid md:grid-cols-2 gap-6 text-center">
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <div className="text-3xl font-black text-yellow-400 mb-2">🏆 ELITE</div>
              <div className="text-lg font-bold text-yellow-300">#1 in ALL 10 Categories</div>
              <div className="text-sm text-yellow-200/70 mt-1">GPT-5.2 + Claude Opus 4.5 + Gemini 3 Pro</div>
            </div>
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <div className="text-3xl font-black text-green-400 mb-2">🆓 FREE</div>
              <div className="text-lg font-bold text-green-300">UNLIMITED After ELITE</div>
              <div className="text-sm text-muted-foreground mt-1">Still beats most single paid models</div>
            </div>
          </div>
        </div>

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-4 mb-10">
          <Label htmlFor="billing-toggle" className={cn(!isAnnual && "text-foreground font-semibold", isAnnual && "text-muted-foreground")}>
            Monthly
          </Label>
          <Switch
            id="billing-toggle"
            checked={isAnnual}
            onCheckedChange={setIsAnnual}
            className="data-[state=checked]:bg-yellow-500"
          />
          <Label htmlFor="billing-toggle" className={cn(isAnnual && "text-foreground font-semibold", !isAnnual && "text-muted-foreground")}>
            Annual
          </Label>
          {isAnnual && (
            <Badge className="bg-yellow-500 text-black font-bold border-0">
              Save 17%
            </Badge>
          )}
        </div>

        {/* ══════════════════════════════════════════════════════════════════════
            PRICING CARDS - PRO IS THE HERO
            - Pro: Biggest, brightest, most prominent
            - Free: Smallest, subtle, entry point only
        ══════════════════════════════════════════════════════════════════════ */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 max-w-7xl mx-auto mb-16">
          {mainTiers.map((tier) => {
            const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
            const period = isAnnual ? "/year" : "/month"
            const isPro = tier.tier === "pro"
            const isFree = tier.tier === "free"

            return (
              <Card
                key={tier.name}
                className={cn(
                  "group relative flex flex-col bg-card/50 backdrop-blur-sm transition-all duration-300",
                  isPro 
                    ? "border-3 border-yellow-400 shadow-2xl shadow-yellow-500/30 scale-105 z-10 h-[620px]" 
                    : isFree
                    ? "border border-white/10 hover:border-white/20 h-[580px] opacity-90"
                    : "border-2 border-[var(--bronze)]/30 hover:border-[var(--bronze)] h-[580px]"
                )}
              >
                {/* Badge - PRO gets huge yellow badge */}
                {tier.badge && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className={cn(
                      "border-0 px-4 py-1.5 font-bold",
                      isPro 
                        ? "bg-yellow-400 text-black text-sm" 
                        : tier.tier === "enterprise"
                        ? "bg-emerald-500 text-white"
                        : "bg-[var(--bronze)] text-white"
                    )}>
                      {isPro && <Trophy className="h-4 w-4 mr-1" />}
                      {tier.badge}
                    </Badge>
                  </div>
                )}

                <CardHeader className="pb-2 flex-shrink-0">
                  <div className="flex items-center gap-2 mb-1">
                    {tier.icon}
                    <CardTitle className={cn(
                      "text-xl",
                      isPro && "text-yellow-400"
                    )}>{tier.name}</CardTitle>
                    {isPro && (
                      <Badge className="bg-yellow-400/20 text-yellow-400 border-yellow-400/30 text-xs">
                        RECOMMENDED
                      </Badge>
                    )}
                  </div>
                  <CardDescription className={cn(
                    "text-xs",
                    isPro && "text-yellow-200/70"
                  )}>{tier.description}</CardDescription>
                </CardHeader>

                <CardContent className="flex-1 overflow-hidden flex flex-col py-2">
                  {/* Price - PRO is bigger */}
                  <div className="mb-4 flex-shrink-0">
                    <div className="flex items-baseline gap-1">
                      <span className={cn(
                        "font-bold",
                        isPro ? "text-4xl text-yellow-400" : "text-3xl"
                      )}>
                        {price === 0 ? "Free" : `$${price.toFixed(2)}`}
                      </span>
                      {price > 0 && (
                        <span className={cn(
                          "text-sm",
                          isPro ? "text-yellow-200/70" : "text-muted-foreground"
                        )}>{period}</span>
                      )}
                    </div>
                  </div>

                  {/* Quotas - Updated messaging */}
                  <div className={cn(
                    "mb-4 p-3 rounded-lg flex-shrink-0",
                    isPro 
                      ? "bg-yellow-500/20 border border-yellow-500/30" 
                      : isFree
                      ? "bg-white/5 border border-white/10"
                      : "bg-muted/30"
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn(
                        "font-bold text-sm",
                        isPro ? "text-yellow-400" : isFree ? "text-green-400" : "text-[var(--bronze)]"
                      )}>
                        {isPro ? "🏆" : isFree ? "🆓" : "⚡"} {tier.quotas.eliteQueries}
                      </span>
                    </div>
                    <div className={cn(
                      "text-xs font-semibold",
                      isFree ? "text-muted-foreground" : "text-green-400"
                    )}>
                      {tier.quotas.afterQuota}
                    </div>
                    <div className={cn(
                      "text-xs mt-1",
                      isPro ? "text-yellow-200/70" : "text-muted-foreground"
                    )}>
                      {tier.quotas.totalQueries}
                    </div>
                  </div>

                  {/* Features */}
                  <div className="flex-1 overflow-y-auto min-h-0">
                    <ul className="space-y-1.5 pr-1">
                      {tier.features.map((feature, index) => (
                        <li key={index} className="flex items-start gap-1.5">
                          <Check className={cn(
                            "h-3.5 w-3.5 mt-0.5 flex-shrink-0",
                            isPro ? "text-yellow-400" : "text-green-500"
                          )} />
                          <span className={cn(
                            "text-xs",
                            isPro && feature.includes("ELITE") && "text-yellow-300 font-semibold"
                          )}>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>

                <CardFooter className="pt-3 pb-4 flex-shrink-0">
                  <Button
                    className={cn(
                      "w-full font-bold transition-all duration-300",
                      isPro
                        ? "bg-yellow-400 hover:bg-yellow-500 text-black text-base py-6"
                        : isFree
                        ? "bg-white/10 hover:bg-white/20 text-white"
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

        {/* Social Proof / Why #1 */}
        <div className="max-w-4xl mx-auto mb-16 text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-yellow-500/10 via-amber-500/10 to-yellow-500/10 border border-yellow-500/30">
            <Trophy className="h-12 w-12 text-yellow-400 mx-auto mb-4" />
            <h2 className="text-2xl font-display font-bold mb-4 text-yellow-400">
              Why We're #1 in ALL 10 Categories
            </h2>
            <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
              Our patented orchestration technology combines the best of GPT-5.2, Claude Opus 4.5, and Gemini 3 Pro
              with consensus voting, challenge-refine workflows, and tool integration.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-xs">
              {["GPQA Diamond", "SWE-Bench", "AIME 2024", "MMMLU", "ARC-AGI 2"].map((bench) => (
                <div key={bench} className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                  <div className="text-yellow-400 font-bold">#1</div>
                  <div className="text-muted-foreground">{bench}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-xs mt-4">
              {["Tool Use", "RAG", "Multimodal", "Dialogue EQ", "Long Context"].map((bench) => (
                <div key={bench} className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                  <div className="text-yellow-400 font-bold">#1</div>
                  <div className="text-muted-foreground">{bench}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* How It Works - Upsell focused */}
        <div className="max-w-3xl mx-auto mb-16 p-8 rounded-2xl bg-card/50 border border-border/50">
          <h2 className="text-2xl font-display font-bold text-center mb-6">
            How It Works
          </h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-yellow-400 font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold text-yellow-400">Get 500 ELITE queries with Pro</h3>
                <p className="text-sm text-muted-foreground">
                  Each ELITE query uses our #1 ranked orchestration with GPT-5.2, Claude Opus 4.5 & Gemini 3 Pro.
                  Perfect for professional work, coding, research, and critical tasks.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-green-400 font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold text-green-400">UNLIMITED FREE queries after</h3>
                <p className="text-sm text-muted-foreground">
                  After your ELITE quota, you get <strong>unlimited</strong> FREE tier queries. 
                  Our FREE orchestration still beats most single paid models — no caps, no limits.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[var(--bronze)]/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[var(--bronze)] font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold">Upgrade anytime for more ELITE</h3>
                <p className="text-sm text-muted-foreground">
                  Need more #1 quality? Upgrade from Lite to Pro for 5x more ELITE queries.
                  Or go Enterprise for team features and compliance.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto mb-16">
          <h2 className="text-2xl font-display font-bold text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What happens after I use my ELITE queries?</h3>
              <p className="text-muted-foreground text-sm">
                You get <strong>UNLIMITED FREE queries</strong> for the rest of the month. There's no cap — 
                our FREE orchestration beats most single paid models, so you still get great quality. 
                Want #1 quality back? Just upgrade for more ELITE queries.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">How is ELITE different from FREE?</h3>
              <p className="text-muted-foreground text-sm">
                ELITE uses premium models (GPT-5.2, Claude Opus 4.5, Gemini 3 Pro) to rank #1 in ALL 10 benchmarks.
                FREE uses free models in consensus — still excellent, but not #1 in all categories.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">Why is Pro the best value?</h3>
              <p className="text-muted-foreground text-sm">
                Pro gives you 5x more ELITE queries than Lite (500 vs 100) for only 2x the price ($29.99 vs $14.99). 
                Plus you get full API access, advanced features, and 30-day memory.
              </p>
            </div>
          </div>
        </div>

        {/* CTA - SELL PRO */}
        <div className="text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-yellow-500/20 via-amber-500/20 to-yellow-500/20 border-2 border-yellow-500/50">
            <Trophy className="h-10 w-10 text-yellow-400 mx-auto mb-4" />
            <h2 className="text-3xl font-display font-bold mb-4 text-yellow-400">
              Get #1 AI Quality Today
            </h2>
            <p className="text-muted-foreground mb-6 max-w-xl mx-auto">
              500 ELITE queries. UNLIMITED FREE after. Full API access. 
              The world's best AI orchestration for just $29.99/month.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Button 
                size="lg" 
                className="bg-yellow-400 hover:bg-yellow-500 text-black font-bold text-lg px-8"
                onClick={() => handleSubscribe(pricingTiers[2])} // Pro tier
              >
                <Trophy className="h-5 w-5 mr-2" />
                Get Pro — $29.99/mo
                <ArrowRight className="h-5 w-5 ml-2" />
              </Button>
              <Link href="/sign-up">
                <Button size="lg" variant="outline" className="border-white/20 text-muted-foreground hover:bg-white/5">
                  Try Free First
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
