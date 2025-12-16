"use client"

export type DebugLogPayload = {
  sessionId: string
  runId?: string
  hypothesisId?: string
  location?: string
  message: string
  data?: Record<string, unknown>
  timestamp?: number
}

/**
 * Sends a debug log payload through the local debug proxy API.
 * Falls back silently if the request fails; avoids throwing to keep UI stable.
 */
export async function sendDebugLog(payload: DebugLogPayload) {
  try {
    const enriched = { ...payload, timestamp: payload.timestamp ?? Date.now() }
    await fetch("/api/debug-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(enriched),
    })
  } catch {
    // Intentionally swallow errors to avoid impacting UX
  }
}

