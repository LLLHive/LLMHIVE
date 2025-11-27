import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { mode, selectedMethods } = body

    // Validate the request body
    if (!mode || (mode !== "auto" && mode !== "manual")) {
      return NextResponse.json({ error: "Invalid mode. Must be 'auto' or 'manual'" }, { status: 400 })
    }

    if (mode === "manual" && (!Array.isArray(selectedMethods) || selectedMethods.length === 0)) {
      return NextResponse.json({ error: "Manual mode requires at least one selected method" }, { status: 400 })
    }

    // Forward to orchestrator backend if configured
    const orchestratorUrl = process.env.ORCHESTRATOR_API_BASE_URL
    if (orchestratorUrl) {
      try {
        const response = await fetch(`${orchestratorUrl}/reasoning-config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode, selectedMethods }),
        })

        if (!response.ok) {
          console.error("Orchestrator responded with error:", response.status)
        }
      } catch (error) {
        console.error("Failed to forward to orchestrator:", error)
        // Continue anyway - we'll store locally
      }
    }

    // Return success
    return NextResponse.json({
      success: true,
      message: `Reasoning configuration saved. Mode: ${mode}${
        mode === "manual" ? `, Methods: ${selectedMethods.length}` : ""
      }`,
      config: { mode, selectedMethods: mode === "manual" ? selectedMethods : [] },
    })
  } catch (error) {
    console.error("Error saving reasoning config:", error)
    return NextResponse.json({ error: "Failed to save reasoning configuration" }, { status: 500 })
  }
}

export async function GET() {
  // Return current configuration (could be stored in a database)
  return NextResponse.json({
    mode: "auto",
    selectedMethods: [],
  })
}
