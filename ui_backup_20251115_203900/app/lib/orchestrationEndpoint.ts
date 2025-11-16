export const ORCHESTRATION_PATH = "/api/v1/orchestration/";

function apiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  return raw.replace(/\/+$/, "");
}

export function buildOrchestrationUrl(path: string = ORCHESTRATION_PATH): string {
  const base = apiBase();
  return base ? `${base}${path}` : path;
}
