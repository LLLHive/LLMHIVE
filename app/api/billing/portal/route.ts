import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"

const BACKEND_URL = process.env.ORCHESTRATOR_API_BASE_URL || "http://localhost:8000"

export async function POST() {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }

    // Call backend to create Stripe billing portal session
    const response = await fetch(`${BACKEND_URL}/api/v1/billing/portal`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.LLMHIVE_API_KEY || "",
      },
      body: JSON.stringify({
        user_id: userId,
        return_url: `${process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai"}/billing`,
      }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }))
      return NextResponse.json(
        { error: error.detail || "Failed to create portal session" },
        { status: response.status }
      )
    }

    const data = await response.json()
    
    return NextResponse.json({
      url: data.url,
    })
  } catch (error) {
    console.error("Error creating portal session:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

