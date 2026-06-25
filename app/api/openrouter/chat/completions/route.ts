import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import { getPaidEntitlement, paymentRequiredResponse } from "@/lib/billing/entitlement"
import { resolvePerRequestMaxCostUsd } from "@/lib/billing/tier-cost-caps"
import { getSiteUrl } from "@/lib/site-url"

const OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

export async function POST(request: Request) {
  try {
    const { userId: clerkUserId } = await auth()
    if (!clerkUserId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const entitlement = await getPaidEntitlement(clerkUserId)
    if (!entitlement.hasAppAccess) {
      return NextResponse.json(paymentRequiredResponse(entitlement.status), { status: 402 })
    }

    const body = await request.json()
    const tierKey = entitlement.tier.toLowerCase()
    const maxCost = resolvePerRequestMaxCostUsd(
      tierKey,
      typeof body.max_cost_usd === "number" ? body.max_cost_usd : null,
    )

    const apiKey = process.env.OPENROUTER_API_KEY
    if (!apiKey) {
      return NextResponse.json(
        { error: "OpenRouter API key not configured" },
        { status: 500 }
      )
    }

    const isStreaming = body.stream === true
    const forwardBody = {
      ...body,
      max_cost_usd: maxCost,
      user: clerkUserId,
    }

    const response = await fetch(OPENROUTER_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
        "HTTP-Referer": getSiteUrl(),
        "X-Title": "LLMHive",
      },
      body: JSON.stringify(forwardBody),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error("OpenRouter API error:", response.status, errorText)
      return NextResponse.json(
        { error: `OpenRouter API error: ${response.status}`, details: errorText },
        { status: response.status }
      )
    }

    if (isStreaming) {
      return new Response(response.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
        },
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("OpenRouter chat completions error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    )
  }
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  })
}
