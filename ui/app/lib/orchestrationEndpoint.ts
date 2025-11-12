export const ORCHESTRATION_PATH = "/api/v1/orchestration/";

/** Build absolute orchestrator URL if NEXT_PUBLIC_API_BASE_URL is set. */
export function orchestrationUrl(base?: string) {
  const origin = (base || process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/,"");
  return origin ? `${origin}${ORCHESTRATION_PATH}` : ORCHESTRATION_PATH;
}
