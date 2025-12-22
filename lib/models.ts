import type { Model } from "./types"

export const AVAILABLE_MODELS: Model[] = [
  // Automatic - Let the orchestrator decide
  {
    id: "automatic",
    name: "Automatic",
    provider: "orchestrator",
    description: "Let the orchestrator select the best models for your task",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  // OpenAI Models
  {
    id: "o1",
    name: "o1",
    provider: "openai",
    description: "OpenAI's most advanced reasoning model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "o1-pro",
    name: "o1 Pro",
    provider: "openai",
    description: "o1 with extended thinking for complex problems",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "o3-mini",
    name: "o3 Mini",
    provider: "openai",
    description: "Fast reasoning model with high efficiency",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "gpt-4.5-preview",
    name: "GPT-4.5 Preview",
    provider: "openai",
    description: "Next-gen GPT with enhanced capabilities",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    description: "OpenAI's flagship multimodal model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "gpt-4o-mini",
    name: "GPT-4o Mini",
    provider: "openai",
    description: "Fast and cost-effective OpenAI model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  // Anthropic Claude Models
  {
    id: "claude-opus-4",
    name: "Claude Opus 4",
    provider: "anthropic",
    description: "Anthropic's most powerful model for complex tasks",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    description: "Best balance of speed and intelligence",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "claude-3.5-haiku",
    name: "Claude 3.5 Haiku",
    provider: "anthropic",
    description: "Fast and efficient Claude model",
    capabilities: {
      vision: true,
      codeExecution: false,
      webSearch: false,
      reasoning: false,
    },
  },
  // xAI Grok Models
  {
    id: "grok-3",
    name: "Grok 3",
    provider: "xai",
    description: "xAI's most advanced model with real-time knowledge",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "grok-2",
    name: "Grok 2",
    provider: "xai",
    description: "xAI's conversational AI with real-time knowledge",
    capabilities: {
      vision: true,
      codeExecution: false,
      webSearch: true,
      reasoning: true,
    },
  },
  // Google Gemini Models
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
    description: "Google's most capable multimodal model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    provider: "google",
    description: "Fast and efficient Gemini model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  // DeepSeek Models
  {
    id: "deepseek-r1",
    name: "DeepSeek R1",
    provider: "deepseek",
    description: "Advanced reasoning model rivaling o1",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "deepseek-chat",
    name: "DeepSeek V3",
    provider: "deepseek",
    description: "DeepSeek's flagship conversational AI",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  // Meta Llama Models
  {
    id: "llama-3.3-70b",
    name: "Llama 3.3 70B",
    provider: "meta",
    description: "Meta's powerful open-source model",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
]

/**
 * Normalize API model name to frontend model ID.
 * Maps full API names to our simplified frontend IDs.
 */
function normalizeModelId(apiModelName: string): string {
  const name = apiModelName.toLowerCase()
  
  // OpenAI reasoning models (o-series)
  if (name.includes("o1-pro") || name.includes("o1pro")) {
    return "o1-pro"
  }
  if (name.includes("o3-mini") || name.includes("o3mini")) {
    return "o3-mini"
  }
  if (name.includes("o1") && !name.includes("o1-pro")) {
    return "o1"
  }
  
  // GPT models
  if (name.includes("gpt-4.5") || name.includes("gpt-4-5")) {
    return "gpt-4.5-preview"
  }
  if (name.includes("gpt-4o-mini") || name.includes("gpt-4-mini")) {
    return "gpt-4o-mini"
  }
  if (name.includes("gpt-4o") || name.includes("gpt-4")) {
    return "gpt-4o"
  }
  
  // Claude models - map full API names to simplified IDs
  if (name.includes("claude-opus-4") || name.includes("claude-4-opus")) {
    return "claude-opus-4"
  }
  if (name.includes("claude-sonnet-4") || name.includes("claude-3-5-sonnet") || name.includes("claude-sonnet")) {
    return "claude-sonnet-4"
  }
  if (name.includes("claude-haiku") || name.includes("claude-3-5-haiku") || name.includes("claude-3.5-haiku")) {
    return "claude-3.5-haiku"
  }
  
  // Gemini models
  if (name.includes("gemini-2.5-flash") || name.includes("gemini-flash")) {
    return "gemini-2.5-flash"
  }
  if (name.includes("gemini-2.5-pro") || name.includes("gemini-pro") || name.includes("gemini-2.5")) {
    return "gemini-2.5-pro"
  }
  
  // Grok models
  if (name.includes("grok-3") || name.includes("grok3")) {
    return "grok-3"
  }
  if (name.includes("grok-2") || name.includes("grok")) {
    return "grok-2"
  }
  
  // DeepSeek models
  if (name.includes("deepseek-r1") || name.includes("deepseek-reasoner")) {
    return "deepseek-r1"
  }
  if (name.includes("deepseek-chat") || name.includes("deepseek-v3") || name.includes("deepseek")) {
    return "deepseek-chat"
  }
  
  // Llama models
  if (name.includes("llama-3.3") || name.includes("llama-3-3") || name.includes("llama3.3")) {
    return "llama-3.3-70b"
  }
  
  // Return original if no mapping found
  return apiModelName
}

export function getModelById(id: string): Model | undefined {
  // First try exact match
  const exactMatch = AVAILABLE_MODELS.find((model) => model.id === id)
  if (exactMatch) return exactMatch
  
  // Try normalized match
  const normalizedId = normalizeModelId(id)
  return AVAILABLE_MODELS.find((model) => model.id === normalizedId)
}

export function getModelsByProvider(provider: string): Model[] {
  return AVAILABLE_MODELS.filter((model) => model.provider === provider)
}

/**
 * Get display-friendly model name from any API model identifier.
 * Always returns a nice UI name, falling back to a formatted version of the ID.
 */
export function getModelDisplayName(apiModelName: string): string {
  const model = getModelById(apiModelName)
  if (model) return model.name
  
  // Format the API name to be more readable
  // e.g., "claude-sonnet-4-20250514" -> "Claude Sonnet 4"
  return apiModelName
    .replace(/-\d{8}$/, '') // Remove date suffix like -20250514
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Provider logo URLs - high quality, full color
const PROVIDER_LOGOS: Record<string, string> = {
  // LLMHive
  orchestrator: "/logo.png",
  llmhive: "/logo.png",
  automatic: "/logo.png",
  
  // OpenAI
  openai: "https://cdn.openai.com/API/images/openai-logo.svg",
  
  // Anthropic
  anthropic: "https://www.anthropic.com/images/icons/apple-touch-icon.png",
  claude: "https://www.anthropic.com/images/icons/apple-touch-icon.png",
  
  // Google
  google: "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg",
  gemini: "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg",
  
  // xAI / Grok
  xai: "https://x.ai/favicon.ico",
  "x-ai": "https://x.ai/favicon.ico",
  grok: "https://x.ai/favicon.ico",
  
  // DeepSeek
  deepseek: "https://chat.deepseek.com/favicon.ico",
  
  // Meta / Llama
  meta: "https://llama.meta.com/favicon.ico",
  "meta-llama": "https://llama.meta.com/favicon.ico",
  llama: "https://llama.meta.com/favicon.ico",
  
  // Mistral
  mistralai: "https://mistral.ai/images/favicon.ico",
  mistral: "https://mistral.ai/images/favicon.ico",
  
  // Cohere
  cohere: "https://cohere.com/favicon.ico",
  
  // Perplexity
  perplexity: "https://www.perplexity.ai/favicon.ico",
  
  // Qwen / Alibaba
  qwen: "https://qwenlm.github.io/favicon.ico",
  alibaba: "https://qwenlm.github.io/favicon.ico",
  
  // Microsoft
  microsoft: "https://www.microsoft.com/favicon.ico",
  
  // Amazon
  amazon: "https://www.amazon.com/favicon.ico",
  
  // Nvidia
  nvidia: "https://www.nvidia.com/favicon.ico",
}

export function getModelLogo(providerOrModelId: string): string {
  // Normalize to lowercase
  const normalized = providerOrModelId.toLowerCase()
  
  // Direct match
  if (PROVIDER_LOGOS[normalized]) {
    return PROVIDER_LOGOS[normalized]
  }
  
  // Extract provider from model ID (e.g., "openai/gpt-4o" -> "openai")
  const provider = normalized.split('/')[0]
  if (PROVIDER_LOGOS[provider]) {
    return PROVIDER_LOGOS[provider]
  }
  
  // Try partial match
  for (const [key, url] of Object.entries(PROVIDER_LOGOS)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return url
    }
  }
  
  // Default fallback - generic AI icon
  return ""
}
