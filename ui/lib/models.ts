import type { Model } from "./types"

export const AVAILABLE_MODELS: Model[] = [
  {
    id: "gpt-5",
    name: "GPT-5",
    provider: "openai",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "gpt-5-mini",
    name: "GPT-5 Mini",
    provider: "openai",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "claude-sonnet-4.5",
    name: "Claude Sonnet 4.5",
    provider: "anthropic",
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: false,
      reasoning: true,
    },
  },
  {
    id: "claude-haiku-4",
    name: "Claude Haiku 4",
    provider: "anthropic",
    capabilities: {
      vision: true,
      codeExecution: false,
      webSearch: false,
      reasoning: false,
    },
  },
  {
    id: "grok-4",
    name: "Grok 4",
    provider: "xai",
    capabilities: {
      vision: true,
      codeExecution: false,
      webSearch: true,
      reasoning: true,
    },
  },
  {
    id: "grok-4-fast",
    name: "Grok 4 Fast",
    provider: "xai",
    capabilities: {
      vision: true,
      codeExecution: false,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
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
    capabilities: {
      vision: true,
      codeExecution: true,
      webSearch: true,
      reasoning: false,
    },
  },
  {
    id: "llama-4-405b",
    name: "Llama 4 405B",
    provider: "meta",
    capabilities: {
      vision: false,
      codeExecution: false,
      webSearch: false,
      reasoning: false,
    },
  },
]

export function getModelById(id: string): Model | undefined {
  return AVAILABLE_MODELS.find((model) => model.id === id)
}

export function getModelsByProvider(provider: string): Model[] {
  return AVAILABLE_MODELS.filter((model) => model.provider === provider)
}

export function getModelLogo(provider: string): string {
  const logos: Record<string, string> = {
    openai: "https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg",
    anthropic: "/claude-logo.png",
    google: "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg",
    xai: "/grok-logo.png",
    meta: "https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg",
  }
  return logos[provider] || ""
}
