/**
 * Canonical production orchestrator URL (us-east1).
 * Used only when ORCHESTRATOR_API_BASE_URL / NEXT_PUBLIC_API_BASE_URL are unset.
 */
export const DEFAULT_ORCHESTRATOR_API_BASE_URL =
  "https://llmhive-orchestrator-792354158895.us-east1.run.app"

/** Resolve backend base URL for Next.js API routes that proxy to Cloud Run. */
export function getOrchestratorApiBaseUrl(): string {
  return (
    process.env.ORCHESTRATOR_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    DEFAULT_ORCHESTRATOR_API_BASE_URL
  )
}
