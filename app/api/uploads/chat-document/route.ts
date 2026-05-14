import { NextRequest, NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import { getPaidEntitlement, paymentRequiredResponse } from "@/lib/billing/entitlement"

export const maxDuration = 120
export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  const { userId: clerkUserId } = await auth()
  if (!clerkUserId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const entitlement = await getPaidEntitlement(clerkUserId)
  if (!entitlement.hasPaidAccess) {
    return NextResponse.json(paymentRequiredResponse(entitlement.status), { status: 402 })
  }

  const apiBase =
    process.env.ORCHESTRATOR_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
  const apiKey = process.env.LLMHIVE_API_KEY

  if (!apiBase) {
    return NextResponse.json(
      { error: "Backend not configured", details: "ORCHESTRATOR_API_BASE_URL is not set." },
      { status: 503 }
    )
  }

  let incoming: FormData
  try {
    incoming = await req.formData()
  } catch {
    return NextResponse.json({ error: "Invalid multipart body" }, { status: 400 })
  }

  const file = incoming.get("file")
  if (!file || !(file instanceof File)) {
    return NextResponse.json({ error: "Expected multipart field \"file\" (File)." }, { status: 400 })
  }

  const forward = new FormData()
  forward.append("file", file)
  forward.append("user_id", clerkUserId)

  const headers: HeadersInit = {}
  if (apiKey) {
    headers["X-API-Key"] = apiKey
  }

  const url = `${apiBase.replace(/\/$/, "")}/v1/uploads/chat-document`
  const upstream = await fetch(url, { method: "POST", body: forward, headers })

  const text = await upstream.text()
  if (!upstream.ok) {
    let body: unknown
    try {
      body = JSON.parse(text) as Record<string, unknown>
    } catch {
      body = { error: text.slice(0, 500) || upstream.statusText }
    }
    return NextResponse.json(body, { status: upstream.status })
  }

  try {
    return NextResponse.json(JSON.parse(text) as Record<string, unknown>)
  } catch {
    return NextResponse.json({ error: "Invalid JSON from orchestrator" }, { status: 502 })
  }
}
