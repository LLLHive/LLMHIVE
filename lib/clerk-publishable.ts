/**
 * Detects a real-looking Clerk **publishable** key (`pk_test_` / `pk_live_`).
 *
 * Common mistakes:
 * - Putting **CLERK_SECRET_KEY** (`sk_…`) into `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (Clerk will reject).
 * - A **truncated** publishable key (Clerk’s own UI / key format can be shorter than JWT-style keys).
 *
 * Length is a loose guard only; the Clerk SDK is the final judge at runtime.
 */
const MIN_CLERK_PUBLISHABLE_LEN = 20

export function isClerkPublishableKeyConfigured(): boolean {
  const k = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim()
  if (!k) return false
  if (k.includes("...")) return false
  if (k.startsWith("sk_test_") || k.startsWith("sk_live_")) return false
  if (!k.startsWith("pk_test_") && !k.startsWith("pk_live_")) return false
  if (k.length < MIN_CLERK_PUBLISHABLE_LEN) return false
  return true
}
