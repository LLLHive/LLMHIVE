import type { Model } from "./types"

export const AVAILABLE_MODELS: Model[] = [
  // OpenAI Models
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
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    description: "Anthropic's latest and most capable model",
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
]

/**
 * Normalize API model name to frontend model ID.
 * Maps full API names to our simplified frontend IDs.
 */
function normalizeModelId(apiModelName: string): string {
  const name = apiModelName.toLowerCase()
  
  // OpenAI models
  if (name.includes("gpt-4o-mini") || name.includes("gpt-4-mini")) {
    return "gpt-4o-mini"
  }
  if (name.includes("gpt-4o") || name.includes("gpt-4")) {
    return "gpt-4o"
  }
  
  // Claude models - map full API names to simplified IDs
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
  if (name.includes("grok-2") || name.includes("grok")) {
    return "grok-2"
  }
  
  // DeepSeek models
  if (name.includes("deepseek-chat") || name.includes("deepseek-v3") || name.includes("deepseek")) {
    return "deepseek-chat"
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

export function getModelLogo(provider: string): string {
  const logos: Record<string, string> = {
    openai: "https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg",
    anthropic: "/claude-logo.png",
    google: "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg",
    xai: "/grok-logo.png",
    deepseek: "/deepseek-logo.svg",
    meta: "https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg",
  }
  return logos[provider] || ""
}
