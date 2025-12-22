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

// Provider logo paths - all hosted locally in /public/logos/ for reliability
// Full color, high quality logos
const PROVIDER_LOGOS: Record<string, string> = {
  // LLMHive / Orchestrator
  orchestrator: "/logos/llmhive.png",
  llmhive: "/logos/llmhive.png",
  automatic: "/logos/llmhive.png",
  
  // OpenAI
  openai: "/logos/openai.svg",
  "gpt-4": "/logos/openai.svg",
  "gpt-4o": "/logos/openai.svg",
  "gpt-4.5": "/logos/openai.svg",
  "gpt-5": "/logos/openai.svg",
  "o1": "/logos/openai.svg",
  "o3": "/logos/openai.svg",
  "chatgpt": "/logos/openai.svg",
  
  // Anthropic / Claude
  anthropic: "/logos/anthropic.png",
  claude: "/logos/anthropic.png",
  "claude-3": "/logos/anthropic.png",
  "claude-sonnet": "/logos/anthropic.png",
  "claude-opus": "/logos/anthropic.png",
  "claude-haiku": "/logos/anthropic.png",
  
  // Google / Gemini
  google: "/logos/google.svg",
  gemini: "/logos/google.svg",
  "gemini-pro": "/logos/google.svg",
  "gemini-flash": "/logos/google.svg",
  "gemini-2": "/logos/google.svg",
  palm: "/logos/google.svg",
  
  // xAI / Grok
  xai: "/logos/xai.png",
  "x-ai": "/logos/xai.png",
  grok: "/logos/xai.png",
  "grok-2": "/logos/xai.png",
  "grok-3": "/logos/xai.png",
  
  // DeepSeek
  deepseek: "/logos/deepseek.svg",
  "deepseek-v3": "/logos/deepseek.svg",
  "deepseek-r1": "/logos/deepseek.svg",
  "deepseek-chat": "/logos/deepseek.svg",
  "deepseek-coder": "/logos/deepseek.svg",
  
  // Meta / Llama
  meta: "/logos/meta.svg",
  "meta-llama": "/logos/meta.svg",
  llama: "/logos/meta.svg",
  "llama-3": "/logos/meta.svg",
  "llama-4": "/logos/meta.svg",
  "llama3": "/logos/meta.svg",
  
  // Mistral
  mistralai: "/logos/mistral.png",
  mistral: "/logos/mistral.png",
  "mistral-large": "/logos/mistral.png",
  "mistral-medium": "/logos/mistral.png",
  "mistral-small": "/logos/mistral.png",
  codestral: "/logos/mistral.png",
  mixtral: "/logos/mistral.png",
  pixtral: "/logos/mistral.png",
  
  // Cohere
  cohere: "/logos/cohere.png",
  command: "/logos/cohere.png",
  "command-r": "/logos/cohere.png",
  "command-a": "/logos/cohere.png",
  
  // Perplexity
  perplexity: "/logos/perplexity.svg",
  "pplx": "/logos/perplexity.svg",
  "sonar": "/logos/perplexity.svg",
  
  // Qwen / Alibaba
  qwen: "/logos/alibaba.svg",
  alibaba: "/logos/alibaba.svg",
  "qwen-2": "/logos/alibaba.svg",
  "qwen2": "/logos/alibaba.svg",
  "qwen-max": "/logos/alibaba.svg",
  
  // Microsoft / Azure
  microsoft: "/logos/microsoft.png",
  azure: "/logos/microsoft.png",
  phi: "/logos/microsoft.png",
  "phi-3": "/logos/microsoft.png",
  "phi-4": "/logos/microsoft.png",
  orca: "/logos/microsoft.png",
  wizardlm: "/logos/microsoft.png",
  
  // Amazon
  amazon: "/logos/amazon.png",
  aws: "/logos/amazon.png",
  titan: "/logos/amazon.png",
  nova: "/logos/amazon.png",
  
  // Nvidia
  nvidia: "/logos/nvidia.svg",
  nemotron: "/logos/nvidia.svg",
  
  // Groq (inference platform)
  groq: "/logos/groq.png",
  
  // Together AI
  together: "/logos/together.png",
  "togethercomputer": "/logos/together.png",
  
  // Replicate
  replicate: "/logos/replicate.png",
  
  // Fireworks
  fireworks: "/logos/fireworks.png",
  "fireworks-ai": "/logos/fireworks.png",
  
  // AI21 Labs
  ai21: "/logos/ai21.png",
  jamba: "/logos/ai21.png",
  jurassic: "/logos/ai21.png",
  
  // Hugging Face
  huggingface: "/logos/huggingface.svg",
  "hugging-face": "/logos/huggingface.svg",
  hf: "/logos/huggingface.svg",
  
  // Cerebras
  cerebras: "/logos/cerebras.png",
  
  // Lepton
  lepton: "/logos/lepton.png",
  
  // Anyscale
  anyscale: "/logos/anyscale.png",
  
  // Other common model names
  yi: "/logos/alibaba.svg",  // Yi models (01.AI)
  databricks: "/logos/unknown.svg",
  dbrx: "/logos/unknown.svg",
  nousresearch: "/logos/unknown.svg",
  nous: "/logos/unknown.svg",
  hermes: "/logos/unknown.svg",
  dolphin: "/logos/unknown.svg",
  openchat: "/logos/unknown.svg",
  teknium: "/logos/unknown.svg",
  "01-ai": "/logos/alibaba.svg",
  inflection: "/logos/unknown.svg",
}

export function getModelLogo(providerOrModelId: string): string {
  if (!providerOrModelId) return "/logos/unknown.svg"
  
  // Normalize to lowercase
  const normalized = providerOrModelId.toLowerCase().trim()
  
  // Direct match
  if (PROVIDER_LOGOS[normalized]) {
    return PROVIDER_LOGOS[normalized]
  }
  
  // Extract provider from model ID (e.g., "openai/gpt-4o" -> "openai")
  const parts = normalized.split('/')
  const provider = parts[0]
  if (PROVIDER_LOGOS[provider]) {
    return PROVIDER_LOGOS[provider]
  }
  
  // Check model name part (e.g., "openai/gpt-4o" -> "gpt-4o")
  if (parts.length > 1) {
    const modelName = parts[1]
    // Check for known model prefixes
    for (const [key, url] of Object.entries(PROVIDER_LOGOS)) {
      if (modelName.startsWith(key) || modelName.includes(key)) {
        return url
      }
    }
  }
  
  // Try partial match on whole string
  for (const [key, url] of Object.entries(PROVIDER_LOGOS)) {
    if (normalized.includes(key)) {
      return url
    }
  }
  
  // Return placeholder for unknown providers
  return "/logos/unknown.svg"
}
