/**
 * Placeholder DSNs copied from env.example (or typos) still initialize @sentry/nextjs and log errors.
 * Only call Sentry.init when the DSN looks like a real ingestion URL.
 */
export function isLikelyValidPublicSentryDsn(dsn: string | undefined): boolean {
  if (!dsn || typeof dsn !== "string") return false
  const s = dsn.trim()
  if (s.length < 20) return false
  // env.example placeholders
  if (s.includes("@...") || s.includes("...ingest")) return false
  try {
    const u = new URL(s)
    if (u.protocol !== "https:" && u.protocol !== "http:") return false
    const host = u.hostname.toLowerCase()
    return (
      host.includes("sentry.io") ||
      host.includes("ingest.us") ||
      host.includes("ingest.de") ||
      host.endsWith("ingest.sentry.io")
    )
  } catch {
    return false
  }
}
