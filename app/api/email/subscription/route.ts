/**
 * Subscription Confirmation Email API Endpoint
 * 
 * Sends a subscription confirmation email after successful payment.
 * Called by Stripe webhook handler after checkout completion.
 */
import { NextRequest, NextResponse } from "next/server"
import { sendSubscriptionEmail } from "@/lib/email"

export async function POST(req: NextRequest) {
  try {
    // Only allow internal calls with API key
    const authHeader = req.headers.get("authorization")
    const isInternalCall = authHeader === `Bearer ${process.env.API_KEY}`
    
    if (!isInternalCall) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await req.json()
    const { email, name, tier, billingCycle, amount, nextBillingDate } = body

    if (!email || !name || !tier || !billingCycle || !amount || !nextBillingDate) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      )
    }

    const result = await sendSubscriptionEmail({
      to: email,
      name,
      tier,
      billingCycle,
      amount,
      nextBillingDate,
    })

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || "Failed to send email" },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      messageId: result.id,
    })
  } catch (error) {
    console.error("[Email/Subscription] Error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
