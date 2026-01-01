"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { CheckCircle, Loader2, ArrowRight, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"
import confetti from "canvas-confetti"

export default function BillingSuccessPage() {
  const searchParams = useSearchParams()
  const sessionId = searchParams.get("session_id")
  const [loading, setLoading] = useState(true)
  const [subscription, setSubscription] = useState<{
    tier: string
    billingCycle: string
  } | null>(null)

  useEffect(() => {
    // Trigger confetti animation
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ["#cd7f32", "#b8860b", "#daa520", "#ffd700"],
    })

    // Verify the session and get subscription details
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
        setSubscription(data.subscription)
      }
    } catch (error) {
      console.error("Error verifying session:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="max-w-lg w-full bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader className="text-center pb-2">
          {loading ? (
            <Loader2 className="h-16 w-16 animate-spin text-[var(--bronze)] mx-auto mb-4" />
          ) : (
            <div className="relative mx-auto mb-4">
              <div className="absolute inset-0 bg-green-500/20 rounded-full blur-xl" />
              <CheckCircle className="h-16 w-16 text-green-500 relative" />
            </div>
          )}
          <CardTitle className="text-2xl">
            {loading ? "Processing..." : "Payment Successful!"}
          </CardTitle>
          <CardDescription>
            {loading 
              ? "Please wait while we confirm your payment..."
              : "Thank you for subscribing to LLMHive"
            }
          </CardDescription>
        </CardHeader>

        <CardContent className="text-center space-y-6">
          {!loading && (
            <>
              {subscription && (
                <div className="p-4 rounded-lg bg-[var(--bronze)]/10 border border-[var(--bronze)]/20">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Sparkles className="h-5 w-5 text-[var(--bronze)]" />
                    <span className="font-semibold capitalize">{subscription.tier} Plan</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {subscription.billingCycle === "annual" ? "Annual" : "Monthly"} subscription activated
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <p className="text-muted-foreground">
                  Your subscription is now active. You have access to all {subscription?.tier || "Pro"} features.
                </p>

                <div className="text-sm text-muted-foreground space-y-1">
                  <p>✓ Receipt sent to your email</p>
                  <p>✓ All features unlocked immediately</p>
                  <p>✓ Cancel anytime from billing settings</p>
                </div>
              </div>

              <div className="flex flex-col gap-3 pt-4">
                <Link href="/">
                  <Button className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-white">
                    Start Using LLMHive
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </Link>
                <Link href="/billing">
                  <Button variant="outline" className="w-full">
                    View Billing Details
                  </Button>
                </Link>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

