export const runtime = "nodejs"

import { NextResponse } from "next/server"
import { appendFile, mkdir } from "fs/promises"
import path from "path"

const ENDPOINT = "http://127.0.0.1:7242/ingest/fe924509-9f05-47fd-9afa-b8675c0d7b63"
const LOG_PATH = path.resolve(process.cwd(), ".cursor/debug.log")

export async function POST(req: Request) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ ok: false, error: "invalid-json" }, { status: 400 })
  }

  let forwardOk = false
  let forwardError: string | null = null
  try {
    await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    forwardOk = true
  } catch (error) {
    forwardOk = false
    forwardError = error instanceof Error ? error.message : "unknown-error"
  }

  // Always write to local debug log for runtime evidence
  try {
    const record = {
      ...(typeof body === "object" && body !== null ? body : { payload: body }),
      forwardOk,
      forwardError,
      timestamp: Date.now(),
    }
    await mkdir(path.dirname(LOG_PATH), { recursive: true })
    await appendFile(LOG_PATH, JSON.stringify(record) + "\n", { encoding: "utf8" })
  } catch {
    // Swallow file write errors to avoid breaking API route
  }

  if (!forwardOk) {
    return NextResponse.json({ ok: false, error: "forward-failed" }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}

