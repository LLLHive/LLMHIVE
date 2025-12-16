import { NextResponse } from "next/server"

// Mock rankings data until backend is ready
const MOCK_RANKINGS = {
  trending: [
    { id: "openai/gpt-4o", name: "GPT-4o", score: 95, change: 12 },
    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", score: 92, change: 8 },
    { id: "google/gemini-pro-1.5", name: "Gemini 1.5 Pro", score: 88, change: 5 },
    { id: "meta-llama/llama-3.3-70b", name: "Llama 3.3 70B", score: 85, change: 15 },
    { id: "deepseek/deepseek-chat", name: "DeepSeek Chat", score: 82, change: 20 },
  ],
  most_used: [
    { id: "openai/gpt-4o", name: "GPT-4o", score: 100, requests: 125000 },
    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", score: 85, requests: 98000 },
    { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", score: 75, requests: 87000 },
    { id: "google/gemini-flash-1.5", name: "Gemini 1.5 Flash", score: 60, requests: 65000 },
    { id: "meta-llama/llama-3.3-70b", name: "Llama 3.3 70B", score: 45, requests: 42000 },
  ],
  best_value: [
    { id: "deepseek/deepseek-chat", name: "DeepSeek Chat", score: 98, cost_per_quality: 0.02 },
    { id: "meta-llama/llama-3.3-70b", name: "Llama 3.3 70B", score: 92, cost_per_quality: 0.05 },
    { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", score: 88, cost_per_quality: 0.08 },
    { id: "google/gemini-flash-1.5", name: "Gemini 1.5 Flash", score: 85, cost_per_quality: 0.10 },
    { id: "mistral/mistral-large", name: "Mistral Large", score: 80, cost_per_quality: 0.15 },
  ],
  long_context: [
    { id: "google/gemini-pro-1.5", name: "Gemini 1.5 Pro", score: 100, context: 2000000 },
    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", score: 90, context: 200000 },
    { id: "openai/gpt-4o", name: "GPT-4o", score: 65, context: 128000 },
    { id: "meta-llama/llama-3.3-70b", name: "Llama 3.3 70B", score: 60, context: 128000 },
    { id: "deepseek/deepseek-chat", name: "DeepSeek Chat", score: 50, context: 64000 },
  ],
  tools_agents: [
    { id: "openai/gpt-4o", name: "GPT-4o", score: 98, tool_success_rate: 0.95 },
    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", score: 95, tool_success_rate: 0.92 },
    { id: "google/gemini-pro-1.5", name: "Gemini 1.5 Pro", score: 88, tool_success_rate: 0.85 },
    { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", score: 82, tool_success_rate: 0.80 },
    { id: "mistral/mistral-large", name: "Mistral Large", score: 75, tool_success_rate: 0.72 },
  ],
  multimodal: [
    { id: "openai/gpt-4o", name: "GPT-4o", score: 98, modalities: ["text", "image", "audio"] },
    { id: "google/gemini-pro-1.5", name: "Gemini 1.5 Pro", score: 95, modalities: ["text", "image", "video"] },
    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", score: 90, modalities: ["text", "image"] },
    { id: "meta-llama/llama-3.2-90b-vision", name: "Llama 3.2 90B Vision", score: 85, modalities: ["text", "image"] },
  ],
  fastest: [
    { id: "google/gemini-flash-1.5", name: "Gemini 1.5 Flash", score: 100, latency_ms: 120 },
    { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", score: 95, latency_ms: 150 },
    { id: "anthropic/claude-3-haiku", name: "Claude 3 Haiku", score: 92, latency_ms: 180 },
    { id: "deepseek/deepseek-chat", name: "DeepSeek Chat", score: 85, latency_ms: 250 },
    { id: "mistral/mistral-small", name: "Mistral Small", score: 80, latency_ms: 300 },
  ],
  most_reliable: [
    { id: "openai/gpt-4o", name: "GPT-4o", score: 99, uptime: 0.999 },
    { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", score: 98, uptime: 0.998 },
    { id: "google/gemini-pro-1.5", name: "Gemini 1.5 Pro", score: 97, uptime: 0.997 },
    { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", score: 96, uptime: 0.996 },
    { id: "mistral/mistral-large", name: "Mistral Large", score: 94, uptime: 0.994 },
  ],
  lowest_cost: [
    { id: "deepseek/deepseek-chat", name: "DeepSeek Chat", score: 100, cost_per_1m: 0.14 },
    { id: "meta-llama/llama-3.3-70b", name: "Llama 3.3 70B", score: 95, cost_per_1m: 0.40 },
    { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", score: 85, cost_per_1m: 0.60 },
    { id: "google/gemini-flash-1.5", name: "Gemini 1.5 Flash", score: 80, cost_per_1m: 0.70 },
    { id: "mistral/mistral-small", name: "Mistral Small", score: 75, cost_per_1m: 0.90 },
  ],
}

type DimensionKey = keyof typeof MOCK_RANKINGS

export async function GET(
  request: Request,
  { params }: { params: Promise<{ dimension: string }> }
) {
  const { dimension } = await params
  
  // Return mock data for now
  const rankings = MOCK_RANKINGS[dimension as DimensionKey] || MOCK_RANKINGS.trending
  
  return NextResponse.json({
    dimension,
    time_range: "7d",
    data: rankings,
    total: rankings.length,
    data_source: "internal_telemetry",
    last_updated: new Date().toISOString(),
  })
}

