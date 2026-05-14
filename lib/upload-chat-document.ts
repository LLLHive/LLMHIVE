import { API_ROUTES } from "@/lib/routes"

export type ChatDocumentUploadResponse = {
  gs_uri: string
  object_path: string
  bucket: string
  size: number
  content_type: string
  original_filename: string
  signed_read_url?: string | null
}

/**
 * Upload a chat attachment (e.g. PDF) via the Next.js route. The server attaches
 * the authenticated Clerk user id when calling the orchestrator.
 */
export async function uploadChatDocument(
  file: File,
  refreshSession?: () => Promise<void>
): Promise<ChatDocumentUploadResponse> {
  const post = async () => {
    const fd = new FormData()
    fd.append("file", file)
    return fetch(API_ROUTES.UPLOAD_CHAT_DOCUMENT, { method: "POST", body: fd })
  }

  let res = await post()
  if (res.status === 401 && refreshSession) {
    await refreshSession()
    res = await post()
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = (await res.json()) as Record<string, unknown>
      const d = j.detail
      if (typeof d === "string" && d.trim()) {
        detail = d
      } else if (d && typeof d === "object" && "message" in d) {
        const m = (d as { message?: unknown }).message
        if (typeof m === "string" && m.trim()) detail = m
      }
      if (detail === res.statusText) {
        const err = j.error
        const details = j.details
        if (typeof err === "string" && err.trim()) detail = err
        else if (typeof details === "string" && details.trim()) detail = details
        else if (typeof j.message === "string" && j.message.trim()) detail = j.message
      }
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail || `Upload failed (${res.status})`)
  }

  return (await res.json()) as ChatDocumentUploadResponse
}
