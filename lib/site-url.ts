/**
 * Canonical site origin (no trailing slash).
 * Production: https://llmhive.ai (apex). Set NEXT_PUBLIC_APP_URL per environment.
 */
export function getSiteUrl(): string {
  return (process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai").replace(/\/$/, "")
}
