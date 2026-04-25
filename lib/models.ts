import type { Model } from "./types"

/**
 * Curated models for chat header / toolbar dropdowns.
 * IDs are OpenRouter slugs (provider/model) so the orchestrator receives the same
 * identifiers as category rankings and the Python stack, except `automatic`.
 */
export const AVAILABLE_MODELS: Model[] = [
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
  {
    id: "openai/gpt-5.4-pro",
    name: "GPT-5.4 Pro",
    provider: "openai",
    description: "OpenAI’s top GPT-5.4 tier on OpenRouter for the hardest agent and reasoning workloads",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.4",
    name: "GPT-5.4",
    provider: "openai",
    description: "Full GPT-5.4 flagship on OpenRouter with strong multimodal and tool use",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.4-mini",
    name: "GPT-5.4 Mini",
    provider: "openai",
    description: "Lower-cost GPT-5.4 class model for high-volume tasks",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.5-pro",
    name: "GPT-5.5 Pro",
    provider: "openai",
    description: "OpenAI’s top GPT-5.5 tier on OpenRouter — long context, tools, and multimodal",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.5",
    name: "GPT-5.5",
    provider: "openai",
    description: "OpenAI GPT-5.5 on OpenRouter — flagship-class general, coding, and agent workloads",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.2-pro",
    name: "GPT-5.2 Pro",
    provider: "openai",
    description: "OpenAI flagship for hardest reasoning and production workloads",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.2",
    name: "GPT-5.2",
    provider: "openai",
    description: "High-capability general model with strong multimodal support",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-5.2-codex",
    name: "GPT-5.2 Codex",
    provider: "openai",
    description: "Coding-optimized GPT-5.2 variant",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/o3",
    name: "OpenAI o3",
    provider: "openai",
    description: "Deep reasoning specialist",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/o1-pro",
    name: "o1 Pro",
    provider: "openai",
    description: "Extended thinking for math, logic, and long chains",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/o4-mini",
    name: "o4-mini",
    provider: "openai",
    description: "Fast OpenAI reasoning at lower cost",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    description: "Proven multimodal flagship",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "openai/gpt-4o-mini",
    name: "GPT-4o Mini",
    provider: "openai",
    description: "Fast, cost-efficient OpenAI model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "anthropic/claude-opus-4.7",
    name: "Claude Opus 4.7",
    provider: "anthropic",
    description: "Anthropic’s latest Opus on OpenRouter for maximum quality on long, difficult tasks",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "anthropic/claude-opus-4.5",
    name: "Claude Opus 4.5",
    provider: "anthropic",
    description: "Anthropic’s strongest model for complex analysis and writing",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "anthropic/claude-sonnet-4.6",
    name: "Claude Sonnet 4.6",
    provider: "anthropic",
    description: "Newer Sonnet generation on OpenRouter with improved coding and reasoning",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "anthropic/claude-sonnet-4.5",
    name: "Claude Sonnet 4.5",
    provider: "anthropic",
    description: "Best balance of speed, quality, and coding",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "anthropic/claude-haiku-4.5",
    name: "Claude Haiku 4.5",
    provider: "anthropic",
    description: "Low-latency Claude for high-throughput workflows",
    capabilities: {
      vision: true,
      codeExecution: false,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "google/gemini-3.1-pro-preview",
    name: "Gemini 3.1 Pro",
    provider: "google",
    description: "Google’s latest long-context multimodal flagship (preview)",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "google/gemini-3.1-flash-lite-preview",
    name: "Gemini 3.1 Flash Lite",
    provider: "google",
    description: "Low-cost Gemini 3.1 flash-lite preview on OpenRouter",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "google/gemini-3-flash-preview",
    name: "Gemini 3 Flash",
    provider: "google",
    description: "Fast Gemini 3-class model for everyday tasks",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "google/gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
    description: "Stable, high-quality Google multimodal model",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "google/gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    provider: "google",
    description: "Very fast Gemini for latency-sensitive use",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "deepseek/deepseek-v3.2",
    name: "DeepSeek V3.2",
    provider: "deepseek",
    description: "Excellent coding and math at aggressive pricing",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "deepseek/deepseek-r1-0528",
    name: "DeepSeek R1",
    provider: "deepseek",
    description: "Open-style reasoning model competitive with o-series",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "deepseek/deepseek-v4-pro",
    name: "DeepSeek V4 Pro",
    provider: "deepseek",
    description: "DeepSeek V4 flagship on OpenRouter — strong agent, math, and coding",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "deepseek/deepseek-v4-flash",
    name: "DeepSeek V4 Flash",
    provider: "deepseek",
    description: "Fast, cost-efficient DeepSeek V4 tier for high-volume coding and math",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "x-ai/grok-4",
    name: "Grok 4",
    provider: "xai",
    description: "xAI flagship with strong real-time and general knowledge",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "x-ai/grok-4-fast",
    name: "Grok 4 Fast",
    provider: "xai",
    description: "Faster xAI Grok 4 variant on OpenRouter for latency-sensitive workloads",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "x-ai/grok-4.1-fast",
    name: "Grok 4.1 Fast",
    provider: "xai",
    description: "Lower-latency Grok for interactive workloads",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "x-ai/grok-4.20",
    name: "Grok 4.2",
    provider: "xai",
    description: "xAI Grok 4.20 on OpenRouter (marketed as Grok 4.2-class flagship)",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "meta-llama/llama-4-maverick",
    name: "Llama 4 Maverick",
    provider: "meta",
    description: "Meta’s latest open-weights class model on OpenRouter",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "meta-llama/llama-4-scout",
    name: "Llama 4 Scout",
    provider: "meta",
    description: "Meta Llama 4 Scout on OpenRouter — efficient long-context variant",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "moonshotai/kimi-k2.6",
    name: "Kimi K2.6",
    provider: "moonshot",
    description: "Moonshot Kimi K2.6 on OpenRouter — long-context agent and coding",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "qwen/qwen3.6-plus",
    name: "Qwen3.6 Plus",
    provider: "qwen",
    description: "Qwen 3.6 Plus on OpenRouter for multilingual STEM and coding",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "qwen/qwen3-max",
    name: "Qwen3 Max",
    provider: "qwen",
    description: "Alibaba flagship for multilingual and STEM tasks",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "mistralai/mistral-large-2512",
    name: "Mistral Large 2512",
    provider: "mistralai",
    description: "Mistral’s latest large instruct model",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "mistralai/mistral-medium-3.1",
    name: "Mistral Medium 3.1",
    provider: "mistralai",
    description: "Mistral Medium 3.1 on OpenRouter — balanced quality and cost",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "z-ai/glm-4.7",
    name: "GLM 4.7",
    provider: "zhipu",
    description: "Zhipu GLM 4.7 on OpenRouter for math, coding, and multilingual tasks",
    capabilities: {
      vision: false,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
]

/**
 * Normalize saved or API model identifiers to canonical OpenRouter IDs
 * (or `automatic`) for lookup in AVAILABLE_MODELS.
 */
function normalizeModelId(apiModelName: string): string {
  const raw = apiModelName.trim()
  const name = raw.toLowerCase()

  if (name === "automatic" || name === "orchestrator") {
    return "automatic"
  }

  // Already using OpenRouter-style IDs
  if (
    name.startsWith("openai/") ||
    name.startsWith("anthropic/") ||
    name.startsWith("google/") ||
    name.startsWith("deepseek/") ||
    name.startsWith("x-ai/") ||
    name.startsWith("meta-llama/") ||
    name.startsWith("qwen/") ||
    name.startsWith("mistralai/") ||
    name.startsWith("moonshotai/") ||
    name.startsWith("z-ai/")
  ) {
    return raw
  }

  // Legacy short IDs and older UI labels → OpenRouter
  if (name.includes("o1-pro") || name.includes("o1pro")) return "openai/o1-pro"
  if (name.includes("o3-mini") || name.includes("o3mini")) return "openai/o3-mini"
  if (name.includes("o4-mini")) return "openai/o4-mini"
  if (name === "o1" || (name.includes("o1") && !name.includes("o1-pro"))) return "openai/o1"
  if (name.includes("o3")) return "openai/o3"

  if (name.includes("gpt-5.5-pro") || name.includes("gpt-5-5-pro")) return "openai/gpt-5.5-pro"
  if (name.includes("gpt-5.5")) return "openai/gpt-5.5"
  if (name.includes("gpt-5.4-pro") || name.includes("gpt-5-4-pro")) return "openai/gpt-5.4-pro"
  if (name.includes("gpt-5.4-mini") || name.includes("gpt-5-4-mini")) return "openai/gpt-5.4-mini"
  if (name.includes("gpt-5.4")) return "openai/gpt-5.4"
  if (name.includes("gpt-5.2-pro") || name.includes("gpt-5-2-pro")) return "openai/gpt-5.2-pro"
  if (name.includes("gpt-5.2-codex") || name.includes("gpt-5-2-codex")) return "openai/gpt-5.2-codex"
  if (name.includes("gpt-5.2")) return "openai/gpt-5.2"
  if (name.includes("gpt-5.1")) return "openai/gpt-5.1"
  if (name.includes("gpt-5")) return "openai/gpt-5"

  if (name.includes("gpt-4o-mini") || name.includes("gpt-4-mini")) return "openai/gpt-4o-mini"
  if (name.includes("gpt-4o") || name === "gpt-4") return "openai/gpt-4o"
  if (name.includes("gpt-4.5") || name.includes("gpt-4-5")) return "openai/gpt-4o"

  if (name.includes("claude-opus-4.7")) return "anthropic/claude-opus-4.7"
  if (name.includes("claude-opus-4.5")) return "anthropic/claude-opus-4.5"
  if (name.includes("claude-opus-4")) return "anthropic/claude-opus-4"
  if (name.includes("claude-sonnet-4.6")) return "anthropic/claude-sonnet-4.6"
  if (name.includes("claude-sonnet-4.5")) return "anthropic/claude-sonnet-4.5"
  if (name.includes("claude-sonnet-4")) return "anthropic/claude-sonnet-4"
  if (name.includes("claude-haiku-4.5")) return "anthropic/claude-haiku-4.5"
  if (name.includes("claude-haiku") || name.includes("claude-3.5-haiku") || name.includes("claude-3.5-haiku")) {
    return "anthropic/claude-haiku-4.5"
  }
  if (name.includes("claude-3-5-sonnet") || name.includes("claude-sonnet")) {
    return "anthropic/claude-sonnet-4"
  }

  if (name.includes("gemini-3.1-flash-lite") || name.includes("gemini 3.1 flash lite")) {
    return "google/gemini-3.1-flash-lite-preview"
  }
  if (name.includes("gemini-3.1")) return "google/gemini-3.1-pro-preview"
  if (name.includes("gemini-3-flash")) return "google/gemini-3-flash-preview"
  if (name.includes("gemini-3")) return "google/gemini-3.1-pro-preview"
  if (name.includes("gemini-2.5-flash")) return "google/gemini-2.5-flash"
  if (name.includes("gemini-2.5-pro") || name.includes("gemini-pro") || name.includes("gemini-2.5")) {
    return "google/gemini-2.5-pro"
  }

  if (name.includes("grok-4.2") || name.includes("grok-4.20") || name.includes("grok-420"))
    return "x-ai/grok-4.20"
  if (name.includes("grok-4-fast") || name.includes("grok 4 fast")) return "x-ai/grok-4-fast"
  if (name.includes("grok-4.1")) return "x-ai/grok-4.1-fast"
  if (name.includes("grok-4")) return "x-ai/grok-4"
  if (name.includes("grok-3") || name.includes("grok3")) return "x-ai/grok-4"
  if (name.includes("grok-2") || name.includes("grok")) return "x-ai/grok-4"

  if (name.includes("deepseek-r1")) return "deepseek/deepseek-r1-0528"
  if (name.includes("deepseek-v4-pro") || name.includes("deepseek v4 pro")) return "deepseek/deepseek-v4-pro"
  if (name.includes("deepseek-v4-flash") || name.includes("deepseek v4 flash")) {
    return "deepseek/deepseek-v4-flash"
  }
  if (
    name.includes("deepseek-v3.2") ||
    name.includes("deepseek-chat") ||
    (name.includes("deepseek") && !name.includes("v4"))
  ) {
    return "deepseek/deepseek-v3.2"
  }

  if (name.includes("llama-4-scout") || (name.includes("scout") && name.includes("llama-4"))) {
    return "meta-llama/llama-4-scout"
  }
  if (name.includes("llama-4")) return "meta-llama/llama-4-maverick"
  if (name.includes("llama-3.3") || name.includes("llama-3-3") || name.includes("llama3.3")) {
    return "meta-llama/llama-4-maverick"
  }

  if (name.includes("qwen3.6") || name.includes("qwen 3.6")) return "qwen/qwen3.6-plus"
  if (name.includes("qwen3") || name.includes("qwen-3")) return "qwen/qwen3-max"

  if (name.includes("kimi-k2.6") || name.includes("kimi k2.6")) return "moonshotai/kimi-k2.6"
  if (name.includes("kimi-k2.5") || name.includes("kimi k2.5")) return "moonshotai/kimi-k2.5"
  if (name.includes("kimi-k2-thinking") || name.includes("kimi k2 thinking")) {
    return "moonshotai/kimi-k2-thinking"
  }
  if (name.includes("kimi-k2") || name.includes("kimi k2")) return "moonshotai/kimi-k2"

  if (name.includes("glm-4.7") || name.includes("glm 4.7")) return "z-ai/glm-4.7"

  if (name.includes("mistral-medium-3.1") || name.includes("mistral medium 3.1")) {
    return "mistralai/mistral-medium-3.1"
  }
  if (name.includes("mistral-large")) return "mistralai/mistral-large-2512"

  return raw
}

export function getModelById(id: string): Model | undefined {
  const exactMatch = AVAILABLE_MODELS.find((model) => model.id === id)
  if (exactMatch) return exactMatch

  const normalizedId = normalizeModelId(id)
  return AVAILABLE_MODELS.find((model) => model.id === normalizedId)
}

export function getModelsByProvider(provider: string): Model[] {
  return AVAILABLE_MODELS.filter((model) => model.provider === provider)
}

/**
 * Get display-friendly model name from any API model identifier.
 */
export function getModelDisplayName(apiModelName: string): string {
  const model = getModelById(apiModelName)
  if (model) return model.name

  const cleaned = apiModelName.replace(/:free$/i, "").replace(/-\d{8}$/, "")
  if (cleaned.includes("/")) {
    const slug = cleaned.split("/").slice(1).join("/")
    return slug
      .split(/[-_]/g)
      .filter(Boolean)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ")
  }

  return cleaned
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
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
  o1: "/logos/openai.svg",
  o3: "/logos/openai.svg",
  chatgpt: "/logos/openai.svg",

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
  llama3: "/logos/meta.svg",

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
  pplx: "/logos/perplexity.svg",
  sonar: "/logos/perplexity.svg",

  // Qwen / Alibaba
  qwen: "/logos/alibaba.svg",
  alibaba: "/logos/alibaba.svg",

  // Moonshot (Kimi) — dedicated asset can replace unknown.svg later
  moonshot: "/logos/unknown.svg",
  moonshotai: "/logos/unknown.svg",
  kimi: "/logos/unknown.svg",

  // Zhipu (GLM)
  zhipu: "/logos/unknown.svg",
  "z-ai": "/logos/unknown.svg",
  glm: "/logos/unknown.svg",
  "qwen-2": "/logos/alibaba.svg",
  qwen2: "/logos/alibaba.svg",
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
  togethercomputer: "/logos/together.png",

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
  yi: "/logos/alibaba.svg", // Yi models (01.AI)
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

  const normalized = providerOrModelId.toLowerCase().trim()

  if (PROVIDER_LOGOS[normalized]) {
    return PROVIDER_LOGOS[normalized]
  }

  const parts = normalized.split("/")
  const provider = parts[0]
  if (PROVIDER_LOGOS[provider]) {
    return PROVIDER_LOGOS[provider]
  }

  if (parts.length > 1) {
    const modelName = parts[1]
    for (const [key, url] of Object.entries(PROVIDER_LOGOS)) {
      if (modelName.startsWith(key) || modelName.includes(key)) {
        return url
      }
    }
  }

  for (const [key, url] of Object.entries(PROVIDER_LOGOS)) {
    if (normalized.includes(key)) {
      return url
    }
  }

  return "/logos/unknown.svg"
}
