export const ORCHESTRATION_PATH = "/api/v1/orchestration/";
export const ORCHESTRATION_PATH = "/api/v1/orchestration";

function stripTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, "");
}

function hasSuffix(haystack: string, suffix: string): boolean {
  return haystack.toLowerCase().endsWith(suffix.toLowerCase());
}

/**
 * Build a stable orchestration URL that tolerates a variety of configured base values.
 *
 * Accepted inputs:
 *   - Origin only (https://example.com)
 *   - Origin with /api (https://example.com/api)
 *   - Origin with /api/v1 (https://example.com/api/v1)
 *   - Full endpoint (https://example.com/api/v1/orchestration)
 *
 * The output always includes the trailing slash required by the FastAPI router.
 */
export function buildOrchestrationUrl(base?: string | null): string {
  if (!base) {
    return ORCHESTRATION_PATH;
  }

  const trimmed = base.trim();
  if (!trimmed) {
    return ORCHESTRATION_PATH;
  }

  const normalizedBase = stripTrailingSlashes(trimmed);

  if (hasSuffix(normalizedBase, "/api/v1/orchestration")) {
    return `${normalizedBase}/`;
  }

  if (hasSuffix(normalizedBase, "/api/v1")) {
    return `${normalizedBase}/orchestration/`;
  }

  if (hasSuffix(normalizedBase, "/api")) {
    return `${normalizedBase}/v1/orchestration/`;
  }

  return `${normalizedBase}/api/v1/orchestration/`;
}

