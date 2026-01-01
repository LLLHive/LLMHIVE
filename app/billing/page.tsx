"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { 
  CreditCard, 
  Calendar, 
  Zap, 
  ArrowUpRight, 
  ArrowDownRight,
  AlertCircle,
  CheckCircle,
  Loader2,
  ExternalLink,
  Settings,
  Receipt
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import Link from "next/link"

interface Subscription {
  tier: string
  status: "active" | "cancelled" | "past_due" | "trialing"
  billingCycle: "monthly" | "annual"
  currentPeriodEnd: string
  cancelAtPeriodEnd: boolean
}

interface UsageData {
  requests: { used: number; limit: number }
  tokens: { used: number; limit: number }
}

export default function BillingPage() {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth()
  const router = useRouter()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [usage, setUsage] = useState<UsageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/sign-in?redirect_url=/billing")
      return
    }

    if (isAuthenticated) {
      loadBillingData()
    }
  }, [isAuthenticated, authLoading, router])

  const loadBillingData = async () => {
    setLoading(true)
    try {
      // Load subscription status
      const subRes = await fetch("/api/billing/subscription")
      if (subRes.ok) {
        const subData = await subRes.json()
        setSubscription(subData.subscription)
      }

      // Load usage data
      const usageRes = await fetch("/api/billing/usage")
      if (usageRes.ok) {
        const usageData = await usageRes.json()
        setUsage(usageData)
      }
    } catch (error) {
      console.error("Error loading billing data:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleManageBilling = async () => {
    setActionLoading("manage")
    try {
      const response = await fetch("/api/billing/portal", {
        method: "POST",
      })
      const data = await response.json()
      if (data.url) {
        window.location.href = data.url
      }
    } catch (error) {
      console.error("Error opening billing portal:", error)
    } finally {
      setActionLoading(null)
    }
  }

  const handleCancelSubscription = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? You'll retain access until the end of your billing period.")) {
      return
    }

    setActionLoading("cancel")
    try {
      const response = await fetch("/api/billing/cancel", {
        method: "POST",
      })
      if (response.ok) {
        await loadBillingData()
      }
    } catch (error) {
      console.error("Error cancelling subscription:", error)
    } finally {
      setActionLoading(null)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--bronze)]" />
      </div>
    )
  }

  const currentTier = subscription?.tier || "free"
  const isFreeTier = currentTier === "free"

  // Calculate usage percentages
  const requestsPercent = usage ? (usage.requests.used / usage.requests.limit) * 100 : 0
  const tokensPercent = usage ? (usage.tokens.used / usage.tokens.limit) * 100 : 0

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
            <Link href="/settings">
              <Button variant="ghost" size="icon">
                <Settings className="h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold mb-2">Billing & Subscription</h1>
          <p className="text-muted-foreground">
            Manage your subscription, view usage, and update payment methods.
          </p>
        </div>

        {/* Current Plan Card */}
        <Card className="mb-8 bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-[var(--bronze)]" />
                  Current Plan
                </CardTitle>
                <CardDescription>
                  Your active subscription details
                </CardDescription>
              </div>
              <Badge 
                className={
                  subscription?.status === "active" 
                    ? "bg-green-500/10 text-green-500 border-green-500/20"
                    : subscription?.status === "cancelled"
                    ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
                    : "bg-red-500/10 text-red-500 border-red-500/20"
                }
              >
                {subscription?.status === "active" && <CheckCircle className="h-3 w-3 mr-1" />}
                {subscription?.status === "cancelled" && <AlertCircle className="h-3 w-3 mr-1" />}
                {subscription?.status || "Active"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-bold capitalize">{currentTier}</h3>
                <p className="text-muted-foreground">
                  {isFreeTier 
                    ? "Limited features • Upgrade anytime"
                    : `${subscription?.billingCycle === "annual" ? "Annual" : "Monthly"} billing`
                  }
                </p>
              </div>
              <div className="text-right">
                {!isFreeTier && subscription?.currentPeriodEnd && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>
                      {subscription.cancelAtPeriodEnd ? "Ends" : "Renews"} on{" "}
                      {new Date(subscription.currentPeriodEnd).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {subscription?.cancelAtPeriodEnd && (
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 mb-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                  <div>
                    <p className="font-medium text-yellow-500">Subscription Ending</p>
                    <p className="text-sm text-muted-foreground">
                      Your subscription will end on {new Date(subscription.currentPeriodEnd).toLocaleDateString()}.
                      You can reactivate anytime before then.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-4">
              {isFreeTier ? (
                <Link href="/pricing" className="flex-1">
                  <Button className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white">
                    <ArrowUpRight className="h-4 w-4 mr-2" />
                    Upgrade Plan
                  </Button>
                </Link>
              ) : (
                <>
                  <Button 
                    variant="outline" 
                    className="flex-1"
                    onClick={handleManageBilling}
                    disabled={actionLoading === "manage"}
                  >
                    {actionLoading === "manage" ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <CreditCard className="h-4 w-4 mr-2" />
                    )}
                    Manage Payment
                  </Button>
                  <Link href="/pricing" className="flex-1">
                    <Button variant="outline" className="w-full">
                      <ArrowUpRight className="h-4 w-4 mr-2" />
                      Change Plan
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Usage Card */}
        <Card className="mb-8 bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader>
            <CardTitle>Usage This Period</CardTitle>
            <CardDescription>
              Track your API requests and token consumption
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Requests */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">API Requests</span>
                <span className="text-sm text-muted-foreground">
                  {usage?.requests.used.toLocaleString() || 0} / {usage?.requests.limit === 0 ? "∞" : usage?.requests.limit.toLocaleString() || 100}
                </span>
              </div>
              <Progress 
                value={Math.min(requestsPercent, 100)} 
                className="h-2"
              />
              {requestsPercent > 80 && (
                <p className="text-xs text-yellow-500 mt-1">
                  You've used {requestsPercent.toFixed(0)}% of your request limit
                </p>
              )}
            </div>

            {/* Tokens */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Tokens</span>
                <span className="text-sm text-muted-foreground">
                  {((usage?.tokens.used || 0) / 1000).toFixed(1)}K / {usage?.tokens.limit === 0 ? "∞" : `${((usage?.tokens.limit || 100000) / 1000).toFixed(0)}K`}
                </span>
              </div>
              <Progress 
                value={Math.min(tokensPercent, 100)} 
                className="h-2"
              />
              {tokensPercent > 80 && (
                <p className="text-xs text-yellow-500 mt-1">
                  You've used {tokensPercent.toFixed(0)}% of your token limit
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Billing History */}
        <Card className="mb-8 bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Receipt className="h-5 w-5" />
                  Billing History
                </CardTitle>
                <CardDescription>
                  View and download past invoices
                </CardDescription>
              </div>
              {!isFreeTier && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleManageBilling}
                >
                  View All
                  <ExternalLink className="h-3 w-3 ml-2" />
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isFreeTier ? (
              <div className="text-center py-8 text-muted-foreground">
                <Receipt className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No billing history</p>
                <p className="text-sm">Upgrade to a paid plan to see invoices here.</p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Click "View All" to access your complete billing history in the Stripe customer portal.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Cancel Subscription */}
        {!isFreeTier && !subscription?.cancelAtPeriodEnd && (
          <Card className="bg-card/50 backdrop-blur-sm border-red-500/20">
            <CardHeader>
              <CardTitle className="text-red-500">Cancel Subscription</CardTitle>
              <CardDescription>
                Cancel your subscription. You'll retain access until the end of your current billing period.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                variant="destructive" 
                onClick={handleCancelSubscription}
                disabled={actionLoading === "cancel"}
              >
                {actionLoading === "cancel" ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 mr-2" />
                )}
                Cancel Subscription
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}

