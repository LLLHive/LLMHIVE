import { NextResponse } from "next/server"

// Create a mock model with realistic data
function mockModel(
  id: string, 
  name: string, 
  author: string,
  context: number = 128000, 
  promptCost: number = 5,
  tokensUsed: string = "10B"
) {
  return {
    id,
    name,
    author,
    description: `${name} by ${author}`,
    context_length: context,
    tokens_used: tokensUsed,
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
      multimodal_input: id.includes("gpt-4o") || id.includes("gemini") || id.includes("vision"),
      multimodal_output: false,
    },
    is_free: promptCost === 0,
    availability_score: 0.99,
    is_active: true,
  }
}

type MockRanking = {
  model: ReturnType<typeof mockModel>
  rank: number
  score: number
  metrics: Record<string, number | string>
}

// Mock rankings data reflecting OpenRouter's actual leaderboard
const MOCK_RANKINGS: Record<string, MockRanking[]> = {
  // Main Leaderboard - Token usage across models
  leaderboard: [
    { model: mockModel("x-ai/grok-code-fast-1", "Grok Code Fast 1", "x-ai", 128000, 2, "548B"), rank: 1, score: 100, metrics: { tokens: "548B", change: 38 } },
    { model: mockModel("google/gemini-2.5-flash", "Gemini 2.5 Flash", "google", 1000000, 0.3, "449B"), rank: 2, score: 82, metrics: { tokens: "449B", change: 8 } },
    { model: mockModel("anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5", "anthropic", 200000, 3, "420B"), rank: 3, score: 77, metrics: { tokens: "420B", change: 5 } },
    { model: mockModel("openai/gpt-oss-120b", "GPT-OSS-120B", "openai", 128000, 15, "361B"), rank: 4, score: 66, metrics: { tokens: "361B", change: 122 } },
    { model: mockModel("anthropic/claude-opus-4.5", "Claude Opus 4.5", "anthropic", 200000, 15, "206B"), rank: 5, score: 38, metrics: { tokens: "206B", change: 7 } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3, "186B"), rank: 6, score: 34, metrics: { tokens: "186B", change: 7 } },
    { model: mockModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite", "google", 1000000, 0.15, "167B"), rank: 7, score: 30, metrics: { tokens: "167B", change: 13 } },
    { model: mockModel("x-ai/grok-4-fast", "Grok 4 Fast", "x-ai", 128000, 5, "156B"), rank: 8, score: 28, metrics: { tokens: "156B", change: 6 } },
    { model: mockModel("google/gemini-3-pro-preview", "Gemini 3 Pro Preview", "google", 2000000, 5, "150B"), rank: 9, score: 27, metrics: { tokens: "150B", change: 14 } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "149B"), rank: 10, score: 27, metrics: { tokens: "149B", change: 9 } },
  ],
  
  // Market Share by Author
  market_share: [
    { model: mockModel("google/gemini", "Google Models", "google", 0, 0, "378B"), rank: 1, score: 21.3, metrics: { share: "21.3%", tokens: "378B" } },
    { model: mockModel("openai/gpt", "OpenAI Models", "openai", 0, 0, "347B"), rank: 2, score: 19.6, metrics: { share: "19.6%", tokens: "347B" } },
    { model: mockModel("x-ai/grok", "X-AI Models", "x-ai", 0, 0, "266B"), rank: 3, score: 15.0, metrics: { share: "15.0%", tokens: "266B" } },
    { model: mockModel("anthropic/claude", "Anthropic Models", "anthropic", 0, 0, "250B"), rank: 4, score: 14.1, metrics: { share: "14.1%", tokens: "250B" } },
    { model: mockModel("deepseek/deepseek", "DeepSeek Models", "deepseek", 0, 0, "140B"), rank: 5, score: 7.9, metrics: { share: "7.9%", tokens: "140B" } },
    { model: mockModel("mistralai/mistral", "Mistral AI Models", "mistralai", 0, 0, "74.3B"), rank: 6, score: 4.2, metrics: { share: "4.2%", tokens: "74.3B" } },
    { model: mockModel("qwen/qwen", "Qwen Models", "qwen", 0, 0, "69.1B"), rank: 7, score: 3.9, metrics: { share: "3.9%", tokens: "69.1B" } },
  ],
  
  // Programming Category
  programming: [
    { model: mockModel("x-ai/grok-code-fast-1", "Grok Code Fast 1", "x-ai", 128000, 2, "1.24T"), rank: 1, score: 49.2, metrics: { share: "49.2%", tokens: "1.24T" } },
    { model: mockModel("anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5", "anthropic", 200000, 3, "291B"), rank: 2, score: 11.5, metrics: { share: "11.5%", tokens: "291B" } },
    { model: mockModel("minimax/minimax-m2", "MiniMax M2", "minimax", 128000, 1, "179B"), rank: 3, score: 7.1, metrics: { share: "7.1%", tokens: "179B" } },
    { model: mockModel("qwen/qwen3-coder-30b", "Qwen3 Coder 30B", "qwen", 128000, 0.5, "102B"), rank: 4, score: 4.0, metrics: { share: "4.0%", tokens: "102B" } },
    { model: mockModel("google/gemini-3-pro-preview", "Gemini 3 Pro Preview", "google", 2000000, 5, "84B"), rank: 5, score: 3.3, metrics: { share: "3.3%", tokens: "84B" } },
    { model: mockModel("kwaipilot/kat-coder-pro", "Kat Coder Pro V1", "kwaipilot", 64000, 0.8, "53.8B"), rank: 6, score: 2.1, metrics: { share: "2.1%", tokens: "53.8B" } },
    { model: mockModel("anthropic/claude-sonnet-4", "Claude Sonnet 4", "anthropic", 200000, 2, "40.6B"), rank: 7, score: 1.6, metrics: { share: "1.6%", tokens: "40.6B" } },
    { model: mockModel("google/gemini-2.5-flash", "Gemini 2.5 Flash", "google", 1000000, 0.3, "40.3B"), rank: 8, score: 1.6, metrics: { share: "1.6%", tokens: "40.3B" } },
  ],
  
  // Roleplay Category
  roleplay: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "85B"), rank: 1, score: 25, metrics: { share: "25%", tokens: "85B" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "72B"), rank: 2, score: 21, metrics: { share: "21%", tokens: "72B" } },
    { model: mockModel("meta-llama/llama-3.3-70b", "Llama 3.3 70B", "meta-llama", 128000, 0.9, "45B"), rank: 3, score: 13, metrics: { share: "13%", tokens: "45B" } },
    { model: mockModel("mistralai/mistral-large", "Mistral Large", "mistralai", 128000, 8, "38B"), rank: 4, score: 11, metrics: { share: "11%", tokens: "38B" } },
    { model: mockModel("nousresearch/hermes-3-llama-3.1-405b", "Hermes 3 Llama 405B", "nousresearch", 128000, 2, "25B"), rank: 5, score: 7, metrics: { share: "7%", tokens: "25B" } },
  ],
  
  // Marketing Category
  marketing: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "120B"), rank: 1, score: 35, metrics: { share: "35%", tokens: "120B" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "85B"), rank: 2, score: 25, metrics: { share: "25%", tokens: "85B" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3, "55B"), rank: 3, score: 16, metrics: { share: "16%", tokens: "55B" } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", "openai", 128000, 0.6, "42B"), rank: 4, score: 12, metrics: { share: "12%", tokens: "42B" } },
  ],
  
  // SEO Category
  seo: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "95B"), rank: 1, score: 40, metrics: { share: "40%", tokens: "95B" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "65B"), rank: 2, score: 27, metrics: { share: "27%", tokens: "65B" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3, "45B"), rank: 3, score: 19, metrics: { share: "19%", tokens: "45B" } },
  ],
  
  // Technology Category
  technology: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "150B"), rank: 1, score: 32, metrics: { share: "32%", tokens: "150B" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "120B"), rank: 2, score: 26, metrics: { share: "26%", tokens: "120B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "85B"), rank: 3, score: 18, metrics: { share: "18%", tokens: "85B" } },
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", "deepseek", 64000, 0.14, "55B"), rank: 4, score: 12, metrics: { share: "12%", tokens: "55B" } },
  ],
  
  // Science Category
  science: [
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "95B"), rank: 1, score: 35, metrics: { share: "35%", tokens: "95B" } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "85B"), rank: 2, score: 31, metrics: { share: "31%", tokens: "85B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "50B"), rank: 3, score: 18, metrics: { share: "18%", tokens: "50B" } },
  ],
  
  // Translation Category  
  translation: [
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3, "85B"), rank: 1, score: 38, metrics: { share: "38%", tokens: "85B" } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "65B"), rank: 2, score: 29, metrics: { share: "29%", tokens: "65B" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "45B"), rank: 3, score: 20, metrics: { share: "20%", tokens: "45B" } },
  ],
  
  // Legal Category
  legal: [
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "75B"), rank: 1, score: 42, metrics: { share: "42%", tokens: "75B" } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "55B"), rank: 2, score: 31, metrics: { share: "31%", tokens: "55B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "28B"), rank: 3, score: 16, metrics: { share: "16%", tokens: "28B" } },
  ],
  
  // Finance Category
  finance: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "95B"), rank: 1, score: 38, metrics: { share: "38%", tokens: "95B" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "72B"), rank: 2, score: 29, metrics: { share: "29%", tokens: "72B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "45B"), rank: 3, score: 18, metrics: { share: "18%", tokens: "45B" } },
  ],
  
  // Health Category
  health: [
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "68B"), rank: 1, score: 40, metrics: { share: "40%", tokens: "68B" } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "52B"), rank: 2, score: 31, metrics: { share: "31%", tokens: "52B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "32B"), rank: 3, score: 19, metrics: { share: "19%", tokens: "32B" } },
  ],
  
  // Academia Category
  academia: [
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3, "85B"), rank: 1, score: 38, metrics: { share: "38%", tokens: "85B" } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5, "72B"), rank: 2, score: 32, metrics: { share: "32%", tokens: "72B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "45B"), rank: 3, score: 20, metrics: { share: "20%", tokens: "45B" } },
  ],
  
  // Tool Calls - Tool usage across models
  tools_agents: [
    { model: mockModel("google/gemini-2.5-flash", "Gemini 2.5 Flash", "google", 1000000, 0.3, "1.64M"), rank: 1, score: 12.9, metrics: { calls: "1.64M", share: "12.9%" } },
    { model: mockModel("z-ai/glm-4.6", "GLM 4.6", "z-ai", 128000, 1, "1.44M"), rank: 2, score: 11.3, metrics: { calls: "1.44M", share: "11.3%" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3, "1.14M"), rank: 3, score: 8.9, metrics: { calls: "1.14M", share: "8.9%" } },
    { model: mockModel("anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5", "anthropic", 200000, 3, "1.04M"), rank: 4, score: 8.2, metrics: { calls: "1.04M", share: "8.2%" } },
    { model: mockModel("x-ai/grok-code-fast-1", "Grok Code Fast 1", "x-ai", 128000, 2, "807K"), rank: 5, score: 6.3, metrics: { calls: "807K", share: "6.3%" } },
    { model: mockModel("minimax/minimax-m2", "MiniMax M2", "minimax", 128000, 1, "477K"), rank: 6, score: 3.7, metrics: { calls: "477K", share: "3.7%" } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", "openai", 128000, 0.6, "448K"), rank: 7, score: 3.5, metrics: { calls: "448K", share: "3.5%" } },
  ],
  
  // Images - Total images processed
  images: [
    { model: mockModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite", "google", 1000000, 0.15, "19.4M"), rank: 1, score: 39.5, metrics: { images: "19.4M", share: "39.5%" } },
    { model: mockModel("google/gemini-2.5-flash", "Gemini 2.5 Flash", "google", 1000000, 0.3, "4.07M"), rank: 2, score: 8.3, metrics: { images: "4.07M", share: "8.3%" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3, "3.62M"), rank: 3, score: 7.4, metrics: { images: "3.62M", share: "7.4%" } },
    { model: mockModel("openai/gpt-5-mini", "GPT-5 Mini", "openai", 128000, 0.8, "2.47M"), rank: 4, score: 5.0, metrics: { images: "2.47M", share: "5.0%" } },
    { model: mockModel("nvidia/nemotron-nano-12b-vl", "Nemotron Nano 12B VL", "nvidia", 32000, 0, "2.13M"), rank: 5, score: 4.3, metrics: { images: "2.13M", share: "4.3%" } },
    { model: mockModel("x-ai/grok-4.1-fast", "Grok 4.1 Fast", "x-ai", 128000, 3, "1.9M"), rank: 6, score: 3.9, metrics: { images: "1.9M", share: "3.9%" } },
    { model: mockModel("anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5", "anthropic", 200000, 3, "1.88M"), rank: 7, score: 3.8, metrics: { images: "1.88M", share: "3.8%" } },
  ],
  
  // Multimodal leaders
  multimodal: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5), rank: 1, score: 98, metrics: { modalities: "text, image, audio" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5), rank: 2, score: 95, metrics: { modalities: "text, image, video" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3), rank: 3, score: 90, metrics: { modalities: "text, image" } },
    { model: mockModel("meta-llama/llama-3.2-90b-vision", "Llama 3.2 90B Vision", "meta-llama", 128000, 1.2), rank: 4, score: 85, metrics: { modalities: "text, image" } },
  ],
  
  // Long Context
  long_context: [
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5), rank: 1, score: 100, metrics: { context_length: "2M tokens" } },
    { model: mockModel("google/gemini-3-pro-preview", "Gemini 3 Pro Preview", "google", 2000000, 5), rank: 2, score: 100, metrics: { context_length: "2M tokens" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3), rank: 3, score: 50, metrics: { context_length: "1M tokens" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3), rank: 4, score: 10, metrics: { context_length: "200K tokens" } },
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5), rank: 5, score: 6.4, metrics: { context_length: "128K tokens" } },
  ],
  
  // Trending
  trending: [
    { model: mockModel("openai/gpt-oss-120b", "GPT-OSS-120B", "openai", 128000, 15, "361B"), rank: 1, score: 122, metrics: { change: "+122%", tokens: "361B" } },
    { model: mockModel("x-ai/grok-code-fast-1", "Grok Code Fast 1", "x-ai", 128000, 2, "548B"), rank: 2, score: 38, metrics: { change: "+38%", tokens: "548B" } },
    { model: mockModel("google/gemini-3-pro-preview", "Gemini 3 Pro Preview", "google", 2000000, 5, "150B"), rank: 3, score: 14, metrics: { change: "+14%", tokens: "150B" } },
    { model: mockModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite", "google", 1000000, 0.15, "167B"), rank: 4, score: 13, metrics: { change: "+13%", tokens: "167B" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5, "149B"), rank: 5, score: 9, metrics: { change: "+9%", tokens: "149B" } },
  ],
  
  // Most Used  
  most_used: [
    { model: mockModel("x-ai/grok-code-fast-1", "Grok Code Fast 1", "x-ai", 128000, 2, "548B"), rank: 1, score: 100, metrics: { tokens: "548B" } },
    { model: mockModel("google/gemini-2.5-flash", "Gemini 2.5 Flash", "google", 1000000, 0.3, "449B"), rank: 2, score: 82, metrics: { tokens: "449B" } },
    { model: mockModel("anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5", "anthropic", 200000, 3, "420B"), rank: 3, score: 77, metrics: { tokens: "420B" } },
    { model: mockModel("openai/gpt-oss-120b", "GPT-OSS-120B", "openai", 128000, 15, "361B"), rank: 4, score: 66, metrics: { tokens: "361B" } },
    { model: mockModel("anthropic/claude-opus-4.5", "Claude Opus 4.5", "anthropic", 200000, 15, "206B"), rank: 5, score: 38, metrics: { tokens: "206B" } },
  ],
  
  // Best Value
  best_value: [
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", "deepseek", 64000, 0.14), rank: 1, score: 98, metrics: { cost_per_1m: "$0.14" } },
    { model: mockModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite", "google", 1000000, 0.15), rank: 2, score: 96, metrics: { cost_per_1m: "$0.15" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3), rank: 3, score: 92, metrics: { cost_per_1m: "$0.30" } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", "openai", 128000, 0.6), rank: 4, score: 88, metrics: { cost_per_1m: "$0.60" } },
    { model: mockModel("meta-llama/llama-3.3-70b", "Llama 3.3 70B", "meta-llama", 128000, 0.9), rank: 5, score: 85, metrics: { cost_per_1m: "$0.90" } },
  ],
  
  // Fastest
  fastest: [
    { model: mockModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite", "google", 1000000, 0.15), rank: 1, score: 100, metrics: { latency: "80ms" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3), rank: 2, score: 95, metrics: { latency: "100ms" } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", "openai", 128000, 0.6), rank: 3, score: 90, metrics: { latency: "150ms" } },
    { model: mockModel("anthropic/claude-3-haiku", "Claude 3 Haiku", "anthropic", 200000, 0.25), rank: 4, score: 88, metrics: { latency: "180ms" } },
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", "deepseek", 64000, 0.14), rank: 5, score: 82, metrics: { latency: "250ms" } },
  ],
  
  // Most Reliable
  most_reliable: [
    { model: mockModel("openai/gpt-4o", "GPT-4o", "openai", 128000, 5), rank: 1, score: 99.9, metrics: { uptime: "99.9%" } },
    { model: mockModel("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "anthropic", 200000, 3), rank: 2, score: 99.8, metrics: { uptime: "99.8%" } },
    { model: mockModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google", 2000000, 2.5), rank: 3, score: 99.7, metrics: { uptime: "99.7%" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3), rank: 4, score: 99.6, metrics: { uptime: "99.6%" } },
  ],
  
  // Lowest Cost
  lowest_cost: [
    { model: mockModel("deepseek/deepseek-chat", "DeepSeek Chat", "deepseek", 64000, 0.14), rank: 1, score: 100, metrics: { cost_per_1m: "$0.14" } },
    { model: mockModel("google/gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite", "google", 1000000, 0.15), rank: 2, score: 97, metrics: { cost_per_1m: "$0.15" } },
    { model: mockModel("anthropic/claude-3-haiku", "Claude 3 Haiku", "anthropic", 200000, 0.25), rank: 3, score: 94, metrics: { cost_per_1m: "$0.25" } },
    { model: mockModel("google/gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1000000, 0.3), rank: 4, score: 90, metrics: { cost_per_1m: "$0.30" } },
    { model: mockModel("openai/gpt-4o-mini", "GPT-4o Mini", "openai", 128000, 0.6), rank: 5, score: 80, metrics: { cost_per_1m: "$0.60" } },
  ],
}

type DimensionKey = keyof typeof MOCK_RANKINGS

export async function GET(
  request: Request,
  { params }: { params: Promise<{ dimension: string }> }
) {
  const { dimension } = await params
  
  // Return mock data in proper RankedModel format
  const rankings = MOCK_RANKINGS[dimension as DimensionKey] || MOCK_RANKINGS.leaderboard
  
  return NextResponse.json({
    dimension,
    time_range: "7d",
    models: rankings,
    count: rankings.length,
    data_source: "OpenRouter Rankings (derived)",
    generated_at: new Date().toISOString(),
    metric_definitions: {
      score: "Overall ranking score",
      tokens: "Total tokens processed",
      share: "Market share percentage",
      change: "Week-over-week change",
    },
  })
}
