/**
 * User Onboarding API Endpoint
 * 
 * Tracks user onboarding completion for analytics.
 * Stores completion state in user metadata.
 */
import { NextRequest, NextResponse } from "next/server"
import { auth, clerkClient } from "@clerk/nextjs/server"

export async function POST(req: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await req.json()
    const { action, step } = body

    // Valid actions: "welcome_seen", "tour_started", "tour_completed", "tour_skipped"
    const validActions = ["welcome_seen", "tour_started", "tour_completed", "tour_skipped"]
    
    if (!action || !validActions.includes(action)) {
      return NextResponse.json(
        { error: "Invalid action. Must be one of: " + validActions.join(", ") },
        { status: 400 }
      )
    }

    // Update user metadata in Clerk
    try {
      const client = await clerkClient()
      await client.users.updateUserMetadata(userId, {
        publicMetadata: {
          onboarding: {
            [action]: true,
            [`${action}_at`]: new Date().toISOString(),
            ...(step !== undefined && { last_step: step }),
          },
        },
      })
    } catch (error) {
      console.error("[Onboarding] Failed to update Clerk metadata:", error)
      // Continue even if Clerk update fails
    }

    console.log(`[Onboarding] User ${userId} completed action: ${action}`)

    return NextResponse.json({
      success: true,
      action,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error("[Onboarding] Error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

export async function GET(req: NextRequest) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    // Get user's onboarding state from Clerk
    try {
      const client = await clerkClient()
      const user = await client.users.getUser(userId)
      const onboarding = (user.publicMetadata?.onboarding as Record<string, unknown>) || {}

      return NextResponse.json({
        hasSeenWelcome: !!onboarding.welcome_seen,
        hasCompletedTour: !!onboarding.tour_completed,
        hasSkippedTour: !!onboarding.tour_skipped,
        welcomeSeenAt: onboarding.welcome_seen_at || null,
        tourCompletedAt: onboarding.tour_completed_at || null,
      })
    } catch (error) {
      console.error("[Onboarding] Failed to fetch Clerk metadata:", error)
      // Return default state if Clerk fetch fails
      return NextResponse.json({
        hasSeenWelcome: false,
        hasCompletedTour: false,
        hasSkippedTour: false,
      })
    }
  } catch (error) {
    console.error("[Onboarding] Error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
