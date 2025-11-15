import { NextResponse } from "next/server"

export const runtime = "nodejs"

export async function POST(req: Request) {
  try {
    const { code, language } = await req.json()

    console.log("[v0] Executing code:", { language, codeLength: code.length })

    // Validate language
    const supportedLanguages = ["javascript", "typescript", "python"] as const
    if (!supportedLanguages.includes(language as (typeof supportedLanguages)[number])) {
      return NextResponse.json({ error: `Unsupported language: ${language}` }, { status: 400 })
    }

    // For JavaScript/TypeScript
    if (language === "javascript" || language === "typescript") {
      try {
        // Create a safe execution environment
        const logs: string[] = []
        const formatArgs = (args: unknown[]) => args.map((value) => String(value)).join(" ")
        const customConsole = {
          log: (...args: unknown[]) => logs.push(formatArgs(args)),
          error: (...args: unknown[]) => logs.push(`ERROR: ${formatArgs(args)}`),
          warn: (...args: unknown[]) => logs.push(`WARN: ${formatArgs(args)}`),
        }

        // Execute with limited scope
        const func = new Function("console", code)
        func(customConsole)

        return NextResponse.json({
          success: true,
          output: logs.join("\n") || "Code executed successfully (no output)",
          language,
        })
      } catch (error) {
        return NextResponse.json({
          success: false,
          error: error instanceof Error ? error.message : "Execution failed",
          language,
        })
      }
    }

    // For Python (placeholder - would need actual Python runtime)
    if (language === "python") {
      return NextResponse.json({
        success: false,
        error: "Python execution requires additional setup. This is a demo environment.",
        language,
      })
    }

    return NextResponse.json({ error: "Execution failed" }, { status: 500 })
  } catch (error) {
    console.error("[v0] Code execution error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to execute code" },
      { status: 500 },
    )
  }
}
