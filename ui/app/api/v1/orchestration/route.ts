import { NextResponse } from "next/server";

export const runtime = "nodejs";

const PUBLIC_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const CONFIGURED_BASE =
  process.env.ORCHESTRATOR_API_BASE_URL ?? (PUBLIC_BASE || undefined);

const DEFAULT_LOCAL_BASE = "http://127.0.0.1:8000";
const baseToUse = (CONFIGURED_BASE ?? DEFAULT_LOCAL_BASE).replace(/\/$/, "");
const upstreamUrl = `${baseToUse}/api/v1/orchestration`;

function buildErrorResponse(
  message: string,
  status: number = 500,
  details?: unknown
) {
  return NextResponse.json(
    {
      error: message,
      details,
    },
    { status }
  );
}

export async function POST(request: Request) {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch (error) {
    return buildErrorResponse("Invalid JSON payload", 400, {
      error: error instanceof Error ? error.message : String(error),
    });
  }

  if (!CONFIGURED_BASE && process.env.NODE_ENV === "production") {
    return buildErrorResponse(
      "Orchestration API base URL is not configured. Set ORCHESTRATOR_API_BASE_URL to your backend.",
      500
    );
  }

  try {
    const response = await fetch(upstreamUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const text = await response.text();

    if (!response.ok) {
      try {
        const data = text ? JSON.parse(text) : {};
        return NextResponse.json(data, { status: response.status });
      } catch {
        return buildErrorResponse(
          text || response.statusText || "Upstream orchestration error",
          response.status
        );
      }
    }

    const data = text ? JSON.parse(text) : {};
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return buildErrorResponse("Failed to reach orchestration service", 502, {
      error: error instanceof Error ? error.message : String(error),
      upstream: upstreamUrl,
      configuredBase: CONFIGURED_BASE ?? null,
    });
  }
}
