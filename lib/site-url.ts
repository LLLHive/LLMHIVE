/**
 * Canonical site origin (no trailing slash).
 * Production: https://llmhive.ai (apex). Set NEXT_PUBLIC_APP_URL per environment.
 */
export function getSiteUrl(): string {
  return (process.env.NEXT_PUBLIC_APP_URL || "https://llmhive.ai").replace(/\/$/, "")
}

/** Absolute URL for a site path — use for canonicals, JSON-LD, and email links. */
export function sitePath(path: string = ""): string {
  const base = getSiteUrl()
  if (!path) return base
  if (path === "/") return `${base}/`
  return `${base}${path.startsWith("/") ? path : `/${path}`}`
}
