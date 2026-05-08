/**
 * Clerk webhook handler.
 *
 * Wires Clerk's `user.created` event to the welcome email so first-time
 * sign-ups receive a transactional email automatically. Other events are
 * acknowledged but not acted on (yet).
 *
 * Setup:
 * 1. In the Clerk Dashboard, create a webhook endpoint pointing at
 *    `https://<your-host>/api/webhooks/clerk`.
 * 2. Subscribe at minimum to `user.created`. (Optional: `user.deleted`
 *    so we can revoke any local state if you add one later.)
 * 3. Copy the signing secret from the Clerk Dashboard into the env var
 *    `CLERK_WEBHOOK_SECRET`. The secret typically starts with `whsec_`.
 *
 * Behavior when `CLERK_WEBHOOK_SECRET` is unset:
 *   The endpoint returns HTTP 503 with a clear message. Clerk will retry
 *   per its standard schedule. This keeps the dormant pattern: deploying
 *   without setting the secret is safe (no false 200s), and flipping the
 *   env var on activates the integration immediately.
 *
 * Signature verification is implemented inline (HMAC-SHA256 over
 * `${svix-id}.${svix-timestamp}.${rawBody}`) so we do not need to add a
 * new npm dependency.
 */
import { NextRequest, NextResponse } from "next/server"
import crypto from "node:crypto"

import { sendWelcomeEmail } from "@/lib/email"

export const runtime = "nodejs"

interface ClerkUserCreatedPayload {
  type: "user.created" | string
  data: {
    id?: string
    first_name?: string | null
    last_name?: string | null
    primary_email_address_id?: string | null
    email_addresses?: Array<{
      id?: string
      email_address?: string
    }>
  }
}

const TIMESTAMP_TOLERANCE_SECONDS = 5 * 60

function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  try {
    return crypto.timingSafeEqual(Buffer.from(a, "hex"), Buffer.from(b, "hex"))
  } catch {
    return false
  }
}

function verifyClerkSignature(
  rawBody: string,
  svixId: string | null,
  svixTimestamp: string | null,
  svixSignature: string | null,
  secret: string,
): { ok: boolean; reason?: string } {
  if (!svixId || !svixTimestamp || !svixSignature) {
    return { ok: false, reason: "missing svix headers" }
  }

  const tsNumber = Number.parseInt(svixTimestamp, 10)
  if (!Number.isFinite(tsNumber)) {
    return { ok: false, reason: "invalid svix-timestamp" }
  }
  const skewSeconds = Math.abs(Math.floor(Date.now() / 1000) - tsNumber)
  if (skewSeconds > TIMESTAMP_TOLERANCE_SECONDS) {
    return { ok: false, reason: "stale svix-timestamp" }
  }

  // Clerk webhook secrets are prefixed `whsec_` followed by base64.
  const secretBody = secret.startsWith("whsec_") ? secret.slice(6) : secret
  let key: Buffer
  try {
    key = Buffer.from(secretBody, "base64")
  } catch {
    return { ok: false, reason: "invalid webhook secret encoding" }
  }

  const signedPayload = `${svixId}.${svixTimestamp}.${rawBody}`
  const expectedHex = crypto
    .createHmac("sha256", key)
    .update(signedPayload)
    .digest("hex")
  const expectedB64 = Buffer.from(expectedHex, "hex").toString("base64")

  // svix-signature has the form "v1,<sig> v1,<sig2>" (space-separated)
  const candidates = svixSignature
    .split(/\s+/)
    .map((entry) => entry.trim())
    .filter(Boolean)

  for (const candidate of candidates) {
    const [, sig] = candidate.split(",")
    if (!sig) continue
    if (sig === expectedB64) return { ok: true }
    if (timingSafeEqualHex(sig, expectedHex)) return { ok: true }
  }
  return { ok: false, reason: "signature mismatch" }
}

function extractPrimaryEmail(
  payload: ClerkUserCreatedPayload["data"],
): string | null {
  const emails = payload.email_addresses || []
  if (payload.primary_email_address_id) {
    const primary = emails.find((e) => e.id === payload.primary_email_address_id)
    if (primary?.email_address) return primary.email_address
  }
  return emails[0]?.email_address || null
}

export async function POST(req: NextRequest) {
  const secret = process.env.CLERK_WEBHOOK_SECRET
  if (!secret) {
    return NextResponse.json(
      {
        error: "CLERK_WEBHOOK_SECRET not configured",
        details:
          "Set CLERK_WEBHOOK_SECRET to the signing secret from the Clerk Dashboard.",
      },
      { status: 503 },
    )
  }

  const rawBody = await req.text()
  const verification = verifyClerkSignature(
    rawBody,
    req.headers.get("svix-id"),
    req.headers.get("svix-timestamp"),
    req.headers.get("svix-signature"),
    secret,
  )
  if (!verification.ok) {
    console.warn("[clerk-webhook] rejected:", verification.reason)
    return NextResponse.json(
      { error: "Invalid signature", reason: verification.reason },
      { status: 400 },
    )
  }

  let event: ClerkUserCreatedPayload
  try {
    event = JSON.parse(rawBody)
  } catch (err) {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 },
    )
  }

  if (event.type !== "user.created") {
    return NextResponse.json({ received: true, processed: false, type: event.type })
  }

  const email = extractPrimaryEmail(event.data || {})
  if (!email) {
    console.warn(
      "[clerk-webhook] user.created without resolvable email:",
      event.data?.id,
    )
    return NextResponse.json({ received: true, processed: false, reason: "no_email" })
  }

  const name = [event.data?.first_name, event.data?.last_name]
    .filter(Boolean)
    .join(" ")
    .trim() || "there"

  try {
    const result = await sendWelcomeEmail({ to: email, name })
    return NextResponse.json({
      received: true,
      processed: true,
      type: event.type,
      messageId: result.id,
      sent: result.success,
    })
  } catch (err) {
    console.error("[clerk-webhook] welcome email send failed:", err)
    // Return 200 so Clerk does not retry; failure is logged for follow-up.
    return NextResponse.json({
      received: true,
      processed: false,
      reason: "email_send_failed",
    })
  }
}
