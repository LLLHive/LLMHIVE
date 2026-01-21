/**
 * Welcome Email API Endpoint
 * 
 * Sends a welcome email to new users after signup.
 * Called by Clerk webhook or manually after registration.
 */
import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import { sendWelcomeEmail } from "@/lib/email"

export async function POST(req: NextRequest) {
  try {
    // Allow both authenticated users and internal calls with API key
    const authHeader = req.headers.get("authorization")
    const isInternalCall = authHeader === `Bearer ${process.env.API_KEY}`
    
    if (!isInternalCall) {
      const { userId } = await auth()
      if (!userId) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
      }
    }

    const body = await req.json()
    const { email, name } = body

    if (!email || !name) {
      return NextResponse.json(
        { error: "Missing required fields: email, name" },
        { status: 400 }
      )
    }

    const result = await sendWelcomeEmail({ to: email, name })

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
    console.error("[Email/Welcome] Error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
