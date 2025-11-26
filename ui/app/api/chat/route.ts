import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { messages, models, reasoningMode, capabilities, criteriaSettings, orchestrationEngine, advancedFeatures } = body

    // Get the backend API URL from environment
    const backendUrl = process.env.ORCHESTRATOR_API_BASE_URL || 'http://localhost:8000'
    
    // Call the backend orchestrator
    const response = await fetch(`${backendUrl}/api/orchestrate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        models,
        reasoning_mode: reasoningMode,
        capabilities,
        criteria_settings: criteriaSettings,
        orchestration_engine: orchestrationEngine,
        advanced_features: advancedFeatures,
      }),
    })

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.statusText}`)
    }

    const data = await response.json()
    
    // Stream the response back
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(data.content || data.response || 'No response from AI'))
        controller.close()
      },
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
      },
    })
  } catch (error) {
    console.error('[Chat API Error]:', error)
    return NextResponse.json(
      { error: 'Failed to process chat request', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
