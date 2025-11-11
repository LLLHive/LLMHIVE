export const ORCHESTRATION_PATH = "/api/v1/orchestration/"; // NOTE: trailing slash required

/**
 * Build a full orchestration URL using NEXT_PUBLIC_API_BASE_URL when defined.
 * Ensures we don't end up with double slashes.
 */
export function buildOrchestrationUrl(base?: string) {
  const root = (base ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/+$/, "");
  return `${root}${ORCHESTRATION_PATH}`;
}
