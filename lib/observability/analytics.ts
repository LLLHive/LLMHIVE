/**
 * Lightweight PostHog product-analytics scaffold.
 *
 * Dormant by default. Activates when `NEXT_PUBLIC_POSTHOG_KEY` is set in the
 * environment. Posts events directly to the PostHog HTTP capture endpoint, so
 * we do NOT add `posthog-js` as a dependency. This keeps the bundle small and
 * the build risk-free until you choose to enable it.
 *
 * Override the host with `NEXT_PUBLIC_POSTHOG_HOST` if you self-host PostHog
 * (default: `https://us.i.posthog.com`, the US Cloud ingestion endpoint).
 *
 * Behavior:
 *   - `track(event, properties?)` — fire-and-forget POST to /capture/.
 *     Returns a Promise<boolean> so callers can `await` if they want to,
 *     but it should be treated as non-blocking. Errors are swallowed.
 *   - `identify(userId, traits?)` — optional, useful when you want to tie
 *     events to a logged-in user. We **never** send PII automatically.
 *   - `pageview(path, properties?)` — convenience wrapper for `$pageview`.
 *   - `isAnalyticsConfigured()` — env-var check for tests/diagnostics.
 *
 * All events are batched only logically: each call hits the network. PostHog
 * handles deduplication by `$insert_id` if needed.
 */

const _DEFAULT_HOST = "https://us.i.posthog.com"
const _DISTINCT_ID_KEY = "llmhive_posthog_distinct_id"

function _key(): string | null {
  const value =
    typeof process !== "undefined" && process.env
      ? process.env.NEXT_PUBLIC_POSTHOG_KEY
      : undefined
  return value && value.trim().length > 0 ? value.trim() : null
}

function _host(): string {
  const value =
    typeof process !== "undefined" && process.env
      ? process.env.NEXT_PUBLIC_POSTHOG_HOST
      : undefined
  const candidate = (value || _DEFAULT_HOST).trim()
  return candidate.replace(/\/+$/, "")
}

function _generateUuidV4(): string {
  // Use crypto.randomUUID where available (modern browsers + Node >= 19).
  const cryptoApi = (typeof globalThis !== "undefined" ? globalThis.crypto : undefined) as
    | Crypto
    | undefined
  if (cryptoApi && typeof cryptoApi.randomUUID === "function") {
    return cryptoApi.randomUUID()
  }
  // Fallback that works in any JS runtime.
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) => {
    const n = Number(c)
    const r =
      cryptoApi && typeof cryptoApi.getRandomValues === "function"
        ? cryptoApi.getRandomValues(new Uint8Array(1))[0] & 15
        : Math.floor(Math.random() * 16)
    return (n ^ (r >> (n / 4))).toString(16)
  })
}

function _resolveDistinctId(explicit?: string): string {
  if (explicit && explicit.trim()) return explicit.trim()
  if (typeof window === "undefined") return "server"
  try {
    const stored = window.localStorage.getItem(_DISTINCT_ID_KEY)
    if (stored) return stored
    const fresh = _generateUuidV4()
    window.localStorage.setItem(_DISTINCT_ID_KEY, fresh)
    return fresh
  } catch {
    return _generateUuidV4()
  }
}

export function isAnalyticsConfigured(): boolean {
  return _key() !== null
}

export interface CaptureOptions {
  distinctId?: string
  /** Optional `$insert_id` for server-side deduplication. */
  insertId?: string
}

export async function track(
  event: string,
  properties?: Record<string, unknown>,
  options?: CaptureOptions,
): Promise<boolean> {
  const apiKey = _key()
  if (!apiKey || !event) return false

  const payload = {
    api_key: apiKey,
    event,
    distinct_id: _resolveDistinctId(options?.distinctId),
    properties: {
      ...(properties || {}),
      $lib: "llmhive-analytics",
      $lib_version: "1.0",
      ...(options?.insertId ? { $insert_id: options.insertId } : {}),
    },
    timestamp: new Date().toISOString(),
  }

  try {
    const response = await fetch(`${_host()}/capture/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: typeof window !== "undefined",
    })
    return response.ok
  } catch (err) {
    if (process.env.NODE_ENV !== "production") {
      console.warn("[analytics.track] failed:", err)
    }
    return false
  }
}

export async function identify(
  userId: string,
  traits?: Record<string, unknown>,
): Promise<boolean> {
  if (!userId) return false
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(_DISTINCT_ID_KEY, userId)
    } catch {
      // ignore quota / disabled storage
    }
  }
  return track("$identify", { $set: traits || {} }, { distinctId: userId })
}

export async function pageview(
  path: string,
  properties?: Record<string, unknown>,
): Promise<boolean> {
  return track("$pageview", { $current_url: path, ...(properties || {}) })
}
