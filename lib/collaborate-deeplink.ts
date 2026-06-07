const COLLABORATE_SESSION_STORAGE_KEY = "llmhive_collaborate_session"

/** Persist session id for CollaborationPanel to pick up after /app loads. */
export function stashCollaborateSession(sessionId: string) {
  if (typeof window === "undefined") return
  sessionStorage.setItem(COLLABORATE_SESSION_STORAGE_KEY, sessionId)
}

export function consumeCollaborateSession(): string | null {
  if (typeof window === "undefined") return null
  const sessionId = sessionStorage.getItem(COLLABORATE_SESSION_STORAGE_KEY)
  if (sessionId) {
    sessionStorage.removeItem(COLLABORATE_SESSION_STORAGE_KEY)
  }
  return sessionId
}
