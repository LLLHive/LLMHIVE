"use client"

import { useState } from "react"
import { useUser, useClerk } from "@clerk/nextjs"
import { Check, Zap, Building2, Sparkles, ArrowRight, Loader2, Home } from "lucide-react"
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
  limits: {
    requests: string
    tokens: string
    models: string
    storage: string
  }
  popular?: boolean
  cta: string
  tier: "free" | "basic" | "pro" | "enterprise"
}

const pricingTiers: PricingTier[] = [
  {
    name: "Free",
    description: "Perfect for trying out LLMHive",
    monthlyPrice: 0,
    annualPrice: 0,
    tier: "free",
    features: [
      "50 messages/month",
      "Budget models only",
      "2 projects",
      "7 days chat history",
      "1 Industry Pack",
      "Community support",
    ],
    limits: {
      requests: "50/month",
      tokens: "50K/month",
      models: "Budget only",
      storage: "50 MB",
    },
    cta: "Get Started Free",
  },
  {
    name: "LLMHive",
    description: "Essential AI access for individuals",
    monthlyPrice: 15,
    annualPrice: 155.99,
    tier: "basic",
    features: [
      "500 messages/month",
      "Budget + Standard models",
      "10 projects",
      "90 days chat history",
      "5 Industry Packs",
      "Vision & image support",
      "Email support (48hr)",
    ],
    limits: {
      requests: "500/month",
      tokens: "500K/month",
      models: "Standard",
      storage: "1 GB",
    },
    cta: "Subscribe",
  },
  {
    name: "Pro",
    description: "For professionals and small teams",
    monthlyPrice: 29.99,
    annualPrice: 299.99,
    tier: "pro",
    popular: true,
    features: [
      "3,000 messages/month",
      "All models including Premium",
      "Unlimited projects",
      "Unlimited chat history",
      "All Industry Packs",
      "Code interpreter",
      "API access (1,000 calls/mo)",
      "5 team members",
      "Priority queue",
      "Priority email support (24hr)",
    ],
    limits: {
      requests: "3,000/month",
      tokens: "3M/month",
      models: "All models",
      storage: "10 GB",
    },
    cta: "Upgrade to Pro",
  },
  {
    name: "Enterprise",
    description: "For large organizations with custom needs",
    monthlyPrice: 199.99,
    annualPrice: 1999.99,
    tier: "enterprise",
    features: [
      "Unlimited messages",
      "All models + Priority access",
      "Unlimited everything",
      "Custom orchestration rules",
      "SSO / SAML authentication",
      "Unlimited team members",
      "Admin controls & audit logs",
      "API access (unlimited)",
      "Webhooks",
      "Dedicated support (4hr SLA)",
    ],
    limits: {
      requests: "Unlimited",
      tokens: "Unlimited",
      models: "All + Priority",
      storage: "Unlimited",
    },
    cta: "Contact Sales",
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
        // Already signed in, go to app
        window.location.href = "/"
      } else {
        // Redirect to sign up
        window.location.href = "/sign-up"
      }
      return
    }

    if (tier.tier === "enterprise") {
      // Open contact form or email
      window.location.href = "mailto:sales@llmhive.ai?subject=Enterprise%20Inquiry"
      return
    }

    // If not signed in, prompt sign in first
    if (!isSignedIn) {
      openSignIn({
        redirectUrl: `/pricing?subscribe=${tier.tier}&cycle=${isAnnual ? "annual" : "monthly"}`,
      })
      return
    }

    // Create checkout session
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
          <Badge className="mb-4 bg-[var(--bronze)]/10 text-[var(--bronze)] border-[var(--bronze)]/20">
            <Sparkles className="h-3 w-3 mr-1" />
            Simple, transparent pricing
          </Badge>
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            Choose Your Plan
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Start free and scale as you grow. All plans include access to our powerful AI orchestration platform.
          </p>
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

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {pricingTiers.map((tier) => {
            const price = isAnnual ? tier.annualPrice : tier.monthlyPrice
            const period = isAnnual ? "/year" : "/month"

            return (
              <div key={tier.name} className="flex flex-col">
                <Card
                  className={cn(
                    "relative flex flex-col bg-card/50 backdrop-blur-sm border-border/50 transition-all duration-300 hover:border-[var(--bronze)]/30 flex-1",
                    tier.popular && "border-[var(--bronze)] ring-2 ring-[var(--bronze)]/20"
                  )}
                >
                  {tier.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <Badge className="bg-[var(--bronze)] text-white border-0 px-4 py-1">
                        <Zap className="h-3 w-3 mr-1" />
                        Most Popular
                      </Badge>
                    </div>
                  )}

                  <CardHeader className="pb-4">
                    <div className="flex items-center gap-2 mb-2">
                      {tier.tier === "free" && <Sparkles className="h-5 w-5 text-muted-foreground" />}
                      {tier.tier === "basic" && <Zap className="h-5 w-5 text-blue-500" />}
                      {tier.tier === "pro" && <Zap className="h-5 w-5 text-[var(--bronze)]" />}
                      {tier.tier === "enterprise" && <Building2 className="h-5 w-5 text-purple-500" />}
                      <CardTitle className="text-xl">{tier.name}</CardTitle>
                    </div>
                    <CardDescription>{tier.description}</CardDescription>
                  </CardHeader>

                  <CardContent className="flex-1 flex flex-col">
                    {/* Price */}
                    <div className="mb-6">
                      <div className="flex items-baseline gap-1">
                        <span className="text-4xl font-bold">
                          {price === 0 ? "Free" : `$${price.toFixed(2)}`}
                        </span>
                        {price > 0 && (
                          <span className="text-muted-foreground">{period}</span>
                        )}
                      </div>
                      {isAnnual && price > 0 && (
                        <p className="text-sm text-muted-foreground mt-1">
                          ${(tier.monthlyPrice).toFixed(2)}/month billed annually
                        </p>
                      )}
                    </div>

                    {/* Limits */}
                    <div className="grid grid-cols-2 gap-3 mb-6 p-4 rounded-lg bg-muted/30">
                      <div>
                        <p className="text-xs text-muted-foreground">Requests</p>
                        <p className="font-medium text-sm">{tier.limits.requests}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Tokens</p>
                        <p className="font-medium text-sm">{tier.limits.tokens}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Models</p>
                        <p className="font-medium text-sm">{tier.limits.models}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Storage</p>
                        <p className="font-medium text-sm">{tier.limits.storage}</p>
                      </div>
                    </div>

                    {/* Features - scrollable area */}
                    <div className="flex-1 min-h-0">
                      <ul className="space-y-2 h-[180px] overflow-y-auto pr-1">
                        {tier.features.map((feature, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </CardContent>

                  <CardFooter className="pt-4 pb-6">
                    <Button
                      className={cn(
                        "w-full",
                        tier.popular
                          ? "bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white"
                          : "bg-secondary hover:bg-secondary/80"
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
                          {tier.tier === "free" && isSignedIn ? "Current Plan" : tier.cta}
                          <ArrowRight className="h-4 w-4 ml-2" />
                        </>
                      )}
                    </Button>
                  </CardFooter>
                </Card>
              </div>
            )
          })}
        </div>

        {/* FAQ Section */}
        <div className="mt-24 max-w-3xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">Can I switch plans anytime?</h3>
              <p className="text-muted-foreground text-sm">
                Yes! You can upgrade or downgrade your plan at any time. When upgrading, you'll be charged the prorated difference. When downgrading, your new rate will apply at the next billing cycle.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What happens if I exceed my limits?</h3>
              <p className="text-muted-foreground text-sm">
                We'll notify you when you're approaching your limits. Free tier users will need to wait until the next billing cycle or upgrade. Pro users can continue with overage charges at $0.01 per 1K tokens.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">Do you offer refunds?</h3>
              <p className="text-muted-foreground text-sm">
                Yes, we offer a 14-day money-back guarantee for new subscriptions. If you're not satisfied, contact us within 14 days for a full refund.
              </p>
            </div>
            <div className="p-6 rounded-lg bg-card/50 border border-border/50">
              <h3 className="font-semibold mb-2">What payment methods do you accept?</h3>
              <p className="text-muted-foreground text-sm">
                We accept all major credit cards (Visa, Mastercard, American Express) through our secure payment processor, Stripe.
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-24 text-center">
          <div className="p-8 rounded-2xl bg-gradient-to-r from-[var(--bronze)]/10 to-purple-500/10 border border-[var(--bronze)]/20">
            <h2 className="text-2xl font-display font-bold mb-4">
              Ready to supercharge your AI workflow?
            </h2>
            <p className="text-muted-foreground mb-6">
              Start with our free tier and experience the power of AI orchestration.
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
          <p>© 2025 LLMHive. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

