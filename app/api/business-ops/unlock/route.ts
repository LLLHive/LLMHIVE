import { timingSafeEqual } from "node:crypto"
import { auth } from "@clerk/nextjs/server"
import { cookies } from "next/headers"
import { NextResponse } from "next/server"
import {
  BUSINESS_OPS_GATE_COOKIE,
  businessOpsGateConfigured,
  expectedGateCookieValue,
} from "@/lib/business-ops-gate"

export async function POST(req: Request) {
  const { userId } = await auth()
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (!businessOpsGateConfigured()) {
    return NextResponse.json(
      { error: "Business Ops gate is not configured on this deployment." },
      { status: 503 },
    )
  }

  const expectedPw = process.env.BUSINESS_OPS_GATE_PASSWORD ?? ""
  let body: { password?: string } = {}
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }
  const password = typeof body.password === "string" ? body.password : ""

  const a = Buffer.from(password, "utf8")
  const b = Buffer.from(expectedPw, "utf8")
  let ok = false
  if (a.length === b.length) {
    ok = timingSafeEqual(a, b)
  }

  if (!ok) {
    return NextResponse.json({ error: "Invalid password" }, { status: 401 })
  }

  const token = expectedGateCookieValue()
  if (!token) {
    return NextResponse.json({ error: "Server misconfiguration" }, { status: 503 })
  }

  const cookieStore = await cookies()
  cookieStore.set(BUSINESS_OPS_GATE_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  })

  return NextResponse.json({ ok: true })
}
