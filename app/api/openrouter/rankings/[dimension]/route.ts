import { NextResponse } from "next/server"

// Create a mock model
function mockModel(id: string, name: string, context: number = 128000, promptCost: number = 5) {
  return {
    id,
    name,
    description: `${name} - a powerful language model`,
    context_length: context,
    architecture: { modality: "text", tokenizer: "gpt", instruct_type: "chat" },
    pricing: {
      prompt: promptCost / 1000000,
      completion: promptCost * 3 / 1000000,
      per_1m_prompt: promptCost,
      per_1m_completion: promptCost * 3,
    },
    capabilities: {
      supports_tools: true,
      supports_structured: true,
      supports_streaming: true,
      multimodal_input: id.includes("gpt-4o") || id.includes("gemini"),
      multimodal_output: false,
    },
    is_free: false,
    availability_score: 0.99,
    is_active: true,
  }
}

// Mock rankings data with proper RankedModel format - updated with latest models
const MOCK_RANKINGS: Record<string, Array<{ model: ReturnType<typeof mockModel>, rank: number, score: number, metrics: Record<string, number | string> }>> = {
  trending: [
    { model: mockModel("openai/gpt-5.2", "GPT-5.2", 128000, 15), rank: 1, score: 99, metrics: { change: 50, usage_count: 180000 } },
    { model: mockModel("openai/gpt-5.2-pro", "GPT-5.2 Pro", 200000, 30), rank: 2, score: 97, metrics: { change: 45, usage_count: 95000 } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, 3), rank: 3, score: 92, metrics: { change: 8, usage_count: 98000 } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", 128000, 5), rank: 4, score: 88, metrics: { change: -5, usage_count: 125000 } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", 1000000, 0.3), rank: 5, score: 85, metrics: { change: 25, usage_count: 75000 } },
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", 64000, 0.14), rank: 6, score: 82, metrics: { change: 20, usage_count: 68000 } },
    { model: mockModel("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B Instruct", 128000, 0.9), rank: 7, score: 80, metrics: { change: 15, usage_count: 42000 } },
  ],
  most_used: [
    { model: mockModel("openai/gpt-5.2", "GPT-5.2", 128000, 15), rank: 1, score: 100, metrics: { usage_count: 180000 } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", 128000, 5), rank: 2, score: 90, metrics: { usage_count: 125000 } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, 3), rank: 3, score: 85, metrics: { usage_count: 98000 } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", 128000, 0.6), rank: 4, score: 75, metrics: { usage_count: 87000 } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", 1000000, 0.3), rank: 5, score: 65, metrics: { usage_count: 75000 } },
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", 64000, 0.14), rank: 6, score: 55, metrics: { usage_count: 68000 } },
    { model: mockModel("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B Instruct", 128000, 0.9), rank: 7, score: 45, metrics: { usage_count: 42000 } },
  ],
  best_value: [
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", 64000, 0.14), rank: 1, score: 98, metrics: { cost_efficiency: 0.02 } },
    { model: mockModel("meta-llama/llama-3.3-70b", "Llama 3.3 70B", 128000, 0.9), rank: 2, score: 92, metrics: { cost_efficiency: 0.05 } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", 128000, 0.6), rank: 3, score: 88, metrics: { cost_efficiency: 0.08 } },
    { model: mockModel("google/gemini-flash-1.5", "Gemini 1.5 Flash", 1000000, 0.7), rank: 4, score: 85, metrics: { cost_efficiency: 0.10 } },
    { model: mockModel("mistral/mistral-large", "Mistral Large", 32000, 8), rank: 5, score: 80, metrics: { cost_efficiency: 0.15 } },
  ],
  long_context: [
    { model: mockModel("google/gemini-pro-1.5", "Gemini 1.5 Pro", 2000000, 2.5), rank: 1, score: 100, metrics: { context_length: 2000000 } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, 3), rank: 2, score: 90, metrics: { context_length: 200000 } },
    { model: mockModel("openai/gpt-4o", "GPT-4o"), rank: 3, score: 65, metrics: { context_length: 128000 } },
    { model: mockModel("meta-llama/llama-3.3-70b", "Llama 3.3 70B", 128000, 0.9), rank: 4, score: 60, metrics: { context_length: 128000 } },
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", 64000, 0.14), rank: 5, score: 50, metrics: { context_length: 64000 } },
  ],
  tools_agents: [
    { model: mockModel("openai/gpt-4o", "GPT-4o"), rank: 1, score: 98, metrics: { tool_success_rate: 0.95 } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, 3), rank: 2, score: 95, metrics: { tool_success_rate: 0.92 } },
    { model: mockModel("google/gemini-pro-1.5", "Gemini 1.5 Pro", 2000000, 2.5), rank: 3, score: 88, metrics: { tool_success_rate: 0.85 } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", 128000, 0.6), rank: 4, score: 82, metrics: { tool_success_rate: 0.80 } },
    { model: mockModel("mistral/mistral-large", "Mistral Large", 32000, 8), rank: 5, score: 75, metrics: { tool_success_rate: 0.72 } },
  ],
  multimodal: [
    { model: mockModel("openai/gpt-4o", "GPT-4o"), rank: 1, score: 98, metrics: { modalities: "text, image, audio" } },
    { model: mockModel("google/gemini-pro-1.5", "Gemini 1.5 Pro", 2000000, 2.5), rank: 2, score: 95, metrics: { modalities: "text, image, video" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, 3), rank: 3, score: 90, metrics: { modalities: "text, image" } },
    { model: mockModel("meta-llama/llama-3.2-90b-vision", "Llama 3.2 90B Vision", 128000, 1.2), rank: 4, score: 85, metrics: { modalities: "text, image" } },
  ],
  fastest: [
    { model: mockModel("google/gemini-flash-1.5", "Gemini 1.5 Flash", 1000000, 0.7), rank: 1, score: 100, metrics: { latency_ms: 120 } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", 128000, 0.6), rank: 2, score: 95, metrics: { latency_ms: 150 } },
    { model: mockModel("anthropic/claude-3-haiku", "Claude 3 Haiku", 200000, 0.25), rank: 3, score: 92, metrics: { latency_ms: 180 } },
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", 64000, 0.14), rank: 4, score: 85, metrics: { latency_ms: 250 } },
    { model: mockModel("mistral/mistral-small", "Mistral Small", 32000, 0.2), rank: 5, score: 80, metrics: { latency_ms: 300 } },
  ],
  most_reliable: [
    { model: mockModel("openai/gpt-4o", "GPT-4o"), rank: 1, score: 99.9, metrics: { uptime: 0.999 } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 200000, 3), rank: 2, score: 99.8, metrics: { uptime: 0.998 } },
    { model: mockModel("google/gemini-pro-1.5", "Gemini 1.5 Pro", 2000000, 2.5), rank: 3, score: 99.7, metrics: { uptime: 0.997 } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", 128000, 0.6), rank: 4, score: 99.6, metrics: { uptime: 0.996 } },
    { model: mockModel("mistral/mistral-large", "Mistral Large", 32000, 8), rank: 5, score: 99.4, metrics: { uptime: 0.994 } },
  ],
  lowest_cost: [
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", 64000, 0.14), rank: 1, score: 100, metrics: { cost_per_1m: 0.14 } },
    { model: mockModel("meta-llama/llama-3.3-70b", "Llama 3.3 70B", 128000, 0.40), rank: 2, score: 95, metrics: { cost_per_1m: 0.40 } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", 128000, 0.60), rank: 3, score: 85, metrics: { cost_per_1m: 0.60 } },
    { model: mockModel("google/gemini-flash-1.5", "Gemini 1.5 Flash", 1000000, 0.70), rank: 4, score: 80, metrics: { cost_per_1m: 0.70 } },
    { model: mockModel("mistral/mistral-small", "Mistral Small", 32000, 0.20), rank: 5, score: 75, metrics: { cost_per_1m: 0.20 } },
  ],
}

type DimensionKey = keyof typeof MOCK_RANKINGS

export async function GET(
  request: Request,
  { params }: { params: Promise<{ dimension: string }> }
) {
  const { dimension } = await params
  
  // Return mock data in proper RankedModel format
  const rankings = MOCK_RANKINGS[dimension as DimensionKey] || MOCK_RANKINGS.trending
  
  return NextResponse.json({
    dimension,
    time_range: "7d",
    models: rankings,
    count: rankings.length,
    data_source: "internal_telemetry",
    generated_at: new Date().toISOString(),
    metric_definitions: {
      score: "Overall ranking score (0-100)",
      usage_count: "Total API requests in period",
    },
  })
}

