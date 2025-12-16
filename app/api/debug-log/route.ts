import { NextResponse } from "next/server"

// Debug log endpoint - silent success to avoid blocking errors
export async function POST(req: Request) {
  try {
    // Just consume the body silently
    await req.json()
  } catch {
    // Ignore parse errors
  }
  
  // Always return success - debug logs are optional
  return NextResponse.json({ ok: true })
}

