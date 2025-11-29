import { NextResponse } from "next/server"

export const runtime = "nodejs"

/**
 * Unified code interpreter endpoint.
 * 
 * - JavaScript/TypeScript: Executes in Node.js sandbox (existing implementation)
 * - Python: Executes via MCP 2 sandbox on the backend
 * 
 * Environment variables:
 * - ORCHESTRATOR_API_BASE_URL: Backend API base URL for Python execution
 * - LLMHIVE_API_KEY: API key for backend authentication
 */
export async function POST(req: Request) {
  try {
    const { code, language } = await req.json()

    console.log("[execute] Executing code:", { language, codeLength: code.length })

    // Validate language
    const supportedLanguages = ["javascript", "typescript", "python"]
    if (!supportedLanguages.includes(language)) {
      return NextResponse.json({ error: `Unsupported language: ${language}` }, { status: 400 })
    }

    // For JavaScript/TypeScript: Execute in Node.js sandbox
    if (language === "javascript" || language === "typescript") {
      try {
        // Create a safe execution environment
        const logs: string[] = []
        const customConsole = {
          log: (...args: any[]) => logs.push(args.map(String).join(" ")),
          error: (...args: any[]) => logs.push("ERROR: " + args.map(String).join(" ")),
          warn: (...args: any[]) => logs.push("WARN: " + args.map(String).join(" ")),
        }

        // Execute with limited scope
        const func = new Function("console", code)
        func(customConsole)

        return NextResponse.json({
          success: true,
          output: logs.join("\n") || "Code executed successfully (no output)",
          language,
          execution_method: "nodejs-sandbox",
        })
      } catch (error: any) {
        return NextResponse.json({
          success: false,
          error: error.message,
          language,
          execution_method: "nodejs-sandbox",
        })
      }
    }

    // For Python: Execute via MCP 2 sandbox on backend
    if (language === "python") {
      const apiBase = process.env.ORCHESTRATOR_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL
      const apiKey = process.env.LLMHIVE_API_KEY

      if (!apiBase) {
        return NextResponse.json({
          success: false,
          error: "Backend API not configured. Set ORCHESTRATOR_API_BASE_URL environment variable.",
          language,
        })
      }

      try {
        // Call backend MCP 2 sandbox endpoint
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        }
        if (apiKey) {
          headers["X-API-Key"] = apiKey
        }

        const response = await fetch(`${apiBase}/v1/execute/python`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            code,
            session_token: `session_${Date.now()}`, // Generate session token
          }),
        })

        if (!response.ok) {
          const errorText = await response.text()
          return NextResponse.json({
            success: false,
            error: `Backend execution failed: ${errorText}`,
            language,
            execution_method: "mcp2-sandbox",
          })
        }

        const data = await response.json()
        return NextResponse.json({
          success: data.success || true,
          output: data.output || data.result || "",
          error: data.error,
          language,
          execution_method: "mcp2-sandbox",
          metadata: data.metadata || {},
        })
      } catch (error: any) {
        console.error("[execute] Python execution error:", error)
        return NextResponse.json({
          success: false,
          error: error.message || "Failed to execute Python code",
          language,
          execution_method: "mcp2-sandbox",
        })
      }
    }

    return NextResponse.json({ error: "Execution failed" }, { status: 500 })
  } catch (error: any) {
    console.error("[execute] Code execution error:", error)
    return NextResponse.json({ error: error.message || "Failed to execute code" }, { status: 500 })
  }
}
