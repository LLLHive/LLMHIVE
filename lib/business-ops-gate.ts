import { createHmac, timingSafeEqual } from "node:crypto"

/** HttpOnly cookie set after successful password verification (value is an HMAC digest). */
export const BUSINESS_OPS_GATE_COOKIE = "llmhive_bo_gate"

const GATE_TOKEN_PAYLOAD = "business-ops-granted-v1"

export function businessOpsGateConfigured(): boolean {
  return Boolean(
    process.env.BUSINESS_OPS_GATE_PASSWORD &&
      process.env.BUSINESS_OPS_GATE_PASSWORD.length > 0 &&
      process.env.BUSINESS_OPS_GATE_SECRET &&
      process.env.BUSINESS_OPS_GATE_SECRET.length > 0,
  )
}

export function expectedGateCookieValue(): string {
  const secret = process.env.BUSINESS_OPS_GATE_SECRET
  if (!secret) return ""
  return createHmac("sha256", secret).update(GATE_TOKEN_PAYLOAD).digest("base64url")
}

export function verifyBusinessOpsGateCookie(cookieValue: string | undefined): boolean {
  if (!cookieValue) return false
  const expected = expectedGateCookieValue()
  if (!expected) return false
  try {
    const a = Buffer.from(cookieValue, "utf8")
    const b = Buffer.from(expected, "utf8")
    if (a.length !== b.length) return false
    return timingSafeEqual(a, b)
  } catch {
    return false
  }
}

export function isBusinessOpsProtectedPath(pathname: string): boolean {
  if (pathname === "/business-ops" || pathname.startsWith("/business-ops/")) {
    return !pathname.startsWith("/business-ops/gate")
  }
  return false
}
