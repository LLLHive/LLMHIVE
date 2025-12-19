/**
 * Provider Logo Resolver
 * 
 * Central utility for resolving provider logos with fallback support.
 * Used by all UI components that display model/provider information.
 */

// =============================================================================
// Logo Mappings
// =============================================================================

/**
 * Primary provider logo mapping
 * Keys are normalized provider/author names (lowercase)
 */
const PROVIDER_LOGOS: Record<string, string> = {
  // Major providers with local assets
  openai: '/logos/openai.svg',
  anthropic: '/logos/anthropic.svg',
  google: '/logos/google.svg',
  'x-ai': '/logos/xai.svg',
  xai: '/logos/xai.svg',
  deepseek: '/logos/deepseek.svg',
  meta: '/logos/meta.svg',
  'meta-llama': '/logos/meta.svg',
  mistralai: '/logos/mistral.svg',
  mistral: '/logos/mistral.svg',
  qwen: '/logos/qwen.svg',
  nvidia: '/logos/nvidia.svg',
  cohere: '/logos/cohere.svg',
  
  // Fallbacks using existing public assets
  grok: '/grok-logo.png',
  claude: '/claude-logo.png',
  
  // LLMHive internal
  orchestrator: '/logo.png',
  llmhive: '/logo.png',
}

/**
 * External logo URLs for providers without local assets
 * These are CDN URLs for well-known provider logos
 */
const EXTERNAL_LOGOS: Record<string, string> = {
  openai: 'https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg',
  google: 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg',
  meta: 'https://upload.wikimedia.org/wikipedia/commons/7/7b/Meta_Platforms_Inc._logo.svg',
}

// =============================================================================
// Provider Colors (for fallback initials)
// =============================================================================

export const PROVIDER_COLORS: Record<string, string> = {
  openai: 'bg-green-500',
  anthropic: 'bg-orange-500',
  google: 'bg-blue-500',
  'x-ai': 'bg-gray-800',
  xai: 'bg-gray-800',
  deepseek: 'bg-blue-600',
  meta: 'bg-blue-700',
  'meta-llama': 'bg-blue-700',
  mistralai: 'bg-orange-600',
  mistral: 'bg-orange-600',
  qwen: 'bg-purple-600',
  nvidia: 'bg-green-600',
  cohere: 'bg-pink-500',
  perplexity: 'bg-cyan-500',
  groq: 'bg-yellow-500',
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Normalize a provider/author name for lookup
 */
function normalizeProvider(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[-_\s]/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

/**
 * Extract provider from a model ID (e.g., "openai/gpt-4o" -> "openai")
 */
export function extractProvider(modelId: string): string {
  const parts = modelId.split('/')
  return parts.length > 1 ? parts[0] : modelId
}

/**
 * Get the initial letter(s) for a provider name
 */
export function getProviderInitials(provider: string): string {
  const normalized = normalizeProvider(provider)
  
  // Special cases
  if (normalized.includes('openai')) return 'OA'
  if (normalized.includes('anthropic')) return 'A'
  if (normalized.includes('google')) return 'G'
  if (normalized.includes('meta')) return 'M'
  if (normalized.includes('deepseek')) return 'DS'
  if (normalized.includes('mistral')) return 'Mi'
  if (normalized.includes('x-ai') || normalized.includes('xai')) return 'X'
  
  // Default: first 1-2 characters
  const clean = provider.replace(/[^a-zA-Z]/g, '')
  return clean.slice(0, 2).toUpperCase() || '?'
}

/**
 * Get the background color class for a provider
 */
export function getProviderColor(provider: string): string {
  const normalized = normalizeProvider(provider)
  
  for (const [key, color] of Object.entries(PROVIDER_COLORS)) {
    if (normalized.includes(key)) {
      return color
    }
  }
  
  // Generate a consistent color from the provider name
  const hash = normalized.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc)
  }, 0)
  
  const colors = [
    'bg-red-500', 'bg-orange-500', 'bg-amber-500', 'bg-yellow-500',
    'bg-lime-500', 'bg-green-500', 'bg-emerald-500', 'bg-teal-500',
    'bg-cyan-500', 'bg-sky-500', 'bg-blue-500', 'bg-indigo-500',
    'bg-violet-500', 'bg-purple-500', 'bg-fuchsia-500', 'bg-pink-500',
  ]
  
  return colors[Math.abs(hash) % colors.length]
}

// =============================================================================
// Main Logo Resolver
// =============================================================================

export interface LogoResult {
  src: string | null
  isLocal: boolean
  isExternal: boolean
  fallbackInitials: string
  fallbackColor: string
}

/**
 * Resolve a logo for a provider/author name
 * 
 * @param provider - Provider or author name (e.g., "openai", "anthropic/claude-3")
 * @param options - Options for resolution
 * @returns LogoResult with src, fallback info
 * 
 * @example
 * const logo = resolveProviderLogo("openai")
 * // logo.src = "/logos/openai.svg"
 * 
 * @example
 * const logo = resolveProviderLogo("unknown-provider")
 * // logo.src = null
 * // logo.fallbackInitials = "UN"
 * // logo.fallbackColor = "bg-purple-500"
 */
export function resolveProviderLogo(
  provider: string,
  options: {
    preferExternal?: boolean
    modelId?: string
  } = {}
): LogoResult {
  const { preferExternal = false, modelId } = options
  
  // Try to extract provider from modelId if provider is empty
  const effectiveProvider = provider || (modelId ? extractProvider(modelId) : '')
  const normalized = normalizeProvider(effectiveProvider)
  
  // Look up in local logos
  let localLogo: string | undefined
  for (const [key, src] of Object.entries(PROVIDER_LOGOS)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      localLogo = src
      break
    }
  }
  
  // Look up in external logos
  let externalLogo: string | undefined
  for (const [key, src] of Object.entries(EXTERNAL_LOGOS)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      externalLogo = src
      break
    }
  }
  
  // Determine which to use
  const src = preferExternal 
    ? (externalLogo || localLogo || null)
    : (localLogo || externalLogo || null)
  
  return {
    src,
    isLocal: !!localLogo && src === localLogo,
    isExternal: !!externalLogo && src === externalLogo,
    fallbackInitials: getProviderInitials(effectiveProvider),
    fallbackColor: getProviderColor(effectiveProvider),
  }
}

/**
 * Get just the logo URL for a provider (convenience function)
 */
export function getProviderLogoUrl(provider: string): string | null {
  return resolveProviderLogo(provider).src
}

/**
 * Check if we have a logo for a provider
 */
export function hasProviderLogo(provider: string): boolean {
  return resolveProviderLogo(provider).src !== null
}

