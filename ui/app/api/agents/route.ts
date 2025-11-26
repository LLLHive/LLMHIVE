import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.ORCHESTRATOR_API_BASE_URL || 'http://localhost:8000'
    
    // Fetch connected agents from the backend
    const response = await fetch(`${backendUrl}/api/agents`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      // Return default agents if backend is unavailable
      return NextResponse.json({
        agents: [
          { id: 'general', name: 'General Agent', provider: 'openai', model: 'gpt-4', status: 'active' },
          { id: 'research', name: 'Research Agent', provider: 'anthropic', model: 'claude-3-opus', status: 'active' },
          { id: 'coding', name: 'Coding Agent', provider: 'openai', model: 'gpt-4-turbo', status: 'active' },
        ]
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('[Agents API Error]:', error)
    // Return default agents on error
    return NextResponse.json({
      agents: [
        { id: 'general', name: 'General Agent', provider: 'openai', model: 'gpt-4', status: 'active' },
        { id: 'research', name: 'Research Agent', provider: 'anthropic', model: 'claude-3-opus', status: 'active' },
        { id: 'coding', name: 'Coding Agent', provider: 'openai', model: 'gpt-4-turbo', status: 'active' },
      ]
    })
  }
}
