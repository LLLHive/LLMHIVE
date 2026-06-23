"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { CheckCircle, Loader2, ArrowRight, Sparkles, Gift } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"
import confetti from "canvas-confetti"
import { BillingPurchaseTracking } from "@/components/marketing/billing-purchase-tracking"
import type { GtmPurchasePayload } from "@/lib/marketing/gtm-events"

export default function BillingSuccessPage() {
  const searchParams = useSearchParams()
  const sessionId = searchParams.get("session_id")
  const [loading, setLoading] = useState(true)
  const [paymentSuccess, setPaymentSuccess] = useState(false)
  const [subscription, setSubscription] = useState<{
    tier: string
    billingCycle: string
    status?: string
    isTrial?: boolean
    trialEnd?: string | null
    amountDueToday?: number | null
  } | null>(null)
  const [purchase, setPurchase] = useState<GtmPurchasePayload | null>(null)

  useEffect(() => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ["#cd7f32", "#b8860b", "#daa520", "#ffd700"],
    })

    if (sessionId) {
      verifySession()
    } else {
      setLoading(false)
    }
  }, [sessionId])

  const verifySession = async () => {
    try {
      const response = await fetch(`/api/billing/verify-session?session_id=${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setPaymentSuccess(Boolean(data.success))
        setSubscription(data.subscription)
        setPurchase(data.purchase ?? null)
      }
    } catch (error) {
      console.error("Error verifying session:", error)
    } finally {
      setLoading(false)
    }
  }

  const planDisplayName = (tier: string | undefined) => {
    if (!tier) return "Your"
    const t = tier.toLowerCase()
    if (t === "lite") return "Standard"
    if (t === "pro") return "Premium"
    if (t === "enterprise") return "Enterprise"
    return tier.charAt(0).toUpperCase() + tier.slice(1)
  }

  const isTrial =
    subscription?.isTrial ||
    subscription?.status === "trialing" ||
    (subscription?.amountDueToday === 0 && subscription?.tier === "lite")

  const trialEndLabel = subscription?.trialEnd
    ? new Date(subscription.trialEnd).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : null

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <BillingPurchaseTracking purchase={purchase} enabled={paymentSuccess && !isTrial} />
      <Card className="max-w-lg w-full bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader className="text-center pb-2">
          {loading ? (
            <Loader2 className="h-16 w-16 animate-spin text-[var(--bronze)] mx-auto mb-4" />
          ) : (
            <div className="relative mx-auto mb-4">
              <div
                className={`absolute inset-0 rounded-full blur-xl ${isTrial ? "bg-amber-500/25" : "bg-green-500/20"}`}
              />
              {isTrial ? (
                <Gift className="h-16 w-16 text-amber-400 relative mx-auto" />
              ) : (
                <CheckCircle className="h-16 w-16 text-green-500 relative mx-auto" />
              )}
            </div>
          )}
          <CardTitle className="text-2xl">
            {loading
              ? "Setting up your account..."
              : isTrial
                ? "Your 3-day free trial is active!"
                : "Payment successful!"}
          </CardTitle>
          <CardDescription className="text-base mt-2">
            {loading
              ? "Please wait while we confirm your subscription..."
              : isTrial
                ? "You were not charged today. Enjoy elite orchestration for 3 days (up to $3 provider spend)."
                : "Thank you for subscribing to LLMHive."}
          </CardDescription>
        </CardHeader>

        <CardContent className="text-center space-y-6">
          {!loading && (
            <>
              {subscription && (
                <div
                  className={`p-4 rounded-lg border ${isTrial ? "bg-amber-500/10 border-amber-500/30" : "bg-[var(--bronze)]/10 border-[var(--bronze)]/20"}`}
                >
                  <div className="flex items-center justify-center gap-2 mb-2">
                    {isTrial ? (
                      <Gift className="h-5 w-5 text-amber-400" />
                    ) : (
                      <Sparkles className="h-5 w-5 text-[var(--bronze)]" />
                    )}
                    <span className="font-semibold">{planDisplayName(subscription.tier)} plan</span>
                  </div>
                  {isTrial ? (
                    <div className="space-y-1 text-sm">
                      <p className="font-medium text-amber-300">$0.00 charged today</p>
                      <p className="text-muted-foreground">
                        Then $10/month{trialEndLabel ? ` starting ${trialEndLabel}` : " after 3 days"} unless
                        you cancel
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {subscription.billingCycle === "annual" ? "Annual" : "Monthly"} subscription activated
                    </p>
                  )}
                </div>
              )}

              <div className="space-y-3">
                <p className="text-muted-foreground">
                  {isTrial
                    ? "Your trial includes full Standard access with elite orchestration while the $3 trial spend cap allows."
                    : `Your subscription is active. You have access to all ${planDisplayName(subscription?.tier)} features.`}
                </p>

                <div className="text-sm text-muted-foreground space-y-1 text-left max-w-sm mx-auto">
                  {isTrial ? (
                    <>
                      <p>✓ No charge today — card saved for after the trial</p>
                      <p>✓ Elite orchestration during trial (up to $3 provider spend)</p>
                      <p>✓ Cancel anytime in Billing before trial ends to avoid $10/mo</p>
                    </>
                  ) : (
                    <>
                      <p>✓ Receipt sent to your email</p>
                      <p>✓ All features unlocked immediately</p>
                      <p>✓ Cancel anytime from billing settings</p>
                    </>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-3 pt-4">
                <Button className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white" asChild>
                  <Link href="/app">
                    {isTrial ? "Start using your free trial" : "Start using LLMHive"}
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" className="w-full" asChild>
                  <Link href="/billing">{isTrial ? "Manage trial & billing" : "View billing details"}</Link>
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
